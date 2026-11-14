// Types + loaders for docs/DATA_CONTRACT.md schema 1.0.
export interface FieldEntry {
  field_id: string; title: string; kind: string; ra: number; dec: number; thumb: string | null; tags: string[];
  base?: string; // resolved base URL of this field's folder (added by the loader)
  root?: string; // bundle root the entry came from
}
export interface BundleIndex { schema_version: string; generated_utc: string; fields: FieldEntry[] }
export interface Wcs { CRVAL1: number; CRVAL2: number; CRPIX1: number; CRPIX2: number; CD1_1: number; CD1_2: number; CD2_1: number; CD2_2: number; [k: string]: unknown }
export interface Frame {
  id: string; instrument: "WISE" | "SPHEREx"; band: string; lambda_um: [number, number];
  mjd_start: number; mjd_end: number; mjd_mid: number; date: string; n_inputs: number;
  file: string; mask_file: string | null; dtype: string; units: string;
  display: { p01: number; p50: number; p99: number; p999: number };
  quality: { masked_frac: number; saturated_frac: number; notes: string[] };
  source_files: string[];
}
export interface Sequence { id: string; label: string; default: boolean; frames: string[] }
export interface RgbComposite { id: string; label: string; r: string; g: string; b: string }
export interface Manifest {
  schema_version: string; field_id: string; title: string;
  center: { ra: number; dec: number; epoch: number };
  grid: { width: number; height: number; pixel_scale_arcsec: number; wcs: Wcs };
  frames: Frame[]; sequences: Sequence[]; rgb_composites?: RgbComposite[];
  objects?: string[]; catalogs?: Record<string, string>; candidates?: string; credits?: string[];
  build?: Record<string, unknown>;
}
export interface SpecPoint { lambda_um: number; flux: number; err?: number; mjd?: number; detector?: string; flagged?: boolean; saturated?: boolean }
export interface Catalog { catalog: string; ref_epoch: number; columns: string[]; rows: (string | number | null)[][] }
export interface MotionTrackPoint { mjd: number; ra: number; dec: number; instrument: string; kind?: string }
export interface ObjectInfo {
  id: string; name: string; kind: string; ra: number; dec: number; epoch: number;
  motion: null | {
    measured: null | { pmra: number; pmdec: number; pm_total: number; err: number; unit: string; n_epochs: number; baseline_yr?: number; parallax?: number; parallax_err?: number };
    reference: null | { source: string; pmra: number; pmdec: number; unit: string };
    agreement_pct: number | null; track: MotionTrackPoint[] | null;
  };
  spectrum: null | { unit_flux: string; points: SpecPoint[];
    template: null | { name: string; lambda_um: number[]; flux: number[] }; notes: string[];
    // DATA_CONTRACT §8 (optional)
    binned?: SpecPoint[] | null; usable?: boolean; method?: string; stats?: Record<string, unknown> };
  lightcurve: null | { points: { mjd: number; instrument: string; band: string; mag: number; err: number; saturated: boolean; kind?: string }[]; notes: string[];
    unit?: string; method?: string; period_days?: number | null;
    validation?: { folded?: null | { period_d?: number; source?: string; W1?: { best_period_d?: number }; W2?: { best_period_d?: number } } } | null };
  copilot: null | { en: string; az: string; model: string; ai_generated?: boolean; generated_from?: string; facts_hash?: string };
  flags: null | { saturated_in: string[]; warnings: string[] };
}
export interface Candidates {
  method: string; stats: { known_movers_in_field: number; recovered: number; new_candidates: number };
  items: { id: string; ra: number; dec: number; pm_total: number; err: number; class: string; match?: Record<string, string | null> | null; score?: number | null;
    object_file?: string | null; significance_sigma?: number; is_nasa_target?: boolean; kind?: string }[];
  caveat?: string;
}

