import { useState } from "react";
import { Search } from "lucide-react";
import { loadIndex } from "../lib/bundle";
import { apiResolve, matchField, nasaFieldFor, parseCoords } from "../lib/resolve";
import { navigate } from "../lib/router";

export function SearchBox({ compact }: { compact?: boolean }) {
  const [q, setQ] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const s = q.trim(); if (!s) return;
    setBusy(true); setMsg("");
    try {
      const { index } = await loadIndex().catch(() => ({ index: { fields: [] as never[] } }));
      const f = matchField(s, index.fields);
      if (f) return navigate(`/view?field=${encodeURIComponent(f.field_id)}`);
      const c = parseCoords(s);
      if (c) return navigate(`/view?ra=${c.ra.toFixed(5)}&dec=${c.dec.toFixed(5)}`);
      const r = await apiResolve(s);
      if (r?.field && index.fields.some((x) => x.field_id === r.field)) return navigate(`/view?field=${encodeURIComponent(r.field)}`);
      if (r) return navigate(`/view?ra=${r.ra.toFixed(5)}&dec=${r.dec.toFixed(5)}`);
      if (nasaFieldFor(s)) return setMsg("This NASA target's 16-year movie is still being built — it will appear here shortly.");
      setMsg("Not found. Try a NASA target name or coordinates like “133.787 −7.245”.");
    } finally { setBusy(false); }
  };
  return (
    <form className={"search" + (compact ? " compact" : "")} onSubmit={submit}>
      <Search className="search-ico" size={compact ? 15 : 18} strokeWidth={1.75} aria-hidden />
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={compact ? "Name or RA Dec…" : "Star name or coordinates, e.g. Barnard's Star"} aria-label="Search sky position" />
      <button className="btn primary" disabled={busy}>{busy ? "…" : compact ? "Go" : "Open"}</button>
      {msg && <div className="search-msg">{msg}</div>}
    </form>
  );
}
