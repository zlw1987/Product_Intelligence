// PILOT-UX-WORKBENCH-A1 layout probe (developer tool).
// Drives headless Chrome over raw CDP (global fetch + WebSocket, no deps)
// and reports, per URL x viewport:
//   - page-level horizontal overflow
//   - elements extending past the viewport without an intended
//     overflow-x:auto/scroll ancestor
//   - clipped elements (overflow hidden / ellipsis with scrollWidth > clientWidth)
//   - in-page anchor targets that do not resolve
//   - key content strings present (per case)
"use strict";

const { spawn } = require("node:child_process");
const path = require("node:path");

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PROFILE = "C:/dev/Product_Intelligence_A1/tmp_preview/chrome_cdp_profile";
const PORT = 9333;

const CASES = [
  {
    name: "intake-empty",
    url: "http://127.0.0.1:8101/research/new",
    expect: ["Run Market Research", "New research request", "Manufacturer part number", "Product description"],
    widths: [1440, 768, 390],
  },
  {
    name: "intake-prefill",
    url: "http://127.0.0.1:8101/research/new?mpn=MTFDKCC3T8TGP-1BK1DABYY&description=480GB%20NVMe%20M.2%20solid%20state%20drive",
    expect: ["MTFDKCC3T8TGP-1BK1DABYY", "480GB NVMe M.2 solid state drive"],
    widths: [1440, 390],
  },
  {
    name: "report-multiquote-allowed",
    url: "http://127.0.0.1:8101/research/edfc8bd2-1eab-4d35-afc1-1a9ba0aeba63",
    expect: [
      "Quote & Market Summary", "Ingram (Vendor API)", "CDW (Vendor API)",
      "Synnex EU (Vendor API)", "example.com", "Quotes found", "Lowest in-stock quote",
      "Comparable public market", "ECB reference date",
    ],
    widths: [1440, 768, 390],
  },
  {
    name: "report-multiquote-denied",
    url: "http://127.0.0.1:8102/research/edfc8bd2-1eab-4d35-afc1-1a9ba0aeba63",
    expect: ["Internal commercial pricing is unavailable for this connection."],
    forbid: ["Ingram (Vendor API)", "CDW (Vendor API)", "Synnex EU (Vendor API)", "$2,023.27", "$1,999.99", "1,705.35"],
    widths: [1440, 390],
  },
  {
    name: "report-zeroquote",
    url: "http://127.0.0.1:8101/research/852cea43-4e2b-4d34-94dd-09106b95e39b",
    expect: ["Source-published price: $0 USD", "Verify price and purchasing availability with the supplier."],
    widths: [1440, 390],
  },
  {
    name: "report-no-evidence",
    url: "http://127.0.0.1:8101/research/0348c883-18f2-44fb-b135-8c2247261c5e",
    expect: ["Price aggregation status:", "UNKNOWN", "Excluded listings"],
    widths: [1440, 390],
  },
  {
    name: "report-ai-review",
    url: "http://127.0.0.1:8101/research/b615ec44-62ce-4b71-a069-6b10ed467350",
    expect: ["AI-assisted evidence & review", "Possible matches", "Include", "Reject"],
    widths: [1440, 390],
  },
  {
    name: "report-comparable",
    url: "http://127.0.0.1:8101/research/e1de488c-c691-465a-b739-0ac69bdd856c",
    expect: ["Comparable products", "Target MPN", "CAND-001", "Specification comparison"],
    widths: [1440, 390],
  },
  {
    name: "report-running",
    url: "http://127.0.0.1:8101/research/338344f9-3ae6-42ce-a3b8-af637ad96b14",
    expect: ["RUNNING", "Research is currently running."],
    widths: [1440, 390],
  },
  {
    name: "report-failed",
    url: "http://127.0.0.1:8101/research/004b42c7-cd02-430f-ac01-79a2d54ef244",
    expect: ["FAILED", "Research did not complete successfully.", "Retry Research"],
    widths: [1440, 390],
  },
];

