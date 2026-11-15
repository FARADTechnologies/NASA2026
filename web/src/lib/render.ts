// Display math (stretch / difference / co-add). Data stays FITS order (row 0 = south); flipping happens here.
export type Stretch = "linear" | "asinh" | "log";

export function percentiles(data: Float32Array, ps: number[]): number[] {
  const step = Math.max(1, Math.floor(data.length / 20000));
  const s: number[] = [];
  for (let i = 0; i < data.length; i += step) { const v = data[i]; if (Number.isFinite(v)) s.push(v); }
  if (!s.length) return ps.map(() => 0);
  s.sort((a, b) => a - b);
  return ps.map((p) => s[Math.min(s.length - 1, Math.max(0, Math.floor((p / 100) * s.length)))]);
}

export function subtract(a: Float32Array, b: Float32Array) {
  const out = new Float32Array(a.length);
  for (let i = 0; i < a.length; i++) out[i] = a[i] - b[i];
  return out;
}

export function mean(arrs: Float32Array[]) {
  const out = new Float32Array(arrs[0].length);
  const n = new Uint16Array(out.length);
  for (const a of arrs) for (let i = 0; i < a.length; i++) if (Number.isFinite(a[i])) { out[i] += a[i]; n[i]++; }
  for (let i = 0; i < out.length; i++) out[i] = n[i] ? out[i] / n[i] : NaN;
  return out;
}

const curve = (t: number, mode: Stretch) => {
  if (t <= 0) return 0; if (t >= 1) return 1;
  if (mode === "asinh") return Math.asinh(t * 10) / Math.asinh(10);
  if (mode === "log") return Math.log10(1 + 1000 * t) / 3;
  return t;
};

export interface RenderOpts { vmin: number; vmax: number; stretch: Stretch; invert: boolean; mask?: Uint8Array | null; showMask?: boolean; flipX?: boolean; /** false for difference images, where 0 means "no change" */ hatchNoData?: boolean }

/** Float32 FITS-order image -> RGBA ImageData with north up. */
export function toImageData(data: Float32Array, w: number, h: number, o: RenderOpts): ImageData {
  const img = new ImageData(w, h);
  const px = img.data;
  const span = o.vmax - o.vmin || 1;
  const lut = new Uint8ClampedArray(1024);
  for (let i = 0; i < 1024; i++) { const v = curve(i / 1023, o.stretch) * 255; lut[i] = o.invert ? 255 - v : v; }
  for (let y = 0; y < h; y++) {
    const srcRow = (h - 1 - y) * w; // flip: canvas row 0 = north = last FITS row
    for (let x = 0; x < w; x++) {
      const sx = o.flipX ? w - 1 - x : x;
      const v = data[srcRow + sx];
      const di = (y * w + x) * 4;
      let g: number;
      let r: number, gg: number, b: number;
      if (!Number.isFinite(v) || (v === 0 && o.hatchNoData !== false)) {
        // no data here (outside the survey tile): quiet diagonal hatch, so it reads as "no coverage", not as a broken image
        const h = ((x + y) % 6) === 0;
        if (o.invert) { r = gg = b = h ? 206 : 226; } else { r = h ? 44 : 22; gg = h ? 52 : 27; b = h ? 70 : 38; }
        px[di] = r; px[di + 1] = gg; px[di + 2] = b; px[di + 3] = 255;
        continue;
      }
      const t = (v - o.vmin) / span; g = lut[t <= 0 ? 0 : t >= 1 ? 1023 : (t * 1023) | 0];
      r = g; gg = g; b = g;
      if (o.showMask && o.mask) {
        const m = o.mask[srcRow + sx];
        if (m & 2) { r = r * 0.55 + 255 * 0.45; gg = gg * 0.55 + 140 * 0.45; b = b * 0.55 + 26 * 0.45; }
        else if (m & 1) { r = r * 0.6 + 128 * 0.4; gg = gg * 0.6 + 128 * 0.4; b = b * 0.6 + 140 * 0.4; }
      }
      px[di] = r; px[di + 1] = gg; px[di + 2] = b; px[di + 3] = 255;
    }
  }
  return img;
}

/** RGB composite of three frames (each stretched by its own percentiles). */
export function toRgbImageData(r: Float32Array, g: Float32Array, b: Float32Array, w: number, h: number, stretch: Stretch, pmin: number, pmax: number, flipX = false) {
  const img = new ImageData(w, h);
  const chans = [r, g, b].map((d) => { const [lo, hi] = percentiles(d, [pmin, pmax]); return { d, lo, span: hi - lo || 1 }; });
  for (let y = 0; y < h; y++) {
    const srcRow = (h - 1 - y) * w;
    for (let x = 0; x < w; x++) {
      const sx = flipX ? w - 1 - x : x; const di = (y * w + x) * 4;
      for (let c = 0; c < 3; c++) { const ch = chans[c]; const v = ch.d[srcRow + sx]; img.data[di + c] = Number.isFinite(v) ? curve((v - ch.lo) / ch.span, stretch) * 255 : 0; }
      img.data[di + 3] = 255;
    }
  }
  return img;
}
