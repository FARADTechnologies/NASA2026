import type { Wcs } from "./bundle";
const D2R = Math.PI / 180;

/** World (deg) -> 0-based array pixel (x along row, y = row index from SOUTH, FITS order). */
export function world2pix(w: Wcs, ra: number, dec: number): [number, number] {
  const a = ra * D2R, d = dec * D2R, a0 = w.CRVAL1 * D2R, d0 = w.CRVAL2 * D2R;
  const cosc = Math.sin(d0) * Math.sin(d) + Math.cos(d0) * Math.cos(d) * Math.cos(a - a0);
  const xi = (Math.cos(d) * Math.sin(a - a0)) / cosc / D2R;
  const eta = (Math.cos(d0) * Math.sin(d) - Math.sin(d0) * Math.cos(d) * Math.cos(a - a0)) / cosc / D2R;
  const det = w.CD1_1 * w.CD2_2 - w.CD1_2 * w.CD2_1;
  const dx = (w.CD2_2 * xi - w.CD1_2 * eta) / det;
  const dy = (-w.CD2_1 * xi + w.CD1_1 * eta) / det;
  return [dx + w.CRPIX1 - 1, dy + w.CRPIX2 - 1];
}

/** 0-based array pixel -> world (deg). */
export function pix2world(w: Wcs, x: number, y: number): [number, number] {
  const dx = x + 1 - w.CRPIX1, dy = y + 1 - w.CRPIX2;
  const xi = (w.CD1_1 * dx + w.CD1_2 * dy) * D2R;
  const eta = (w.CD2_1 * dx + w.CD2_2 * dy) * D2R;
  const a0 = w.CRVAL1 * D2R, d0 = w.CRVAL2 * D2R;
  const den = Math.cos(d0) - eta * Math.sin(d0);
  const a = a0 + Math.atan2(xi, den);
  const d = Math.atan2(Math.sin(d0) + eta * Math.cos(d0), Math.hypot(xi, den));
  let ra = a / D2R; if (ra < 0) ra += 360; if (ra >= 360) ra -= 360;
  return [ra, d / D2R];
}

/** Gaia-style linear propagation (SCIENCE_NOTES §3). pm in mas/yr, pmra already × cos δ. */
export function propagate(ra: number, dec: number, pmra: number, pmdec: number, tYear: number, refYear: number): [number, number] {
  const dt = tYear - refYear;
  return [ra + (pmra * dt) / (3.6e6 * Math.cos(dec * D2R)), dec + (pmdec * dt) / 3.6e6];
}

export function fmtRaHms(ra: number) {
  const h = ra / 15; const hh = Math.floor(h); const m = (h - hh) * 60; const mm = Math.floor(m); const ss = (m - mm) * 60;
  return `${String(hh).padStart(2, "0")}h${String(mm).padStart(2, "0")}m${ss.toFixed(2).padStart(5, "0")}s`;
}
export function fmtDecDms(dec: number) {
  const s = dec < 0 ? "−" : "+"; const a = Math.abs(dec); const dd = Math.floor(a); const m = (a - dd) * 60; const mm = Math.floor(m); const ss = (m - mm) * 60;
  return `${s}${String(dd).padStart(2, "0")}°${String(mm).padStart(2, "0")}′${ss.toFixed(1).padStart(4, "0")}″`;
}
