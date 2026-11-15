// Ask SkyLapse — action-taking assistant (orchestrator, O6 #122). Text or voice command → validated viewer actions.
// Not a chatbot: it never answers with numbers or facts; it only drives the viewer and shows what it did.
// One mount point: <AskSkyLapse /> in the header (floats bottom-right as a chat widget; styles: .ask-* in styles.css).
import { useEffect, useRef, useState } from "react";
import { ArrowUp, MessageCircle, Mic, Square, X } from "lucide-react";
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
  const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), 7000);
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
  const bodyRef = useRef<HTMLDivElement>(null);
  useEffect(() => { const b = bodyRef.current; if (b) b.scrollTop = b.scrollHeight; }, [log, busy, open]);
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

  const Avatar = ({ big }: { big?: boolean }) => (
    <span className={"ask-avatar" + (big ? " lg" : "")} aria-hidden>
      <svg viewBox="0 0 32 32" width={big ? 30 : 18} height={big ? 30 : 18}><circle cx="8" cy="22" r="3" fill="#F0A040" opacity=".55" /><circle cx="16" cy="16" r="3.2" fill="#F0A040" /><circle cx="24" cy="10" r="3.6" fill="#3CC0D6" /></svg>
    </span>
  );
  const sourceLabel = (s: LogItem["source"]) => (s === "claude" ? "understood by Claude (AI)" : s === "local" ? "understood offline" : "not understood");
  return (
    <div className="ask">
      {!open && (
        <button className="ask-launcher" onClick={() => setOpen(true)} aria-expanded={false} title="Ask SkyLapse — drive the viewer by voice or text">
          <MessageCircle size={18} strokeWidth={1.9} /> Ask SkyLapse
        </button>
      )}
      {open && (
        <div role="dialog" aria-label="Ask SkyLapse" className="ask-panel">
          <header className="ask-head">
            <Avatar />
            <div className="ask-title"><b>SkyLapse assistant</b><span>Moves the viewer for you · uses only our data</span></div>
            <button className="icon-btn" onClick={() => setOpen(false)} aria-label="Close" title="Close"><X size={18} strokeWidth={1.75} /></button>
          </header>
          <div className="ask-body" ref={bodyRef}>
            <div className="ask-welcome">
              <Avatar big />
              <b>Salam! Hi!</b>
              <p>Tell me what you want to see — in English or Azerbaijani, by typing or by voice.</p>
            </div>
            <div className="msg bot">I can open a target, compare years, change the speed or zoom, switch overlays, and show the spectrum or the explanation. I never make up numbers.</div>
            {log.length === 0 && (
              <div className="chips">
                {EXAMPLES.map((x) => <button key={x} type="button" className="chip" onClick={() => run(x)}>{x}</button>)}
              </div>
            )}
            {[...log].reverse().map((item, i) => (
              <div key={i} className="turn">
                <div className="msg me">{item.text}</div>
                <div className="msg bot">
                  {item.actions.length > 0 && <ul>{item.actions.map((a, k) => <li key={k}>{a}</li>)}</ul>}
                  {item.note && <p>{item.note}</p>}
                  <span className="msg-meta">{sourceLabel(item.source)}</span>
                </div>
              </div>
            ))}
            {busy && <div className="msg bot typing" aria-label="Working"><i /><i /><i /></div>}
          </div>
          <form className="ask-input" onSubmit={(e) => { e.preventDefault(); run(text); }}>
            <input ref={inputRef} value={text} onChange={(e) => setText(e.target.value)} placeholder={listening ? "Listening…" : "Write a message…"}
              aria-label="Command" disabled={busy} />
            {SR && (
              <button type="button" className={"icon-btn" + (listening ? " rec" : "")} onClick={listen} title="Speak a command" aria-pressed={listening}>
                {listening ? <Square size={15} strokeWidth={2} /> : <Mic size={16} strokeWidth={1.75} />}
              </button>
            )}
            <select value={lang} onChange={(e) => setLang(e.target.value)} aria-label="Voice language" title="Voice language">
              {LANGS.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
            </select>
            <button type="submit" className="ask-send" disabled={busy || !text.trim()} aria-label="Send" title="Send"><ArrowUp size={18} strokeWidth={2} /></button>
          </form>
        </div>
      )}
    </div>
  );
}
