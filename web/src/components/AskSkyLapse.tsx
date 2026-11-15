// Ask SkyLapse — action-taking assistant (orchestrator, O6 #122). Text or voice command → validated viewer actions.
// Not a chatbot: it never answers with numbers or facts; it only drives the viewer and shows what it did.
// One mount point: <AskSkyLapse /> in the header. Styles are inline so the theme redesign cannot break it.
import { useEffect, useRef, useState } from "react";
import { Mic, Sparkles, Square } from "lucide-react";
import { navigate } from "../lib/router";
import { DEFAULTS, parseView, serializeView, type ViewState } from "../lib/url";
import { ACTIONS_EVENT, READY_EVENT, applyToView, type AskAction } from "../lib/commandBridge";
import { describe, parseCommand } from "../lib/askParser";

type LogItem = { text: string; source: "claude" | "local" | "none"; actions: string[]; note?: string };
const LANGS = [{ id: "en-US", label: "EN" }, { id: "tr-TR", label: "TR" }, { id: "az-AZ", label: "AZ" }];
const EXAMPLES = ["show Barnard's Star in difference mode at double speed", "compare 2010 with today", "go to RA 162.3 Dec -53.3",
  "show the spectrum", "explain this object in Azerbaijani"];
const OPEN = new Set(["open_field", "open_coordinates"]);
const VIEW_ONLY = new Set(["set_sequence", "set_compare", "set_speed", "set_stretch", "set_zoom", "toggle_overlay"]);
// survives the header remount that happens when a command opens a new page
const persist: { open: boolean; log: LogItem[] } = { open: false, log: [] };

async function callApi(text: string): Promise<{ actions: AskAction[]; rejected: string[] } | null> {
  const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), 9000);
  try {
    const field = new URLSearchParams(location.search).get("field");
    const r = await fetch("/api/command", { method: "POST", headers: { "content-type": "application/json" }, signal: ctl.signal,
      body: JSON.stringify({ text, context: { path: location.pathname, field } }) });
    if (!r.ok) return null;
    const j = await r.json();
    return Array.isArray(j.actions) ? { actions: j.actions, rejected: j.rejected || [] } : null;
  } catch { return null; } finally { clearTimeout(timer); }
}

function waitForBridge(ms = 8000): Promise<boolean> {
  return new Promise((res) => {
    const t = setTimeout(() => { window.removeEventListener(READY_EVENT, on); res(!!window.__skylapseBridgeReady); }, ms);
    const on = () => { clearTimeout(t); window.removeEventListener(READY_EVENT, on); setTimeout(() => res(true), 300); };
    window.addEventListener(READY_EVENT, on);
  });
}

/** Opening a field: fold view-only actions into the URL; the rest runs once the new viewer is ready. */
async function applyActions(actions: AskAction[]): Promise<string | undefined> {
  const open = actions.find((a) => OPEN.has(a.type));
  if (open) {
    let v: ViewState = { ...DEFAULTS };
    if (open.type === "open_field") v.field = open.field;
    else if (open.type === "open_coordinates") { v.ra = open.ra; v.dec = open.dec; v.fov = 8.8; }
    for (const a of actions) if (VIEW_ONLY.has(a.type) && !(a.type === "set_compare" && a.mode === "chosen")) v = applyToView(v, a, 8.8);
    const rest = actions.filter((a) => !OPEN.has(a.type) && !(VIEW_ONLY.has(a.type) && !(a.type === "set_compare" && a.mode === "chosen")));
    window.__skylapseBridgeReady = false;
    navigate("/view?" + serializeView(v));
    if (rest.length && (await waitForBridge())) window.dispatchEvent(new CustomEvent(ACTIONS_EVENT, { detail: rest }));
    return undefined;
  }
  if (!location.pathname.startsWith("/view") || !window.__skylapseBridgeReady) {
    // not in the viewer: view-only actions still work on the current target if the URL has one
    const cur = parseView(location.search);
    if (!cur.field && cur.ra === null) return "Open a target first, e.g. “show WISE 0855”.";
  }
  window.dispatchEvent(new CustomEvent(ACTIONS_EVENT, { detail: actions }));
  return undefined;
}

