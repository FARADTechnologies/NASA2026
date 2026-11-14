import { useEffect, useRef, useState } from "react";
import type { Catalog, Frame, Manifest, MotionTrackPoint } from "../lib/bundle";
import { mjdToYear } from "../lib/bundle";
import { pix2world, propagate, world2pix, fmtRaHms, fmtDecDms } from "../lib/wcs";

export interface PlayerProps {
  manifest: Manifest;
  image: ImageData | null;          // already stretched, north-up, full grid
  frame: Frame | null;
  catalogs: { gaia: Catalog | null; catwise: Catalog | null };
  track: MotionTrackPoint[] | null;
  overlay: string[];
  fovArcmin: number | null;
  centerRaDec: [number, number] | null;
  loadingText?: string;
  onPick?: (ra: number, dec: number) => void;
  targetLabel?: string;
}

/** Target position at `mjd`, linearly interpolated along the track (clamped at the ends). */
export function trackAt(track: MotionTrackPoint[], mjd: number): [number, number] | null {
  if (!track.length) return null;
  const t = [...track].sort((a, b) => a.mjd - b.mjd);
  if (mjd <= t[0].mjd) return [t[0].ra, t[0].dec];
  if (mjd >= t[t.length - 1].mjd) return [t[t.length - 1].ra, t[t.length - 1].dec];
  for (let i = 1; i < t.length; i++) if (mjd <= t[i].mjd) {
    const a = t[i - 1], b = t[i], f = (mjd - a.mjd) / (b.mjd - a.mjd || 1);
    return [a.ra + (b.ra - a.ra) * f, a.dec + (b.dec - a.dec) * f];
  }
  return null;
}

