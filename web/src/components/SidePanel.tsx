import { useState } from "react";
import type { Candidates, Frame, Manifest, ObjectInfo } from "../lib/bundle";
import { mjdToYear } from "../lib/bundle";
import { ScatterChart, type Series } from "./ScatterChart";

const pct = (x: number) => (x * 100).toFixed(x < 0.01 ? 2 : 1) + "%";
const NA = <span className="muted">not available yet</span>;

type LC = NonNullable<ObjectInfo["lightcurve"]>;
/** True when the values are a relative brightness index (saturated stars), not calibrated magnitudes. */
const isRelativeIndex = (lc: LC) => /relative/i.test(lc.unit ?? "") || (lc.points.length > 0 && lc.points.every((p) => p.kind === "relative_wing_index"));

function periodLine(lc: LC): string | null {
  const f = lc.validation?.folded;
  const fmt = (d?: number) => (d != null ? `${Math.round(d)} d` : null);
  if (f && (f.W1?.best_period_d || f.W2?.best_period_d)) {
    const found = [f.W1?.best_period_d ? `${fmt(f.W1.best_period_d)} (W1)` : null, f.W2?.best_period_d ? `${fmt(f.W2.best_period_d)} (W2)` : null].filter(Boolean).join(" / ");
    return `Period found: ${found}${f.period_d ? ` · known: ${f.period_d} d${f.source ? ` (${f.source})` : ""}` : ""}`;
  }
  if (lc.period_days) return `Period found: ${Math.round(lc.period_days)} d`;
  const n = lc.notes?.find((t) => /best period/i.test(t));
  return n ?? null;
}

