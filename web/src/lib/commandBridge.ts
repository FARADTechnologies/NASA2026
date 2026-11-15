// Ask SkyLapse — command bridge (orchestrator, O6 #122).
// The viewer calls useCommandBridge(...) ONCE; AskSkyLapse dispatches validated actions as a window event.
// Actions only change viewer state (the same state the controls change); they never compute or show new numbers.
import { useEffect, useRef } from "react";
import type { ViewState } from "./url";

export type AskAction =
  | { type: "open_field"; field: string }
  | { type: "open_coordinates"; ra: number; dec: number }
  | { type: "set_sequence"; sequence: string }
  | { type: "set_compare"; mode: "off" | "vs2010" | "previous" | "chosen" }
  | { type: "set_speed"; factor?: number; fps?: number }
  | { type: "set_stretch"; stretch: "linear" | "asinh" | "log" }
  | { type: "set_zoom"; factor?: number; fov_arcmin?: number }
  | { type: "toggle_overlay"; overlay: "gaia" | "track" | "mask"; on?: boolean }
  | { type: "play" } | { type: "pause" } | { type: "step"; direction?: number }
  | { type: "go_to_frame"; which: "first" | "last" }
  | { type: "show_spectrum" } | { type: "show_lightcurve" } | { type: "explain"; lang: "en" | "az" }
  | { type: "set_fingerprint"; on?: boolean; which?: "first" | "last" | "next" }
  | { type: "show_spectral_motion" }
  | { type: "tell_about"; lang?: "en" | "az" };

export const ACTIONS_EVENT = "skylapse:actions";
export const READY_EVENT = "skylapse:bridge-ready";
declare global { interface Window { __skylapseBridgeReady?: boolean } }

type Api = {
  setView: (f: (v: ViewState) => ViewState) => void;
  setPlaying: (p: boolean | ((p: boolean) => boolean)) => void;
  n: number;                       // frames in the current sequence
  sequenceIds: string[];
  frameIdAt: (i: number) => string | undefined;
  fullFovArcmin: number | null;    // grid width in arcmin
  rgbIds?: string[];               // SPHEREx colour-fingerprint composites, oldest first
  currentRgb?: string;
};
export const SAY_EVENT = "skylapse:say";
const say = (text: string) => window.dispatchEvent(new CustomEvent(SAY_EVENT, { detail: text }));
/** Speak and wait until the sentence has been said (AskSkyLapse resolves it; a time cap means a tour can never hang). */
const sayWait = (text: string, lang: "en" | "az" = "en") => new Promise<void>((res) => {
  let done = false; const fin = () => { if (!done) { done = true; res(); } };
  setTimeout(fin, 5000 + text.length * 110);
  window.dispatchEvent(new CustomEvent(SAY_EVENT, { detail: { text, lang, done: fin } }));
});
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
/** Poll until the page shows something (data arrive after the viewer mounts, e.g. when a command opened it from the home page). */
export async function waitFor<T>(get: () => T | null | undefined | false, ms = 8000): Promise<T | null> {
  const t0 = Date.now();
  for (;;) { const v = get(); if (v) return v; if (Date.now() - t0 > ms) return null; await sleep(150); }
}
/** Guided tour: scroll a card into view and keep it outlined while the assistant talks about it. */
function spotlight(el: Element | null) {
  document.querySelectorAll("[data-ask-spot]").forEach((e) => { const h = e as HTMLElement; h.style.outline = ""; h.style.outlineOffset = ""; h.removeAttribute("data-ask-spot"); });
  if (!el) return;
  el.scrollIntoView({ behavior: document.hidden ? "auto" : "smooth", block: "center" });
  const h = el as HTMLElement; h.setAttribute("data-ask-spot", ""); h.style.outline = "2px solid #4cc9f0"; h.style.outlineOffset = "3px";
}
const txt = (el: Element | null | undefined) => (el?.textContent || "").replace(/\s+/g, " ").trim();
/** Read the measured-motion card exactly as the page shows it (numbers come only from our bundle). */
function factsOf(card: Element): Record<string, string> {
  const m: Record<string, string> = {};
  card.querySelectorAll("dl.facts dt").forEach((dt) => { const dd = dt.nextElementSibling; if (dd) m[txt(dt).toLowerCase()] = txt(dd); });
  return m;
}
const spokenEn = (s: string) => s.replace(/mas\/yr/g, "milliarcseconds per year").replace(/±/g, "plus or minus").replace(/%/g, " percent")
  .replace(/(\d) d\b/g, "$1 days").replace(/\s*·\s*/g, ". ");
