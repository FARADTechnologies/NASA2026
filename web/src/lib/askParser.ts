// Ask SkyLapse — deterministic fallback parser (used when /api/command or the organizers' API is unavailable).
// Covers the ~10 most common commands in English, Turkish and Azerbaijani. Numbers come ONLY from the user's words.
import type { AskAction } from "./commandBridge";

const FIELD_WORDS: [RegExp, string][] = [
  [/barnard/i, "barnard"],
  [/(eps(ilon)?\.?\s*ind(i|us)?\s*b|ε\s*ind)/i, "eps_indi_b"],
  [/(wise\s*0?855|0855|coldest brown dwarf|en soğuk|ən soyuq)/i, "wise0855"],
  [/(rw\s*aur)/i, "rw_aur"],
  [/(r\s*dra(co(nis)?)?\b|r\s*draconis)/i, "r_dra"],
];
// named live demo fields — coordinates from our own file pipeline/qa/live_api_test.md (T9)
const NAMED_LIVE: [RegExp, number, number][] = [
  [/luhman/i, 162.3057, -53.3177], [/teegarden/i, 43.2716, 16.8623], [/kapteyn/i, 77.9651, -45.047],
];
const has = (t: string, ...re: RegExp[]) => re.some((r) => r.test(t));

export function parseCommand(input: string): AskAction[] {
  const t = input.toLowerCase().replace(/[’']/g, "'");
  const out: AskAction[] = [];

  // 1. open a target / live field / coordinates
  const f = FIELD_WORDS.find(([re]) => re.test(t));
  const live = NAMED_LIVE.find(([re]) => re.test(t));
  const coord = t.match(/ra\s*[:=]?\s*(-?\d+(?:\.\d+)?)[^\d-]+dec\s*[:=]?\s*([-+−]?\d+(?:\.\d+)?)/i)
    || t.match(/(?:go to|open|show|git|göster|aç|göstər)\s+(-?\d+(?:\.\d+)?)[\s,]+([-+−]?\d+(?:\.\d+)?)/i);
  if (coord) {
    const ra = +coord[1], dec = +coord[2].replace("−", "-");
    if (ra >= 0 && ra < 360 && dec >= -90 && dec <= 90) out.push({ type: "open_coordinates", ra, dec });
  } else if (live) out.push({ type: "open_coordinates", ra: live[1], dec: live[2] });
  else if (f) out.push({ type: "open_field", field: f[1] });

  // 2. compare / difference
  if (has(t, /compare 2010|2010 (with|ile|ilə)|vs\.? ?2010|since 2010|2010'?(dan|den|dən)/)) {
    out.push({ type: "set_compare", mode: "vs2010" });
    if (has(t, /today|now|bugün|indi|son\b|latest|recent/)) { out.push({ type: "go_to_frame", which: "last" }); out.push({ type: "pause" }); }
  } else if (has(t, /difference|diff mode|fark|fərq/)) out.push({ type: "set_compare", mode: has(t, /previous|önceki|əvvəlki/) ? "previous" : "vs2010" });
  else if (has(t, /(compare|comparison|fark|fərq).*(off|kapat|söndür)|normal (mode|view)|no difference/)) out.push({ type: "set_compare", mode: "off" });

  // 3. speed
  const fps = t.match(/(\d+(?:\.\d+)?)\s*(fps|frames? per second|kare)/);
  if (fps) out.push({ type: "set_speed", fps: +fps[1] });
  else if (has(t, /double speed|twice as fast|2x|faster|iki kat|daha hızlı|hızlandır|ikiqat|sürətli/)) out.push({ type: "set_speed", factor: 2 });
  else if (has(t, /half speed|slower|yavaş|yarı/)) out.push({ type: "set_speed", factor: 0.5 });

  // 4. zoom / stretch / sequence
  // only explicit arcminutes (an apostrophe is also a Turkish suffix, e.g. "WISE 0855'i")
  const fov = t.match(/(\d+(?:\.\d+)?)\s*(arcmin|arc ?minutes?|′)/);
  if (fov && +fov[1] >= 1 && +fov[1] <= 30) out.push({ type: "set_zoom", fov_arcmin: +fov[1] });
  else if (has(t, /zoom in|yakınlaş|yaxınlaş/)) out.push({ type: "set_zoom", factor: 2 });
  else if (has(t, /zoom out|uzaklaş|uzaqlaş/)) out.push({ type: "set_zoom", factor: 0.5 });
  if (has(t, /\blinear\b|doğrusal|xətti/)) out.push({ type: "set_stretch", stretch: "linear" });
  else if (has(t, /\blog(arithmic)?\b/)) out.push({ type: "set_stretch", stretch: "log" });
  if (has(t, /3\.4|w1\b|d4\b/)) out.push({ type: "set_sequence", sequence: "w1d4" });
  else if (has(t, /spherex only|sadece spherex|yalnız spherex/)) out.push({ type: "set_sequence", sequence: "spherex6" });

  // 5. overlays
  const off = has(t, /hide|remove|turn off|gizle|kapat|gizlət|söndür/);
  if (has(t, /gaia|known stars|bilinen yıldız|məlum ulduz/)) out.push({ type: "toggle_overlay", overlay: "gaia", on: !off });
  if (has(t, /track|path|ring|iz\b|yol|halqa/)) out.push({ type: "toggle_overlay", overlay: "track", on: !off });
  if (has(t, /mask|saturat|doymuş/)) out.push({ type: "toggle_overlay", overlay: "mask", on: !off });

  // 5b. full spectral view (SPHEREx colour fingerprint) / agentic spectral tour
  if (has(t, /full spectral|all spectral|spectral (view|mode|fingerprint)|fingerprint|all colou?rs|full colou?r|tam spektr|spektral|bütün renk|rəngli|tam rəng/)) {
    if (has(t, /off|kapat|söndür|normal/)) out.push({ type: "set_fingerprint", on: false });
    else if (has(t, /motion|move|moving|movement|hareket|hərəkət|tour|tur/) || out.some((a) => a.type === "open_field")) out.push({ type: "show_spectral_motion" });
    else out.push({ type: "set_fingerprint", on: true, which: "last" });
  }
  // 6. panels / explanation
  if (has(t, /spectrum|spektr/) && !out.some((a) => a.type === "show_spectral_motion" || a.type === "set_fingerprint")) out.push({ type: "show_spectrum" });
  if (has(t, /light ?curve|ışık eğrisi|işıq əyrisi|brightness over time/)) out.push({ type: "show_lightcurve" });
  if (has(t, /explain|what is this|açıkla|anlat|izah|nədir|nedir/)) out.push({ type: "explain", lang: has(t, /azerbaijani|azərbaycan|azerbaycan|\baz\b/) ? "az" : "en" });

  // 7. transport
  if (has(t, /\bstep back|previous frame|geri\b/)) out.push({ type: "step", direction: -1 });
  else if (has(t, /\bstep|next frame|ileri|irəli/)) out.push({ type: "step", direction: 1 });
  if (has(t, /\bpause|\bstop\b|durdur|dayandır/)) out.push({ type: "pause" });
  else if (has(t, /\bplay\b|start|oynat|başlat|göster$|oynad/) && !out.some((a) => a.type === "pause")) out.push({ type: "play" });
  if (has(t, /first frame|ilk kare|ilk kadr/)) out.push({ type: "go_to_frame", which: "first" });
  else if (has(t, /last frame|son kare|son kadr/)) out.push({ type: "go_to_frame", which: "last" });

  // opening a field with nothing else → start playing
  if (out.length === 1 && (out[0].type === "open_field" || out[0].type === "open_coordinates")) out.push({ type: "play" });
  return out;
}

export function describe(a: AskAction): string {
  switch (a.type) {
    case "open_field": return `Open ${({ barnard: "Barnard's Star", eps_indi_b: "Epsilon Indi B", wise0855: "WISE 0855", rw_aur: "RW Aurigae", r_dra: "R Draconis" } as Record<string, string>)[a.field] ?? a.field}`;
    case "open_coordinates": return `Open live field RA ${a.ra}, Dec ${a.dec}`;
    case "set_sequence": return `Sequence → ${a.sequence}`;
    case "set_compare": return { off: "Compare off", vs2010: "Compare: each frame vs 2010", previous: "Compare: vs previous frame", chosen: "Compare: vs this frame" }[a.mode];
    case "set_speed": return a.fps ? `Speed → ${a.fps} fps` : `Speed ×${a.factor}`;
    case "set_stretch": return `Brightness → ${a.stretch}`;
    case "set_zoom": return a.fov_arcmin ? `Zoom → ${a.fov_arcmin}′ wide` : `Zoom ×${a.factor}`;
    case "toggle_overlay": return `${a.on === false ? "Hide" : "Show"} ${a.overlay}`;
    case "play": return "Play";
    case "pause": return "Pause";
    case "step": return (a.direction ?? 1) < 0 ? "Step back" : "Step forward";
    case "go_to_frame": return a.which === "last" ? "Go to the latest frame" : "Go to the 2010 frame";
    case "show_spectrum": return "Show the spectrum";
    case "show_lightcurve": return "Show the light curve";
    case "explain": return `Show our fact-checked explanation (${a.lang === "az" ? "Azerbaijani" : "English"})`;
    case "set_fingerprint": return a.on === false ? "Spectral fingerprint off" : "Full spectral view (SPHEREx colour fingerprint)";
    case "show_spectral_motion": return "Spectral tour: the 16-year movie, then the SPHEREx colours epoch by epoch, then the spectrum";
  }
}
