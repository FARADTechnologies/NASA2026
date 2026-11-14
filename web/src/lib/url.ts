import type { Stretch } from "./render";

export type DiffMode = "none" | "first" | "prev" | "ref";
export interface ViewState {
  field: string; seq: string; speed: number; stretch: Stretch; min: number; max: number; invert: boolean;
  diff: DiffMode; ref: string; coadd: string; fov: number | null; overlay: string[]; frame: number; rgb: string;
  ra: number | null; dec: number | null;
}
export const DEFAULTS: ViewState = {
  field: "", seq: "", speed: 300, stretch: "asinh", min: 1, max: 99.5, invert: false, diff: "none", ref: "",
  coadd: "", fov: null, overlay: ["gaia", "track"], frame: 0, rgb: "", ra: null, dec: null,
};

const num = (v: string | null, d: number) => (v !== null && v !== "" && Number.isFinite(+v) ? +v : d);
export function parseView(search: string): ViewState {
  const q = new URLSearchParams(search);
  const st = q.get("stretch");
  const diff = q.get("diff");
  return {
    field: q.get("field") ?? "",
    seq: q.get("seq") ?? "",
    speed: Math.min(3000, Math.max(40, num(q.get("speed"), DEFAULTS.speed))),
    stretch: st === "linear" || st === "log" || st === "asinh" ? st : DEFAULTS.stretch,
    min: num(q.get("min"), DEFAULTS.min),
    max: num(q.get("max"), DEFAULTS.max),
    invert: q.get("invert") === "1",
    diff: diff === "first" || diff === "prev" || diff === "ref" ? diff : "none",
    ref: q.get("ref") ?? "",
    coadd: q.get("coadd") ?? "",
    fov: q.get("fov") ? num(q.get("fov"), 0) || null : null,
    overlay: q.has("overlay") ? (q.get("overlay") || "").split(",").filter(Boolean) : DEFAULTS.overlay,
    frame: Math.max(0, Math.floor(num(q.get("frame"), 0))),
    rgb: q.get("rgb") ?? "",
    ra: q.get("ra") ? num(q.get("ra"), NaN) : null,
    dec: q.get("dec") ? num(q.get("dec"), NaN) : null,
  };
}
export function serializeView(s: ViewState): string {
  const q = new URLSearchParams();
  if (s.field) q.set("field", s.field);
  if (s.seq) q.set("seq", s.seq);
  q.set("speed", String(s.speed));
  q.set("stretch", s.stretch);
  q.set("min", String(s.min));
  q.set("max", String(s.max));
  if (s.invert) q.set("invert", "1");
  if (s.diff !== "none") q.set("diff", s.diff);
  if (s.diff === "ref" && s.ref) q.set("ref", s.ref);
  if (s.coadd) q.set("coadd", s.coadd);
  if (s.fov) q.set("fov", String(s.fov));
  q.set("overlay", s.overlay.join(","));
  if (s.frame) q.set("frame", String(s.frame));
  if (s.rgb) q.set("rgb", s.rgb);
  if (s.ra !== null && Number.isFinite(s.ra)) q.set("ra", s.ra.toFixed(5));
  if (s.dec !== null && Number.isFinite(s.dec)) q.set("dec", s.dec.toFixed(5));
  return q.toString().replace(/%2C/g, ",");
}