const PROBE_JS = `
() => {
  const vw = window.innerWidth;
  const doc = document.documentElement;
  const pageOverflow = doc.scrollWidth > vw + 1;
  const overflow = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width === 0) return;
    if (r.right > vw + 1) {
      let p = el.parentElement, intended = false;
      while (p) {
        const ox = getComputedStyle(p).overflowX;
        if (ox === 'auto' || ox === 'scroll') { intended = true; break; }
        p = p.parentElement;
      }
      if (!intended) {
        overflow.push(el.tagName + '.' + String(el.className).slice(0, 40) + ' right=' + Math.round(r.right));
        if (overflow.length >= 12) return;
      }
    }
  });
  const clipped = [];
  document.querySelectorAll('body *').forEach(el => {
    const cs = getComputedStyle(el);
    if ((cs.overflow === 'hidden' || cs.textOverflow === 'ellipsis') && el.scrollWidth > el.clientWidth + 1) {
      clipped.push(el.tagName + '.' + String(el.className).slice(0, 40) + ' "' + (el.textContent || '').trim().slice(0, 40) + '"');
      if (clipped.length >= 12) return;
    }
  });
  const missingAnchors = [];
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    const id = a.getAttribute('href').slice(1);
    if (id && !document.getElementById(id)) missingAnchors.push(id);
  });
  return JSON.stringify({
    vw, docScrollWidth: doc.scrollWidth, pageOverflow,
    overflow, clipped, missingAnchors,
    h1Count: document.querySelectorAll('h1').length,
    focusables: document.querySelectorAll('a, button, input, textarea, summary, [tabindex]').length,
  });
}
`;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function cdpEval(ws, expr) {
  const id = Math.floor(Math.random() * 1e9);
  await new Promise((resolve, reject) => {
    const onMsg = (ev) => {
      const msg = JSON.parse(typeof ev === "string" ? ev : ev.data);
      if (msg.id === id) {
        ws.removeEventListener("message", onMsg);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      }
    };
    ws.addEventListener("message", onMsg);
    ws.send(JSON.stringify({ id, method: "Runtime.evaluate", params: { expression: expr, returnByValue: true } }));
    setTimeout(() => reject(new Error("eval timeout")), 15000);
  });
}

async function main() {
  const chrome = spawn(
    CHROME,
    [
      "--headless=new",
      "--disable-gpu",
      "--no-first-run",
      "--no-default-browser-check",
      `--remote-debugging-port=${PORT}`,
      `--user-data-dir=${PROFILE}`,
      "about:blank",
    ],
    { stdio: "ignore" },
  );

  let targetWs = null;
  try {
    // wait for devtools endpoint
    let targets = null;
    for (let i = 0; i < 40; i++) {
      await sleep(500);
      try {
        const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
        targets = await res.json();
        if (targets && targets.length) break;
      } catch {}
    }
    if (!targets || !targets.length) throw new Error("no CDP targets");
    const page = targets.find((t) => t.type === "page");
    targetWs = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      targetWs.addEventListener("open", resolve);
      targetWs.addEventListener("error", () => reject(new Error("ws error")));
    });
    let seq = 1;
    const send = (method, params = {}) =>
      new Promise((resolve, reject) => {
        const id = seq++;
        const onMsg = (ev) => {
          const msg = JSON.parse(typeof ev === "string" ? ev : ev.data);
          if (msg.id === id) {
            targetWs.removeEventListener("message", onMsg);
            msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
          }
        };
        targetWs.addEventListener("message", onMsg);
        targetWs.send(JSON.stringify({ id, method, params }));
        setTimeout(() => reject(new Error(method + " timeout")), 20000);
      });

    const results = [];
    for (const c of CASES) {
      for (const w of c.widths) {
        const h = w === 1440 ? 900 : w === 768 ? 900 : 780;
        await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: w < 500 });
        await send("Page.enable");
        const nav = send("Page.navigate", { url: c.url });
        await nav;
        // wait for load event
        await new Promise((resolve) => {
          const onMsg = (ev) => {
            const msg = JSON.parse(typeof ev === "string" ? ev : ev.data);
            if (msg.method === "Page.loadEventFired") {
              targetWs.removeEventListener("message", onMsg);
              resolve();
            }
          };
          targetWs.addEventListener("message", onMsg);
          setTimeout(resolve, 10000);
        });
        await sleep(400);
        const body = await send("Runtime.evaluate", {
          expression: "document.body ? document.body.innerText : ''",
          returnByValue: true,
        });
        const text = body.result.value || "";
        const probeRaw = await send("Runtime.evaluate", { expression: `(${PROBE_JS})()`, returnByValue: true });
        const probe = JSON.parse(probeRaw.result.value);
        const missing = (c.expect || []).filter((s) => !text.includes(s));
        const leaked = (c.forbid || []).filter((s) => text.includes(s));
        results.push({
          case: c.name,
          width: w,
          ok: missing.length === 0 && leaked.length === 0 && !probe.pageOverflow && probe.overflow.length === 0 && probe.clipped.length === 0 && probe.missingAnchors.length === 0 && probe.h1Count === 1,
          missing,
          leaked,
          pageOverflow: probe.pageOverflow ? `docScrollWidth=${probe.docScrollWidth} > ${w}` : null,
          overflow: probe.overflow,
          clipped: probe.clipped,
          missingAnchors: probe.missingAnchors,
          h1Count: probe.h1Count,
          focusables: probe.focusables,
        });
      }
    }
    console.log(JSON.stringify(results, null, 2));
  } finally {
    if (targetWs) targetWs.close();
    chrome.kill();
  }
}

main().catch((e) => {
  console.error("PROBE FAILED:", e.message);
  process.exit(1);
});