const spokenAz = (s: string) => s.replace(/mas\/yr/g, "milliqövs saniyə ildə").replace(/±/g, "artı-əksi").replace(/(\d+(?:\.\d+)?)%/g, "$1 faiz")
  .replace(/Period found:/g, "Tapdığımız period:").replace(/known:/g, "məlum dəyər:").replace(/(\d) d\b/g, "$1 gün").replace(/\s*·\s*/g, ". ");

/** "Tell me about X": play the movie, then walk down the page card by card and read what each card shows. */
async function guidedTour(lang: "en" | "az", alive: () => boolean, api: () => Api) {
  const az = lang === "az";
  const card = await waitFor(() => { const c = document.querySelector(".obj-card"); return c && c.querySelector("dl.facts, table.pm, .kind") ? c : null; }, 9000)
    ?? document.querySelector(".obj-card");
  if (!alive()) return;
  const name = txt(card?.querySelector("h3")) || (az ? "Bu obyekt" : "This object");
  const kind = txt(card?.querySelector(".kind"));
  api().setView((v) => ({ ...v, rgb: "", diff: "none", coadd: "", overlay: v.overlay.includes("track") ? v.overlay : [...v.overlay, "track"] }));
  api().setPlaying(true);
  spotlight(document.querySelector(".stage"));
  await sayWait(az ? `${name}. Bu, onun on altı illik infraqırmızı filmidir: 2010-dan WISE, sonra SPHEREx. Halqa hədəfi göstərir.`
    : `${name}${kind ? `, ${kind}` : ""}. This is its sixteen-year infrared movie: WISE from 2010, then SPHEREx. The ring marks the target.`, lang);
  if (!alive()) return;
  if (card) {
    const f = factsOf(card);
    const mv = f["motion we measured"], pub = f["published value"], agr = f["agreement"], fit = f["fit"];
    let line = "";
    if (mv) {
      if (az) {
        const fm = fit?.match(/(\d+) epochs(?: over ([\d.]+) years)?/);
        line = `Ölçdüyümüz hərəkət: ${spokenAz(mv)}.` + (pub ? ` Dərc olunmuş dəyər: ${spokenAz(pub)}.` : "") + (agr ? ` Uyğunluq: ${spokenAz(agr)}.` : "")
          + (fm ? ` ${fm[1]} epoxa${fm[2] ? `, ${fm[2]} il ərzində` : ""}.` : "");
      } else {
        line = `What we measured: ${spokenEn(mv)}.` + (pub ? ` Published value: ${spokenEn(pub)}.` : "") + (agr ? ` Agreement: ${spokenEn(agr)}.` : "") + (fit ? ` Fit: ${fit}.` : "");
      }
    } else {
      const total = txt(card.querySelector("table.pm tbody tr td:last-child"));
      if (total) line = az ? `Dərc olunmuş hərəkəti: ${total} milliqövs saniyə ildə.` : `Its published motion: ${total} milliarcseconds per year.`;
    }
    if (line) { spotlight(card); await sayWait(line, lang); if (!alive()) return; }
  }
  const cop = document.querySelector('[data-section="copilot"]');
  if (cop) {
    (cop.querySelector(`[data-lang="${lang}"]`) as HTMLButtonElement | null)?.click();
    await sleep(300);
    const p = Array.from(cop.querySelectorAll("p")).map(txt).filter((t) => t.length > 60).sort((a, b) => b.length - a.length)[0];
    if (p) { spotlight(cop); await sayWait(p, lang); if (!alive()) return; }
  }
  const lc = document.querySelector('[data-section="lightcurve"]');
  if (lc) {
    const per = txt(lc.querySelector(".period-line"));
    spotlight(lc);
    await sayWait(az ? `Parlaqlığının zamanla dəyişməsi.${per ? " " + spokenAz(per) + "." : ""}` : `Its brightness over time.${per ? " " + spokenEn(per) + "." : ""}`, lang);
    if (!alive()) return;
  }
  const sp = document.querySelector('[data-section="spectrum"]');
  if (sp) {
    const honest = txt(sp.querySelector(".honest-note b"));
    spotlight(sp);
    await sayWait(honest ? (az ? "Bu hədəf SPHEREx detektorları üçün çox parlaqdır, ona görə etibarlı spektr göstərmirik." : honest)
      : (az ? "Bu isə onun SPHEREx spektridir, 0,75-dən 5 mikrona qədər." : "And this is its SPHEREx spectrum, from 0.75 to 5 microns."), lang);
    if (!alive()) return;
  }
  spotlight(document.querySelector(".stage"));
  api().setPlaying(true);
  await sayWait(az ? "Bu qədər. Başqa ulduzu da soruşa bilərsiniz." : "That's the tour. Ask me about another target any time.", lang);
  spotlight(null);
}

