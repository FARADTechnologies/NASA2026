"""Voice replies for Ask SkyLapse via ElevenLabs (AI-generated audio — labelled in the UI). Optional: the browser voice is the fallback.

POST /api/speak {"text": str, "lang": "en"|"tr"|"az"} → audio/mpeg, or 503 {fallback: true}.
Config ONLY from env: ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID (default "Sarah"), ELEVENLABS_MODEL (default eleven_flash_v2_5).
Only short texts (the action log or our precomputed explanation) are sent; identical texts are served from a small memory cache
so repeated narration does not spend credits.
"""
from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

import httpx

_cache: "OrderedDict[str, bytes]" = OrderedDict()
MAX_CHARS = 900


def configured() -> bool:
    return bool(os.environ.get("ELEVENLABS_API_KEY"))


def synth(text: str, timeout_s: float = 8.0) -> tuple[int, bytes | dict]:
    text = (text or "").strip()[:MAX_CHARS]
    if not text:
        return 400, {"error": "empty text"}
    if not configured():
        return 503, {"fallback": True, "reason": "not configured"}
    voice = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
    model = os.environ.get("ELEVENLABS_MODEL", "eleven_flash_v2_5")
    key = hashlib.sha1(f"{voice}|{model}|{text}".encode()).hexdigest()
    if key in _cache:
        _cache.move_to_end(key)
        return 200, _cache[key]
    try:
        r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}", params={"output_format": "mp3_44100_64"},
                       headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "content-type": "application/json"},
                       json={"text": text, "model_id": model}, timeout=timeout_s)
    except httpx.HTTPError as e:
        return 503, {"fallback": True, "reason": f"unreachable ({type(e).__name__})"}
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("audio"):
        return 503, {"fallback": True, "reason": f"upstream HTTP {r.status_code}"}
    _cache[key] = r.content
    while len(_cache) > 120:
        _cache.popitem(last=False)
    return 200, r.content
