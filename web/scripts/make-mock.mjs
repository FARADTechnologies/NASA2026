// Dev-only mock bundle that follows docs/DATA_CONTRACT.md (schema 1.0).
// Writes web/public/devmock/ — NOT web/public/bundle/ (that folder belongs to the pipeline).
// The app falls back to devmock only when no real/orchestrator bundle exists.
import fs from "node:fs";
import path from "node:path";

const OUT = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "../public/devmock");
const D2R = Math.PI / 180;
const W = 192, H = 192, SCALE = 2.75;
const yearToMjd = (y) => 51544.5 + (y - 2000) * 365.25;
const mjdToDate = (m) => new Date(Date.UTC(1858, 10, 17) + m * 86400000).toISOString().slice(0, 10);

let seed = 12345;
const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());

function wcsFor(ra0, dec0) {
  return { CTYPE1: "RA---TAN", CTYPE2: "DEC--TAN", CRVAL1: ra0, CRVAL2: dec0, CRPIX1: W / 2 + 0.5, CRPIX2: H / 2 + 0.5,
    CD1_1: -SCALE / 3600, CD1_2: 0, CD2_1: 0, CD2_2: SCALE / 3600 };
}
function world2pix(w, ra, dec) {
  const a = ra * D2R, d = dec * D2R, a0 = w.CRVAL1 * D2R, d0 = w.CRVAL2 * D2R;
  const cosc = Math.sin(d0) * Math.sin(d) + Math.cos(d0) * Math.cos(d) * Math.cos(a - a0);
  const xi = (Math.cos(d) * Math.sin(a - a0)) / cosc / D2R;
  const eta = (Math.cos(d0) * Math.sin(d) - Math.sin(d0) * Math.cos(d) * Math.cos(a - a0)) / cosc / D2R;
  const det = w.CD1_1 * w.CD2_2 - w.CD1_2 * w.CD2_1;
  const dx = (w.CD2_2 * xi - w.CD1_2 * eta) / det, dy = (-w.CD2_1 * xi + w.CD1_1 * eta) / det;
  return [dx + w.CRPIX1 - 1, dy + w.CRPIX2 - 1]; // 0-based array coords, y = row from SOUTH
}
const propagate = (ra, dec, pmra, pmdec, t, t0) => [ra + (pmra * (t - t0)) / (3.6e6 * Math.cos(dec * D2R)), dec + (pmdec * (t - t0)) / 3.6e6];

function percentile(arr, p) {
  const s = Float32Array.from(arr).sort();
  return s[Math.min(s.length - 1, Math.floor(p * s.length))];
}