/** Apply view-only actions to a ViewState (also used to build the URL when a field is opened). */
export function applyToView(v: ViewState, a: AskAction, fullFov: number | null, sequenceIds?: string[]): ViewState {
  switch (a.type) {
    case "set_sequence": return !sequenceIds || sequenceIds.includes(a.sequence) ? { ...v, seq: a.sequence, frame: 0 } : v;
    case "set_compare":
      return a.mode === "off" ? { ...v, diff: "none" } : a.mode === "vs2010" ? { ...v, diff: "first" }
        : a.mode === "previous" ? { ...v, diff: "prev" } : { ...v, diff: "ref" };
    case "set_speed": {
      const ms = a.fps ? 1000 / a.fps : a.factor ? v.speed / a.factor : v.speed;
      return { ...v, speed: Math.round(Math.min(3000, Math.max(40, ms))) };
    }
    case "set_stretch": return { ...v, stretch: a.stretch };
    case "set_zoom": {
      const cur = v.fov ?? fullFov ?? 8.8;
      const fov = a.fov_arcmin ?? (a.factor ? cur / a.factor : cur);
      return { ...v, fov: Math.round(Math.min(fullFov ?? 30, Math.max(1, fov)) * 10) / 10 };
    }
    case "toggle_overlay": {
      const has = v.overlay.includes(a.overlay);
      const on = a.on ?? !has;
      return { ...v, overlay: on ? (has ? v.overlay : [...v.overlay, a.overlay]) : v.overlay.filter((x) => x !== a.overlay) };
    }
    default: return v;
  }
}

/** Scroll to a side-panel section; prefers data-section, falls back to the heading text. */
export function scrollToSection(key: "spectrum" | "lightcurve" | "copilot"): boolean {
  const words = { spectrum: "spectrum", lightcurve: "light curve", copilot: "ai copilot" }[key];
  let el: Element | null = document.querySelector(`[data-section="${key}"]`);
  if (!el) el = Array.from(document.querySelectorAll("h2, h3, h4")).find((h) => (h.textContent || "").trim().toLowerCase().startsWith(words)) ?? null;
  if (!el) return false;
  el.scrollIntoView({ behavior: window.innerHeight > 0 && !document.hidden ? "smooth" : "auto", block: "center" });
  (el as HTMLElement).animate?.([{ outline: "2px solid #4cc9f0" }, { outline: "2px solid transparent" }], { duration: 1600 });
  return true;
}

export function chooseCopilotLang(lang: "en" | "az"): boolean {
  let btn: Element | null = document.querySelector(`[data-lang="${lang}"]`);
  if (!btn) btn = Array.from(document.querySelectorAll("button")).find((b) => (b.textContent || "").trim().toUpperCase() === lang.toUpperCase()) ?? null;
  if (btn) (btn as HTMLButtonElement).click();
  return scrollToSection("copilot") || !!btn;
}

