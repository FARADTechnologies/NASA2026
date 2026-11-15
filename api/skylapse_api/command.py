"""Ask SkyLapse (O6): natural-language command → validated viewer actions. Not a chatbot: it never answers questions or states numbers.

POST /api/command {"text": str, "context": {"path": str, "field": str|None, "lang": "en"|"tr"|"az"}}
→ 200 {"actions": [...], "source": "claude", "model": ...}  |  503 {"fallback": true, ...} (the browser then uses its own parser)

The language model may only pick from a fixed tool list; every action is re-validated here. Numbers (coordinates, fps, zoom)
must literally appear in the user's text, so the assistant cannot invent them. Config ONLY from env (ANTHROPIC_API_KEY,
ANTHROPIC_BASE_URL, COPILOT_MODEL) — the organizers' tunnel URL can change.
"""
from __future__ import annotations

import os
import re

import httpx

FIELDS = {
    "barnard": "Barnard's Star", "eps_indi_b": "Epsilon Indi B", "wise0855": "WISE 0855-0714",
    "rw_aur": "RW Aurigae", "r_dra": "R Draconis",
}
SEQUENCES = {"thermal46", "w1d4", "spherex6"}
COMPARE = {"off", "vs2010", "previous", "chosen"}
STRETCH = {"linear", "asinh", "log"}
OVERLAYS = {"gaia", "track", "mask"}
LANGS = {"en", "az"}

TOOLS = [
    {"name": "open_field", "description": "Open one of the precomputed NASA target fields.",
     "input_schema": {"type": "object", "properties": {"field": {"type": "string", "enum": sorted(FIELDS)}}, "required": ["field"]}},
    {"name": "open_coordinates", "description": "Open a live field at sky coordinates given IN THE USER'S WORDS (degrees).",
     "input_schema": {"type": "object", "properties": {"ra": {"type": "number"}, "dec": {"type": "number"}}, "required": ["ra", "dec"]}},
    {"name": "set_sequence", "description": "thermal46 = 4.6 µm WISE W2 + SPHEREx D6 (default); w1d4 = 3.4 µm; spherex6 = SPHEREx only.",
     "input_schema": {"type": "object", "properties": {"sequence": {"type": "string", "enum": sorted(SEQUENCES)}}, "required": ["sequence"]}},
    {"name": "set_compare", "description": "Difference mode: off, vs2010 (each frame minus the first, 2010), previous (minus previous frame), chosen.",
     "input_schema": {"type": "object", "properties": {"mode": {"type": "string", "enum": sorted(COMPARE)}}, "required": ["mode"]}},
    {"name": "set_speed", "description": "Playback speed. Use factor (2 = double speed, 0.5 = half) or fps if the user says a number.",
     "input_schema": {"type": "object", "properties": {"factor": {"type": "number"}, "fps": {"type": "number"}}}},
    {"name": "set_stretch", "description": "Brightness scale.",
     "input_schema": {"type": "object", "properties": {"stretch": {"type": "string", "enum": sorted(STRETCH)}}, "required": ["stretch"]}},
    {"name": "set_zoom", "description": "Zoom: factor (2 = zoom in twice) or field width in arcminutes if the user says a number.",
     "input_schema": {"type": "object", "properties": {"factor": {"type": "number"}, "fov_arcmin": {"type": "number"}}}},
    {"name": "toggle_overlay", "description": "Show or hide an overlay: gaia (known stars), track (target path), mask (flagged/saturated pixels).",
     "input_schema": {"type": "object", "properties": {"overlay": {"type": "string", "enum": sorted(OVERLAYS)}, "on": {"type": "boolean"}},
                      "required": ["overlay"]}},
    {"name": "play", "description": "Play the movie.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "pause", "description": "Pause the movie.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "step", "description": "Step frames forward (+1) or backward (-1).",
     "input_schema": {"type": "object", "properties": {"direction": {"type": "integer", "enum": [-1, 1]}}}},
    {"name": "go_to_frame", "description": "Jump to the first (2010) or last (most recent) frame.",
     "input_schema": {"type": "object", "properties": {"which": {"type": "string", "enum": ["first", "last"]}}, "required": ["which"]}},
    {"name": "show_spectrum", "description": "Scroll to the object's SPHEREx spectrum.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "show_lightcurve", "description": "Scroll to the object's light curve.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "explain", "description": "Show our precomputed, fact-checked explanation of the current object in English (en) or Azerbaijani (az).",
     "input_schema": {"type": "object", "properties": {"lang": {"type": "string", "enum": sorted(LANGS)}}, "required": ["lang"]}},
]

