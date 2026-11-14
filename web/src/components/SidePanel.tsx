import { useState } from "react";
import type { Candidates, Frame, Manifest, ObjectInfo } from "../lib/bundle";
import { mjdToYear } from "../lib/bundle";
import { ScatterChart } from "./ScatterChart";

const pct = (x: number) => (x * 100).toFixed(x < 0.01 ? 2 : 1) + "%";
const NA = <span className="muted">not available yet</span>;

const EPOCH_COLORS = ["#4cc9f0", "#ffd166", "#ff5d8f", "#7cfc9a", "#c792ea", "#f4a259"];
type SpecPt = NonNullable<ObjectInfo["spectrum"]>["points"][number];
/** Group spectrum points into epochs (gap > 30 d) so each epoch gets its own colour (LVF: one star, different λ per visit). */
function spectrumByEpoch(points: SpecPt[]) {
  const sorted = [...points].sort((a, b) => a.mjd - b.mjd);
  const groups: SpecPt[][] = [];
  for (const p of sorted) { const g = groups[groups.length - 1]; if (g && p.mjd - g[g.length - 1].mjd <= 30) g.push(p); else groups.push([p]); }
  return groups.map((g, i) => {
    const y = mjdToYear(g[0].mjd);
    const name = `${Math.floor(y)} ${y % 1 < 0.5 ? "spring" : "autumn"}`;
    return { name: groups.length > 1 ? name : "SPHEREx", color: EPOCH_COLORS[i % EPOCH_COLORS.length],
      points: g.map((p) => ({ x: p.lambda_um, y: p.flux, err: p.err, hollow: p.flagged })) };
  });
}

export function SidePanel({ frame, obj, cands, manifest, isMock, objectIds, objectId, onObject }: {
  frame: Frame | null; obj: ObjectInfo | null; cands: Candidates | null; manifest: Manifest | null; isMock: boolean;
  objectIds?: string[]; objectId?: string; onObject?: (id: string) => void;
}) {
  const [lang, setLang] = useState<"en" | "az">("en");
  const m = obj?.motion;
  return (
    <aside className="panel side">
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

      <section className="card">
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
                {m.agreement_pct != null && (
                  <div className="big-stat"><b>{m.agreement_pct.toFixed(1)}%</b><span>agreement with {m.reference?.source ?? "reference"}</span></div>
                )}
                <table className="pm">
                  <thead><tr><th /><th>µ<sub>α*</sub></th><th>µ<sub>δ</sub></th><th>total</th></tr></thead>
                  <tbody>
                    <tr><td>Measured</td><td>{m.measured.pmra}</td><td>{m.measured.pmdec}</td><td><b>{m.measured.pm_total}</b> ± {m.measured.err}</td></tr>
                    {m.reference && <tr><td>{m.reference.source}</td><td>{m.reference.pmra}</td><td>{m.reference.pmdec}</td><td>{Math.round(Math.hypot(m.reference.pmra, m.reference.pmdec))}</td></tr>}
                  </tbody>
                </table>
                <div className="muted small">mas/yr · fitted over {m.measured.n_epochs} epochs</div>
              </div>
            ) : <div className="muted small">No significant motion measured.</div>}
            {obj.flags?.warnings?.length ? <ul className="warnings">{obj.flags.warnings.map((w) => <li key={w}>⚠ {w}</li>)}</ul> : null}
            {obj.flags?.saturated_in?.length ? <div className="warn small">⚠ Saturated in: {obj.flags.saturated_in.join(", ")}</div> : null}
          </>
        ) : NA}
      </section>

      <section className="card">
        <div className="card-head">
          <h3>AI Copilot</h3>
          <div className="seg tiny">
            <button className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>EN</button>
            <button className={lang === "az" ? "on" : ""} onClick={() => setLang("az")}>AZ</button>
          </div>
        </div>
        {obj?.copilot ? <p className="copilot">{obj.copilot[lang]}</p> : NA}
        {obj?.copilot && <div className="muted small">Written by AI only from the measured facts above.</div>}
      </section>

      <section className="card">
        <h3>Spectrum</h3>
        {obj?.spectrum?.points?.length ? (
          <>
            <ScatterChart xLabel="wavelength (µm)" yLabel={`flux (${obj.spectrum.unit_flux})`}
              series={spectrumByEpoch(obj.spectrum.points)}
              line={obj.spectrum.template ? { name: obj.spectrum.template.name, color: "var(--accent2)", xs: obj.spectrum.template.lambda_um, ys: obj.spectrum.template.flux } : undefined} />
            {obj.spectrum.notes.map((t) => <div key={t} className="muted small">{t}</div>)}
          </>
        ) : NA}
      </section>

      <section className="card">
        <h3>Light curve</h3>
        {obj?.lightcurve?.points?.length ? (
          <>
            <ScatterChart xLabel="year" yLabel="magnitude" invertY
              series={["WISE", "SPHEREx"].map((ins) => ({ name: ins, color: ins === "WISE" ? "var(--wise)" : "var(--spherex)",
                points: obj.lightcurve!.points.filter((p) => p.instrument === ins).map((p) => ({ x: mjdToYear(p.mjd), y: p.mag, err: p.err, hollow: p.saturated })) }))}
              hollowLabel="saturated (less reliable)" />
            {obj.lightcurve.notes.map((t) => <div key={t} className="muted small">{t}</div>)}
          </>
        ) : NA}
      </section>

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
