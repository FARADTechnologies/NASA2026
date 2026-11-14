// SkyLapse pitch deck v1 generator (pitch role). Run: node build_deck.js <out.pptx>
// Needs pptxgenjs (npm). Numbers in [brackets] are placeholders until science/VALIDATION.md + deployed site exist.
// Screenshot slots are marked "SCREENSHOT"; replace them with real screenshots from the deployed site (A5/A6).
const pptxgen = require("pptxgenjs");
const path = require("path");
const out = process.argv[2] || "SkyLapse_FARAD_v1.pptx";

const THEME = {
  name: "SkyLapse Infrared",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "0A0F1E", lt1: "F3F5FA", dk2: "141B33", lt2: "9AA6C4",
    accent1: "FF6B35", accent2: "FFB347", accent3: "5B8CFF", accent4: "2E3A63",
    accent5: "39D98A", accent6: "C9D2EA", hlink: "FFB347", folHlink: "FF6B35",
  },
};
const H = THEME.colors; // hex for hex-only options
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.title = "SkyLapse — Team FARAD — NASA Space Apps 2026 Baku";
pres.author = "Team FARAD";
const C = pres.SchemeColor;
const FOOT = "SkyLapse · Team FARAD · Challenge: Planet X and SPHEREx · NASA Space Apps 2026 Baku";

pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: H.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.3, w: 9, h: 0.75, fontSize: 30, bold: true, color: C.background1, fontFace: THEME.headFontFace, valign: "middle", margin: 0 }, text: "" } },
    { text: { text: FOOT, options: { x: 0.5, y: 5.2, w: 7.8, h: 0.3, fontSize: 9, color: C.background2, margin: 0 } } },
  ],
  slideNumber: { x: 9.1, y: 5.2, w: 0.4, h: 0.3, fontSize: 9, color: H.lt2, align: "right" },
});
pres.defineSlideMaster({ title: "TITLE", background: { color: H.dk1 }, objects: [] });

// ---------- helpers ----------
function tb(slide, text, o) { slide.addText(text, Object.assign({ isTextBox: true, margin: 0, color: C.background1, fontSize: 16, valign: "top" }, o)); }
function starfield(slide, seed, n, box) {
  let s = seed;
  const rnd = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  for (let i = 0; i < n; i++) {
    const d = 0.02 + rnd() * 0.05;
    slide.addShape(pres.shapes.OVAL, { x: box.x + rnd() * box.w, y: box.y + rnd() * box.h, w: d, h: d, fill: { color: H.lt1, transparency: 20 + Math.round(rnd() * 60) }, line: { type: "none" }, objectName: "star" });
  }
}
// Motif: a "blink strip" of frames; the red dot (the mover) shifts frame to frame.
function blinkStrip(slide, x, y, frameW, n, labels, shiftPerFrame) {
  for (let i = 0; i < n; i++) {
    const fx = x + i * (frameW + 0.12);
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: fx, y, w: frameW, h: frameW, rectRadius: 0.06, fill: { color: H.dk2 }, line: { color: H.accent4, width: 1 }, objectName: `frame${i}` });
    starfield(slide, 18, 6, { x: fx + 0.08, y: y + 0.08, w: frameW - 0.2, h: frameW - 0.2 });
    const d = frameW * 0.12;
    slide.addShape(pres.shapes.OVAL, { x: fx + frameW * 0.2 + i * shiftPerFrame, y: y + frameW * 0.45, w: d, h: d, fill: { color: H.accent1 }, line: { type: "none" }, objectName: `mover${i}` });
    if (labels) tb(slide, labels[i], { x: fx, y: y + frameW + 0.06, w: frameW, h: 0.25, fontSize: 11, color: C.background2, align: "center", fontFace: "Calibri" });
  }
}
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill || H.dk2 }, line: { color: H.accent4, width: 1 }, objectName: "card" });
}
function shotSlot(slide, x, y, w, h, label) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: H.dk2 }, line: { color: H.accent2, width: 1.5, dashType: "dash" }, objectName: "screenshot-slot" });
  tb(slide, [{ text: "SCREENSHOT", options: { bold: true, color: C.accent2, fontSize: 12, breakLine: true } }, { text: label, options: { fontSize: 12, color: C.background2 } }], { x: x + 0.15, y: y + h / 2 - 0.3, w: w - 0.3, h: 0.6, align: "center", valign: "middle" });
}

