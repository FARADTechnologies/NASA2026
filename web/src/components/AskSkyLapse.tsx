// Ask SkyLapse — action-taking assistant (orchestrator, O6 #122). Text or voice command → validated viewer actions.
// Not a chatbot: it never answers with numbers or facts; it only drives the viewer and shows what it did.
// One mount point: <AskSkyLapse /> in the header. Styles are inline so the theme redesign cannot break it.
import { useEffect, useRef, useState } from "react";
import { ArrowUp, MessageCircle, Mic, RotateCcw, Square, Volume2, VolumeX, X } from "lucide-react";
import { navigate } from "../lib/router";
import { DEFAULTS, parseView, serializeView, type ViewState } from "../lib/url";
import { ACTIONS_EVENT, READY_EVENT, applyToView, type AskAction } from "../lib/commandBridge";
import { describe, parseCommand } from "../lib/askParser";

type LogItem = { text: string; source: "claude" | "local" | "none"; actions: string[]; note?: string };
const LANGS = [{ id: "az-AZ", label: "AZ", name: "Azərbaycan dili" }, { id: "en-US", label: "EN", name: "English" }, { id: "tr-TR", label: "TR", name: "Türkçe" }];
const EXAMPLES = ["show Barnard's Star in difference mode at double speed", "compare 2010 with today", "go to RA 162.3 Dec -53.3",
  "show the spectrum", "explain this object in Azerbaijani"];
