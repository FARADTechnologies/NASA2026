import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Candidates, Catalog, Frame, Manifest, ObjectInfo } from "../lib/bundle";
import { loadField, loadFrame, loadIndex, loadOptional } from "../lib/bundle";
import { mean, percentiles, subtract, toImageData, toRgbImageData } from "../lib/render";
import { DEFAULTS, parseView, serializeView, type ViewState } from "../lib/url";
import { navigate } from "../lib/router";
import { sepDeg } from "../lib/resolve";
import { Player } from "../components/Player";
import { Timeline } from "../components/Timeline";
import { ControlsPanel } from "../components/ControlsPanel";
import { SidePanel } from "../components/SidePanel";
import { TopBar } from "../components/TopBar";

type FrameData = { data: Float32Array; mask: Uint8Array | null };

export function Viewer({ search }: { search: string }) {
  const [view, setView] = useState<ViewState>(() => parseView(search));
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [base, setBase] = useState("");
  const [isMock, setIsMock] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cats, setCats] = useState<{ gaia: Catalog | null; catwise: Catalog | null }>({ gaia: null, catwise: null });
  const [obj, setObj] = useState<ObjectInfo | null>(null);
  const [cands, setCands] = useState<Candidates | null>(null);
  const [playing, setPlaying] = useState(() => !new URLSearchParams(search).has("frame")); // shared link with a frame opens paused there
  const store = useRef(new Map<string, FrameData>());
  const [loadedVer, setLoadedVer] = useState(0);
  const [failed, setFailed] = useState<Set<string>>(new Set());

  const [objectId, setObjectId] = useState("");
  useEffect(() => {
    if (!objectId || !base) { setObj(null); return; }
    let alive = true;
    loadOptional<ObjectInfo>(base + `objects/${objectId}.json`).then((o) => alive && setObj(o));
    return () => { alive = false; };
  }, [objectId, base]);
  const update = useCallback((patch: Partial<ViewState>) => setView((v) => ({ ...v, ...patch })), []);

  // apply a (new or refreshed) manifest. `fresh` = a different field → clear frame cache.
  const fieldRef = useRef("");
  const applyManifest = useCallback(async (m: Manifest, b: string, mock: boolean, alive: () => boolean) => {
    const fresh = fieldRef.current !== m.field_id;
    fieldRef.current = m.field_id;
    if (fresh) { store.current.clear(); setLoadedVer((x) => x + 1); setFailed(new Set()); }
    setManifest(m); setBase(b); setIsMock(mock); setError(null);
    setView((v) => ({ ...v, seq: m.sequences.some((s) => s.id === v.seq) ? v.seq : (m.sequences.find((s) => s.default) ?? m.sequences[0])?.id ?? "" }));
    if (!fresh) return;
    const c = m.catalogs ?? {};
    const [gaia, catwise] = await Promise.all([c.gaia ? loadOptional<Catalog>(b + c.gaia) : null, c.catwise ? loadOptional<Catalog>(b + c.catwise) : null]);
    if (!alive()) return;
    setCats({ gaia, catwise });
    const wanted = new URLSearchParams(location.search).get("obj");
    setObjectId(wanted && m.objects?.includes(wanted) ? wanted : m.objects?.includes("target") ? "target" : m.objects?.[0] ?? "");
    if (m.candidates) loadOptional<Candidates>(b + m.candidates).then((x) => alive() && setCands(x));
  }, []);

  // live job for coordinates without a precomputed field (DATA_CONTRACT §7)
  const [live, setLive] = useState<{ state: string; progress: number } | null>(null);
  const runLive = useCallback(async (ra: number, dec: number, fov: number, alive: () => boolean) => {
    setLive({ state: "queued", progress: 0 });
    let job: { field_id: string; status_url: string } | null = null;
    try {
      const r = await fetch("/api/fields", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ ra, dec, fov_arcmin: fov }) });
      if (r.ok && (r.headers.get("content-type") || "").includes("json")) job = await r.json();
    } catch { /* API offline */ }
    if (!job?.status_url) {
      setLive(null);
      setError(`Live fetching is not available right now, so RA ${ra.toFixed(4)}°, Dec ${dec.toFixed(4)}° cannot be built on the fly. The NASA targets on the home page always work.`);
      return;
    }
    let lastKey = ""; let misses = 0;
    while (alive()) {
      let st: { state: string; progress: number; manifest_url?: string } | null = null;
      try { const r = await fetch(job.status_url, { cache: "no-store" }); if (r.ok) st = await r.json(); } catch { /* retry */ }
      if (!st) { if (++misses > 15) { setError("The live job stopped answering. Please try again in a minute."); return; } }
      else {
        misses = 0;
        setLive({ state: st.state, progress: st.progress ?? 0 });
        if (st.state === "error") { setError("We could not build this field (the survey servers may be busy). Please try again, or pick a NASA target."); return; }
        if (st.manifest_url && st.state !== "queued") {
          const key = `${st.state}|${st.progress}`;
          if (key !== lastKey) {
            lastKey = key;
            const m = await loadOptional<Manifest>(st.manifest_url);
            if (m && alive()) await applyManifest(m, st.manifest_url.replace(/manifest\.json.*$/, ""), false, alive);
          }
        }
        if (st.state === "done") { setLive(null); return; }
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
  }, [applyManifest]);

  // resolve field: explicit field, nearest bundled field to ra/dec, or a live job
  useEffect(() => {
    let alive = true;
    const isAlive = () => alive;
    (async () => {
      try {
        let fieldId = view.field;
        if (!fieldId) {
          const { index } = await loadIndex();
          if (view.ra !== null && view.dec !== null && Number.isFinite(view.ra) && Number.isFinite(view.dec)) {
            const near = index.fields.map((f) => ({ f, d: sepDeg(f.ra, f.dec, view.ra!, view.dec!) })).sort((a, b) => a.d - b.d)[0];
            if (near && near.d < 0.1) fieldId = near.f.field_id;
            else return runLive(view.ra, view.dec, view.fov ?? 8.8, isAlive);
          } else fieldId = index.fields[0].field_id;
          if (alive) update({ field: fieldId });
        }
        const { manifest, base, isMock } = await loadField(fieldId);
        if (alive) await applyManifest(manifest, base, isMock, isAlive);
      } catch (e) {
        if (alive) setError("This field could not be loaded. Please pick another target.");
        console.error(e);
      }
    })();
    return () => { alive = false; };
  }, [view.field]);

  const frameById = useMemo(() => new Map((manifest?.frames ?? []).map((f) => [f.id, f])), [manifest]);
  const seq = manifest?.sequences.find((s) => s.id === view.seq) ?? null;
  const seqFrames: Frame[] = useMemo(() => (seq ? seq.frames.map((id) => frameById.get(id)).filter((f): f is Frame => !!f) : []), [seq, frameById]);
  const rgb = manifest?.rgb_composites?.find((r) => r.id === view.rgb) ?? null;

  // load frames of the active sequence (+ rgb + ref) progressively, ≤ 6 in flight
  useEffect(() => {
    if (!manifest) return;
    let alive = true;
    const { width: W, height: H } = manifest.grid;
    const want: Frame[] = [...seqFrames];
    if (rgb) for (const id of [rgb.r, rgb.g, rgb.b]) { const f = frameById.get(id); if (f) want.push(f); }
    if (view.ref) { const f = frameById.get(view.ref); if (f) want.push(f); }
    // load current frame first, then the rest in time order
    const start = Math.min(view.frame, Math.max(0, seqFrames.length - 1));
    want.sort((a, b) => (a === seqFrames[start] ? -1 : b === seqFrames[start] ? 1 : 0));
    const queue = want.filter((f, i, arr) => arr.indexOf(f) === i && !store.current.has(f.id));
    let inflight = 0;
    const fieldAtStart = fieldRef.current;
    const pump = () => {
      while (alive && inflight < 6 && queue.length) {
        const f = queue.shift()!; inflight++;
        loadFrame(base, f, W, H)
          .then((d) => { if (fieldRef.current === fieldAtStart) { store.current.set(f.id, d); setLoadedVer((x) => x + 1); } })
          .catch(() => alive && setFailed((s) => new Set(s).add(f.id)))
          .finally(() => { inflight--; pump(); });
      }
    };
    pump();
    return () => { alive = false; };
  }, [manifest, base, seqFrames, rgb, view.ref]);

  const loaded = useMemo(() => new Set(store.current.keys()), [loadedVer]);
  const n = seqFrames.length;
  const idx = n ? Math.min(view.frame, n - 1) : 0;
  const cur = seqFrames[idx] ?? null;

  // playback: advance to the next loaded frame
  useEffect(() => {
    if (!playing || n < 2 || view.coadd || rgb) return;
    const t = setInterval(() => {
      setView((v) => {
        for (let s = 1; s <= n; s++) { const j = (v.frame + s) % n; if (store.current.has(seqFrames[j].id)) return { ...v, frame: j }; }
        return v;
      });
    }, view.speed);
    return () => clearInterval(t);
  }, [playing, n, view.speed, seqFrames, view.coadd, rgb]);

  // keyboard
  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input, select, textarea")) return;
      if (e.code === "Space") { e.preventDefault(); setPlaying((p) => !p); }
      else if (e.key === "ArrowRight") { setPlaying(false); setView((v) => ({ ...v, frame: n ? (v.frame + 1) % n : 0 })); }
      else if (e.key === "ArrowLeft") { setPlaying(false); setView((v) => ({ ...v, frame: n ? (v.frame - 1 + n) % n : 0 })); }
      else if (e.key === "i") setView((v) => ({ ...v, invert: !v.invert }));
      else if (e.key === "d") setView((v) => ({ ...v, diff: v.diff === "none" ? "first" : "none" }));
    };
    window.addEventListener("keydown", on); return () => window.removeEventListener("keydown", on);
  }, [n]);

  // URL sync (replace, throttled by React batching; frame excluded while playing to avoid history spam)
  useEffect(() => {
    if (!view.field) return;
    const q = serializeView({ ...view, frame: playing ? 0 : view.frame });
    const t = setTimeout(() => navigate(`/view?${q}`, true), 250);
    return () => clearTimeout(t);
  }, [view, playing]);

  const coaddRange: [number, number] | null = useMemo(() => {
    const m = /^(\d+)-(\d+)$/.exec(view.coadd); if (!m || !n) return null;
    const a = Math.min(+m[1], n - 1), b = Math.min(+m[2], n - 1); return [Math.min(a, b), Math.max(a, b)];
  }, [view.coadd, n]);

  // compute the displayed image
  const { image, note } = useMemo((): { image: ImageData | null; note: string } => {
    if (!manifest) return { image: null, note: "" };
    const { width: W, height: H, wcs } = manifest.grid; const flipX = wcs.CD1_1 > 0;
    if (rgb) {
      const [r, g, b] = [rgb.r, rgb.g, rgb.b].map((id) => store.current.get(id)?.data);
      if (!r || !g || !b) return { image: null, note: "Loading fingerprint…" };
      return { image: toRgbImageData(r, g, b, W, H, view.stretch, view.min, view.max, flipX), note: rgb.label };
    }
    if (!cur) return { image: null, note: "" };
    let arr: Float32Array | undefined; let isDiff = false; let label = "";
    if (coaddRange) {
      const parts = seqFrames.slice(coaddRange[0], coaddRange[1] + 1).map((f) => store.current.get(f.id)?.data).filter((x): x is Float32Array => !!x);
      if (!parts.length) return { image: null, note: "Loading…" };
      arr = mean(parts); label = `Co-add of ${parts.length} frames`;
    } else {
      arr = store.current.get(cur.id)?.data;
      if (!arr) return { image: null, note: "Loading frame…" };
    }
    if (view.diff !== "none" && !coaddRange) {
      const refF = view.diff === "first" ? seqFrames[0] : view.diff === "prev" ? seqFrames[(idx - 1 + n) % n] : frameById.get(view.ref) ?? seqFrames[0];
      const refD = refF && store.current.get(refF.id)?.data;
      if (refD) { arr = subtract(arr, refD); isDiff = true; label = `Difference: this frame − ${refF.date} (${refF.instrument} ${refF.band})`; }
    }
    let vmin: number, vmax: number;
    if (isDiff) {
      const abs = new Float32Array(arr.length); for (let i = 0; i < arr.length; i++) abs[i] = Math.abs(arr[i]);
      // symmetric range = k × robust sigma; the white-point slider controls k (99.5% → 6σ), zero = mid grey
      const sig = 1.4826 * percentiles(abs, [50])[0] || 1; const a = sig * Math.max(2, (view.max - 60) / 6.6); vmin = -a; vmax = a;
    } else if (!coaddRange && view.min === 1 && [99, 99.9].includes(view.max) && cur.display) {
      vmin = cur.display.p01; vmax = view.max === 99 ? cur.display.p99 : cur.display.p999;
    } else [vmin, vmax] = percentiles(arr, [view.min, view.max]);
    const mask = coaddRange ? null : store.current.get(cur.id)?.mask ?? null;
    return { image: toImageData(arr, W, H, { vmin, vmax, stretch: isDiff ? "linear" : view.stretch, invert: view.invert, mask, showMask: view.overlay.includes("mask"), flipX }), note: label };
  }, [manifest, cur, loadedVer, view.diff, view.ref, view.stretch, view.min, view.max, view.invert, view.overlay, coaddRange, rgb, idx]);

  if (error) return (
    <div className="page"><TopBar /><div className="empty-state"><h2>Not available yet</h2><p>{error}</p><a className="btn" href="/" onClick={(e) => { e.preventDefault(); navigate("/"); }}>Back to targets</a></div></div>
  );

  const nLoaded = seqFrames.filter((f) => loaded.has(f.id)).length;
  const span = seqFrames.length ? `${seqFrames[0].date.slice(0, 4)}–${seqFrames[n - 1].date.slice(0, 4)}` : "";
  const shownFrame = rgb ? frameById.get(rgb.r) ?? null : cur;

  return (
    <div className="page viewer">
      <TopBar title={manifest?.title} isMock={isMock} />
      <div className="viewer-grid">
        <ControlsPanel view={view} update={update} manifest={manifest} seqFrames={seqFrames} idx={idx} playing={playing} />
        <main className="stage">
          <div className="frame-label">
            {shownFrame ? (
              <>
                <div className="fl-date mono">{rgb ? shownFrame.date.slice(0, 7) : shownFrame.date}</div>
                <div className="fl-meta">
                  <span className={"badge " + (shownFrame.instrument === "WISE" ? "b-wise" : "b-spx")}>{rgb ? "SPHEREx" : shownFrame.instrument}</span>
                  <span className="fl-band">{rgb ? "RGB D6 / D3 / D1" : `${shownFrame.band} · ${fmtLam(shownFrame.lambda_um)}`}</span>
                  {!rgb && <span className="muted mono">frame {idx + 1}/{n}</span>}
                </div>
              </>
            ) : <div className="fl-date skeleton-text">Loading…</div>}
            {note && <div className="fl-note">{note}</div>}
          </div>
          {live && (
            <div className="live-banner">
              <span className="pulse" />
              <b>{live.state === "queued" ? "Live job queued — fetching WISE epochs…" : live.state === "wise_ready" ? "WISE frames ready · SPHEREx frames streaming…" : "SPHEREx frames streaming…"}</b>
              <div className="bar"><i style={{ width: `${Math.round((live.progress || 0) * 100)}%` }} /></div>
              <span className="mono">{Math.round((live.progress || 0) * 100)}%</span>
            </div>
          )}
          {manifest ? (
            <Player manifest={manifest} image={image} frame={shownFrame} catalogs={cats} track={obj?.motion?.track ?? null}
              overlay={view.overlay} fovArcmin={view.fov} centerRaDec={view.ra !== null && view.dec !== null ? [view.ra, view.dec] : null}
              loadingText={!image ? "Loading frames…" : undefined} />
          ) : <div className="player-wrap"><div className="skeleton-box">{live && <div className="skeleton-msg">Building this field from WISE and SPHEREx archives — the first frames usually appear in under a minute.</div>}</div></div>}
          <div className="transport">
            <button className="btn icon" title="Previous frame (←)" onClick={() => { setPlaying(false); update({ frame: (idx - 1 + n) % Math.max(1, n) }); }}>⏮</button>
            <button className="btn primary play" title="Play / pause (space)" onClick={() => setPlaying((p) => !p)}>{playing ? "❚❚ Pause" : "▶ Play"}</button>
            <button className="btn icon" title="Next frame (→)" onClick={() => { setPlaying(false); update({ frame: (idx + 1) % Math.max(1, n) }); }}>⏭</button>
            <label className="speed">
              <span>Speed</span>
              <input type="range" min={40} max={1500} step={10} value={1540 - view.speed} onChange={(e) => update({ speed: 1540 - +e.target.value })} />
              <span className="mono">{(1000 / view.speed).toFixed(1)} fps</span>
            </label>
            <div className="span-label"><b className="mono">{span}</b> <span className="muted">{nLoaded < n ? `· loading ${nLoaded}/${n}` : `· ${n} frames`}{failed.size ? ` · ${failed.size} unavailable` : ""}</span></div>
          </div>
          <Timeline frames={seqFrames} index={idx} loaded={loaded} onSelect={(i) => { setPlaying(false); update({ frame: i }); }} range={coaddRange}
            refId={view.diff === "ref" ? view.ref : view.diff === "first" ? seqFrames[0]?.id : undefined} />
        </main>
        <SidePanel frame={shownFrame} obj={obj} cands={cands} manifest={manifest} isMock={isMock}
          objectIds={manifest?.objects} objectId={objectId} onObject={setObjectId} />
      </div>
    </div>
  );
}

export function fmtLam(l: [number, number]) {
  return l[0] === l[1] ? `${l[0]} µm` : `${l[0].toFixed(2)}–${l[1].toFixed(2)} µm`;
}
export { DEFAULTS };