SYSTEM = (
    "You are the command interpreter of SkyLapse, a web viewer that plays 16 years of infrared sky images as a movie. "
    "Translate the user's command (English, Turkish or Azerbaijani) into one or more tool calls, in the order they should run. "
    "Use ONLY the tools. Never answer questions in text and never state facts or numbers. Numbers in tool inputs must come from the "
    "user's own words (for 'double speed' use factor 2; 'half speed' factor 0.5). 'Compare 2010 with today' = set_compare vs2010 + "
    "go_to_frame last + pause. Turkish/Azerbaijani requests for an explanation in Azerbaijani → explain az; otherwise explain en. "
    f"Known fields: {', '.join(f'{k} = {v}' for k, v in FIELDS.items())}. Named live fields (use open_coordinates with exactly these): "
    "Luhman 16 = 162.3057 -53.3177, Teegarden's Star = 43.2716 16.8623, Kapteyn's Star = 77.9651 -45.0470. "
    "If the command cannot be done with the tools, call no tool."
)

NUM = re.compile(r"[-+−]?\d+(?:[.,]\d+)?")
# named live demo fields (coordinates from our own file pipeline/qa/live_api_test.md, T9 #78): allowed by name only
NAMED_LIVE = {"luhman": (162.3057, -53.3177), "teegarden": (43.2716, 16.8623), "kapteyn": (77.9651, -45.0470)}
WORD_FACTORS = {2.0: ("double", "twice", "2x", "faster", "iki kat", "2 kat", "daha hızlı", "hızlandır", "iki dəfə", "ikiqat", "sürətli"),
                0.5: ("half", "slower", "yarı", "yarım", "yarıya", "yavaş", "yarı sürət"), 3.0: ("triple", "3x", "üç kat"), 4.0: ("4x",)}


def _nums_in(text: str) -> list[float]:
    out = []
    for n in NUM.findall(text):
        try:
            out.append(float(n.replace("−", "-").replace(",", ".")))
        except ValueError:
            pass
    return out


def _in_text(x: float, text: str, tol: float = 1e-6) -> bool:
    return any(abs(abs(x) - abs(n)) < max(tol, 1e-9) for n in _nums_in(text))


def _factor_ok(f: float, text: str) -> bool:
    low = text.lower()
    return _in_text(f, text) or any(abs(f - k) < 1e-9 and any(w in low for w in ws) for k, ws in WORD_FACTORS.items())


