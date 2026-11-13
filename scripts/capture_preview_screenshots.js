// PILOT-UX-WORKBENCH-A1-FU1 screenshot capture (developer tool).
//
// Corrects the A1 capture defect: A1's 390px screenshots were taken with a
// capture path whose layout viewport was WIDER than the requested CSS width
// (headless Chrome clamps its window to a minimum width; the captures were
// then cropped to the requested size), so the right side of every page was
// clipped. The layout probe measured a DIFFERENT path (CDP
// Emulation.setDeviceMetricsOverride) whose viewport was correct, which is
// why its overflow-only checks passed while the captures clipped.
//
// This script captures through the SAME CDP device-metrics path as
// scripts/layout_probe.js and fails the whole run if the measured layout
// viewport ever differs from the requested CSS width:
//
//   for every case x viewport:
//     1. Emulation.setDeviceMetricsOverride(width, mobile = width < 500,
//        deviceScaleFactor 1)
//     2. assert window.innerWidth === requested        (layout viewport)
//     3. assert document.doctype present and
//        document.compatMode === "CSS1Compat"          (standards mode)
//     4. assert document.documentElement.scrollWidth <= window.innerWidth
//        (no page-level horizontal overflow)
//     5. grow the viewport to the document's full height (no vertical
//        scrollbar participates in the layout), re-assert innerWidth,
//        clientWidth and scrollWidth, then capture the viewport
//     6. assert the PNG pixel width === requested
//
// Run addresses come from <preview-dir>/preview_urls.json (written by
// scripts/preview_fixtures.py). Expected servers: 8101 (vendor ALLOWED) and
// 8102 (vendor DENIED).
"use strict";

const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const REPO = path.resolve(__dirname, "..");
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const PROFILE = path.join(REPO, "tmp_preview", "chrome_cdp_profile");
const PORT = 9334;
const URLS_JSON = process.argv[2] || path.join(REPO, "tmp_preview", "preview_urls.json");
const OUT_DIR =
  process.argv[3] || path.join(REPO, "docs", "pilot_ux_workbench_a1_screenshots");

const manifest = JSON.parse(fs.readFileSync(URLS_JSON, "utf-8"));
const run = (key) => manifest.runs[key];
const H = { allowed: "http://127.0.0.1:8101", denied: "http://127.0.0.1:8102" };

// The 16-shot matrix (same case set as the A1 capture).
const SCROLL_QUOTE_TABLE = `
  (() => {
    const w = document.querySelector(".pi-quote-wrapper");
    if (w) { w.scrollLeft = w.scrollWidth; }
  })()
`;

