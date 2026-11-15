import { useEffect, useState } from "react";
import type { Candidates, FieldEntry, Manifest } from "../lib/bundle";
import { loadIndex, loadOptional } from "../lib/bundle";
import { navigate } from "../lib/router";
import { TopBar } from "../components/TopBar";

type Row = Candidates["items"][number] & { field: FieldEntry };
const CLASS_LABEL: Record<string, string> = { candidate: "New candidate", known: "Known mover", artifact: "Artifact" };

export function Discover() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [stats, setStats] = useState({ known: 0, recovered: 0, cand: 0, fields: 0 });
  const [methods, setMethods] = useState<string[]>([]);
  const [caveats, setCaveats] = useState<string[]>([]);
  const [perField, setPerField] = useState<{ f: FieldEntry; s: Candidates["stats"] }[]>([]);
  const [filter, setFilter] = useState<"all" | "candidate" | "known" | "artifact">("all");
  const [err, setErr] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const { index } = await loadIndex();
        const per = await Promise.all(index.fields.map(async (f) => {
          const m = await loadOptional<Manifest>(f.base + "manifest.json");
          const c = m?.candidates ? await loadOptional<Candidates>(f.base + m.candidates) : null;
          return { f, c };
        }));
        const all: Row[] = []; const st = { known: 0, recovered: 0, cand: 0, fields: 0 }; const ms = new Set<string>(); const cv = new Set<string>();
        const pf: { f: FieldEntry; s: Candidates["stats"] }[] = [];
        for (const { f, c } of per) {
          if (!c) continue;
          pf.push({ f, s: c.stats });
          st.fields++; st.known += c.stats.known_movers_in_field; st.recovered += c.stats.recovered; st.cand += c.stats.new_candidates;
          if (c.method) ms.add(c.method);
          if (c.caveat) cv.add(c.caveat);
          for (const it of c.items) all.push({ ...it, field: f });
        }
        all.sort((a, b) => (a.class === "candidate" ? -1 : 0) - (b.class === "candidate" ? -1 : 0) || (b.score ?? b.significance_sigma ?? 0) - (a.score ?? a.significance_sigma ?? 0));
        setRows(all); setPerField(pf); setStats(st); setMethods([...ms]); setCaveats([...cv]);
      } catch { setErr(true); }
    })();
  }, []);

  const shown = rows?.filter((r) => filter === "all" || r.class === filter) ?? [];
  const recall = stats.known ? (100 * stats.recovered) / stats.known : null;
  const open = (r: Row) => {
    const objId = r.object_file?.match(/objects\/([^/]+)\.json$/)?.[1];
    navigate(`/view?field=${encodeURIComponent(r.field.field_id)}&ra=${r.ra.toFixed(5)}&dec=${r.dec.toFixed(5)}&fov=4${objId ? `&obj=${objId}` : ""}`);
  };

  return (
    <div className="page">
      <TopBar />
      <div className="doc">
        <h1>Discover</h1>
        <p className="lede-s">Every field is searched automatically: sources are detected in WISE images and linked across 14 years (2010–2024), and their motion is measured.
          Each mover is then cross-matched with Gaia DR3 and CatWISE2020 and labelled. Re-finding the <b>known</b> movers is our validation.</p>
        {err && <div className="empty-state small">Discovery results could not be loaded.</div>}
        {stats.fields > 0 && (
          <div className="headline">Blind search recovered <b>{stats.recovered} of {stats.known}</b> known fast movers · <b>{stats.cand}</b> false alarm{stats.cand === 1 ? "" : "s"}
            <span className="muted small"> (new candidates in fields of known objects)</span></div>
        )}
        <div className="stat-row">
          <div className="stat"><b>{recall === null ? "—" : `${recall.toFixed(0)}%`}</b><span>recall of known movers<br />({stats.recovered} of {stats.known} re-found)</span></div>
          <div className="stat"><b>{stats.cand}</b><span>candidates for follow-up</span></div>
          <div className="stat"><b>{stats.fields}</b><span>fields searched</span></div>
        </div>
        {perField.length > 0 && (
          <>
            <h2>Per field</h2>
            <table className="cand-table">
              <thead><tr><th>Field</th><th>Known movers</th><th>Re-found</th><th>New candidates</th><th>Sources tracked</th><th /></tr></thead>
              <tbody>
                {perField.map(({ f, s }) => (
                  <tr key={f.field_id} onClick={() => navigate(`/view?field=${encodeURIComponent(f.field_id)}`)}>
                    <td><b>{f.title}</b></td>
                    <td className="mono">{s.known_movers_in_field}</td>
                    <td className="mono"><b className={s.recovered === s.known_movers_in_field ? "ok" : "warn"}>{s.recovered}</b></td>
                    <td className="mono">{s.new_candidates}</td>
                    <td className="mono muted">{(s as Record<string, number>).sources_early ?? "—"}</td>
                    <td><button className="btn small">Watch →</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <h2>Detected movers</h2>
          </>
        )}
        <div className="seg filter">
          {(["all", "candidate", "known", "artifact"] as const).map((k) => (
            <button key={k} className={filter === k ? "on" : ""} onClick={() => setFilter(k)}>{k === "all" ? "All" : CLASS_LABEL[k]}</button>
          ))}
        </div>
        {rows === null && !err && <div className="skeleton-box" style={{ minHeight: 140 }} />}
        {rows && shown.length === 0 && <div className="empty-state small">Nothing in this category yet.</div>}
        {shown.length > 0 && (
          <table className="cand-table">
            <thead><tr><th>Field</th><th>Label</th><th>Motion (mas/yr)</th><th>Match</th><th>Score / significance</th><th /></tr></thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.field.field_id + r.id} onClick={() => open(r)}>
                  <td><b>{r.field.title}</b><div className="mono muted small">{r.id} · {r.ra.toFixed(4)}° {r.dec.toFixed(4)}°</div></td>
                  <td><span className={"cls cls-" + r.class}>{CLASS_LABEL[r.class] ?? r.class}</span></td>
                  <td className="mono">{Math.round(r.pm_total)} ± {Math.round(r.err)}</td>
                  <td className="small">{Object.entries(r.match ?? {}).filter(([, v]) => v).map(([k, v]) => <div key={k}><span className="muted">{k === "gaia" ? "Gaia" : k === "catwise" ? "CatWISE" : k}:</span> {v}</div>)}
                    {r.is_nasa_target && <div>NASA test target</div>}
                    {!r.is_nasa_target && !Object.values(r.match ?? {}).some(Boolean) && <span className="muted">no catalogue match</span>}</td>
                  <td className="mono">{r.score != null ? r.score.toFixed(2) : r.significance_sigma != null ? `${Math.round(r.significance_sigma)}σ` : "—"}</td>
                  <td><button className="btn small">Watch →</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {caveats.map((c) => <p key={c} className="muted small">{c}</p>)}
        {methods.length > 0 && <p className="muted small">Method: {methods.join("; ")}. Candidates are not discoveries — they need follow-up by astronomers.</p>}
      </div>
    </div>
  );
}