const SHORT: Record<string, string> = {
  "show Barnard's Star in difference mode at double speed": "Barnard's Star, difference, 2× speed",
  "compare 2010 with today": "Compare 2010 with today",
  "go to RA 162.3 Dec -53.3": "Go to Luhman 16",
  "show the spectrum": "Show the spectrum",
  "explain this object in Azerbaijani": "Explain in Azerbaijani",
};
const TXT = {
  en: { sub: "Online · uses only our data", hi: "Hi!", welcome: "Tell me what you want to see — type or speak.",
    intro: "I can open a target, compare years, change speed or zoom, switch overlays, and show the spectrum or the explanation. I never make up numbers.",
    lang: "Which language will you speak?", today: "Today", ph: "Write a message…", listening: "Listening…", reset: "New conversation", close: "Close",
    voiceOn: "Voice replies on (browser speech)", voiceOff: "Voice replies off",
    src: { claude: "understood by Claude (AI)", local: "understood by the offline parser", none: "not understood" } },
  az: { sub: "Onlayn · yalnız bizim məlumat", hi: "Salam!", welcome: "Nə görmək istədiyinizi yazın və ya deyin.",
    intro: "Hədəfi aça, illəri müqayisə edə, sürəti və miqyası dəyişə, işarələri açıb-bağlaya, spektri və izahı göstərə bilərəm. Rəqəm uydurmuram.",
    lang: "Hansı dildə danışacaqsınız?", today: "Bu gün", ph: "Mesajınızı yazın…", listening: "Dinləyirəm…", reset: "Yeni söhbət", close: "Bağla",
    voiceOn: "Səsli cavab açıqdır (brauzer səsi)", voiceOff: "Səsli cavab bağlıdır",
    src: { claude: "Claude (AI) başa düşdü", local: "oflayn başa düşüldü", none: "başa düşülmədi" } },
};
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
// Voice replies: the browser's built-in speech (Web Speech API, no key, not AI-generated audio).
// It only reads our action log or our precomputed, fact-checked explanation — it never says anything else.
function speak(text: string, lang: string) {
  try {
    const s = window.speechSynthesis; if (!s || !text) return;
    s.cancel();
    const u = new SpeechSynthesisUtterance(text.slice(0, 900));
    const vs = s.getVoices(); const want = lang.toLowerCase();
    const v = vs.find((x) => x.lang.toLowerCase() === want) || vs.find((x) => x.lang.toLowerCase().startsWith(want.slice(0, 2)))
      || (want.startsWith("az") ? vs.find((x) => x.lang.toLowerCase().startsWith("tr")) : undefined);
    if (v) u.voice = v;
    u.lang = v?.lang || lang; u.rate = 1.03;
    s.speak(u);
  } catch { /* speech not available */ }
}
function copilotText(): string {
  const sec = document.querySelector('[data-section="copilot"]');
  if (!sec) return "";
  const ps = Array.from(sec.querySelectorAll("p")).map((p) => (p.textContent || "").trim()).filter((t) => t.length > 60);
  return ps.sort((a, b) => b.length - a.length)[0] || "";
}

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
  const [voice, setVoice] = useState(() => { try { return localStorage.getItem("skylapse.ask.voice") !== "off"; } catch { return true; } });
  const [log, setLogRaw] = useState<LogItem[]>(persist.log);
  // write the module copy first: after a command opens a new page this instance is already unmounted
  const setLog = (f: (l: LogItem[]) => LogItem[]) => { persist.log = f(persist.log); setLogRaw(persist.log); window.dispatchEvent(new Event("skylapse:asklog")); };
  // a command that opens a new page writes the log after this (new) instance mounted: listen for it
  useEffect(() => { const on = () => { setLogRaw(persist.log); setOpenRaw(persist.open); }; window.addEventListener("skylapse:asklog", on); return () => window.removeEventListener("skylapse:asklog", on); }, []);
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
    const local = parseCommand(c);
    const res = await callApi(c);
    let actions = res?.actions ?? [];
    const rejected = res?.rejected ?? [];
    let picked: string | undefined;
    // use whichever reading covers more of the command; ties go to Claude. Both only produce whitelisted actions.
    if (local.length > actions.length) {
      if (res && actions.length) picked = "Claude's reading was incomplete, so the offline parser's fuller reading was used.";
      actions = local; source = "local";
    } else if (!actions.length) source = res ? "claude" : "none";
    let note: string | undefined;
    if (actions.length) note = await applyActions(actions);
    else note = "I can only drive the viewer (open a target, compare, speed, zoom, overlays, spectrum, explanation). Try: “" + EXAMPLES[1] + "”.";
    if (picked) note = [picked, note].filter(Boolean).join(" · ");
    if (rejected.length) note = [note, "Ignored: " + rejected.join("; ")].filter(Boolean).join(" · ");
    setLog((l) => [{ text: c, source, actions: actions.map(describe), note }, ...l].slice(0, 12));
    if (voice) {
      const ex = actions.find((a) => a.type === "explain") as { type: "explain"; lang: "en" | "az" } | undefined;
      if (ex) setTimeout(() => speak(copilotText() || "The explanation is not available for this object.", ex.lang === "az" ? "az-AZ" : "en-US"), 1400);
      else speak(actions.length ? actions.map(describe).join(". ") + "." : "Sorry, I can only drive the viewer.", "en-US");
    }
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

  // same handler as before (voice on/off), only moved into the chat header
  const toggleVoice = () => { const v = !voice; setVoice(v); try { localStorage.setItem("skylapse.ask.voice", v ? "on" : "off"); } catch { /* blocked */ } if (!v) window.speechSynthesis?.cancel(); };
  const T = lang.startsWith("az") ? TXT.az : TXT.en;
  const Avatar = ({ big }: { big?: boolean }) => (
    <span className={"ask-avatar" + (big ? " lg" : "")} aria-hidden>
      <svg viewBox="0 0 32 32" width={big ? 30 : 18} height={big ? 30 : 18}><circle cx="8" cy="22" r="3" fill="#F0A040" opacity=".55" /><circle cx="16" cy="16" r="3.2" fill="#F0A040" /><circle cx="24" cy="10" r="3.6" fill="#3CC0D6" /></svg>
    </span>
  );
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
            <div className="ask-title"><b>SkyLapse assistant</b><span><i className="ask-dot" />{T.sub}</span></div>
            <button className="icon-btn" onClick={toggleVoice} aria-pressed={voice} aria-label={voice ? T.voiceOn : T.voiceOff} title={voice ? T.voiceOn : T.voiceOff}>
              {voice ? <Volume2 size={17} strokeWidth={1.75} /> : <VolumeX size={17} strokeWidth={1.75} />}
            </button>
            {log.length > 0 && (
              <button className="icon-btn" onClick={() => setLog(() => [])} aria-label={T.reset} title={T.reset}><RotateCcw size={16} strokeWidth={1.75} /></button>
            )}
            <button className="icon-btn" onClick={() => setOpen(false)} aria-label="Close" title={T.close}><X size={18} strokeWidth={1.75} /></button>
          </header>
          <div className="ask-body" ref={bodyRef}>
            <div className="ask-welcome">
              <Avatar big />
              <b>{T.hi}</b>
              <p>{T.welcome}</p>
            </div>
            <div className="ask-day"><span>{T.today}</span></div>
            <div className="msg-row"><Avatar /><div className="msg bot">{T.intro}</div></div>
            <div className="msg-row"><Avatar /><div className="msg bot">{T.lang}</div></div>
            <div className="chips">
              {LANGS.map((l) => (
                <button key={l.id} type="button" className={"chip" + (lang === l.id ? " on" : "")} onClick={() => setLang(l.id)} aria-pressed={lang === l.id}>
                  <small>{l.label}</small> {l.name}
                </button>
              ))}
            </div>
            {log.length === 0 && (
              <div className="chips">
                {EXAMPLES.map((x) => <button key={x} type="button" className="chip" onClick={() => run(x)} title={x}>{SHORT[x] ?? x}</button>)}
              </div>
            )}
            {[...log].reverse().map((item, i) => (
              <div key={i} className="turn">
                <div className="msg me">{item.text}</div>
                <div className="msg-row"><Avatar />
                  <div className="msg bot">
                    {item.actions.length > 0 && <ul>{item.actions.map((a, k) => <li key={k}>{a}</li>)}</ul>}
                    {item.note && <p>{item.note}</p>}
                    <span className="msg-meta">{T.src[item.source]}</span>
                  </div>
                </div>
              </div>
            ))}
            {busy && <div className="msg-row"><Avatar /><div className="msg bot typing" aria-label="Working"><i /><i /><i /></div></div>}
          </div>
          <form className="ask-input" onSubmit={(e) => { e.preventDefault(); run(text); }}>
            <input ref={inputRef} value={text} onChange={(e) => setText(e.target.value)} placeholder={listening ? T.listening : T.ph}
              aria-label="Command" disabled={busy} />
            {SR && (
              <button type="button" className={"icon-btn" + (listening ? " rec" : "")} onClick={listen} title={`Speak (${LANGS.find((l) => l.id === lang)?.name ?? lang})`} aria-pressed={listening}>
                {listening ? <Square size={15} strokeWidth={2} /> : <Mic size={16} strokeWidth={1.75} />}
              </button>
            )}
            <button type="submit" className="ask-send" disabled={busy || !text.trim()} aria-label="Send" title="Send"><ArrowUp size={18} strokeWidth={2} /></button>
          </form>
        </div>
      )}
    </div>
  );
}
