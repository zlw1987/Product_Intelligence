// PILOT-UX-WORKBENCH-A1 layout probe (developer tool).
// Drives headless Chrome over raw CDP (global fetch + WebSocket, no deps)
// and reports, per URL x viewport:
//   - VIEWPORT FIDELITY (FU1): the actual layout viewport must equal the
//     requested width (window.innerWidth === requested), the document must
//     be standards mode (<!DOCTYPE html> present, compatMode CSS1Compat),
//     and there must be no page-level horizontal overflow. A CSS viewport
//     that differs from the requested width FAILS the audit even when
//     document.scrollWidth == window.innerWidth — that is exactly the
//     A1 defect: the committed 390px captures were laid out wider than
//     390 CSS px, so the probe's old overflow-only checks passed while the
//     captures visibly clipped the right side of every page.
//   - elements extending past the viewport without an intended
//     overflow-x:auto/scroll ancestor
//   - clipped elements (overflow hidden / ellipsis with scrollWidth > clientWidth)
//   - in-page anchor targets that do not resolve
//   - key content strings present (per case)
//
// Run addresses come from the preview manifest written by
// scripts/preview_fixtures.py (PI_PREVIEW_DB_DIR=... python
// scripts/preview_fixtures.py): <preview-dir>/preview_urls.json. Default:
// tmp_preview/preview_urls.json next to this script's repository root.
// Two dev servers are expected: port 8101 with
// PI_VENDOR_PRICE_ALLOWED_CIDRS=127.0.0.1/32 (vendor ALLOWED) and port 8102
// without that variable (vendor DENIED, fail-closed default).
"use strict";

const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const REPO = path.resolve(__dirname, "..");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PROFILE = path.join(REPO, "tmp_preview", "chrome_cdp_profile");
const PORT = 9333;
const URLS_JSON = process.argv[2] || path.join(REPO, "tmp_preview", "preview_urls.json");

const manifest = JSON.parse(fs.readFileSync(URLS_JSON, "utf-8"));
const run = (key) => manifest.runs[key];

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
    url: `http://127.0.0.1:8101${run("multiquote")}`,
    expect: [
      "Quote & Market Summary", "Ingram (Vendor API)", "CDW (Vendor API)",
      "Synnex EU (Vendor API)", "example.com", "Quotes found", "Lowest in-stock quote",
      "Comparable public market", "ECB reference date",
    ],
    widths: [1440, 768, 390],
  },
  {
    name: "report-multiquote-denied",
    url: `http://127.0.0.1:8102${run("multiquote")}`,
    expect: ["Internal commercial pricing is unavailable for this connection."],
    forbid: ["Ingram (Vendor API)", "CDW (Vendor API)", "Synnex EU (Vendor API)", "$2,023.27", "$1,999.99", "1,705.35"],
    widths: [1440, 390],
  },
  {
    name: "report-zeroquote",
    url: `http://127.0.0.1:8101${run("zeroquote")}`,
    expect: ["Source-published price: $0 USD", "Verify price and purchasing availability with the supplier."],
    widths: [1440, 390],
  },
  {
    name: "report-no-evidence",
    url: `http://127.0.0.1:8101${run("noevidence")}`,
    expect: ["Price aggregation status:", "UNKNOWN", "Excluded listings"],
    widths: [1440, 390],
  },
  {
    name: "report-ai-review",
    url: `http://127.0.0.1:8101${run("aireview")}`,
    expect: ["AI-assisted evidence & review", "Possible matches", "Include", "Reject"],
    widths: [1440, 390],
  },
  {
    name: "report-comparable",
    url: `http://127.0.0.1:8101${run("comparable")}`,
    expect: ["Comparable products", "Target MPN", "CAND-001", "Specification comparison"],
    widths: [1440, 390],
  },
  {
    name: "report-running",
    url: `http://127.0.0.1:8101${run("running")}`,
    expect: ["RUNNING", "Research is currently running."],
    widths: [1440, 390],
  },
  {
    name: "report-failed",
    url: `http://127.0.0.1:8101${run("failed")}`,
    expect: ["FAILED", "Research did not complete successfully.", "Retry Research"],
    widths: [1440, 390],
  },
];

