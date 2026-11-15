import { useEffect, useState } from "react";
import type { FieldEntry } from "../lib/bundle";
import { loadIndex, prefetchFields } from "../lib/bundle";
import { prewarmLive } from "../lib/live";
import { navigate } from "../lib/router";
import { SearchBox } from "../components/SearchBox";
import { TopBar } from "../components/TopBar";
import { ArrowRight } from "lucide-react";

// Pre-warmed on the live API (pipeline T9, #78): same RA/Dec/FOV as cached → the movie opens in ~1 s.
const LIVE_FIELDS = [
  { name: "Luhman 16", ra: "162.3057", dec: "-53.3177", caption: "Nearest brown-dwarf pair, ~40″ west over 2010–2024" },
  { name: "Teegarden's Star", ra: "43.2716", dec: "16.8623", caption: "Red dwarf with planets, ~70″ south-east" },
  { name: "Kapteyn's Star", ra: "77.9651", dec: "-45.0470", caption: "Fast halo star, ~2′ south-east (saturated core)" },
];

export function Home() {
  const [fields, setFields] = useState<FieldEntry[] | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    loadIndex().then(({ index }) => {
      setFields(index.fields);
      // warm the cache so a target's movie starts instantly (NASA targets first, then the rest)
      const t = index.fields.filter((f) => f.kind === "nasa_test_target");
      prefetchFields(t.length ? t : index.fields.slice(0, 5));
      // then warm the 3 pre-built live fields (one after another, low priority)
      setTimeout(async () => { for (const l of LIVE_FIELDS) await prewarmLive(+l.ra, +l.dec, 8.8); }, 1500);
    }).catch(() => setErr(true));
  }, []);
  const targets = fields?.filter((f) => f.kind === "nasa_test_target") ?? [];
  const others = fields?.filter((f) => f.kind !== "nasa_test_target") ?? [];
  const open = (f: FieldEntry) => navigate(`/view?field=${encodeURIComponent(f.field_id)}`);

  return (
    <div className="page home">
      <TopBar />
      <section className="hero">
        <div className="hero-inner">
          <div className="eyebrow">NASA Space Apps 2026 · Planet X and SPHEREx</div>
          <h1>Watch <span className="num">16 years</span> of the infrared sky and catch what moves.</h1>
          <p className="lede">Two NASA telescopes photographed the same sky years apart: WISE from 2010 to 2024, SPHEREx since 2025.
            We line up their pictures of one small patch and play them in order. The stars that drift are our neighbours.</p>
          <SearchBox />
          <p className="how-line">Not sure where to start? Open one of NASA's five test targets below.</p>
        </div>
      </section>
      <section className="targets">
        {(fields === null || targets.length > 0) && <h2>NASA test targets</h2>}
        {err && <div className="empty-state small">The sky data could not be loaded. Please refresh in a moment.</div>}
        <div className="cards">
          {fields === null && !err && Array.from({ length: 5 }).map((_, i) => <div key={i} className="tcard skeleton-box" />)}
          {targets.map((f) => <TargetCard key={f.field_id} f={f} onOpen={() => open(f)} />)}
        </div>
        <h2>Try a live field <span className="h2-sub">built from WISE in seconds</span></h2>
        <div className="live-row">
          {LIVE_FIELDS.map((l) => (
            <button key={l.name} className="live-btn" onClick={() => navigate(`/view?ra=${l.ra}&dec=${l.dec}&fov=8.8`)}>
              <span className="live-name">{l.name}</span>
              <span className="muted small">{l.caption}</span>
              <ArrowRight className="live-arrow" size={16} strokeWidth={1.75} aria-hidden />
            </button>
          ))}
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
  // Some fields lie at the edge of a survey tile: the preview then has an empty (pure black) band.
  // Zoom the thumbnail onto the rows that actually contain data, so the card never looks broken.
  const [crop, setCrop] = useState<React.CSSProperties | undefined>();
  const fitToData = (e: React.SyntheticEvent<HTMLImageElement>) => {
    try {
      const n = 64; const c = document.createElement("canvas"); c.width = n; c.height = n;
      const g = c.getContext("2d")!; g.drawImage(e.currentTarget, 0, 0, n, n);
      const d = g.getImageData(0, 0, n, n).data;
      const empty = (y: number) => { let mx = 0; for (let x = 0; x < n; x++) { const i = (y * n + x) * 4; mx = Math.max(mx, d[i], d[i + 1], d[i + 2]); } return mx < 6; };
      let top = 0; while (top < n / 2 && empty(top)) top++;
      let bot = 0; while (bot < n / 2 && empty(n - 1 - bot)) bot++;
      if (top + bot >= 3) { const h = n - top - bot; setCrop({ transform: `scale(${(n / h).toFixed(3)})`, transformOrigin: `50% ${((100 * top) / (n - h)).toFixed(1)}%` }); }
    } catch { /* keep the plain thumbnail */ }
  };
  return (
    <button className="tcard" onClick={onOpen}>
      <div className="tthumb">
        {thumb && !broken ? <img src={thumb} alt="" style={crop} onLoad={fitToData} onError={() => setBroken(true)} /> : <div className="tthumb-ph"><span /><span /><span /></div>}
      </div>
      <div className="tbody">
        <div className="tname">{f.title}</div>
        <div className="ttags">{f.tags.join(" · ")}</div>
        <div className="tcoord mono muted">{f.ra.toFixed(3)}° {f.dec >= 0 ? "+" : "−"}{Math.abs(f.dec).toFixed(3)}°</div>
      </div>
    </button>
  );
}
