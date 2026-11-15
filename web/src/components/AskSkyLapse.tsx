// Ask SkyLapse — action-taking assistant (orchestrator, O6 #122). Text or voice command → validated viewer actions.
// Not a chatbot: it never answers with numbers or facts; it only drives the viewer and shows what it did.
// One mount point: <AskSkyLapse /> in the header (floats bottom-right as a chat widget; styles: .ask-* / .msg / .chip in styles.css).
import { useEffect, useRef, useState } from "react";
import { ArrowUp, MessageCircle, Mic, RotateCcw, Square, Volume2, VolumeX, X } from "lucide-react";
import { navigate } from "../lib/router";
import { DEFAULTS, parseView, serializeView, type ViewState } from "../lib/url";
import { ACTIONS_EVENT, READY_EVENT, SAY_EVENT, applyToView, waitFor, type AskAction } from "../lib/commandBridge";
import { describe, parseCommand } from "../lib/askParser";

type LogItem = { text: string; source: "claude" | "local" | "none"; actions: string[]; note?: string };
const LANGS = [{ id: "az-AZ", label: "AZ", name: "Azərbaycan dili" }, { id: "en-US", label: "EN", name: "English" }, { id: "tr-TR", label: "TR", name: "Türkçe" }];
// short chip labels → the full command that is sent
const QUICK: { label: string; cmd: string }[] = [
  { label: "Tell me about WISE 0855", cmd: "tell me about WISE 0855" },
  { label: "Barnard's Star in full spectral view", cmd: "find Barnard's Star and show its motion in full spectral view" },
  { label: "Barnard's Star, difference, 2× speed", cmd: "show Barnard's Star in difference mode at double speed" },
  { label: "Compare 2010 with today", cmd: "compare 2010 with today" },
  { label: "Go to Luhman 16", cmd: "go to RA 162.3 Dec -53.3" },
  { label: "Show the spectrum", cmd: "show the spectrum" },
  { label: "Explain in Azerbaijani", cmd: "explain this object in Azerbaijani" },
];
const TXT = {
  en: { sub: "Online · uses only our data", hi: "Hi!", welcome: "Tell me what you want to see — type or speak.",
    intro: "I can open a target, compare years, change speed or zoom, switch overlays, show the spectrum or the explanation — or walk you through a target card by card and read its facts aloud (“tell me about Barnard's Star”). I never make up numbers.",
    lang: "Which language will you speak?", today: "Today", ph: "Write a message…", listening: "Listening…", reset: "New conversation", close: "Close",
    voiceOn: "Voice replies on — AI-generated voice (ElevenLabs), browser voice as fallback", voiceOff: "Voice replies off",
    voiceNote: "Spoken replies use an AI-generated voice (ElevenLabs).",
    src: { claude: "understood by Claude (AI)", local: "understood offline", none: "not understood" } },
  az: { sub: "Onlayn · yalnız bizim məlumat", hi: "Salam!", welcome: "Nə görmək istədiyinizi yazın və ya deyin.",
    intro: "Hədəfi aça, illəri müqayisə edə, sürəti və miqyası dəyişə, işarələri açıb-bağlaya, spektri və izahı göstərə, ya da hədəfi səhifədə kart-kart göstərib faktlarını səsli oxuya bilərəm (“Barnard ulduzu haqqında danış”). Rəqəm uydurmuram.",
    lang: "Hansı dildə danışacaqsınız?", today: "Bu gün", ph: "Mesajınızı yazın…", listening: "Dinləyirəm…", reset: "Yeni söhbət", close: "Bağla",
    voiceOn: "Səsli cavab açıqdır — süni intellekt səsi (ElevenLabs)", voiceOff: "Səsli cavab bağlıdır",
    voiceNote: "Səsli cavablar süni intellektlə yaradılmış səsdir (ElevenLabs).",
    src: { claude: "Claude (AI) başa düşdü", local: "oflayn başa düşüldü", none: "başa düşülmədi" } },
};
const EXAMPLES = ["find Barnard's Star and show its motion in full spectral view", "show Barnard's Star in difference mode at double speed", "compare 2010 with today", "go to RA 162.3 Dec -53.3",
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
// Voice replies: the browser's built-in speech (Web Speech API, no key, not AI-generated audio).
// It only reads our action log or our precomputed, fact-checked explanation — it never says anything else.
let currentAudio: HTMLAudioElement | null = null;
export let lastVoice: "elevenlabs" | "browser" | null = null;
// ElevenLabs first (server-side key, AI voice), browser speech as the fallback
let speechId = 0;
/** Stop whatever is being said (a new command or the mic must not talk over the user). */
export function stopSpeech() {
  speechId++;
  try { currentAudio?.pause(); window.speechSynthesis?.cancel(); } catch { /* ignore */ }
}
/** Say a sentence; resolves when it has been said (or was interrupted). */
function speakWait(text: string, lang: string): Promise<void> {
  return new Promise((resolve) => {
    if (!text) { resolve(); return; }
    window.dispatchEvent(new Event("skylapse:speaking")); // the panel closes while the answer is spoken (UI only)
    stopSpeech();
    const my = speechId;
    (async () => {
      const ctl = new AbortController(); const timer = setTimeout(() => ctl.abort(), 6000);
      try {
        const r = await fetch("/api/speak", { method: "POST", headers: { "content-type": "application/json" }, signal: ctl.signal,
          body: JSON.stringify({ text: text.slice(0, 900), lang: lang.slice(0, 2) }) });
        if (r.ok && (r.headers.get("content-type") || "").startsWith("audio")) {
          const blob = await r.blob();
          if (my !== speechId) { resolve(); return; } // something newer started meanwhile
          const url = URL.createObjectURL(blob);
          const a = new Audio(url); currentAudio = a; lastVoice = "elevenlabs";
          const fin = () => { URL.revokeObjectURL(url); resolve(); };
          a.onended = fin; a.onpause = fin; a.onerror = fin;
          await a.play();
          return;
        }
      } catch { /* fall through to the browser voice */ } finally { clearTimeout(timer); }
      if (my !== speechId) { resolve(); return; }
      browserSpeak(text, lang, resolve);
    })();
  });
}
// spoken replies go through the event, so the assistant that is mounted NOW (after a page change) speaks and shows the subtitle
const sayNow = (text: string, lang: "en" | "az" = "en") => window.dispatchEvent(new CustomEvent(SAY_EVENT, { detail: { text, lang } }));
function browserSpeak(text: string, lang: string, done: () => void = () => {}) {
  lastVoice = "browser";
  try {
    const s = window.speechSynthesis; if (!s || !text) { done(); return; }
    s.cancel();
    const u = new SpeechSynthesisUtterance(text.slice(0, 900));
    const vs = s.getVoices(); const want = lang.toLowerCase();
    const v = vs.find((x) => x.lang.toLowerCase() === want) || vs.find((x) => x.lang.toLowerCase().startsWith(want.slice(0, 2)))
      || (want.startsWith("az") ? vs.find((x) => x.lang.toLowerCase().startsWith("tr")) : undefined);
    if (v) u.voice = v;
    u.lang = v?.lang || lang; u.rate = 1.03;
    u.onend = () => done(); u.onerror = () => done();
    s.speak(u);
  } catch { done(); /* speech not available */ }
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
  // subtitles of what the assistant says (the panel is closed while it talks; useful in a noisy room or with voice off)
  const [caption, setCaption] = useState("");
  const talk = async (t: string, l: string) => {
    if (!t) return;
    setCaption(t);
    if (voice) await speakWait(t, l);
    else { window.dispatchEvent(new Event("skylapse:speaking")); await new Promise((r) => setTimeout(r, Math.min(12000, 1800 + t.length * 55))); }
    setCaption((c) => (c === t ? "" : c));
  };
  // the bridge narrates tours through this event; {done} lets a guided tour wait for each sentence
  useEffect(() => {
    const on = (e: Event) => {
      const d = (e as CustomEvent).detail as string | { text: string; lang?: string; done?: () => void };
      const o = typeof d === "string" ? { text: d } : d || { text: "" };
      void talk(String(o.text || ""), o.lang === "az" ? "az-AZ" : "en-US").finally(() => o.done?.());
    };
    window.addEventListener(SAY_EVENT, on); return () => window.removeEventListener(SAY_EVENT, on);
  }, [voice]);
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

  // header mic (push-to-talk) sends its transcript here; a spoken answer closes the panel (reopen with the button)
  const runRef = useRef<(c: string) => void>(() => {});
  useEffect(() => {
    const onRun = (e: Event) => runRef.current(String((e as CustomEvent).detail || ""));
    const onSpeak = () => setOpen(false);
    window.addEventListener("skylapse:ask-run", onRun); window.addEventListener("skylapse:speaking", onSpeak);
    return () => { window.removeEventListener("skylapse:ask-run", onRun); window.removeEventListener("skylapse:speaking", onSpeak); };
  }, []);
  async function run(cmd: string) {
    const c = cmd.trim(); if (!c || busy) return;
    stopSpeech(); setCaption(""); // a new command interrupts whatever is being said
    setBusy(true);
    setOpen(false); // collapse back to the button at once, so the whole page is visible while the answer runs
    let source: LogItem["source"] = "claude";
    const local = parseCommand(c);
    const res = await callApi(c);
    let actions = res?.actions ?? [];
    const rejected = res?.rejected ?? [];
    let picked: string | undefined;
    // use whichever reading covers more of the command; ties go to Claude. Both only produce whitelisted actions.
    const AGENTIC = new Set(["tell_about", "show_spectral_motion"]);
    const tourOnlyLocal = local.some((a) => AGENTIC.has(a.type)) && !actions.some((a) => AGENTIC.has(a.type));
    if (local.length > actions.length || (tourOnlyLocal && local.length >= actions.length)) {
      if (res && actions.length) picked = "Claude's reading was incomplete, so the offline parser's fuller reading was used.";
      actions = local; source = "local";
    } else if (!actions.length) source = res ? "claude" : "none";
    let note: string | undefined;
    let blocked = false;
    if (actions.length) { note = await applyActions(actions); blocked = !!note; }
    else note = "I can only drive the viewer (open a target, compare, speed, zoom, overlays, spectrum, explanation). Try: “" + EXAMPLES[1] + "”.";
    if (picked) note = [picked, note].filter(Boolean).join(" · ");
    if (rejected.length) note = [note, "Ignored: " + rejected.join("; ")].filter(Boolean).join(" · ");
    setLog((l) => [{ text: c, source, actions: actions.map(describe), note }, ...l].slice(0, 12));
    setOpen(false); // the answer starts: close the panel so it does not cover the page (reopen with the button)
    {
      const ex = actions.find((a) => a.type === "explain") as { type: "explain"; lang: "en" | "az" } | undefined;
      // the explanation appears once the object data have loaded (also when the command opened the viewer from the home page)
      if (ex) void waitFor(() => document.querySelector('[data-section="copilot"]'), 8000).then(() => new Promise((r) => setTimeout(r, 400)))
        .then(() => sayNow(copilotText() || "The explanation is not available for this object.", ex.lang));
      else if (blocked || !actions.length) sayNow(blocked ? "I need a target first. Say, for example: tell me about Barnard's Star." : "Sorry, I can only drive the viewer. Try: compare 2010 with today.");
      else if (!actions.some((a) => a.type === "show_spectral_motion" || a.type === "tell_about")) sayNow(actions.map(describe).join(". ") + ".");
    }
    setText(""); setBusy(false);
  }

  runRef.current = run;
  function listen() {
    if (!SR) return;
    if (listening) { recRef.current?.stop(); return; }
    stopSpeech(); setCaption(""); // do not record our own voice
    // press = start listening; talk as long as needed; press again = stop and send (nothing is sent before that)
    const rec = new SR(); recRef.current = rec; let said = "";
    rec.lang = lang; rec.continuous = true; rec.interimResults = true; rec.maxAlternatives = 1;
    rec.onresult = (e: any) => {
      let finalT = "", interim = "";
      for (let i = 0; i < e.results.length; i++) { const r = e.results[i]; if (r.isFinal) finalT += r[0].transcript + " "; else interim += r[0].transcript; }
      said = (finalT + interim).trim(); setText(said);
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => { setListening(false); if (said.trim()) run(said.trim()); };
    setListening(true); setOpen(true); rec.start();
  }

  const toggleVoice = () => { const v = !voice; setVoice(v); try { localStorage.setItem("skylapse.ask.voice", v ? "on" : "off"); } catch { /* blocked */ } if (!v) stopSpeech(); };
  const T = lang.startsWith("az") ? TXT.az : TXT.en;
  const Avatar = ({ big }: { big?: boolean }) => (
    <span className={"ask-avatar" + (big ? " lg" : "")} aria-hidden>
      <svg viewBox="0 0 32 32" width={big ? 30 : 18} height={big ? 30 : 18}><circle cx="8" cy="22" r="3" fill="#F0A040" opacity=".55" /><circle cx="16" cy="16" r="3.2" fill="#F0A040" /><circle cx="24" cy="10" r="3.6" fill="#3CC0D6" /></svg>
    </span>
  );
  return (
    <div className="ask">
      {caption && !open && (
        <div className="ask-caption" role="status" aria-live="polite" style={{ position: "fixed", left: "50%", bottom: 22, transform: "translateX(-50%)",
          width: "max-content", maxWidth: "min(720px, calc(100vw - 32px))", maxHeight: "30vh", overflow: "hidden", padding: "10px 16px", borderRadius: 12,
          background: "rgba(8, 12, 22, 0.86)", color: "#f2f5fa", fontSize: 15, lineHeight: 1.45, zIndex: 70, pointerEvents: "none",
          boxShadow: "0 6px 24px rgba(0,0,0,.35)" }}>{caption}</div>
      )}
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
            <div className="msg-row"><Avatar /><div className="msg bot">{T.intro}{voice && <span className="msg-meta">{T.voiceNote}</span>}</div></div>
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
                {QUICK.map((q) => <button key={q.cmd} type="button" className="chip" onClick={() => run(q.cmd)} title={q.cmd}>{q.label}</button>)}
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


/** Header microphone — push-to-talk for Ask SkyLapse: press once to start listening, press again to send. UI only. */
export function AskMic() {
  const SR: any = typeof window !== "undefined" ? ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition) : null;
  const [on, setOn] = useState(false);
  const [heard, setHeard] = useState("");
  const recRef = useRef<any>(null);
  const textRef = useRef("");
  if (!SR) return null;
  function toggle() {
    if (on) { recRef.current?.stop(); return; } // second press: stop → onend sends
    stopSpeech(); // do not record our own voice
    let lang = "en-US"; try { lang = localStorage.getItem("skylapse.ask.lang") || "en-US"; } catch { /* storage blocked */ }
    const rec = new SR(); recRef.current = rec; textRef.current = ""; setHeard("");
    rec.lang = lang; rec.continuous = true; rec.interimResults = true; rec.maxAlternatives = 1;
    rec.onresult = (e: any) => {
      let finalT = "", interim = "";
      for (let i = 0; i < e.results.length; i++) { const r = e.results[i]; if (r.isFinal) finalT += r[0].transcript + " "; else interim += r[0].transcript; }
      textRef.current = (finalT + interim).trim(); setHeard(textRef.current);
    };
    rec.onerror = () => setOn(false);
    rec.onend = () => {
      setOn(false);
      const said = textRef.current.trim(); setHeard("");
      if (said) window.dispatchEvent(new CustomEvent("skylapse:ask-run", { detail: said }));
    };
    setOn(true); rec.start();
  }
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, minWidth: 0 }}>
      <button type="button" className={"icon-btn" + (on ? " rec" : "")} onClick={toggle} aria-pressed={on}
        title={on ? "Listening — press again to send" : "Speak to SkyLapse (press, talk, press again)"} aria-label={on ? "Stop and send" : "Speak to SkyLapse"}
        style={on ? { background: "#c0392b", color: "#fff", borderColor: "#c0392b" } : undefined}>
        {on ? <Square size={15} strokeWidth={2} /> : <Mic size={17} strokeWidth={1.75} />}
      </button>
      {on && <span className="muted small" style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{heard || "Listening… press again to send"}</span>}
    </span>
  );
}