export function useCommandBridge(api: Api) {
  const ref = useRef(api); ref.current = api;
  const pendingFrame = useRef<"first" | "last" | null>(null);
  const tour = useRef(0);
  useEffect(() => {
    const on = (e: Event) => {
      const actions = ((e as CustomEvent).detail || []) as AskAction[];
      const a0 = ref.current;
      tour.current++; // any new command cancels a running tour
      for (const a of actions) {
        switch (a.type) {
          case "play": a0.setPlaying(true); break;
          case "pause": a0.setPlaying(false); break;
          case "step": a0.setPlaying(false);
            a0.setView((v) => ({ ...v, frame: a0.n ? (v.frame + ((a.direction ?? 1) < 0 ? -1 : 1) + a0.n) % a0.n : 0 })); break;
          case "go_to_frame": a0.setPlaying(false);
            if (a0.n) a0.setView((v) => ({ ...v, frame: a.which === "last" ? a0.n - 1 : 0 })); else pendingFrame.current = a.which; break;
          case "set_compare":
            a0.setView((v) => {
              const nv = applyToView(v, a, a0.fullFovArcmin);
              return a.mode === "chosen" ? { ...nv, ref: a0.frameIdAt(v.frame) ?? v.ref } : nv;
            }); break;
          case "show_spectrum": void waitFor(() => document.querySelector('[data-section="spectrum"]'), 8000).then(() => scrollToSection("spectrum")); break;
          case "show_lightcurve": void waitFor(() => document.querySelector('[data-section="lightcurve"]'), 8000).then(() => scrollToSection("lightcurve")); break;
          case "explain": void waitFor(() => document.querySelector('[data-section="copilot"]'), 8000).then(() => chooseCopilotLang(a.lang)); break;
          case "tell_about": { const my = tour.current; void guidedTour(a.lang ?? "en", () => tour.current === my, () => ref.current); break; }
          case "set_fingerprint": {
            const ids = a0.rgbIds ?? [];
            if (a.on === false || !ids.length) { a0.setView((v) => ({ ...v, rgb: "" })); break; }
            a0.setPlaying(false);
            a0.setView((v) => {
              const i = ids.indexOf(v.rgb);
              const id = a.which === "first" ? ids[0] : a.which === "next" ? ids[(i + 1) % ids.length] : ids[ids.length - 1];
              return { ...v, rgb: id, diff: "none" };
            });
            break;
          }
          case "show_spectral_motion": {
            // agentic tour: the 16-year movie with the target ring → SPHEREx colour fingerprint epoch by epoch → spectrum
            const my = tour.current; const ids = a0.rgbIds ?? [];
            const alive = () => tour.current === my;
            a0.setView((v) => ({ ...v, rgb: "", diff: "none", coadd: "", overlay: v.overlay.includes("track") ? v.overlay : [...v.overlay, "track"] }));
            a0.setPlaying(true);
            say("Watch it move: sixteen years of infrared images, WISE then SPHEREx, at four point six microns.");
            let t = 8000;
            ids.forEach((id, k) => {
              setTimeout(() => {
                if (!alive()) return;
                ref.current.setPlaying(false); ref.current.setView((v) => ({ ...v, rgb: id, diff: "none" }));
                if (k === 0) say("Now the full spectral view: SPHEREx colours, blue at one micron, green at two, red at almost five microns.");
              }, t);
              t += 3200;
            });
            setTimeout(() => { if (!alive()) return; scrollToSection("spectrum"); say("And here is its spectrum from SPHEREx."); }, t + 400);
            break;
          }
          default: a0.setView((v) => applyToView(v, a, a0.fullFovArcmin, a0.sequenceIds));
        }
      }
    };
    window.addEventListener(ACTIONS_EVENT, on);
    window.__skylapseBridgeReady = true;
    window.dispatchEvent(new Event(READY_EVENT));
    return () => { window.removeEventListener(ACTIONS_EVENT, on); window.__skylapseBridgeReady = false; };
  }, []);
  useEffect(() => {
    if (pendingFrame.current && api.n) {
      const w = pendingFrame.current; pendingFrame.current = null;
      api.setView((v) => ({ ...v, frame: w === "last" ? api.n - 1 : 0 }));
    }
  }, [api.n]);
}