function LightCurve({ lc }: { lc: LC }) {
  const rel = isRelativeIndex(lc);
  // one series per instrument + band (W1 / W2 / SPHEREx)
  const groups = new Map<string, LC["points"]>();
  for (const p of lc.points) { const k = p.instrument === "WISE" ? `WISE ${p.band}` : p.instrument; if (!groups.has(k)) groups.set(k, []); groups.get(k)!.push(p); }
  const color = (k: string) => (k === "WISE W1" ? "var(--wise-2)" : k.startsWith("WISE") ? "var(--wise)" : "var(--spherex)");
  const period = periodLine(lc);
  const firstNote = rel ? lc.notes?.[0] : null;
  const otherNotes = (lc.notes ?? []).filter((t) => t !== firstNote && t !== period);
  return (
    <>
      <div className="muted small y-caption">{rel ? "Relative brightness (0 = median, up = brighter)" : "Magnitude (up = brighter)"}</div>
      <ScatterChart xLabel="year" yLabel={rel ? "rel. brightness" : "magnitude"} invertY
        series={[...groups.entries()].map(([k, pts]) => ({ name: k, color: color(k), points: pts.map((p) => ({ x: mjdToYear(p.mjd), y: p.mag, err: p.err, hollow: rel ? false : p.saturated })) }))}
        hollowLabel="saturated (less reliable)" />
      {rel && <div className="small lc-note">Saturated core: brightness index measured from the star's outer wings (not a calibrated magnitude).</div>}
      {period && <div className="period-line">{period}</div>}
      {otherNotes.length > 0 && (
        <details className="lc-more"><summary className="muted small">How this was measured</summary>
          {otherNotes.map((t) => <div key={t} className="muted small">{t}</div>)}
        </details>
      )}
    </>
  );
}

const SPEC_BANDS = [
  { x0: 3.2, x1: 3.45, label: "CH₄ 3.3", color: "var(--band-a)" },
  { x0: 4.4, x1: 4.85, label: "W2 / D6 4.6", color: "var(--band-b)" },
];
/** Binned spectrum = main curve (line + points + error bars); single measurements faint, coloured by epoch; flagged hidden unless asked. */
function spectrumSeries(sp: NonNullable<ObjectInfo["spectrum"]>, showFlagged: boolean): Series[] {
  const pts = (sp.points ?? []).filter((p) => showFlagged || !p.flagged);
  if (sp.binned?.length) {
    return [
      { name: "single measurements", color: "var(--muted)", faint: true, points: pts.map((p) => ({ x: p.lambda_um, y: p.flux, hollow: p.flagged || p.saturated })) },
      { name: "SPHEREx (binned)", color: "var(--spherex)", connect: true, points: sp.binned.map((p) => ({ x: p.lambda_um, y: p.flux, err: p.err, hollow: p.saturated })) },
    ];
  }
  return spectrumByEpoch(pts as SpecPt[]);
}

const EPOCH_COLORS = ["var(--spherex)", "var(--wise)", "var(--target)", "var(--gaia)", "var(--ai)", "var(--muted)"];
type SpecPt = NonNullable<ObjectInfo["spectrum"]>["points"][number];
/** Group spectrum points into epochs (gap > 30 d) so each epoch gets its own colour (LVF: one star, different λ per visit). */
function spectrumByEpoch(points: SpecPt[]) {
  const sorted = [...points].sort((a, b) => (a.mjd ?? 0) - (b.mjd ?? 0));
  const groups: SpecPt[][] = [];
  for (const p of sorted) { const g = groups[groups.length - 1]; if (g && (p.mjd ?? 0) - (g[g.length - 1].mjd ?? 0) <= 30) g.push(p); else groups.push([p]); }
  return groups.map((g, i) => {
    const y = mjdToYear(g[0].mjd ?? 61000);
    const name = `${Math.floor(y)} ${y % 1 < 0.5 ? "spring" : "autumn"}`;
    return { name: groups.length > 1 ? name : "SPHEREx", color: EPOCH_COLORS[i % EPOCH_COLORS.length],
      points: g.map((p) => ({ x: p.lambda_um, y: p.flux, err: p.err, hollow: p.flagged || p.saturated })) };
  });
}

export function SidePanel({ frame, obj, cands, manifest, isMock, objectIds, objectId, onObject, panelRef, flash }: {
  panelRef?: React.Ref<HTMLDivElement>; flash?: number;
  frame: Frame | null; obj: ObjectInfo | null; cands: Candidates | null; manifest: Manifest | null; isMock: boolean;
  objectIds?: string[]; objectId?: string; onObject?: (id: string) => void;
}) {
  const [lang, setLang] = useState<"en" | "az">("en");
  const [showFlagged, setShowFlagged] = useState(false);
  const [more, setMore] = useState(false);
  const m = obj?.motion;
  const coming = [
    !(m?.measured && m.measured.pm_total > 0) && !m?.reference ? "motion" : null,
    !obj?.lightcurve?.points?.length ? "light curve" : null,
    !obj?.spectrum ? "spectrum" : null,
    !obj?.copilot ? "AI explanation (EN / AZ)" : null,
  ].filter(Boolean) as string[];
  return (
    <aside className="panel side" ref={panelRef as React.Ref<HTMLElement>}>
      {isMock && <div className="mock-banner">Demo data (mock) — real survey frames replace this automatically.</div>}

      <section className="card">
        <h3>This frame</h3>
        {frame ? (
          <dl className="meta">
            <dt>Date</dt><dd className="mono">{frame.date}</dd>
            <dt>Instrument</dt><dd>{frame.instrument} {frame.band}</dd>
            <dt>Wavelength</dt><dd className="mono">{frame.lambda_um[0] === frame.lambda_um[1] ? `${frame.lambda_um[0]} µm` : `${frame.lambda_um[0]}–${frame.lambda_um[1]} µm`}</dd>
            <dt>Images combined</dt><dd className="mono">{frame.n_inputs}</dd>
            <dt>Masked pixels</dt><dd className="mono">{pct(frame.quality.masked_frac)}</dd>
            <dt>Saturated pixels</dt><dd className={"mono" + (frame.quality.saturated_frac > 0 ? " warn" : "")}>{pct(frame.quality.saturated_frac)}</dd>
            {frame.quality.notes.length > 0 && <><dt>Notes</dt><dd>{frame.quality.notes.join("; ")}</dd></>}
          </dl>
        ) : NA}
      </section>

      <section className={"card obj-card" + (flash ? " flash" : "")} key={"obj" + (flash ?? 0)}>
        <div className="card-head">
          <h3>{obj?.name ?? manifest?.title ?? "Object"}</h3>
          {objectIds && objectIds.length > 1 && onObject && (
            <select className="obj-pick" value={objectId} onChange={(e) => onObject(e.target.value)} aria-label="Choose object">
              {objectIds.map((id) => <option key={id} value={id}>{id === "target" ? "Target" : id}</option>)}
            </select>
          )}
        </div>
        {obj ? (
          <>
            <div className="muted kind">{obj.kind.replace(/_/g, " ")}</div>
            {m?.measured && m.measured.pm_total > 0 ? (
              <div className="motion">
                <dl className="facts">
                  <dt>Motion we measured</dt><dd className="mono"><b>{Math.round(m.measured.pm_total)}</b> ± {Math.round(m.measured.err)} mas/yr</dd>
                  {m.reference && <><dt>Published value</dt><dd className="mono">{Math.round(Math.hypot(m.reference.pmra, m.reference.pmdec))} mas/yr</dd></>}
                  {m.agreement_pct != null && <><dt>Agreement</dt><dd className="agree">{m.agreement_pct.toFixed(1)}%</dd></>}
                  <dt>Fit</dt><dd>{m.measured.n_epochs} epochs{m.measured.baseline_yr ? ` over ${m.measured.baseline_yr.toFixed(1)} years` : ""}</dd>
                </dl>
                {m.reference && <div className="muted small ref-src">Published: {m.reference.source}</div>}
                <details className="lc-more">
                  <summary className="muted small">Components (µα*, µδ)</summary>
                  <table className="pm">
                    <thead><tr><th /><th>µ<sub>α*</sub></th><th>µ<sub>δ</sub></th><th>total</th></tr></thead>
                    <tbody>
                      <tr><td>Measured</td><td>{Math.round(m.measured.pmra)}</td><td>{Math.round(m.measured.pmdec)}</td><td>{Math.round(m.measured.pm_total)} ± {Math.round(m.measured.err)}</td></tr>
                      {m.reference && <tr><td title={m.reference.source}>Published</td><td>{Math.round(m.reference.pmra)}</td><td>{Math.round(m.reference.pmdec)}</td><td>{Math.round(Math.hypot(m.reference.pmra, m.reference.pmdec))}</td></tr>}
                    </tbody>
                  </table>
                  <div className="muted small">mas/yr</div>
                </details>
              </div>
            ) : m?.reference ? (
              <div className="motion">
                <div className="muted small" style={{ marginBottom: 4 }}>Reference motion (published, not our measurement)</div>
                <table className="pm">
                  <thead><tr><th /><th>µ<sub>α*</sub></th><th>µ<sub>δ</sub></th><th>total</th></tr></thead>
                  <tbody>
                    <tr><td title={m.reference.source}>Published</td><td>{Math.round(m.reference.pmra)}</td><td>{Math.round(m.reference.pmdec)}</td><td>{Math.round(Math.hypot(m.reference.pmra, m.reference.pmdec))}</td></tr>
                  </tbody>
                </table>
                <div className="muted small ref-src">{m.reference.source} · mas/yr</div>
              </div>
            ) : null}
            {obj.flags?.warnings?.length || obj.flags?.saturated_in?.length ? (
              <div className="notes">
                <div className="notes-h">Data notes</div>
                <ul>
                  {(obj.flags?.warnings ?? []).map((w) => <li key={w}>{w}</li>)}
                  {obj.flags?.saturated_in?.length ? <li>Saturated in: {obj.flags.saturated_in.join(", ")}</li> : null}
                </ul>
              </div>
            ) : null}
          </>
        ) : <span className="muted small">No object details for this field — the movie, overlays and controls all work.</span>}
      </section>

      {obj?.copilot && (
        <section className="card" data-section="copilot">
          <div className="card-head">
            <h3>In plain words</h3>
            <div className="seg tiny">
              <button data-lang="en" className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>EN</button>
              <button data-lang="az" className={lang === "az" ? "on" : ""} onClick={() => setLang("az")}>AZ</button>
            </div>
          </div>
          {/* text and AI label are rendered together — the text is never shown without the label */}
          <figure className="copilot-block">
            <p className={"copilot" + (more ? "" : " clamp")}>{obj.copilot[lang]}</p>
            {obj.copilot[lang].length > 240 && <button className="link-btn" onClick={() => setMore((x) => !x)}>{more ? (lang === "az" ? "Daha az" : "Show less") : (lang === "az" ? "Davamını oxu" : "Read more")}</button>}
            <figcaption className="ai-label" title={obj.copilot.generated_from ? `facts: ${obj.copilot.generated_from}` : undefined}>
              {lang === "az" ? "Ölçdüyümüz faktlardan süni intellekt (AI) ilə yaradılıb" : "AI-generated from our measured facts"}
              {obj.copilot.model ? <> · model: <span className="mono">{obj.copilot.model}</span></> : null}
            </figcaption>
          </figure>
        </section>
      )}

      {obj?.spectrum && <section className="card" data-section="spectrum">
        <div className="card-head">
          <h3>Spectrum <span className="muted small" style={{ textTransform: "none", letterSpacing: 0 }}>SPHEREx 0.75–5 µm</span></h3>
          {obj?.spectrum?.points?.some((p) => p.flagged) && obj.spectrum.usable !== false && (
            <label className="check tiny-check"><input type="checkbox" checked={showFlagged} onChange={(e) => setShowFlagged(e.target.checked)} /><span>flagged</span></label>
          )}
        </div>
        {!obj?.spectrum ? NA : obj.spectrum.usable === false ? (
          <div className="honest-note">
            <b>No reliable spectrum for this target.</b>
            {(obj.spectrum.notes?.length ? obj.spectrum.notes : ["It is too bright for the SPHEREx detectors (saturated)."]).map((t) => <p key={t}>{t}</p>)}
          </div>
        ) : obj.spectrum.points?.length || obj.spectrum.binned?.length ? (
          <>
            <ScatterChart xLabel="wavelength (µm)" yLabel={`flux (${obj.spectrum.unit_flux})`} xRange={[0.7, 5.05]}
              bands={SPEC_BANDS}
              series={spectrumSeries(obj.spectrum, showFlagged)}
              line={obj.spectrum.template?.lambda_um?.length ? { name: obj.spectrum.template.name, color: "var(--muted)", xs: obj.spectrum.template.lambda_um, ys: obj.spectrum.template.flux } : undefined}
              hollowLabel="flagged / saturated" />
            {obj.spectrum.method && <div className="muted small caption" title={obj.spectrum.method}>Method: {obj.spectrum.method}</div>}
            {obj.spectrum.notes?.map((t) => <div key={t} className="muted small">{t}</div>)}
          </>
        ) : NA}
      </section>}

      {obj?.lightcurve?.points?.length ? (
        <section className="card" data-section="lightcurve">
          <h3>Light curve</h3>
          <LightCurve lc={obj.lightcurve} />
        </section>
      ) : null}

      {obj && coming.length > 0 && <div className="coming muted small">Coming soon for this object: {coming.join(", ")}.</div>}

      {cands && (
        <section className="card">
          <h3>Auto-discovery in this field</h3>
          <div className="stats3">
            <div><b>{cands.stats.known_movers_in_field}</b><span>known movers</span></div>
            <div><b>{cands.stats.recovered}</b><span>recovered</span></div>
            <div><b>{cands.stats.new_candidates}</b><span>candidates</span></div>
          </div>
        </section>
      )}
    </aside>
  );
}
