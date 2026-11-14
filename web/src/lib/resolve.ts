// Search: local NASA target names + "ra dec" parsing (degrees or sexagesimal); /api/resolve when available.
import type { FieldEntry } from "./bundle";

const ALIASES: Record<string, string[]> = {
  barnard: ["barnard", "barnard's star", "barnards star", "gj 699", "gl 699"],
  eps_indi_b: ["eps indi b", "epsilon indi b", "ε indi b", "eps ind b"],
  wise0855: ["wise 0855", "wise0855", "wise 0855-0714", "wise j0855-0714", "0855"],
  rw_aur: ["rw aur", "rw aurigae", "rwaur"],
  r_dra: ["r dra", "r draconis", "rdra"],
};
const norm = (s: string) => s.toLowerCase().replace(/[−–]/g, "-").replace(/\s+/g, " ").trim();

export function matchField(q: string, fields: FieldEntry[]): FieldEntry | null {
  const n = norm(q);
  if (!n) return null;
  for (const f of fields) {
    const names = [norm(f.title), norm(f.field_id), ...(ALIASES[f.field_id] ?? [])];
    if (names.some((x) => x === n || x.replace(/[^a-z0-9]/g, "") === n.replace(/[^a-z0-9]/g, ""))) return f;
  }
  for (const f of fields) if (norm(f.title).includes(n) || n.includes(norm(f.title))) return f;
  // alias substring (e.g. "barnard")
  for (const f of fields) if ((ALIASES[f.field_id] ?? []).some((a) => a.includes(n) && n.length >= 4)) return f;
  return null;
}

export function parseCoords(q: string): { ra: number; dec: number } | null {
  const toks = q.replace(/[−–]/g, "-").replace(/[hdms°'":,]/gi, " ").trim().split(/\s+/);
  const parts = toks.map(Number);
  if (!toks.length || parts.some((x) => !Number.isFinite(x))) return null;
  if (parts.length === 2) { const [ra, dec] = parts; if (ra >= 0 && ra < 360 && Math.abs(dec) <= 90) return { ra, dec }; return null; }
  if (parts.length === 6) {
    const ra = (parts[0] + parts[1] / 60 + parts[2] / 3600) * 15;
    const d = Math.abs(parts[3]) + parts[4] / 60 + parts[5] / 3600;
    const dec = toks[3].startsWith("-") ? -d : d;
    if (ra >= 0 && ra < 360 && Math.abs(dec) <= 90) return { ra, dec };
  }
  return null;
}

export async function apiResolve(q: string): Promise<{ name: string; ra: number; dec: number; source: string } | null> {
  try {
    const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 6000);
    const r = await fetch(`/api/resolve?q=${encodeURIComponent(q)}`, { signal: ctl.signal }); clearTimeout(t);
    if (!r.ok || !(r.headers.get("content-type") || "").includes("json")) return null;
    return await r.json();
  } catch { return null; }
}

/** Angular separation in degrees (small-angle ok). */
export function sepDeg(ra1: number, d1: number, ra2: number, d2: number) {
  const r = Math.PI / 180;
  const c = Math.sin(d1 * r) * Math.sin(d2 * r) + Math.cos(d1 * r) * Math.cos(d2 * r) * Math.cos((ra1 - ra2) * r);
  return Math.acos(Math.min(1, Math.max(-1, c))) / r;
}