// Bundle roots tried in order: real bundle, then the orchestrator's mock bundle.
// `?bundle=_mock` (or `?bundle=devmock` for the local generator output) forces one root; it sticks for the browser tab.
const ROOTS = ["/bundle/", "/bundle/_mock/"];
export function bundleOverride(): string | null {
  let b = new URLSearchParams(location.search).get("bundle");
  try {
    if (b !== null) { if (b) sessionStorage.setItem("skylapse.bundle", b); else sessionStorage.removeItem("skylapse.bundle"); }
    else b = sessionStorage.getItem("skylapse.bundle");
  } catch { /* storage blocked */ }
  if (!b || !/^[\w-]+$/.test(b)) return null;
  return b === "devmock" ? "/devmock/" : `/bundle/${b}/`;
}

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${url}`);
  const ct = r.headers.get("content-type") || "";
  if (ct.includes("text/html")) throw new Error(`not json: ${url}`); // SPA fallback page
  return (await r.json()) as T;
}

let indexPromise: Promise<{ index: BundleIndex; root: string }> | null = null;
export function loadIndex() {
  if (!indexPromise) {
    indexPromise = (async () => {
      const ov = bundleOverride();
      for (const root of ov ? [ov] : ROOTS) {
        try {
          const index = await getJson<BundleIndex>(root + "index.json");
          if (index.fields?.length) {
            index.fields.forEach((f) => { f.root = root; f.base = root + f.field_id + "/"; });
            return { index, root };
          }
        } catch { /* try next root */ }
      }
      throw new Error("No bundle found");
    })();
    indexPromise.catch(() => (indexPromise = null));
  }
  return indexPromise;
}

export async function loadField(fieldId: string) {
  const { index, root } = await loadIndex();
  let entry = index.fields.find((f) => f.field_id === fieldId);
  let base = entry?.base ?? root + fieldId + "/";
  if (!entry && !bundleOverride()) { // e.g. an old link to the mock field after the real bundle landed
    for (const r of ROOTS.filter((x) => x !== root)) {
      const other = await loadOptional<BundleIndex>(r + "index.json");
      const e = other?.fields?.find((f) => f.field_id === fieldId);
      if (e) { entry = { ...e, root: r, base: r + fieldId + "/" }; base = entry.base!; break; }
    }
  }
  const manifest = await loadOptional<Manifest>(base + "manifest.json");
  if (!manifest) throw new Error(`no manifest for ${fieldId}`);
  return { manifest, base, entry, isMock: base.includes("_mock/") || base.startsWith("/devmock/") || /mock/i.test(fieldId) };
}

/** Uncached JSON (live manifests change while a job runs). */
export async function loadFresh<T>(url: string): Promise<T | null> {
  try { return await getJson<T>(url + (url.includes("?") ? "&" : "?") + "t=" + Date.now()); } catch { return null; }
}
const jsonCache = new Map<string, Promise<unknown>>();
export async function loadOptional<T>(url: string): Promise<T | null> {
  let p = jsonCache.get(url);
  if (!p) { p = getJson<T>(url); jsonCache.set(url, p); p.catch(() => jsonCache.delete(url)); }
  try { return (await p) as T; } catch { return null; }
}

// Global binary cache (survives navigation; the home page pre-fills it in idle time). Keyed by URL.
const bufCache = new Map<string, Promise<ArrayBuffer>>();
function getBuf(url: string): Promise<ArrayBuffer> {
  let p = bufCache.get(url);
  if (!p) {
    p = fetch(url).then((r) => { if (!r.ok) throw new Error(`${r.status} ${url}`); return r.arrayBuffer(); });
    p.catch(() => bufCache.delete(url));
    bufCache.set(url, p);
  }
  return p;
}
export const isCached = (url: string) => bufCache.has(url);

/** Frame pixels (Float32, FITS order). Masks are loaded separately (only when the mask overlay is on). */
export async function loadFrame(base: string, f: Frame, w: number, h: number) {
  const data = new Float32Array(await getBuf(base + f.file));
  if (data.length !== w * h) throw new Error(`frame ${f.id}: size ${data.length} != ${w}x${h}`);
  return data;
}
export async function loadMask(base: string, f: Frame, w: number, h: number): Promise<Uint8Array | null> {
  if (!f.mask_file) return null;
  try { const m = new Uint8Array(await getBuf(base + f.mask_file)); return m.length === w * h ? m : null; } catch { return null; }
}

/** Fetch URLs into the frame cache, 2 at a time. */
export async function prefetchUrls(urls: string[]) {
  let i = 0;
  const worker = async () => { while (i < urls.length) { const u = urls[i++]; try { await getBuf(u); } catch { /* ignore */ } } };
  await Promise.all([worker(), worker()]);
}

/** Idle-time warm-up: fetch the default sequence of the given fields into the cache, 2 requests at a time. */
export function prefetchFields(fields: FieldEntry[]) {
  const idle = (cb: () => void) => ((window as unknown as { requestIdleCallback?: (c: () => void, o?: object) => void }).requestIdleCallback
    ? (window as unknown as { requestIdleCallback: (c: () => void, o?: object) => void }).requestIdleCallback(cb, { timeout: 3000 })
    : setTimeout(cb, 800));
  idle(async () => {
    const urls: string[] = [];
    for (const f of fields) {
      const m = await loadOptional<Manifest>(f.base + "manifest.json");
      if (!m) continue;
      const seq = m.sequences.find((s) => s.default) ?? m.sequences[0];
      const byId = new Map(m.frames.map((x) => [x.id, x]));
      seq?.frames.forEach((id) => { const fr = byId.get(id); if (fr) urls.push(f.base + fr.file); });
    }
    let i = 0;
    const worker = async () => { while (i < urls.length) { const u = urls[i++]; try { await getBuf(u); } catch { /* ignore */ } } };
    await Promise.all([worker(), worker()]);
  });
}

export const mjdToYear = (mjd: number) => 2000.0 + (mjd - 51544.5) / 365.25;