export function AskSkyLapse() {
  const [open, setOpenRaw] = useState(persist.open);
  const setOpen = (f: boolean | ((o: boolean) => boolean)) => setOpenRaw((o) => (persist.open = typeof f === "function" ? f(o) : f));
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [lang, setLang] = useState(() => { try { return localStorage.getItem("skylapse.ask.lang") || "en-US"; } catch { return "en-US"; } });
  const [log, setLogRaw] = useState<LogItem[]>(persist.log);
  // write the module copy first: after a command opens a new page this instance is already unmounted
  const setLog = (f: (l: LogItem[]) => LogItem[]) => { persist.log = f(persist.log); setLogRaw(persist.log); };
  const inputRef = useRef<HTMLInputElement>(null);
  const recRef = useRef<any>(null);
  const SR: any = typeof window !== "undefined" ? ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition) : null;

  useEffect(() => { if (open && !persist.log.length) setTimeout(() => inputRef.current?.focus(), 50); }, [open]);
  useEffect(() => { try { localStorage.setItem("skylapse.ask.lang", lang); } catch { /* storage blocked */ } }, [lang]);

  async function run(cmd: string) {
    const c = cmd.trim(); if (!c || busy) return;
    setBusy(true);
    let source: LogItem["source"] = "claude";
    let res = await callApi(c);
    let actions = res?.actions ?? [];
    const rejected = res?.rejected ?? [];
    if (!res || actions.length === 0) {
      const local = parseCommand(c);
      if (local.length) { actions = local; source = "local"; } else source = res ? "claude" : "none";
    }
    let note: string | undefined;
    if (actions.length) note = await applyActions(actions);
    else note = "I can only drive the viewer (open a target, compare, speed, zoom, overlays, spectrum, explanation). Try: “" + EXAMPLES[1] + "”.";
    if (rejected.length) note = [note, "Ignored: " + rejected.join("; ")].filter(Boolean).join(" · ");
    setLog((l) => [{ text: c, source, actions: actions.map(describe), note }, ...l].slice(0, 12));
    setText(""); setBusy(false);
  }

  function listen() {
    if (!SR) return;
    if (listening) { recRef.current?.stop(); return; }
    const rec = new SR(); recRef.current = rec;
    rec.lang = lang; rec.interimResults = true; rec.maxAlternatives = 1;
    rec.onresult = (e: any) => {
      const r = e.results[e.results.length - 1]; const said = r[0].transcript;
      setText(said); if (r.isFinal) { rec.stop(); run(said); }
    };
    rec.onerror = () => setListening(false); rec.onend = () => setListening(false);
    setListening(true); setOpen(true); rec.start();
  }

  const btn: React.CSSProperties = { border: "1px solid var(--line, #2a3550)", background: "var(--panel, #111a2b)", color: "var(--text, #e8eefc)",
    borderRadius: 8, padding: "6px 10px", cursor: "pointer", font: "inherit", fontSize: 13 };
  return (
    <div style={{ position: "relative" }}>
      <button style={{ ...btn, borderColor: "var(--accent, #4cc9f0)" }} onClick={() => setOpen((o) => !o)} aria-expanded={open} title="Ask SkyLapse — drive the viewer by voice or text">
        <Sparkles size={14} strokeWidth={1.75} style={{ verticalAlign: -2, marginRight: 6 }} />Ask SkyLapse
      </button>
      {open && (
        <div role="dialog" aria-label="Ask SkyLapse" style={{ position: "absolute", right: 0, top: "calc(100% + 8px)", zIndex: 50, width: "min(440px, 92vw)",
          background: "var(--panel, #0d1424)", color: "var(--text, #e8eefc)", border: "1px solid var(--line, #2a3550)", borderRadius: 12,
          boxShadow: "0 12px 40px rgba(0,0,0,.45)", padding: 12 }}>
          <div style={{ fontSize: 12, opacity: .75, marginBottom: 8 }}>Tell SkyLapse what to do — it drives the viewer. It does not make up facts or numbers.</div>
          <form onSubmit={(e) => { e.preventDefault(); run(text); }} style={{ display: "flex", gap: 6 }}>
            <input ref={inputRef} value={text} onChange={(e) => setText(e.target.value)} placeholder={listening ? "Listening…" : "e.g. compare 2010 with today"}
              aria-label="Command" style={{ ...btn, flex: 1, cursor: "text" }} disabled={busy} />
            {SR && <button type="button" onClick={listen} style={{ ...btn, background: listening ? "#c0392b" : btn.background }} title="Speak a command" aria-pressed={listening}>{listening ? <Square size={14} strokeWidth={2} style={{ verticalAlign: -2 }} /> : <Mic size={14} strokeWidth={1.75} style={{ verticalAlign: -2 }} />}</button>}
            <select value={lang} onChange={(e) => setLang(e.target.value)} style={btn} aria-label="Voice language">
              {LANGS.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
            <button type="submit" style={btn} disabled={busy}>{busy ? "…" : "Go"}</button>
          </form>
          {log.length === 0 && (
            <div style={{ marginTop: 10, fontSize: 12, opacity: .85 }}>Try:
              {EXAMPLES.map((x) => <div key={x}><button type="button" onClick={() => run(x)} style={{ ...btn, padding: "2px 6px", marginTop: 4, fontSize: 12 }}>{x}</button></div>)}
            </div>
          )}
          {log.length > 0 && (
            <ol aria-label="Actions taken" style={{ listStyle: "none", padding: 0, margin: "10px 0 0", maxHeight: 260, overflow: "auto", fontSize: 12 }}>
              {log.map((item, i) => (
                <li key={i} style={{ borderTop: i ? "1px solid var(--line, #2a3550)" : "none", padding: "6px 0" }}>
                  <div><b>“{item.text}”</b> <span style={{ opacity: .6 }}>· {item.source === "claude" ? "understood by Claude (AI)" : item.source === "local" ? "understood by the offline parser" : "not understood"}</span></div>
                  {item.actions.map((a, j) => <div key={j} style={{ color: "var(--accent, #4cc9f0)" }}>→ {a}</div>)}
                  {item.note && <div style={{ opacity: .75 }}>{item.note}</div>}
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}
