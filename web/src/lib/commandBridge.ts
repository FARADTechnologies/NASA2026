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
  | { type: "show_spectral_motion" };

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
          case "show_spectrum": scrollToSection("spectrum"); break;
          case "show_lightcurve": scrollToSection("lightcurve"); break;
          case "explain": chooseCopilotLang(a.lang); break;
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