// ---------- 1 Title ----------
pres.addSection({ title: "Pitch" });
let s = pres.addSlide({ masterName: "TITLE", sectionTitle: "Pitch" });
starfield(s, 3, 30, { x: 6.7, y: 0.2, w: 3.1, h: 3.7 });
starfield(s, 5, 10, { x: 0.2, y: 0.05, w: 9.6, h: 0.45 });
starfield(s, 9, 8, { x: 8.0, y: 4.0, w: 1.8, h: 1.4 });
tb(s, "SkyLapse", { x: 0.6, y: 0.7, w: 8.8, h: 1.0, fontSize: 54, bold: true, fontFace: "Arial" });
tb(s, "Watch 16 years of the infrared sky — and catch what moves.", { x: 0.6, y: 1.7, w: 8.8, h: 0.5, fontSize: 20, italic: true, color: C.accent2 });
blinkStrip(s, 0.6, 2.45, 1.0, 5, ["2010", "2014", "2018", "2022", "2026"], 0.13);
tb(s, [
  { text: "Team FARAD", options: { bold: true, fontSize: 16, breakLine: true } },
  { text: "Amal Mirzayev · Hasan Dadashzada · Murad Qaramollayev · Azer Valiyev · Kanan Pashazada", options: { fontSize: 13, color: C.background2, breakLine: true } },
  { text: "Challenge: Planet X and SPHEREx  ·  NASA Space Apps Challenge 2026, Baku", options: { fontSize: 13, color: C.background2 } },
], { x: 0.6, y: 4.1, w: 8.8, h: 1.0 });
s.addNotes("0:20 — Good afternoon. We are team FARAD. Our challenge is Planet X and SPHEREx. This is SkyLapse: watch sixteen years of the infrared sky — and catch what moves.");

// ---------- 2 Challenge ----------
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pitch" });
s.addText("One year of SPHEREx is too short", { placeholder: "title" });
card(s, 0.5, 1.3, 4.3, 3.6);
tb(s, "SPHEREx alone (~1 year)", { x: 0.75, y: 1.45, w: 3.8, h: 0.35, fontSize: 15, bold: true, color: C.accent2 });
blinkStrip(s, 0.9, 2.0, 1.05, 3, ["2025", "2025.5", "2026"], 0.02);
tb(s, "A nearby star moves 1–2 pixels. It hides in plain sight.", { x: 0.75, y: 3.65, w: 3.8, h: 0.9, fontSize: 15 });
const stats = [["102", "infrared colours"], ["All sky", "every 6 months"], ["~1 yr", "of data so far"]];
stats.forEach((st, i) => {
  const y = 1.3 + i * 1.22;
  card(s, 5.2, y, 4.3, 1.08);
  tb(s, st[0], { x: 5.4, y: y + 0.14, w: 2.3, h: 0.8, fontSize: 30, bold: true, color: C.accent1, valign: "middle", fontFace: "Arial" });
  tb(s, st[1], { x: 7.75, y: y + 0.14, w: 1.65, h: 0.8, fontSize: 15, color: C.background2, valign: "middle" });
});
s.addNotes("0:35 — NASA's SPHEREx telescope maps the whole sky in one hundred and two colours of infrared light, every six months. That is amazing data. But SPHEREx is new. Its record is about one year long. In one year, even a nearby star moves only a pixel or two. So the closest, coldest worlds hide in plain sight. And no single person can check a billion objects.");

// ---------- 3 Solution ----------
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pitch" });
s.addText("A 16-year infrared time machine", { placeholder: "title" });
tb(s, "NASA's WISE watched the same sky for 14 years at the same wavelength. We join it with SPHEREx on one grid.", { x: 0.5, y: 1.2, w: 9, h: 0.6, fontSize: 16, color: C.background2 });
// timeline
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 2.15, w: 7.35, h: 0.55, rectRadius: 0.08, fill: { color: H.accent3 }, line: { type: "none" }, objectName: "wise-bar" });
tb(s, "WISE / NEOWISE  2010 – 2024  ·  23 epochs  ·  4.6 µm", { x: 0.65, y: 2.15, w: 7.1, h: 0.55, fontSize: 14, bold: true, valign: "middle", color: C.text1 });
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.95, y: 2.15, w: 1.55, h: 0.55, rectRadius: 0.08, fill: { color: H.accent1 }, line: { type: "none" }, objectName: "spherex-bar" });
tb(s, "SPHEREx 2025–26", { x: 7.95, y: 2.15, w: 1.55, h: 0.55, fontSize: 12, bold: true, valign: "middle", align: "center", color: C.text1 });
tb(s, "2010", { x: 0.5, y: 2.75, w: 0.8, h: 0.3, fontSize: 11, color: C.background2 });
tb(s, "2026", { x: 8.7, y: 2.75, w: 0.8, h: 0.3, fontSize: 11, color: C.background2, align: "right" });
const big = [["≈ 130″", "WISE 0855 moves in 16 years"], ["≈ 166″", "Barnard's Star"], ["1–2 px", "all that SPHEREx's own ~1 year shows"]];
big.forEach((b, i) => {
  const x = 0.5 + i * 3.08;
  card(s, x, 3.3, 2.85, 1.65);
  tb(s, b[0], { x: x + 0.2, y: 3.45, w: 2.45, h: 0.75, fontSize: 32, bold: true, color: i === 2 ? C.background2 : C.accent2, fontFace: "Arial" });
  tb(s, b[1], { x: x + 0.2, y: 4.2, w: 2.45, h: 0.6, fontSize: 14, color: C.background2 });
});
s.addNotes("0:30 — Our insight: NASA already watched this sky before. The WISE mission took pictures of the whole sky for fourteen years, at the same wavelength — four point six microns. We put WISE and SPHEREx on one grid. Now you get a sixteen-year movie. In sixteen years, nearby objects move not one pixel, but minutes of arc. You can see them move.");