const SHOTS = [
  { file: "01_intake_empty_1440.png", w: 1440, viewportOnly: true, url: `${H.allowed}/research/new`,
    expect: ["Run Market Research", "New research request"] },
  { file: "02_intake_prefill_1440.png", w: 1440, viewportOnly: true,
    url: `${H.allowed}/research/new?mpn=MTFDKCC3T8TGP-1BK1DABYY&description=480GB%20NVMe%20M.2%20solid%20state%20drive`,
    expect: ["MTFDKCC3T8TGP-1BK1DABYY", "480GB NVMe M.2 solid state drive"] },
  { file: "03_intake_empty_768.png", w: 768, viewportOnly: true, url: `${H.allowed}/research/new`,
    expect: ["Run Market Research", "New research request"] },
  { file: "04_intake_empty_390.png", w: 390, viewportOnly: true, url: `${H.allowed}/research/new`,
    expect: ["Run Market Research", "New research request"] },
  { file: "05_report_multiquote_allowed_1440.png", w: 1440, url: `${H.allowed}${run("multiquote")}`,
    expect: ["Ingram (Vendor API)", "CDW (Vendor API)", "Synnex EU (Vendor API)", "example.com"],
    forbid: ["Internal commercial pricing is unavailable for this connection."] },
  { file: "06_report_multiquote_allowed_768.png", w: 768, url: `${H.allowed}${run("multiquote")}`,
    expect: ["Ingram (Vendor API)", "CDW (Vendor API)", "Synnex EU (Vendor API)", "example.com"] },
  { file: "07_report_multiquote_allowed_390.png", w: 390, url: `${H.allowed}${run("multiquote")}`,
    expect: ["Ingram (Vendor API)", "CDW (Vendor API)", "Synnex EU (Vendor API)", "example.com"] },
  { file: "08_report_multiquote_denied_1440.png", w: 1440, url: `${H.denied}${run("multiquote")}`,
    expect: ["Internal commercial pricing is unavailable for this connection."],
    forbid: ["Ingram (Vendor API)", "CDW (Vendor API)", "Synnex EU (Vendor API)", "$2,023.27", "$1,999.99", "1,705.35"] },
  { file: "09_report_zeroquote_1440.png", w: 1440, url: `${H.allowed}${run("zeroquote")}`,
    expect: ["Source-published price: $0 USD", "Verify price and purchasing availability with the supplier."] },
  // The zero-price notice sits in the Market Use column (7th of 8). At 390
  // CSS px the 8-column table is wider than the card, so the table's
  // designed horizontal scroll (overflow-x: auto on .spec-table-wrapper)
  // exposes it; this capture is taken with that container scrolled fully
  // right so the committed image proves the notice is reachable/readable.
  { file: "10_report_zeroquote_390.png", w: 390, url: `${H.allowed}${run("zeroquote")}`,
    preCapture: SCROLL_QUOTE_TABLE,
    expect: ["Source-published price: $0 USD", "Verify price and purchasing availability with the supplier."] },
  { file: "11_report_no_evidence_1440.png", w: 1440, url: `${H.allowed}${run("noevidence")}`,
    expect: ["Price aggregation status:", "UNKNOWN", "Excluded listings"] },
  { file: "12_report_ai_review_1440.png", w: 1440, url: `${H.allowed}${run("aireview")}`,
    expect: ["AI-assisted evidence & review", "Possible matches"] },
  { file: "13_report_ai_review_390.png", w: 390, url: `${H.allowed}${run("aireview")}`,
    expect: ["AI-assisted evidence & review", "Possible matches"] },
  { file: "14_report_comparable_1440.png", w: 1440, url: `${H.allowed}${run("comparable")}`,
    expect: ["Comparable products", "CAND-001"] },
  { file: "15_report_running_1440.png", w: 1440, url: `${H.allowed}${run("running")}`,
    expect: ["RUNNING", "Research is currently running."] },
  { file: "16_report_failed_1440.png", w: 1440, url: `${H.allowed}${run("failed")}`,
    expect: ["FAILED", "Retry Research"] },
];

const METRICS_JS = `
() => {
  const doc = document.documentElement;
  return JSON.stringify({
    innerWidth: window.innerWidth,
    clientWidth: doc.clientWidth,
    scrollWidth: doc.scrollWidth,
    visualViewportWidth: window.visualViewport ? window.visualViewport.width : null,
    compatMode: document.compatMode,
    hasDoctype: !!document.doctype,
  });
}
`;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function pngSize(buf) {
  return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
}

