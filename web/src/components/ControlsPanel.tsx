import { useState } from "react";
import { Check, CircleHelp, Link2, X } from "lucide-react";
import type { Frame, Manifest } from "../lib/bundle";
import type { ViewState } from "../lib/url";

/** Small "?" with a native tooltip (works on hover and long-press). */
const Tip = ({ text }: { text: string }) => <span className="tip" title={text} aria-label={text}><CircleHelp size={13} strokeWidth={1.75} /></span>;

export function ControlsPanel({ view, update, manifest, seqFrames, idx, open, onClose }: {
  view: ViewState; update: (p: Partial<ViewState>) => void; manifest: Manifest | null; seqFrames: Frame[]; idx: number; playing: boolean;
  open?: boolean; onClose?: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const full = manifest ? (manifest.grid.width * manifest.grid.pixel_scale_arcsec) / 60 : 8.8;
  const fov = view.fov ?? full;
  const n = seqFrames.length;
  const co = /^(\d+)-(\d+)$/.exec(view.coadd);
  const coA = co ? +co[1] : 0, coB = co ? +co[2] : Math.max(0, n - 1);
  const toggleOverlay = (k: string) => update({ overlay: view.overlay.includes(k) ? view.overlay.filter((x) => x !== k) : [...view.overlay, k] });
  const advancedActive = !!view.coadd || view.min !== 30 || view.max !== 99.8 || view.overlay.includes("catwise") || view.overlay.includes("mask") || view.overlay.includes("gaiaall");

  return (
    <aside className={"panel controls" + (open ? " open" : "")}>
      {onClose && <button className="btn small controls-close" onClick={onClose}><X size={14} strokeWidth={1.75} /> Close controls</button>}
      <section>
        <h3>What to watch <Tip text="Each sequence is a movie of the same patch of sky at one infrared wavelength, from 2010 to 2026." /></h3>
        <select value={view.seq} onChange={(e) => update({ seq: e.target.value, frame: 0, coadd: "" })}>
          {manifest?.sequences.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
        {!!manifest?.rgb_composites?.length && (
          <div className="row">
            <label className="check" title="SPHEREx sees 102 colours. This shows three of them as red / green / blue: cold brown dwarfs look red because they glow only at long wavelengths.">
              <input type="checkbox" checked={!!view.rgb} onChange={(e) => update({ rgb: e.target.checked ? manifest.rgb_composites![manifest.rgb_composites!.length - 1].id : "" })} />
              <span>Spectral Fingerprint <small className="muted">(infrared colours as RGB)</small></span>
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
        <h3>Compare times <Tip text="Shows only what changed: moving objects appear as a black/white pair (black = where it was, white = where it is now)." /></h3>
        <div className="seg seg-grid">
          {([["none", "Off"], ["first", "vs 2010"], ["prev", "vs previous"], ["ref", "vs chosen"]] as const).map(([k, l]) => (
            <button key={k} className={view.diff === k ? "on" : ""} disabled={!!view.coadd}
              title={k === "first" ? "Each frame minus the first (2010) frame" : k === "prev" ? "Each frame minus the one before it" : k === "ref" ? "Each frame minus a frame you choose" : "Normal movie"}
              onClick={() => update({ diff: k, ref: k === "ref" ? (view.ref || seqFrames[idx]?.id || "") : view.ref })}>{l}</button>
          ))}
        </div>
        {view.diff === "ref" && (
          <button className="btn small" onClick={() => update({ ref: seqFrames[idx]?.id ?? "" })}>Use current frame ({seqFrames[idx]?.date}) as reference</button>
        )}
      </section>

      <section>
        <h3>Brightness <Tip text="How faint things are made visible. 'asinh' shows faint and bright stars together." /></h3>
        <div className="seg">
          {(["linear", "asinh", "log"] as const).map((s) => (
            <button key={s} className={view.stretch === s ? "on" : ""} onClick={() => update({ stretch: s })}>{s}</button>
          ))}
        </div>
        <label className="check"><input type="checkbox" checked={view.invert} onChange={(e) => update({ invert: e.target.checked })} /><span>Dark stars on white <kbd>I</kbd></span></label>
      </section>

      <section>
        <h3>Zoom <Tip text="Width of the sky patch shown. The full field is about a quarter of the Moon's width." /></h3>
        <label className="slider">
          <span>Width <b className="mono">{fov.toFixed(1)}′</b></span>
          <input type="range" min={1} max={full} step={0.1} value={fov} onChange={(e) => update({ fov: +e.target.value >= full - 0.05 ? null : +e.target.value })} />
        </label>
      </section>

      <section>
        <h3>Show on the image</h3>
        <label className="check"><input type="checkbox" checked={view.overlay.includes("track")} onChange={() => toggleOverlay("track")} /><span><i className="ring-ico" />Target ring + its 16-year path</span></label>
        <label className="check" title="Circles = stars catalogued by ESA's Gaia satellite, moved to the date of this frame using their measured motion.">
          <input type="checkbox" checked={view.overlay.includes("gaia")} onChange={() => toggleOverlay("gaia")} /><span><i className="dot" style={{ borderColor: "var(--gaia)" }} />Known stars (ESA Gaia) at this date</span>
        </label>
      </section>

      <details className="advanced" open={advancedActive || undefined}>
        <summary>Advanced</summary>
        <section>
          <h3>Contrast <Tip text="Percent of pixels shown as pure black / pure white." /></h3>
          <label className="slider">
            <span>Black point <b className="mono">{view.min}%</b></span>
            <input type="range" min={0} max={50} step={0.5} value={view.min} onChange={(e) => update({ min: Math.min(+e.target.value, view.max - 1) })} />
          </label>
          <label className="slider">
            <span>White point <b className="mono">{view.max}%</b></span>
            <input type="range" min={60} max={100} step={0.1} value={view.max} onChange={(e) => update({ max: Math.max(+e.target.value, view.min + 1) })} />
          </label>
        </section>
        <section>
          <label className="check" title="Averages several frames into one deeper image (fainter things become visible; moving things smear).">
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
          <h3>More overlays</h3>
          <label className="check" title="By default only the 40 brightest Gaia stars in view and all fast-moving stars are circled, so crowded fields stay readable.">
            <input type="checkbox" checked={view.overlay.includes("gaiaall")} onChange={() => toggleOverlay("gaiaall")} /><span>All Gaia stars (crowded fields get busy)</span>
          </label>
          <label className="check"><input type="checkbox" checked={view.overlay.includes("catwise")} onChange={() => toggleOverlay("catwise")} /><span><i className="dot sq" style={{ borderColor: "var(--catwise)" }} />CatWISE2020 infrared catalogue</span></label>
          <label className="check" title="Pixels the instrument flagged: orange = too bright (saturated), grey = bad/masked. Data quality flags from the archive.">
            <input type="checkbox" checked={view.overlay.includes("mask")} onChange={() => toggleOverlay("mask")} /><span><i className="sw" style={{ background: "var(--sat)" }} />Saturated / <i className="sw" style={{ background: "#80808c" }} />flagged pixels</span>
          </label>
        </section>
      </details>

      <section>
        <button className="btn wide" onClick={async () => {
          try { await navigator.clipboard.writeText(location.href); setCopied(true); setTimeout(() => setCopied(false), 1800); } catch { prompt("Copy this link:", location.href); }
        }}>{copied ? <><Check size={15} strokeWidth={2} /> Link copied</> : <><Link2 size={15} strokeWidth={1.75} /> Share this view</>}</button>
        <p className="hint muted"><kbd>Space</kbd> play · <kbd>←</kbd><kbd>→</kbd> step · <kbd>D</kbd> compare</p>
      </section>
    </aside>
  );
}
