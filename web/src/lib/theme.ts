// Light / dark theme: follows the system setting until the user picks one; the choice is remembered.
import { useEffect, useState } from "react";

export type Theme = "light" | "dark";
const KEY = "skylapse.theme";

export function storedTheme(): Theme | null {
  try { const t = localStorage.getItem(KEY); return t === "light" || t === "dark" ? t : null; } catch { return null; }
}
export function systemTheme(): Theme {
  return typeof matchMedia !== "undefined" && matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}
export function applyTheme(t: Theme) { document.documentElement.dataset.theme = t; }

export function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => storedTheme() ?? systemTheme());
  useEffect(() => { applyTheme(theme); }, [theme]);
  useEffect(() => { // follow system changes only while the user has not chosen
    const mq = matchMedia("(prefers-color-scheme: light)");
    const on = () => { if (!storedTheme()) setTheme(systemTheme()); };
    mq.addEventListener("change", on); return () => mq.removeEventListener("change", on);
  }, []);
  const toggle = () => setTheme((t) => { const n = t === "light" ? "dark" : "light"; try { localStorage.setItem(KEY, n); } catch { /* ignore */ } return n; });
  return [theme, toggle];
}

/** Meaning colours used on the (always dark) canvas — keep in sync with the dark-theme tokens in styles.css. */
export const CANVAS = {
  wise: "#F0A040", spherex: "#3CC0D6", gaia: "rgba(92,201,138,0.7)", catwise: "rgba(170,186,214,0.75)",
  target: "#FF6B9A", targetSoft: "rgba(255,107,154,0.6)", ink: "#E7EAF0", bg: "#05070B",
};
