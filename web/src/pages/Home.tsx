import { useEffect, useState } from "react";
import type { FieldEntry } from "../lib/bundle";
import { loadIndex, prefetchFields } from "../lib/bundle";
import { navigate } from "../lib/router";
import { SearchBox } from "../components/SearchBox";
import { TopBar } from "../components/TopBar";

export function Home() {
  const [fields, setFields] = useState<FieldEntry[] | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    loadIndex().then(({ index }) => {
      setFields(index.fields);
      // warm the cache so a target's movie starts instantly (NASA targets first, then the rest)
      const t = index.fields.filter((f) => f.kind === "nasa_test_target");
      prefetchFields(t.length ? t : index.fields.slice(0, 5));
    }).catch(() => setErr(true));
  }, []);
  const targets = fields?.filter((f) => f.kind === "nasa_test_target") ?? [];
  const others = fields?.filter((f) => f.kind !== "nasa_test_target") ?? [];
  const open = (f: FieldEntry) => navigate(`/view?field=${encodeURIComponent(f.field_id)}`);

  return (
    <div className="page home">
      <TopBar />
      <section className="hero">
        <div className="hero-bg" aria-hidden />
        <div className="hero-inner">
          <div className="eyebrow">NASA Space Apps 2026 · Planet X and SPHEREx</div>
          <h1>Watch <span className="accent">16 years</span> of the infrared sky<br />and catch what moves.</h1>
          <p className="lede">SkyLapse joins NASA's WISE/NEOWISE (2010–2024) and SPHEREx (2025–2026) into one movie of any patch of sky,
            so nearby brown dwarfs and fast stars visibly crawl across the screen.</p>
          <SearchBox />
          <div className="how"><b>How it works:</b> pick a target <span>→</span> watch 16 years play <span>→</span> the moving dot is the object.</div>
        </div>
      </section>
      <section className="targets">
        {(fields === null || targets.length > 0) && <h2>NASA test targets</h2>}
        {err && <div className="empty-state small">The sky data could not be loaded. Please refresh in a moment.</div>}
        <div className="cards">
          {fields === null && !err && Array.from({ length: 5 }).map((_, i) => <div key={i} className="tcard skeleton-box" />)}
          {targets.map((f) => <TargetCard key={f.field_id} f={f} onOpen={() => open(f)} />)}
        </div>
        {others.length > 0 && (<><h2>{targets.length ? "Showcase fields" : "Fields"}</h2><div className="cards">{others.map((f) => <TargetCard key={f.field_id} f={f} onOpen={() => open(f)} />)}</div></>)}
      </section>
      <footer className="foot muted">
        Data: NASA/IPAC IRSA (SPHEREx), unWISE time-resolved coadds via byw.tools, ESA Gaia DR3, CatWISE2020. Built by team FARAD (Baku) with AI assistance — see About.
      </footer>
    </div>
  );
}

function TargetCard({ f, onOpen }: { f: FieldEntry; onOpen: () => void }) {
  const [broken, setBroken] = useState(false);
  const thumb = f.thumb && f.root ? f.root + f.thumb : null;
  return (
    <button className="tcard" onClick={onOpen}>
      <div className="tthumb">
        {thumb && !broken ? <img src={thumb} alt="" onError={() => setBroken(true)} /> : <div className="tthumb-ph"><span /><span /><span /></div>}
      </div>
      <div className="tbody">
        <div className="tname">{f.title}</div>
        <div className="ttags">{f.tags.map((t) => <span key={t} className={"tag " + (t === "variability" ? "t-var" : t === "motion" ? "t-mot" : "")}>{t}</span>)}</div>
        <div className="tcoord mono muted">{f.ra.toFixed(3)}° {f.dec >= 0 ? "+" : "−"}{Math.abs(f.dec).toFixed(3)}°</div>
      </div>
    </button>
  );
}
