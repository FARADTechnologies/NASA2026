// Live-field warm-up (home page idle time): submit the job (cached on the API → instant), read its status and manifest,
// and pull the default sequence's frames into the frame cache. The viewer then opens a warmed field without network waits.
import type { Manifest } from "./bundle";
import { loadFresh, prefetchUrls } from "./bundle";

export interface WarmLive { status_url: string; state: string; message?: string; manifest_url: string; manifest: Manifest }
const warm = new Map<string, WarmLive>();
export const liveKey = (ra: number, dec: number, fov: number) => `${ra.toFixed(4)},${dec.toFixed(4)},${fov.toFixed(1)}`;
export const getWarmLive = (ra: number, dec: number, fov: number) => warm.get(liveKey(ra, dec, fov)) ?? null;

export async function prewarmLive(ra: number, dec: number, fov: number): Promise<void> {
  try {
    const r = await fetch("/api/fields", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ ra, dec, fov_arcmin: fov }) });
    if (!r.ok || !(r.headers.get("content-type") || "").includes("json")) return;
    const job = await r.json() as { status_url?: string; cached?: boolean };
    if (!job.status_url || !job.cached) return; // only warm fields that are already built
    const st = await loadFresh<{ state: string; message?: string; manifest_url?: string | null }>(job.status_url);
    if (!st?.manifest_url || !["done", "wise_ready", "spherex_partial"].includes(st.state)) return;
    const manifest = await loadFresh<Manifest>(st.manifest_url);
    if (!manifest) return;
    warm.set(liveKey(ra, dec, fov), { status_url: job.status_url, state: st.state, message: st.message, manifest_url: st.manifest_url, manifest });
    const base = st.manifest_url.replace(/manifest\.json.*$/, "");
    const seq = manifest.sequences.find((s) => s.default) ?? manifest.sequences[0];
    const byId = new Map(manifest.frames.map((f) => [f.id, f]));
    await prefetchUrls((seq?.frames ?? []).map((id) => byId.get(id)).filter(Boolean).map((f) => base + f!.file));
  } catch { /* API offline: the viewer shows its normal fallback */ }
}
