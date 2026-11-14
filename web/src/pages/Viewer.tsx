import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Candidates, Catalog, Frame, Manifest, MotionTrackPoint, ObjectInfo } from "../lib/bundle";
import { loadField, loadFrame, loadFresh, loadIndex, loadMask, loadOptional } from "../lib/bundle";
import { mean, percentiles, subtract, toImageData, toRgbImageData } from "../lib/render";
import { DEFAULTS, parseView, serializeView, type ViewState } from "../lib/url";
import { navigate } from "../lib/router";
import { matchRadiusDeg, sepDeg } from "../lib/resolve";
import { propagate } from "../lib/wcs";
import { Player, trackAt } from "../components/Player";
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
  const [showControls, setShowControls] = useState(false); // phone layout only
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
            const m = await loadFresh<Manifest>(st.manifest_url);
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
            if (near && near.d < matchRadiusDeg(near.f.kind)) fieldId = near.f.field_id;
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

  // target path: measured track if present, else a model path from the catalogue/measured proper motion
  const track: MotionTrackPoint[] | null = useMemo(() => {
    if (!obj) return null;
    if (obj.motion?.track?.length) return obj.motion.track;
    const pm = obj.motion?.measured ?? obj.motion?.reference;
    if (!pm || !Number.isFinite(obj.ra) || !Number.isFinite(obj.dec)) return null;
    const ep = obj.epoch || 2018.0;
    return [2010.0, 2026.9].map((y) => { const [ra, dec] = propagate(obj.ra, obj.dec, pm.pmra, pm.pmdec, y, ep); return { mjd: 51544.5 + (y - 2000) * 365.25, ra, dec, instrument: "model", kind: "model" }; });
  }, [obj]);

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
      // the first frame goes alone (full bandwidth → visible sooner), then up to 6 in parallel
      const limit = store.current.size === 0 && inflight === 0 ? 1 : store.current.size === 0 ? 1 : 6;
      while (alive && inflight < limit && queue.length) {
        const f = queue.shift()!; inflight++;
        loadFrame(base, f, W, H)
          .then((data) => { if (fieldRef.current === fieldAtStart) { store.current.set(f.id, { data, mask: store.current.get(f.id)?.mask ?? null }); setLoadedVer((x) => x + 1); } })
          .catch(() => alive && setFailed((s) => new Set(s).add(f.id)))
          .finally(() => { inflight--; pump(); });
      }
    };
    pump();
    return () => { alive = false; };
  }, [manifest, base, seqFrames, rgb, view.ref]);

  // masks only when the mask overlay is on (halves the requests for the default view)
  const wantMask = view.overlay.includes("mask");
  useEffect(() => {
    if (!manifest || !wantMask) return;
    const { width: W, height: H } = manifest.grid;
    const fieldAtStart = fieldRef.current;
    let alive = true;
    (async () => {
      for (const f of seqFrames) {
        const e = store.current.get(f.id);
        if (!alive || !e || e.mask || !f.mask_file) continue;
        const m = await loadMask(base, f, W, H);
        if (m && fieldRef.current === fieldAtStart) { e.mask = m; setLoadedVer((x) => x + 1); }
      }
    })();
    return () => { alive = false; };
  }, [manifest, base, seqFrames, wantMask, loadedVer > 0 && seqFrames.every((f) => store.current.has(f.id))]);

  const loaded = useMemo(() => new Set(store.current.keys()), [loadedVer]);
  const n = seqFrames.length;
  const idx = n ? Math.min(view.frame, n - 1) : 0;
  const cur = seqFrames[idx] ?? null;

  // playback: starts once ≥ 4 frames (or all, if fewer) are ready; advances to the next loaded frame
  const nReady = seqFrames.reduce((k, f) => k + (loaded.has(f.id) ? 1 : 0), 0);
  const canPlay = nReady >= Math.min(4, n);
  useEffect(() => {
    if (!playing || !canPlay || n < 2 || view.coadd || rgb) return;
    const t = setInterval(() => {
      setView((v) => {
        for (let s = 1; s <= n; s++) { const j = (v.frame + s) % n; if (store.current.has(seqFrames[j].id)) return { ...v, frame: j }; }
        return v;
      });
    }, view.speed);
    return () => clearInterval(t);
  }, [playing, canPlay, n, view.speed, seqFrames, view.coadd, rgb]);

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

  // click on the image: select the object under the cursor (target ring or a discovery candidate) and show its card
  const sideRef = useRef<HTMLDivElement>(null);
  const [flash, setFlash] = useState(0);
  const pick = useCallback((ra: number, dec: number) => {
    if (!manifest || !shownFrameRef.current) return;
    const tol = Math.max(12, manifest.grid.pixel_scale_arcsec * 4) / 3600; // ~4 px
    const hits: { id: string; d: number }[] = [];
    if (obj && track?.length) {
      const pos = trackAt(track, shownFrameRef.current.mjd_mid);
      if (pos) hits.push({ id: obj.id, d: sepDeg(pos[0], pos[1], ra, dec) });
    }
    for (const c of cands?.items ?? []) {
      const id = c.object_file?.match(/objects\/([^/]+)\.json$/)?.[1];
      if (id && manifest.objects?.includes(id)) hits.push({ id, d: sepDeg(c.ra, c.dec, ra, dec) });
    }
    const best = hits.filter((h) => h.d < tol).sort((a, b) => a.d - b.d)[0];
    if (!best) return;
    setObjectId(best.id); setFlash((x) => x + 1);
    sideRef.current?.querySelector(".obj-card")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [manifest, obj, cands, track]);

  // first-visit hint (dismissible; storage may be blocked → just show it)
  const [showHint, setShowHint] = useState(() => { try { return localStorage.getItem("skylapse.hint.v1") !== "done"; } catch { return true; } });
  const closeHint = () => { setShowHint(false); try { localStorage.setItem("skylapse.hint.v1", "done"); } catch { /* ignore */ } };

  // timing marks for demo-speed checks (performance.getEntriesByType("mark"))
  const marked = useRef({ first: false, play: false });
  const shownFrameRef = useRef<Frame | null>(null);
  useEffect(() => {
    if (image && !marked.current.first) { marked.current.first = true; performance.mark("skylapse:first-frame"); }
    if (canPlay && n > 1 && !marked.current.play) { marked.current.play = true; performance.mark("skylapse:playing"); }
  }, [image, canPlay, n]);

  if (error) return (
    <div className="page"><TopBar /><div className="empty-state"><h2>Not available yet</h2><p>{error}</p><a className="btn" href="/" onClick={(e) => { e.preventDefault(); navigate("/"); }}>Back to targets</a></div></div>
  );

  const nLoaded = seqFrames.filter((f) => loaded.has(f.id)).length;
  const span = seqFrames.length ? `${seqFrames[0].date.slice(0, 4)}–${seqFrames[n - 1].date.slice(0, 4)}` : "";
  const shownFrame = rgb ? frameById.get(rgb.r) ?? null : cur;
  shownFrameRef.current = shownFrame;

  return (
    <div className="page viewer">
      <TopBar title={manifest?.title} isMock={isMock} />
      <div className="viewer-grid">
        <ControlsPanel view={view} update={update} manifest={manifest} seqFrames={seqFrames} idx={idx} playing={playing}
          open={showControls} onClose={() => setShowControls(false)} />
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
          {showHint && manifest && (
            <div className="hint-card" role="note">
              <div className="hint-steps">
                <span><b>1</b> Watch the movie — 16 years of the same patch of sky</span>
                <span><b>2</b> Follow the <i className="ring-ico" /> circled target as it moves</span>
                <span><b>3</b> Click it for its story</span>
              </div>
              <button className="btn small" onClick={closeHint}>Got it</button>
            </div>
          )}
          {live && (
            <div className="live-banner">
              <span className="pulse" />
              <b>{live.state === "queued" ? "Live job queued — fetching WISE epochs…" : live.state === "wise_ready" ? "WISE frames ready · SPHEREx frames streaming…" : "SPHEREx frames streaming…"}</b>
              <div className="bar"><i style={{ width: `${Math.round((live.progress || 0) * 100)}%` }} /></div>
              <span className="mono">{Math.round((live.progress || 0) * 100)}%</span>
            </div>
          )}
          {manifest ? (
            <Player manifest={manifest} image={image} frame={shownFrame} catalogs={cats} track={track}
              overlay={view.overlay} fovArcmin={view.fov} centerRaDec={view.ra !== null && view.dec !== null ? [view.ra, view.dec] : null}
              loadingText={!image ? "Loading frames…" : undefined}
              targetLabel={view.overlay.includes("track") ? obj?.name : undefined} onPick={pick} />
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
            <button className="btn controls-toggle" onClick={() => setShowControls((x) => !x)}>⚙ Controls</button>
            <div className="span-label"><b className="mono">{span}</b> <span className="muted">{nLoaded < n ? `· loading ${nLoaded}/${n}` : `· ${n} frames`}{failed.size ? ` · ${failed.size} unavailable` : ""}</span></div>
          </div>
          {n > 0 && nReady < n && <div className="load-bar" title={`loading frames ${nReady}/${n}`}><i style={{ width: `${(100 * nReady) / n}%` }} /></div>}
          <Timeline frames={seqFrames} index={idx} loaded={loaded} onSelect={(i) => { setPlaying(false); update({ frame: i }); }} range={coaddRange}
            refId={view.diff === "ref" ? view.ref : view.diff === "first" ? seqFrames[0]?.id : undefined} />
        </main>
        <SidePanel panelRef={sideRef} flash={flash} frame={shownFrame} obj={obj} cands={cands} manifest={manifest} isMock={isMock}
          objectIds={manifest?.objects} objectId={objectId} onObject={setObjectId} />
      </div>
    </div>
  );
}

export function fmtLam(l: [number, number]) {
  return l[0] === l[1] ? `${l[0]} µm` : `${l[0].toFixed(2)}–${l[1].toFixed(2)} µm`;
}
export { DEFAULTS };
