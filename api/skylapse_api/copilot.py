"""Live AI copilot (contract §7: POST /api/copilot {facts} → {en, az}). Optional add-on: the site never depends on it.

Config ONLY from environment variables (never hard-coded — the organizers' tunnel URL can change):
  ANTHROPIC_API_KEY   key for the Messages API
  ANTHROPIC_BASE_URL  base URL of an Anthropic-compatible Messages API (default https://api.anthropic.com)
  COPILOT_MODEL       model id (default claude-opus-5-5)
Every failure returns a fallback payload; the frontend keeps showing the precomputed texts from the bundle.
"""
from __future__ import annotations

import json
import os
import re

import httpx

SYSTEM = (
    "You explain astronomy measurements to curious students. Use ONLY the facts in the JSON the user sends; "
    "do not add any number, name, date or claim that is not in the facts. Never say 'discovery' or 'discovered' "
    "(say 'candidate'), never mention Planet X. At most 110 words per language. "
    'Answer with JSON only: {"en": "<English text>", "az": "<Azerbaijani text, Latin script>"}.'
)
FALLBACK_MSG = "The live AI copilot is not available right now; the precomputed explanation is shown instead."
NUM = re.compile(r"\d+(?:[.,]\d+)?")


def configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _fallback(reason: str) -> dict:
    return {"fallback": True, "message": FALLBACK_MSG, "reason": reason}


def _numbers_ok(text: str, facts_blob: str) -> bool:
    """Every number with ≥ 2 digits in the text must occur in the facts (decimal comma allowed for AZ)."""
    for n in NUM.findall(text):
        if len(n.replace(".", "").replace(",", "")) < 2:
            continue
        if n not in facts_blob and n.replace(",", ".") not in facts_blob:
            return False
    return True


def generate(facts: dict, timeout_s: float = 45.0) -> tuple[int, dict]:
    if not configured():
        return 503, _fallback("not configured")
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    model = os.environ.get("COPILOT_MODEL", "claude-opus-5-5")
    facts_blob = json.dumps(facts, ensure_ascii=False)
    if len(facts_blob) > 8000:
        return 400, {"error": "facts too large"}
    try:
        r = httpx.post(f"{base}/v1/messages", timeout=timeout_s, headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": 4000, "thinking": {"type": "disabled"}, "system": SYSTEM,
                  "messages": [{"role": "user", "content": f"Facts JSON:\n{facts_blob}"}]})
    except httpx.HTTPError as e:
        return 503, _fallback(f"unreachable ({type(e).__name__})")
    if r.status_code != 200:
        return 503, _fallback(f"upstream HTTP {r.status_code}")
    try:
        text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
        m = re.search(r"\{.*\}", text, re.S)
        out = json.loads(m.group(0)) if m else {}
        en, az = str(out.get("en", "")).strip(), str(out.get("az", "")).strip()
    except Exception:  # noqa: BLE001
        return 503, _fallback("unparseable answer")
    if not en or not az:
        return 503, _fallback("empty answer")
    low = f"{en} {az}".lower()
    if "planet x" in low or "discover" in low or not (_numbers_ok(en, facts_blob) and _numbers_ok(az, facts_blob)):
        return 503, _fallback("answer failed the facts guard")
    return 200, {"en": en, "az": az, "model": model, "ai_generated": True, "generated_from": "facts sent in the request"}