export function Player(p: PlayerProps) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const off = useRef<HTMLCanvasElement | null>(null);
  const [size, setSize] = useState(600);
  const [cursor, setCursor] = useState<[number, number] | null>(null);
  const { width: W, height: H, pixel_scale_arcsec: scale, wcs } = p.manifest.grid;
  const flipX = wcs.CD1_1 > 0;

  useEffect(() => {
    const el = wrapRef.current; if (!el) return;
    const ro = new ResizeObserver(() => setSize(Math.max(200, Math.floor(Math.min(el.clientWidth, el.clientHeight)))));
    ro.observe(el); return () => ro.disconnect();
  }, []);

  // crop window in canvas orientation (u to the right, v down = south)
  const cropPx = Math.min(W, Math.max(16, p.fovArcmin ? (p.fovArcmin * 60) / scale : W));
  let cu = W / 2, cv = H / 2;
  if (p.centerRaDec) {
    const [x, y] = world2pix(wcs, p.centerRaDec[0], p.centerRaDec[1]);
    if (x >= 0 && x < W && y >= 0 && y < H) { cu = (flipX ? W - 1 - x : x) + 0.5; cv = H - 1 - y + 0.5; }
  }
  const u0 = Math.min(W - cropPx, Math.max(0, cu - cropPx / 2));
  const v0 = Math.min(H - cropPx, Math.max(0, cv - cropPx / 2));
  const k = size / cropPx; // css px per data pixel

  const toScreen = (x: number, y: number): [number, number] => {
    const u = (flipX ? W - 1 - x : x) + 0.5, v = H - 1 - y + 0.5;
    return [(u - u0) * k, (v - v0) * k];
  };
  const fromScreen = (sx: number, sy: number): [number, number] => {
    const u = sx / k + u0 - 0.5, v = sy / k + v0 - 0.5;
    return [flipX ? W - 1 - u : u, H - 1 - v];
  };

  useEffect(() => {
    const c = canvasRef.current; if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    c.width = Math.round(size * dpr); c.height = Math.round(size * dpr);
    c.style.width = size + "px"; c.style.height = size + "px";
    const g = c.getContext("2d")!;
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.fillStyle = "#000"; g.fillRect(0, 0, size, size);
    if (p.image) {
      if (!off.current) off.current = document.createElement("canvas");
      const o = off.current; o.width = W; o.height = H;
      o.getContext("2d")!.putImageData(p.image, 0, 0);
      g.imageSmoothingEnabled = false;
      g.drawImage(o, u0, v0, cropPx, cropPx, 0, 0, size, size);
    }
    const year = p.frame ? mjdToYear(p.frame.mjd_mid) : null;
    const rCirc = Math.max(4, (4.5 / scale) * k); // catalogue circles stay smaller/thinner than the target ring

    const drawCat = (cat: Catalog, color: string, square: boolean, limit: number | null) => {
      if (year === null) return;
      const ci = (n: string) => cat.columns.indexOf(n);
      const [iRa, iDec, iPmra, iPmdec, iMag] = [ci("ra"), ci("dec"), ci("pmra"), ci("pmdec"), ci("mag")];
      g.lineWidth = 1; g.strokeStyle = color; g.fillStyle = color;
      // project everything in view first, then keep the brightest `limit` + every fast mover (µ > 100 mas/yr)
      const inView: { sx: number; sy: number; ra: number; dec: number; pmra: number; pmdec: number; mag: number; pm: number }[] = [];
      for (const row of cat.rows) {
        const ra = Number(row[iRa]), dec = Number(row[iDec]);
        const pmra = Number(row[iPmra]) || 0, pmdec = Number(row[iPmdec]) || 0;
        const [r1, d1] = propagate(ra, dec, pmra, pmdec, year, cat.ref_epoch);
        const [sx, sy] = toScreen(...world2pix(wcs, r1, d1));
        if (sx < -20 || sy < -20 || sx > size + 20 || sy > size + 20) continue;
        const m = iMag >= 0 && row[iMag] !== null ? Number(row[iMag]) : 99;
        inView.push({ sx, sy, ra, dec, pmra, pmdec, mag: Number.isFinite(m) ? m : 99, pm: Math.hypot(pmra, pmdec) });
      }
      let shown = inView;
      if (limit !== null && inView.length > limit) {
        const bright = new Set([...inView].sort((a, b) => a.mag - b.mag).slice(0, limit));
        shown = inView.filter((s) => bright.has(s) || s.pm > 100);
      }
      for (const { sx, sy, ra, dec, pmra, pmdec } of shown) {
        g.beginPath();
        if (square) g.rect(sx - rCirc, sy - rCirc, rCirc * 2, rCirc * 2); else g.arc(sx, sy, rCirc, 0, Math.PI * 2);
        g.stroke();
        const pm = Math.hypot(pmra, pmdec);
        if (pm > 100) { // proper-motion arrow: where it will be in 5 years
          const [r2, d2] = propagate(ra, dec, pmra, pmdec, year + 5, cat.ref_epoch);
          const [ex, ey] = toScreen(...world2pix(wcs, r2, d2));
          const ang = Math.atan2(ey - sy, ex - sx);
          const len = Math.hypot(ex - sx, ey - sy);
          if (len > rCirc + 4) {
            const bx = sx + Math.cos(ang) * rCirc, by = sy + Math.sin(ang) * rCirc;
            g.beginPath(); g.moveTo(bx, by); g.lineTo(ex, ey); g.stroke();
            g.beginPath(); g.moveTo(ex, ey);
            g.lineTo(ex - 8 * Math.cos(ang - 0.4), ey - 8 * Math.sin(ang - 0.4));
            g.lineTo(ex - 8 * Math.cos(ang + 0.4), ey - 8 * Math.sin(ang + 0.4)); g.closePath(); g.fill();
          }
        }
      }
    };
    if (p.overlay.includes("gaia") && p.catalogs.gaia) drawCat(p.catalogs.gaia, "rgba(124,252,154,0.6)", false, p.overlay.includes("gaiaall") ? null : 40);
    if (p.overlay.includes("catwise") && p.catalogs.catwise) drawCat(p.catalogs.catwise, "rgba(199,146,234,0.7)", true, p.overlay.includes("gaiaall") ? null : 40);

    if (p.overlay.includes("track") && p.track && p.track.length > 1) {
      g.strokeStyle = "rgba(255,93,143,0.55)"; g.lineWidth = 1.5; g.setLineDash([4, 4]);
      g.beginPath();
      p.track.forEach((t, i) => { const [sx, sy] = toScreen(...world2pix(wcs, t.ra, t.dec)); if (i) g.lineTo(sx, sy); else g.moveTo(sx, sy); });
      g.stroke(); g.setLineDash([]);
      for (const t of p.track) { // measured positions = small dots, model/predicted = hollow
        const [sx, sy] = toScreen(...world2pix(wcs, t.ra, t.dec));
        g.beginPath(); g.arc(sx, sy, 2.2, 0, Math.PI * 2);
        if (t.kind && t.kind !== "measured") { g.strokeStyle = "rgba(255,93,143,0.8)"; g.lineWidth = 1; g.stroke(); }
        else { g.fillStyle = "rgba(255,93,143,0.75)"; g.fill(); }
      }
      if (p.frame) {
        const pos = trackAt(p.track, p.frame.mjd_mid);
        if (pos) {
          const [sx, sy] = toScreen(...world2pix(wcs, pos[0], pos[1]));
          const r = Math.max(14, rCirc + 8);
          g.strokeStyle = "#ff5d8f"; g.lineWidth = 2.5;
          g.beginPath(); g.arc(sx, sy, r, 0, Math.PI * 2); g.stroke();
          if (p.targetLabel) {
            g.font = "700 13px Inter, system-ui";
            const tw = g.measureText(p.targetLabel).width;
            const lx = Math.min(size - tw - 14, Math.max(6, sx + r + 6)), ly = Math.max(18, sy - r - 4);
            g.fillStyle = "rgba(5,7,13,0.75)"; g.fillRect(lx - 5, ly - 14, tw + 10, 19);
            g.fillStyle = "#ff8fb1"; g.fillText(p.targetLabel, lx, ly);
          }
        }
      }
    }
    // scale bar: 1 arcmin
    const bar = (60 / scale) * k;
    if (bar < size * 0.6) {
      g.strokeStyle = "#e8ecf5"; g.lineWidth = 2; g.beginPath();
      g.moveTo(16, size - 18); g.lineTo(16 + bar, size - 18); g.stroke();
      g.fillStyle = "#e8ecf5"; g.font = "600 13px Inter, system-ui"; g.fillText("1′", 16 + bar / 2 - 5, size - 26);
    }
    // compass
    g.fillStyle = "rgba(232,236,245,0.85)"; g.font = "600 12px Inter, system-ui";
    g.fillText("N", size - 26, 20); g.fillText(flipX ? "E" : "E", flipX ? size - 12 : size - 52, 44);
    g.strokeStyle = "rgba(232,236,245,0.85)"; g.lineWidth = 1.5; g.beginPath();
    g.moveTo(size - 22, 40); g.lineTo(size - 22, 26); g.moveTo(size - 22, 40); g.lineTo(flipX ? size - 8 : size - 36, 40); g.stroke();
  }, [p.image, p.frame, p.overlay, p.catalogs, p.track, p.targetLabel, size, u0, v0, cropPx]);

  return (
    <div className="player-wrap" ref={wrapRef}>
      <div className="player-stage" style={{ width: size, height: size }}>
        <canvas
          ref={canvasRef}
          className="player-canvas"
          onMouseMove={(e) => {
            const r = (e.target as HTMLCanvasElement).getBoundingClientRect();
            const [x, y] = fromScreen(e.clientX - r.left, e.clientY - r.top);
            setCursor(pix2world(wcs, x, y));
          }}
          onMouseLeave={() => setCursor(null)}
          onClick={(e) => {
            if (!p.onPick) return;
            const r = (e.target as HTMLCanvasElement).getBoundingClientRect();
            const [x, y] = fromScreen(e.clientX - r.left, e.clientY - r.top);
            const [ra, dec] = pix2world(wcs, x, y); p.onPick(ra, dec);
          }}
        />
        {p.loadingText && <div className="player-loading">{p.loadingText}</div>}
        <div className="coord-readout mono">
          {cursor ? <>{fmtRaHms(cursor[0])} {fmtDecDms(cursor[1])}<span className="muted"> · {cursor[0].toFixed(4)}° {cursor[1].toFixed(4)}°</span></> : <span className="muted">hover for RA / Dec</span>}
        </div>
      </div>
    </div>
  );
}