// The viewport-fidelity + overflow audit. `requested` is the CSS width the
// case asked for; every mismatch is a hard failure of that case.
const PROBE_JS = `
(requested) => {
  const vw = window.innerWidth;
  const doc = document.documentElement;
  const hasDoctype = !!document.doctype;
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
    requested,
    vw,
    clientWidth: doc.clientWidth,
    docScrollWidth: doc.scrollWidth,
    visualViewportWidth: window.visualViewport ? window.visualViewport.width : null,
    compatMode: document.compatMode,
    hasDoctype,
    pageOverflow,
    overflow,
    clipped,
    missingAnchors,
    h1Count: document.querySelectorAll('h1').length,
    focusables: document.querySelectorAll('a, button, input, textarea, summary, [tabindex]').length,
  });
}
`;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
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
  let failed = 0;
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
        // Make collapsed disclosure content visible before checking content
        // (innerText is render-aware; the audit cares that content EXISTS
        // and is reachable by expanding, not that it is open by default).
        await send("Runtime.evaluate", {
          expression: "document.querySelectorAll('details').forEach(d => { d.open = true; }); true",
          returnByValue: true,
        });
        await sleep(100);
        const body = await send("Runtime.evaluate", {
          // innerText + form control values (input/textarea values are not
          // part of innerText, but prefill IS the intake contract).
          expression: "(() => { const parts = []; if (document.body) parts.push(document.body.innerText); document.querySelectorAll('input, textarea').forEach(el => parts.push(el.value || '')); return parts.join('\\n'); })()",
          returnByValue: true,
        });
        const text = (body.result.value || "").toLowerCase();
        const probeRaw = await send("Runtime.evaluate", {
          expression: `(${PROBE_JS})(${w})`,
          returnByValue: true,
        });
        const probe = JSON.parse(probeRaw.result.value);

        // --- FU1 viewport-fidelity gate (hard) -------------------------
        // A CSS viewport that differs from the requested width fails the
        // audit even when document.scrollWidth == window.innerWidth: that
        // equality only proves the page is consistent at ITS width, not
        // that its width is the one under test.
        const fidelityProblems = [];
        if (!probe.hasDoctype) fidelityProblems.push("missing <!DOCTYPE html> (quirks-mode document)");
        if (probe.compatMode !== "CSS1Compat") fidelityProblems.push(`compatMode=${probe.compatMode} (not standards mode)`);
        if (probe.vw !== w) fidelityProblems.push(`layout viewport window.innerWidth=${probe.vw} != requested ${w}`);
        if (w < 500) {
          // Mobile emulation: overlay scrollbars, so the visual viewport
          // must equal the layout viewport exactly.
          if (probe.visualViewportWidth !== null && probe.visualViewportWidth !== w) {
            fidelityProblems.push(`visualViewport.width=${probe.visualViewportWidth} != requested ${w}`);
          }
        } else if (probe.visualViewportWidth !== null && (probe.visualViewportWidth < w - 16 || probe.visualViewportWidth > w)) {
          // Desktop: a classic vertical scrollbar may take up to ~16px off
          // the visual viewport; anything more is a fidelity failure.
          fidelityProblems.push(`visualViewport.width=${probe.visualViewportWidth} deviates from requested ${w} by more than a scrollbar`);
        }
        // ---------------------------------------------------------------

        // Content matching is case-insensitive: the design system uppercases
        // labels via text-transform, which innerText reflects. The DENIED
        // forbid list is security-relevant and is matched on the same
        // normalized text (no vendor string may appear in any casing).
        const missing = (c.expect || []).filter((s) => !text.includes(s.toLowerCase()));
        const leaked = (c.forbid || []).filter((s) => text.includes(s.toLowerCase()));
        const ok =
          fidelityProblems.length === 0 &&
          missing.length === 0 &&
          leaked.length === 0 &&
          !probe.pageOverflow &&
          probe.overflow.length === 0 &&
          probe.clipped.length === 0 &&
          probe.missingAnchors.length === 0 &&
          probe.h1Count === 1;
        if (!ok) failed++;
        results.push({
          case: c.name,
          requested: w,
          ok,
          fidelity: fidelityProblems,
          innerWidth: probe.vw,
          clientWidth: probe.clientWidth,
          docScrollWidth: probe.docScrollWidth,
          visualViewportWidth: probe.visualViewportWidth,
          compatMode: probe.compatMode,
          doctype: probe.hasDoctype,
          pageOverflow: probe.pageOverflow ? `docScrollWidth=${probe.docScrollWidth} > ${probe.vw}` : null,
          overflow: probe.overflow,
          clipped: probe.clipped,
          missingAnchors: probe.missingAnchors,
          missing,
          leaked,
          h1Count: probe.h1Count,
          focusables: probe.focusables,
        });
      }
    }
    console.log(JSON.stringify(results, null, 2));
    const bad = results.filter((r) => !r.ok).length;
    console.error(
      bad === 0
        ? `LAYOUT AUDIT PASS: ${results.length}/${results.length} case-viewport combinations (viewport fidelity + overflow + content).`
        : `LAYOUT AUDIT FAIL: ${bad}/${results.length} case-viewport combinations have findings.`,
    );
  } finally {
    if (targetWs) targetWs.close();
    chrome.kill();
  }
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error("PROBE FAILED:", e.message);
  process.exit(1);
});
