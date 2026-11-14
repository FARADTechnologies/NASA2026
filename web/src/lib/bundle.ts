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
export interface Catalog { catalog: string; ref_epoch: number; columns: string[]; rows: (string | number | null)[][] }
export interface MotionTrackPoint { mjd: number; ra: number; dec: number; instrument: string }
export interface ObjectInfo {
  id: string; name: string; kind: string; ra: number; dec: number; epoch: number;
  motion: null | {
    measured: null | { pmra: number; pmdec: number; pm_total: number; err: number; unit: string; n_epochs: number };
    reference: null | { source: string; pmra: number; pmdec: number; unit: string };
    agreement_pct: number | null; track: MotionTrackPoint[] | null;
  };
  spectrum: null | { unit_flux: string; points: { lambda_um: number; flux: number; err: number; mjd: number; detector: string; flagged: boolean }[];
    template: null | { name: string; lambda_um: number[]; flux: number[] }; notes: string[] };
  lightcurve: null | { points: { mjd: number; instrument: string; band: string; mag: number; err: number; saturated: boolean }[]; notes: string[] };
  copilot: null | { en: string; az: string; model: string };
  flags: null | { saturated_in: string[]; warnings: string[] };
}
export interface Candidates {
  method: string; stats: { known_movers_in_field: number; recovered: number; new_candidates: number };
  items: { id: string; ra: number; dec: number; pm_total: number; err: number; class: string; match: Record<string, string | null>; score: number; object_file: string | null }[];
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
  const entry = index.fields.find((f) => f.field_id === fieldId);
  const base = entry?.base ?? root + fieldId + "/";
  const manifest = await getJson<Manifest>(base + "manifest.json");
  return { manifest, base, entry, isMock: root !== "/bundle/" || /mock/i.test(fieldId) };
}

export async function loadOptional<T>(url: string): Promise<T | null> {
  try { return await getJson<T>(url); } catch { return null; }
}

export async function loadFrame(base: string, f: Frame, w: number, h: number) {
  const r = await fetch(base + f.file);
  if (!r.ok) throw new Error(`${r.status} ${f.file}`);
  const buf = await r.arrayBuffer();
  const data = new Float32Array(buf);
  if (data.length !== w * h) throw new Error(`frame ${f.id}: size ${data.length} != ${w}x${h}`);
  let mask: Uint8Array | null = null;
  if (f.mask_file) {
    try {
      const m = await fetch(base + f.mask_file);
      if (m.ok) { const mb = new Uint8Array(await m.arrayBuffer()); if (mb.length === w * h) mask = mb; }
    } catch { /* optional */ }
  }
  return { data, mask };
}

export const mjdToYear = (mjd: number) => 2000.0 + (mjd - 51544.5) / 365.25;