// ---------- 4 How it works ----------
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pitch" });
s.addText("Type a position. Watch. Catch.", { placeholder: "title" });
const steps = [["1  Movie", "16-year blink movie of any sky position"], ["2  Fingerprint", "SPHEREx spectrum: 102 colours of one object"], ["3  Explain", "Plain-language AZ / EN, only from our measurements"]];
steps.forEach((st, i) => {
  const x = 0.5 + i * 3.08;
  shotSlot(s, x, 1.25, 2.85, 2.35, st[0] + " — from the deployed site");
  tb(s, st[0], { x, y: 3.75, w: 2.85, h: 0.35, fontSize: 16, bold: true, color: C.accent2 });
  tb(s, st[1], { x, y: 4.12, w: 2.85, h: 0.8, fontSize: 14, color: C.background2 });
});
s.addNotes("0:10 — You type a position in the sky, or a name. SkyLapse plays the movie. Let me show you — live.\n\nLIVE DEMO 1:30 (pitch/STORY.md §3): WISE 0855 play → spectral fingerprint → Barnard's Star validation card → AI explanation in Azerbaijani. Fallback: backup video.");

// ---------- 5 Space data + proof ----------
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pitch" });
s.addText("NASA data, tested on NASA's own targets", { placeholder: "title" });
const data = [["NASA SPHEREx", "102-band images, DR1 + QR3 (IRSA)"], ["NASA WISE / NEOWISE", "unWISE time-resolved coadds 2010–2024"], ["CatWISE2020", "motion catalogue built from NASA WISE"], ["ESA Gaia DR3", "partner agency: star positions + motions"]];
data.forEach((d, i) => {
  const y = 1.25 + i * 0.86;
  card(s, 0.5, y, 4.2, 0.74);
  tb(s, [{ text: d[0], options: { bold: true, fontSize: 14, color: i === 3 ? C.accent3 : C.accent2, breakLine: true } }, { text: d[1], options: { fontSize: 12, color: C.background2 } }], { x: 0.7, y: y + 0.08, w: 3.9, h: 0.6, valign: "middle" });
});
const rows = [
  [{ text: "NASA target", options: { bold: true, color: H.lt2 } }, { text: "Measured", options: { bold: true, color: H.lt2 } }, { text: "Reference", options: { bold: true, color: H.lt2 } }, { text: "Result", options: { bold: true, color: H.lt2 } }],
  ["Barnard's Star", "10.40″/yr", "Gaia DR3", "99.8 %"],
  ["ε Indi B", "4.72″/yr", "Gaia DR3", "99.0 %"],
  ["WISE 0855", "8.16″/yr", "Kirkpatrick+21", "99.9 %"],
  ["RW Aurigae", "variability", "—", "[shown]"],
  ["R Draconis", "variability", "—", "[shown]"],
];
s.addTable(rows, { x: 5.0, y: 1.25, w: 4.5, colW: [1.45, 1.0, 1.2, 0.85], fontSize: 12, fontFace: "Calibri", color: H.lt1, fill: { color: H.dk2 }, border: { type: "solid", pt: 0.75, color: H.accent4 }, rowH: 0.42, valign: "middle", objectName: "validation-table" });
tb(s, "Tools: Python · Astropy · React", { x: 5.0, y: 4.0, w: 4.5, h: 0.6, fontSize: 13, color: C.background2 });
s.addNotes("0:35 — Everything runs on open space data. NASA SPHEREx, NASA WISE and NEOWISE, and ESA's Gaia catalogue as partner data. We tested on all five NASA target objects. For the three moving ones, our measured speeds agree with Gaia and the literature to better than ninety-nine percent. For the two variable stars, we show their brightness changes — and we honestly flag when a star is too bright for the detector.");