def validate(actions: list[dict], text: str) -> tuple[list[dict], list[str]]:
    """Keep only well-formed actions whose numbers come from the user's text. Returns (actions, rejected-reasons)."""
    ok, rejected = [], []
    for a in actions[:8]:
        t, p = a.get("type"), {k: v for k, v in a.items() if k != "type"}
        try:
            if t == "open_field" and p.get("field") in FIELDS:
                ok.append({"type": t, "field": p["field"]})
            elif t == "open_coordinates":
                ra, dec = float(p["ra"]), float(p["dec"])
                named = [c for k, c in NAMED_LIVE.items() if k in text.lower()]
                if named and abs(named[0][0] - ra) < 0.01 and abs(named[0][1] - dec) < 0.01:
                    ok.append({"type": t, "ra": named[0][0], "dec": named[0][1]})
                elif 0 <= ra < 360 and -90 <= dec <= 90 and _in_text(ra, text) and _in_text(dec, text):
                    ok.append({"type": t, "ra": ra, "dec": dec})
                else:
                    rejected.append("coordinates not found in your words")
            elif t == "set_sequence" and p.get("sequence") in SEQUENCES:
                ok.append({"type": t, "sequence": p["sequence"]})
            elif t == "set_compare" and p.get("mode") in COMPARE:
                ok.append({"type": t, "mode": p["mode"]})
            elif t == "set_speed":
                if "fps" in p and p["fps"] is not None and 0.2 <= float(p["fps"]) <= 25 and _in_text(float(p["fps"]), text):
                    ok.append({"type": t, "fps": float(p["fps"])})
                elif "factor" in p and p["factor"] is not None and 0.1 <= float(p["factor"]) <= 10 and _factor_ok(float(p["factor"]), text):
                    ok.append({"type": t, "factor": float(p["factor"])})
                else:
                    rejected.append("speed value not found in your words")
            elif t == "set_stretch" and p.get("stretch") in STRETCH:
                ok.append({"type": t, "stretch": p["stretch"]})
            elif t == "set_zoom":
                if p.get("fov_arcmin") is not None and 1 <= float(p["fov_arcmin"]) <= 30 and _in_text(float(p["fov_arcmin"]), text):
                    ok.append({"type": t, "fov_arcmin": float(p["fov_arcmin"])})
                elif p.get("factor") is not None and 0.2 <= float(p["factor"]) <= 8 and _factor_ok(float(p["factor"]), text):
                    ok.append({"type": t, "factor": float(p["factor"])})
                else:
                    rejected.append("zoom value not found in your words")
            elif t == "toggle_overlay" and p.get("overlay") in OVERLAYS:
                ok.append({"type": t, "overlay": p["overlay"], **({"on": bool(p["on"])} if "on" in p else {})})
            elif t in ("play", "pause", "show_spectrum", "show_lightcurve"):
                ok.append({"type": t})
            elif t == "step":
                ok.append({"type": t, "direction": -1 if int(p.get("direction", 1)) < 0 else 1})
            elif t == "go_to_frame" and p.get("which") in ("first", "last"):
                ok.append({"type": t, "which": p["which"]})
            elif t == "explain" and p.get("lang") in LANGS:
                ok.append({"type": t, "lang": p["lang"]})
            else:
                rejected.append(f"unknown action {t}")
        except (TypeError, ValueError, KeyError):
            rejected.append(f"malformed action {t}")
    return ok, rejected


def interpret(text: str, context: dict | None = None, timeout_s: float = 6.0) -> tuple[int, dict]:
    text = (text or "").strip()[:300]
    if not text:
        return 400, {"error": "empty command"}
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return 503, {"fallback": True, "reason": "not configured"}
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    # fastest model for commands (set COMMAND_MODEL on Railway after measuring); falls back to the copilot model
    model = os.environ.get("COMMAND_MODEL") or os.environ.get("COPILOT_MODEL", "claude-opus-5-5")
    ctx = context or {}
    user = f"Current view: {ctx.get('field') or ctx.get('path') or 'home page'}.\nCommand: {text}"
    try:
        r = httpx.post(f"{base}/v1/messages", timeout=timeout_s, headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": 1024, "thinking": {"type": "disabled"}, "system": SYSTEM, "tools": TOOLS,
                  "tool_choice": {"type": "auto"}, "messages": [{"role": "user", "content": user}]})
    except httpx.TimeoutException:
        return 503, {"fallback": True, "reason": f"AI took longer than {timeout_s:.0f} s"}
    except httpx.HTTPError as e:
        return 503, {"fallback": True, "reason": f"unreachable ({type(e).__name__})"}
    if r.status_code != 200:
        return 503, {"fallback": True, "reason": f"upstream HTTP {r.status_code}"}
    try:
        blocks = r.json().get("content", [])
    except ValueError:
        return 503, {"fallback": True, "reason": "unparseable answer"}
    raw = [{"type": b.get("name"), **(b.get("input") or {})} for b in blocks if b.get("type") == "tool_use"]
    actions, rejected = validate(raw, text)
    return 200, {"actions": actions, "rejected": rejected, "source": "claude", "model": model}