function buildField(f) {
  const dir = path.join(OUT, f.field_id);
  for (const sub of ["frames", "previews", "catalogs", "objects"]) fs.mkdirSync(path.join(dir, sub), { recursive: true });
  const wcs = wcsFor(f.ra, f.dec);
  // background stars (fixed), ref epoch 2016
  const stars = [];
  for (let i = 0; i < 70; i++) {
    const x = rnd() * W, y = rnd() * H;
    const ra = f.ra + ((W / 2 - x) * SCALE) / 3600 / Math.cos(f.dec * D2R), dec = f.dec + ((y - H / 2) * SCALE) / 3600;
    const amp = Math.exp(rnd() * 5) * 2;
    stars.push({ id: String(4.4e18 + i * 7919), ra, dec, pmra: gauss() * 8, pmdec: gauss() * 8, amp, mag: 20 - Math.log(amp) * 1.4, color: 1 + rnd() * 2 });
  }
  // WISE epochs
  const wiseYears = [2010.35, 2010.85];
  for (let y = 2014.3; y <= 2024.31; y += 0.5) wiseYears.push(+y.toFixed(2));
  const spxYears = [2025.45, 2025.95, 2026.45];
  const frames = [];
  const tgt = f.target;
  const addFrame = (id, instrument, band, lam, year, psf, ampScale, tgtAmp, ninp) => {
    const mjd = yearToMjd(year);
    const data = new Float32Array(W * H), mask = new Uint8Array(W * H);
    for (let i = 0; i < data.length; i++) data[i] = gauss() * (instrument === "WISE" ? 1.0 : 1.6);
    const draw = (px, py, amp) => {
      const r = Math.ceil(psf * 4);
      for (let yy = Math.max(0, Math.floor(py - r)); yy < Math.min(H, py + r); yy++)
        for (let xx = Math.max(0, Math.floor(px - r)); xx < Math.min(W, px + r); xx++) {
          const d2 = (xx - px) ** 2 + (yy - py) ** 2;
          data[yy * W + xx] += amp * Math.exp(-d2 / (2 * psf * psf));
          if (amp * Math.exp(-d2 / (2 * psf * psf)) > 900) mask[yy * W + xx] |= 2;
        }
    };
    for (const s of stars) {
      const [ra, dec] = propagate(s.ra, s.dec, s.pmra, s.pmdec, year, 2016);
      const [px, py] = world2pix(wcs, ra, dec);
      draw(px, py, s.amp * ampScale);
    }
    const [tra, tdec] = propagate(tgt.ra, tgt.dec, tgt.pmra, tgt.pmdec, year, 2018);
    const [tx, ty] = world2pix(wcs, tra, tdec);
    if (tgtAmp > 0) draw(tx, ty, tgtAmp * (f.variable ? 1 + 0.6 * Math.sin(year * 2.1) : 1));
    if (instrument === "WISE" && Math.round(year * 10) % 7 === 0) for (let yy = 0; yy < H; yy++) mask[yy * W + 140] |= 1;
    let nm = 0, ns = 0;
    for (let i = 0; i < mask.length; i++) { if (mask[i] & 1) nm++; if (mask[i] & 2) ns++; }
    fs.writeFileSync(path.join(dir, "frames", id + ".f32"), Buffer.from(data.buffer));
    fs.writeFileSync(path.join(dir, "frames", id + ".mask.u8"), Buffer.from(mask.buffer));
    const span = instrument === "WISE" ? 3 : 14;
    frames.push({ id, instrument, band, lambda_um: lam, mjd_start: +(mjd - span / 2).toFixed(2), mjd_end: +(mjd + span / 2).toFixed(2),
      mjd_mid: +mjd.toFixed(2), date: mjdToDate(mjd), n_inputs: ninp, file: `frames/${id}.f32`, mask_file: `frames/${id}.mask.u8`,
      dtype: "float32", units: "relative",
      display: { p01: +percentile(data, 0.01).toFixed(2), p50: +percentile(data, 0.5).toFixed(2), p99: +percentile(data, 0.99).toFixed(2), p999: +percentile(data, 0.999).toFixed(2) },
      quality: { masked_frac: +(nm / mask.length).toFixed(4), saturated_frac: +(ns / mask.length).toFixed(4), notes: ns ? ["bright star saturated core"] : [] },
      source_files: [instrument === "WISE" ? `mock unWISE epoch ${frames.length}` : "mock SPHEREx cutouts"], _year: year, _t: [tra, tdec] });
  };
  wiseYears.forEach((y, i) => {
    const e = String(i).padStart(2, "0");
    addFrame(`wise_w2_e${e}`, "WISE", "W2", [4.6, 4.6], y, 0.95, 1, tgt.w2, 1);
    addFrame(`wise_w1_e${e}`, "WISE", "W1", [3.4, 3.4], y, 0.9, 1.2, tgt.w1, 1);
  });
  const det = { D1: [0.75, 1.09, 0], D2: [1.10, 1.62, 0.1], D3: [1.63, 2.41, 0.15], D4: [2.42, 3.82, 0.3], D5: [3.83, 4.41, 0.6], D6: [4.42, 5.0, 1.0] };
  spxYears.forEach((y, i) => {
    const t = String(i).padStart(2, "0");
    for (const [d, [l0, l1, k]] of Object.entries(det)) addFrame(`spx_${d.toLowerCase()}_t${t}`, "SPHEREx", d, [l0, l1], y, 1.5, 0.9, tgt.w2 * k, 6 + i);
  });
  const ids = (re) => frames.filter((fr) => re.test(fr.id)).sort((a, b) => a.mjd_mid - b.mjd_mid).map((fr) => fr.id);
  const manifest = {
    schema_version: "1.0", field_id: f.field_id, title: f.title, center: { ra: f.ra, dec: f.dec, epoch: 2018.0 },
    grid: { width: W, height: H, pixel_scale_arcsec: SCALE, wcs },
    frames: frames.map(({ _year, _t, ...fr }) => fr),
    sequences: [
      { id: "thermal46", label: "4.6 µm — WISE W2 + SPHEREx D6", default: true, frames: ids(/^(wise_w2|spx_d6)/) },
      { id: "w1d4", label: "3.4 µm — WISE W1 + SPHEREx D4", default: false, frames: ids(/^(wise_w1|spx_d4)/) },
      { id: "spherex6", label: "SPHEREx only — D1…D6", default: false, frames: ids(/^spx_/) },
    ],
    rgb_composites: spxYears.map((_, i) => { const t = String(i).padStart(2, "0"); return { id: `fingerprint_t${t}`, label: `Spectral fingerprint (D1/D3/D6), ${Math.floor(spxYears[i])}`, r: `spx_d6_t${t}`, g: `spx_d3_t${t}`, b: `spx_d1_t${t}` }; }),
    objects: ["target"], catalogs: { gaia: "catalogs/gaia.json", catwise: "catalogs/catwise.json" }, candidates: "candidates.json",
    credits: ["MOCK DATA — generated by web/scripts/make-mock.mjs"], build: { pipeline_version: "mock", generated_utc: new Date().toISOString(), spherex_releases: [] },
  };
  fs.writeFileSync(path.join(dir, "manifest.json"), JSON.stringify(manifest, null, 1));
  fs.writeFileSync(path.join(dir, "catalogs", "gaia.json"), JSON.stringify({ catalog: "Gaia DR3", ref_epoch: 2016.0,
    columns: ["id", "ra", "dec", "pmra", "pmdec", "parallax", "mag", "color"],
    rows: stars.filter((s) => s.mag < 19).map((s) => [s.id, +s.ra.toFixed(6), +s.dec.toFixed(6), +s.pmra.toFixed(1), +s.pmdec.toFixed(1), 1.0, +s.mag.toFixed(2), +s.color.toFixed(2)]) }));
  const [cra, cdec] = propagate(tgt.ra, tgt.dec, tgt.pmra, tgt.pmdec, 2015.4, 2018);
  fs.writeFileSync(path.join(dir, "catalogs", "catwise.json"), JSON.stringify({ catalog: "CatWISE2020", ref_epoch: 2015.4,
    columns: ["id", "ra", "dec", "pmra", "pmdec", "parallax", "mag", "color"], rows: [["J0855-0714", +cra.toFixed(6), +cdec.toFixed(6), tgt.pmra, tgt.pmdec, 0, 13.9, 0]] }));
  const track = frames.filter((fr) => /^(wise_w2|spx_d6)/.test(fr.id)).sort((a, b) => a.mjd_mid - b.mjd_mid)
    .map((fr) => ({ mjd: fr.mjd_mid, ra: +(fr._t[0] + gauss() * 2e-4).toFixed(6), dec: +(fr._t[1] + gauss() * 2e-4).toFixed(6), instrument: fr.instrument }));
  const pmTot = Math.hypot(tgt.pmra, tgt.pmdec);
  const obj = { id: "target", name: f.title, kind: f.kind, ra: tgt.ra, dec: tgt.dec, epoch: 2018.0,
    motion: { measured: { pmra: tgt.pmra + 10, pmdec: tgt.pmdec - 10, pm_total: Math.round(pmTot), err: 60, unit: "mas/yr", n_epochs: track.length },
      reference: { source: "CatWISE2020 (mock)", pmra: tgt.pmra, pmdec: tgt.pmdec, unit: "mas/yr" }, agreement_pct: 99.6, track },
    spectrum: f.variable ? null : { unit_flux: "mJy", points: [1.0, 1.4, 2.0, 2.8, 3.3, 3.6, 4.0, 4.3, 4.6, 4.9].map((l, i) => ({ lambda_um: l, flux: l < 3 ? 0.01 : l > 4.2 ? 0.4 : l > 3.2 && l < 3.5 ? 0.03 : 0.12, err: 0.04, mjd: yearToMjd(2025.45 + (i % 2) * 0.5), detector: "D" + Math.min(6, 1 + Math.floor(i / 1.7)), flagged: false })),
      template: { name: "Y1 template (mock)", lambda_um: [1, 2, 3, 3.3, 3.6, 4, 4.5, 5], flux: [0.005, 0.01, 0.06, 0.02, 0.1, 0.18, 0.42, 0.38] }, notes: ["Undetected below 3 µm (mock)"] },
    lightcurve: { points: track.map((p, i) => ({ mjd: p.mjd, instrument: p.instrument, band: p.instrument === "WISE" ? "W2" : "D6", mag: +(13.9 + (f.variable ? 0.6 * Math.sin(i) : gauss() * 0.05)).toFixed(2), err: 0.05, saturated: i === 3 })), notes: [] },
    copilot: { en: `MOCK TEXT. ${f.title} moves about ${(pmTot / 1000).toFixed(1)} arcseconds per year across this field.`, az: `SINAQ MƏTNİ. ${f.title} hər il təxminən ${(pmTot / 1000).toFixed(1)} qövs saniyəsi hərəkət edir.`, model: "mock", facts_hash: "mock", audio_en: null, audio_az: null },
    flags: { saturated_in: [], warnings: [] } };
  fs.writeFileSync(path.join(dir, "objects", "target.json"), JSON.stringify(obj, null, 1));
  fs.writeFileSync(path.join(dir, "candidates.json"), JSON.stringify({ method: "mock", stats: { known_movers_in_field: 2, recovered: 2, new_candidates: 1 },
    items: [{ id: "c001", ra: f.ra + 0.01, dec: f.dec - 0.005, pm_total: 950, err: 120, class: "candidate", match: { gaia: null, catwise: null }, score: 0.82, object_file: null }] }));
  return { field_id: f.field_id, title: f.title, kind: "nasa_test_target", ra: f.ra, dec: f.dec, thumb: null, tags: f.tags };
}

fs.rmSync(OUT, { recursive: true, force: true });
const fields = [
  { field_id: "wise0855", title: "WISE 0855−0714", kind: "brown_dwarf", ra: 133.7871, dec: -7.2451, tags: ["motion", "brown dwarf"],
    target: { ra: 133.7871, dec: -7.2451, pmra: -8118, pmdec: 680, w2: 60, w1: 4 } },
  { field_id: "rdra", title: "R Draconis", kind: "variable_star", ra: 245.2908, dec: 66.7531, tags: ["variability"], variable: true,
    target: { ra: 245.2908, dec: 66.7531, pmra: 0, pmdec: 0, w2: 400, w1: 500 } },
];
const index = { schema_version: "1.0", generated_utc: new Date().toISOString(), fields: fields.map(buildField) };
fs.writeFileSync(path.join(OUT, "index.json"), JSON.stringify(index, null, 1));
console.log("devmock written to", OUT, index.fields.map((f) => f.field_id));
