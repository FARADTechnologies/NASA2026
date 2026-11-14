// Backup demo recording (A7 #72). Drives the installed Microsoft Edge with playwright-core, records the LIVE site
// https://skylapse.vercel.app at 1600x900 and burns English captions into the page (fixed overlay).
// Run: NODE_PATH=<dir with playwright-core>/node_modules node record_demo.js <outDir>
// Then build the MP4: python pitch/video/make_mp4.py <outDir> <out.mp4>
const { chromium } = require("playwright-core");
const outDir = process.argv[2] || ".";
const SITE = "https://skylapse.vercel.app";
const W = 1600, H = 900;

async function caption(page, text) {
  await page.evaluate((t) => {
    let el = document.getElementById("__cap");
    if (!el) {
      el = document.createElement("div");
      el.id = "__cap";
      Object.assign(el.style, {
        position: "fixed", left: "50%", bottom: "28px", transform: "translateX(-50%)", zIndex: 2147483647,
        maxWidth: "1200px", padding: "12px 22px", borderRadius: "10px", background: "rgba(0,0,0,0.82)",
        color: "#fff", font: "600 26px/1.3 Inter, Segoe UI, Arial, sans-serif", textAlign: "center", pointerEvents: "none",
      });
      document.body.appendChild(el);
    }
    el.textContent = t;
    el.style.display = t ? "block" : "none";
  }, text);
}
async function badge(page) { // small corner label, always on
  await page.evaluate(() => {
    if (document.getElementById("__badge")) return;
    const b = document.createElement("div");
    b.id = "__badge";
    b.textContent = "SkyLapse · Team FARAD · NASA Space Apps 2026 Baku · live site recording";
    Object.assign(b.style, { position: "fixed", right: "14px", top: "74px", zIndex: 2147483647, padding: "4px 10px", borderRadius: "6px",
      background: "rgba(0,0,0,0.6)", color: "#cbd3ea", font: "500 13px Segoe UI, Arial, sans-serif", pointerEvents: "none" });
    document.body.appendChild(b);
  });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function open(page, field) {
  await page.goto(`${SITE}/view?field=${field}`, { waitUntil: "networkidle", timeout: 90000 });
  await page.waitForFunction(() => /\d+ frames/.test(document.body.innerText) && !/loading \d+\/\d+/.test(document.body.innerText), null, { timeout: 90000 });
  const got = page.getByRole("button", { name: "Got it" });
  if (await got.count()) await got.first().click().catch(() => {});
  await badge(page);
}
async function scrollTo(page, headingText) {
  await page.evaluate((t) => {
    const h = [...document.querySelectorAll("h3")].find((e) => e.textContent.trim().startsWith(t));
    if (h) h.scrollIntoView({ behavior: "smooth", block: "start" });
  }, headingText);
}

(async () => {
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  // warm-up pass (not recorded) so frames are cached and the recording has no loading pauses
  const warm = await browser.newContext({ viewport: { width: W, height: H } });
  const wp = await warm.newPage();
  for (const f of ["wise0855", "eps_indi_b", "barnard", "r_dra"]) await open(wp, f);
  await warm.close();

  const ctx = await browser.newContext({ viewport: { width: W, height: H } });
  const page = await ctx.newPage();
  // CDP screencast → timestamped JPEG frames (no Playwright ffmpeg needed); assembled later by make_mp4.py
  const fs = require("fs"), path = require("path");
  const cdp = await ctx.newCDPSession(page);
  const frames = [];
  cdp.on("Page.screencastFrame", async (f) => {
    const name = `f${String(frames.length).padStart(5, "0")}.jpg`;
    fs.writeFileSync(path.join(outDir, name), Buffer.from(f.data, "base64"));
    frames.push({ name, t: Date.now() });
    await cdp.send("Page.screencastFrameAck", { sessionId: f.sessionId }).catch(() => {});
  });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 85, maxWidth: W, maxHeight: H, everyNthFrame: 1 });
  const t0 = Date.now();
  const mark = (s) => console.log(((Date.now() - t0) / 1000).toFixed(1) + " s  " + s);

  // 1 — WISE 0855: the 16-year movie (≈ 25 s)
  await open(page, "wise0855"); mark("wise0855 open");
  await caption(page, "One patch of sky, 2010 → 2026: NASA WISE + SPHEREx joined on one grid.");
  await sleep(8000);
  await caption(page, "The circled dot is WISE 0855 — the coldest known brown dwarf. It crawls ~2 arcminutes in 16 years.");
  await sleep(9000);
  await page.getByRole("button", { name: "AZ" }).first().click().catch(() => {});
  await scrollTo(page, "AI Copilot");
  await caption(page, "99.9 % agreement with the published motion — explained by AI in Azerbaijani, only from our measurements.");
  await sleep(8000);

  // 2 — ε Indi B: spectral fingerprint (≈ 18 s)
  await open(page, "eps_indi_b"); mark("eps_indi_b open");
  await caption(page, "ε Indi B moves too — and SPHEREx's 102 colours give its infrared fingerprint.");
  await sleep(5000);
  await scrollTo(page, "Spectrum");
  await caption(page, "Water and methane dips: the classic spectrum of a cold T-type brown dwarf.");
  await sleep(9000);

  // 3 — Barnard's Star: validation (≈ 14 s)
  await open(page, "barnard"); mark("barnard open");
  await caption(page, "Barnard's Star, the fastest star in our sky: 10.40″ per year measured — Gaia says 10.39″ (99.8 %).");
  await sleep(8000);
  await caption(page, "Too bright for the detectors — we fit the edges of the star and say so honestly.");
  await sleep(5000);

  // 4 — R Draconis: variability (≈ 16 s)
  await open(page, "r_dra"); mark("r_dra open");
  await caption(page, "R Draconis is not moving — it pulses.");
  await sleep(4000);
  await scrollTo(page, "Light curve");
  await caption(page, "14 years of brightness: period 246 days — the known period is 245.6 days.");
  await sleep(8500);

  // 5 — close (≈ 8 s)
  await caption(page, "Blind search found all 3 NASA movers, 0 false alarms. Try it: skylapse.vercel.app");
  await sleep(6500);
  mark("end");
  await caption(page, "");
  await sleep(500);
  await cdp.send("Page.stopScreencast").catch(() => {});
  fs.writeFileSync(path.join(outDir, "frames.json"), JSON.stringify({ t0, frames }));
  console.log("frames:", frames.length);
  await ctx.close();
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