async function main() {
  fs.mkdirSync(OUT_DIR, { recursive: true });
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
        setTimeout(() => reject(new Error(method + " timeout")), 30000);
      });

    const report = [];
    for (const s of SHOTS) {
      const h = s.w === 390 ? 780 : 900;
      await send("Emulation.setDeviceMetricsOverride", {
        width: s.w, height: h, deviceScaleFactor: 1, mobile: s.w < 500,
      });
      await send("Page.enable");
      await send("Page.navigate", { url: s.url });
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

      const problems = [];
      const mRaw = await send("Runtime.evaluate", { expression: `(${METRICS_JS})()`, returnByValue: true });
      const m = JSON.parse(mRaw.result.value);
      if (!m.hasDoctype) problems.push("missing <!DOCTYPE html>");
      if (m.compatMode !== "CSS1Compat") problems.push(`compatMode=${m.compatMode}`);
      if (m.innerWidth !== s.w) problems.push(`innerWidth=${m.innerWidth} != requested ${s.w}`);
      if (s.w < 500) {
        if (m.visualViewportWidth !== null && m.visualViewportWidth !== s.w)
          problems.push(`visualViewport.width=${m.visualViewportWidth} != requested ${s.w}`);
      } else if (m.visualViewportWidth !== null && (m.visualViewportWidth < s.w - 16 || m.visualViewportWidth > s.w)) {
        problems.push(`visualViewport.width=${m.visualViewportWidth} deviates from requested ${s.w} by more than a scrollbar`);
      }
      if (m.scrollWidth > m.innerWidth + 1) problems.push(`page-level horizontal overflow: scrollWidth=${m.scrollWidth} > innerWidth=${m.innerWidth}`);

      // Content checks use textContent (render-independent: includes
      // collapsed <details> and form values) so the capture itself keeps
      // the default visual state of the page.
      const body = await send("Runtime.evaluate", {
        expression: "(() => { const parts = []; if (document.body) parts.push(document.body.textContent); document.querySelectorAll('input, textarea').forEach(el => parts.push(el.value || '')); return parts.join('\\n'); })()",
        returnByValue: true,
      });
      const text = (body.result.value || "").toLowerCase();
      for (const e of s.expect || []) if (!text.includes(e.toLowerCase())) problems.push(`missing content: ${e}`);
      for (const f of s.forbid || []) if (text.includes(f.toLowerCase())) problems.push(`forbidden content present: ${f}`);

      if (s.preCapture) {
        await send("Runtime.evaluate", { expression: s.preCapture, returnByValue: true });
        await sleep(150);
      }

      let pngW = null, pngH = null;
      if (problems.length === 0) {
        let m2;
        if (s.viewportOnly) {
          // Intake shots: the first viewport is the design surface. Assert
          // the viewport itself has no scrollbar (clientWidth == innerWidth)
          // and capture it as-is.
          if (m.clientWidth !== m.innerWidth) problems.push(`viewport clientWidth=${m.clientWidth} != innerWidth=${m.innerWidth} (scrollbar in layout; intake shot must fit its viewport)`);
          m2 = m;
        } else {
          // Full-page capture at the INTENDED viewport width: grow the
          // viewport to the document's full height so no vertical scrollbar
          // participates in the layout, then re-verify the width and capture.
          // (A viewport-height capture of a scrolling page would otherwise
          // be clientWidth = requested - 15px wide, mixing scrollbar geometry
          // into the design review.)
          let fullH = null;
          for (let pass = 0; pass < 2; pass++) {
            const hh = await send("Runtime.evaluate", {
              expression: "Math.max(document.body ? document.body.scrollHeight : 0, document.documentElement.scrollHeight)",
              returnByValue: true,
            });
            const nextH = Math.ceil(hh.result.value || h);
            if (fullH !== null && nextH <= fullH) break;
            fullH = nextH;
            await send("Emulation.setDeviceMetricsOverride", {
              width: s.w, height: fullH, deviceScaleFactor: 1, mobile: s.w < 500,
            });
            await sleep(150);
          }
          const m2Raw = await send("Runtime.evaluate", { expression: `(${METRICS_JS})()`, returnByValue: true });
          m2 = JSON.parse(m2Raw.result.value);
          m2.fullPageHeight = fullH;
          if (m2.innerWidth !== s.w) problems.push(`full-page innerWidth=${m2.innerWidth} != requested ${s.w}`);
          if (m2.clientWidth !== m2.innerWidth) problems.push(`full-page clientWidth=${m2.clientWidth} != innerWidth=${m2.innerWidth} (scrollbar in layout)`);
          if (m2.scrollWidth > m2.clientWidth + 1) problems.push(`full-page horizontal overflow: scrollWidth=${m2.scrollWidth} > clientWidth=${m2.clientWidth}`);
        }
        if (s.preCapture) {
          await send("Runtime.evaluate", { expression: s.preCapture, returnByValue: true });
          await sleep(150);
        }
        if (problems.length === 0) {
          const shot = await send("Page.captureScreenshot", { format: "png" });
          const buf = Buffer.from(shot.data, "base64");
          const size = pngSize(buf);
          pngW = size.w; pngH = size.h;
          if (pngW !== s.w) problems.push(`PNG pixel width ${pngW} != requested ${s.w}`);
          Object.assign(m, m2);
          fs.writeFileSync(path.join(OUT_DIR, s.file), buf);
        }
      } else {
        // Do not write a capture whose viewport is not proven to be the
        // requested width: a cropped image is worse than no image.
      }

      if (problems.length) failed++;
      report.push({ file: s.file, requested: s.w, ok: problems.length === 0, problems, ...m, png: pngW ? `${pngW}x${pngH}` : null });
    }
    console.log(JSON.stringify(report, null, 2));
    console.error(
      failed === 0
        ? `CAPTURE PASS: ${report.length}/${report.length} screenshots at proven viewports.`
        : `CAPTURE FAIL: ${failed}/${report.length} shots have viewport-fidelity or content problems.`,
    );
  } finally {
    if (targetWs) targetWs.close();
    chrome.kill();
  }
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((e) => {
  console.error("CAPTURE FAILED:", e.message);
  process.exit(1);
});
