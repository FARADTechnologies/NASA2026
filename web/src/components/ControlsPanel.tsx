import { useState } from "react";
import type { Frame, Manifest } from "../lib/bundle";
import type { ViewState } from "../lib/url";

export function ControlsPanel({ view, update, manifest, seqFrames, idx }: {
  view: ViewState; update: (p: Partial<ViewState>) => void; manifest: Manifest | null; seqFrames: Frame[]; idx: number; playing: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const full = manifest ? (manifest.grid.width * manifest.grid.pixel_scale_arcsec) / 60 : 8.8;
  const fov = view.fov ?? full;
  const n = seqFrames.length;
  const co = /^(\d+)-(\d+)$/.exec(view.coadd);
  const coA = co ? +co[1] : 0, coB = co ? +co[2] : Math.max(0, n - 1);
  const toggleOverlay = (k: string) => update({ overlay: view.overlay.includes(k) ? view.overlay.filter((x) => x !== k) : [...view.overlay, k] });

  return (
    <aside className="panel controls">
      <section>
        <h3>Sequence</h3>
        <select value={view.seq} onChange={(e) => update({ seq: e.target.value, frame: 0, coadd: "" })}>
          {manifest?.sequences.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
        {!!manifest?.rgb_composites?.length && (
          <div className="row">
            <label className="check">
              <input type="checkbox" checked={!!view.rgb} onChange={(e) => update({ rgb: e.target.checked ? manifest.rgb_composites![manifest.rgb_composites!.length - 1].id : "" })} />
              <span>Spectral Fingerprint <small className="muted">(RGB = D6 / D3 / D1)</small></span>
            </label>
            {view.rgb && manifest.rgb_composites!.length > 1 && (
              <select value={view.rgb} onChange={(e) => update({ rgb: e.target.value })}>
                {manifest.rgb_composites!.map((r) => <option key={r.id} value={r.id}>{r.label}</option>)}
              </select>
            )}
          </div>
        )}
      </section>

      <section>
        <h3>Stretch</h3>
        <div className="seg">
          {(["linear", "asinh", "log"] as const).map((s) => (
            <button key={s} className={view.stretch === s ? "on" : ""} onClick={() => update({ stretch: s })}>{s}</button>
          ))}
        </div>
        <label className="slider">
          <span>Black point <b className="mono">{view.min}%</b></span>
          <input type="range" min={0} max={50} step={0.5} value={view.min} onChange={(e) => update({ min: Math.min(+e.target.value, view.max - 1) })} />
        </label>
        <label className="slider">
          <span>White point <b className="mono">{view.max}%</b></span>
          <input type="range" min={60} max={100} step={0.1} value={view.max} onChange={(e) => update({ max: Math.max(+e.target.value, view.min + 1) })} />
        </label>
        <label className="check"><input type="checkbox" checked={view.invert} onChange={(e) => update({ invert: e.target.checked })} /><span>Invert (dark stars on white) <kbd>I</kbd></span></label>
      </section>

      <section>
        <h3>Field of view</h3>
        <label className="slider">
          <span>Width <b className="mono">{fov.toFixed(1)}′</b></span>
          <input type="range" min={1} max={full} step={0.1} value={fov} onChange={(e) => update({ fov: +e.target.value >= full - 0.05 ? null : +e.target.value })} />
        </label>
      </section>

      <section>
        <h3>Compare times</h3>
        <div className="seg">
          {([["none", "Off"], ["first", "− first"], ["prev", "− previous"], ["ref", "− chosen"]] as const).map(([k, l]) => (
            <button key={k} className={view.diff === k ? "on" : ""} disabled={!!view.coadd}
              onClick={() => update({ diff: k, ref: k === "ref" ? (view.ref || seqFrames[idx]?.id || "") : view.ref })}>{l}</button>
          ))}
        </div>
        {view.diff === "ref" && (
          <button className="btn small" onClick={() => update({ ref: seqFrames[idx]?.id ?? "" })}>Use current frame ({seqFrames[idx]?.date}) as reference</button>
        )}
        <label className="check">
          <input type="checkbox" checked={!!view.coadd} onChange={(e) => update({ coadd: e.target.checked ? `0-${Math.max(0, n - 1)}` : "", diff: "none" })} />
          <span>Co-add (average a time range)</span>
        </label>
        {view.coadd && n > 0 && (
          <div className="coadd">
            <label className="slider"><span>From <b className="mono">{seqFrames[Math.min(coA, n - 1)]?.date}</b></span>
              <input type="range" min={0} max={n - 1} value={coA} onChange={(e) => update({ coadd: `${Math.min(+e.target.value, coB)}-${coB}` })} /></label>
            <label className="slider"><span>To <b className="mono">{seqFrames[Math.min(coB, n - 1)]?.date}</b></span>
              <input type="range" min={0} max={n - 1} value={coB} onChange={(e) => update({ coadd: `${coA}-${Math.max(+e.target.value, coA)}` })} /></label>
          </div>
        )}
      </section>

      <section>
        <h3>Overlays</h3>
        <label className="check"><input type="checkbox" checked={view.overlay.includes("gaia")} onChange={() => toggleOverlay("gaia")} /><span><i className="dot" style={{ borderColor: "var(--gaia)" }} />Gaia DR3 stars at this date</span></label>
        <label className="check"><input type="checkbox" checked={view.overlay.includes("catwise")} onChange={() => toggleOverlay("catwise")} /><span><i className="dot sq" style={{ borderColor: "var(--catwise)" }} />CatWISE2020</span></label>
        <label className="check"><input type="checkbox" checked={view.overlay.includes("track")} onChange={() => toggleOverlay("track")} /><span><i className="dash" />Target track</span></label>
        <label className="check"><input type="checkbox" checked={view.overlay.includes("mask")} onChange={() => toggleOverlay("mask")} /><span><i className="sw" style={{ background: "var(--sat)" }} />Saturated / <i className="sw" style={{ background: "#80808c" }} />masked pixels</span></label>
      </section>

      <section>
        <button className="btn primary wide" onClick={async () => {
          try { await navigator.clipboard.writeText(location.href); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch { prompt("Copy this link:", location.href); }
        }}>{copied ? "✓ Link copied" : "🔗 Share this view"}</button>
        <p className="hint muted"><kbd>Space</kbd> play · <kbd>←</kbd><kbd>→</kbd> step · <kbd>D</kbd> difference</p>
      </section>
    </aside>
  );
}