// ---------- 6 Impact ----------
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pitch" });
s.addText("Anyone can discover", { placeholder: "title" });
card(s, 0.5, 1.25, 4.3, 3.65);
tb(s, "Precedent", { x: 0.75, y: 1.45, w: 3.8, h: 0.35, fontSize: 15, bold: true, color: C.accent2 });
tb(s, "In NASA's Backyard Worlds project, volunteers blinking WISE images found cold brown dwarfs that automated searches missed.", { x: 0.75, y: 1.9, w: 3.8, h: 1.5, fontSize: 15 });
tb(s, "SkyLapse brings that to SPHEREx — in a browser, free, in Azerbaijani and English.", { x: 0.75, y: 3.25, w: 3.8, h: 1.2, fontSize: 15, color: C.background2 });
const users = [["University students", "first users, in Azerbaijan"], ["Space-agency school lessons", "a ready channel to young learners"], ["Citizen scientists", "anyone, worldwide"]];
users.forEach((u, i) => {
  const y = 1.25 + i * 1.25;
  card(s, 5.2, y, 4.3, 1.1);
  s.addShape(pres.shapes.OVAL, { x: 5.4, y: y + 0.33, w: 0.44, h: 0.44, fill: { color: H.accent1 }, line: { type: "none" }, objectName: "user-dot" });
  tb(s, [{ text: u[0], options: { bold: true, fontSize: 15, breakLine: true } }, { text: u[1], options: { fontSize: 13, color: C.background2 } }], { x: 6.05, y: y + 0.15, w: 3.3, h: 0.8, valign: "middle" });
});
s.addNotes("0:30 — Why does it matter? With NASA's Backyard Worlds project, volunteers blinking sky images found cold brown dwarfs that computers missed. SkyLapse brings that power to SPHEREx — in a browser, free, for anyone. Our first users: university students in Azerbaijan — and, through space agencies' school lessons, young learners too. We do not claim discoveries. We help people find candidates for scientists to follow up.");

// ---------- 7 Next steps + AI ----------
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Pitch" });
s.addText("Next steps — and how we used AI", { placeholder: "title" });
const nexts = ["New SPHEREx data every week: one command rebuilds a field", "Automatic candidate lists for follow-up", "More languages + a classroom program with universities"];
nexts.forEach((n, i) => {
  const y = 1.3 + i * 0.95;
  s.addShape(pres.shapes.OVAL, { x: 0.5, y: y + 0.05, w: 0.5, h: 0.5, fill: { color: H.accent1 }, line: { type: "none" }, objectName: "step-dot" });
  tb(s, String(i + 1), { x: 0.5, y: y + 0.05, w: 0.5, h: 0.5, fontSize: 16, bold: true, align: "center", valign: "middle", color: C.text1 });
  tb(s, n, { x: 1.2, y, w: 3.8, h: 0.65, fontSize: 15, valign: "middle" });
});
card(s, 5.3, 1.25, 4.2, 2.45, H.dk2);
tb(s, "AI use (disclosed)", { x: 5.5, y: 1.4, w: 3.8, h: 0.35, fontSize: 15, bold: true, color: C.accent3 });
tb(s, [
  { text: "Claude Code coding assistants helped build the pipeline and web app; humans decided and reviewed.", options: { bullet: true, breakLine: true } },
  { text: "AI explanations are written only from numbers our code computed.", options: { bullet: true, breakLine: true } },
  { text: "Any AI image/audio is watermarked.", options: { bullet: true } },
], { x: 5.5, y: 1.8, w: 3.85, h: 1.8, fontSize: 13, paraSpaceAfter: 6 });
tb(s, "Try it: [deployed URL]", { x: 5.3, y: 3.95, w: 4.2, h: 0.5, fontSize: 18, bold: true, color: C.accent2 });
s.addNotes("0:30 — SPHEREx sends new data every week. Updating a field is one command, and hosting costs almost nothing. Next: automatic candidate lists, more languages, and a class program for schools. We used AI openly: coding assistants helped us build it, and the AI explanations are written only from our own measurements. SkyLapse — sixteen years of sky, for everyone. Thank you.");

(async () => {
  await pres.writeFile({ fileName: out });
  const skill = process.env.PPTX_SKILL_DIR;
  if (skill) {
    const { applyTheme } = require(path.join(skill, "scripts", "apply_theme.js"));
    await applyTheme(out, THEME);
  }
  console.log("wrote", out);
})();
