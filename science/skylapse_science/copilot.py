"""S5 — AI copilot texts (English + Azerbaijani) generated ONLY from computed facts.

1. build_facts(field): a small JSON of facts taken from our own computed blocks (motion, spectrum, light curve, flags) plus a few
   curated, verified descriptors (SCIENCE_NOTES §4). Every number the copilot may use is in this JSON.
2. The facts go to Claude (claude-sonnet-5-5) with a strict system prompt (<= 110 words, only these facts, no new numbers,
   'candidate' never 'discovery', never 'Planet X').
3. Automatic guard: every number in the generated text must appear in the facts JSON (or be in a tiny whitelist); otherwise
   the text is rejected and regenerated once, then left null. A human still reviews every text by eye.
4. facts_hash = sha256(model + system prompt + facts); texts are regenerated only when it changes.

Key: ANTHROPIC_API_KEY from the environment or from the repo-root .env file (gitignored). Never printed, never committed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re

from . import config

MODEL = "claude-sonnet-5-5"
MAX_WORDS = 110

SYSTEM = """You write short explanations for SkyLapse, a public web tool that plays 16 years of infrared sky images \
(NASA WISE/NEOWISE 2010-2024 and NASA SPHEREx 2025-2026) as a movie.
Audience: curious students and the general public.
Rules (all mandatory):
- Use ONLY the facts in the FACTS JSON. Do not add any fact, name, date or number that is not in it.
- Every number you write must appear in the FACTS JSON exactly as written there (you may round it to fewer digits). Prefer fewer numbers.
- At most 110 words. Plain language, no jargon without a short explanation. No headings, no lists, no emoji.
- Say "candidate", never "discovery" or "discovered" for anything new. Never mention "Planet X".
- If the facts say a measurement is not possible (for example because the star is too bright), say so honestly.
- End with one sentence telling the viewer what to look for in the SkyLapse movie (from the facts).
Write only the explanation text."""

LANG_INSTRUCTION = {
    "en": "Write the explanation in English.",
    "az": "Write the explanation in Azerbaijani (Latin script, natural modern Azerbaijani as used in Baku). "
          "Keep object names as they are (for example 'Barnard's Star' may become 'Barnard ulduzu'); keep numbers and units.",
}

DESCRIPTORS = {   # curated, verified (SCIENCE_NOTES §4 / SIMBAD); not computed by us
    "barnard": "a red dwarf star (spectral type M4 V), one of the closest stars to the Sun",
    "eps_indi_b": "a pair of brown dwarfs (types T1 and T6, called Ba and Bb) that orbit the star epsilon Indi A",
    "wise0855": "a Y-type brown dwarf with a temperature of about 250 K (around -20 °C), the coldest known object of its kind",
    "rw_aur": "a young star (a T Tauri star, still surrounded by a disk of gas and dust) that is known for irregular dimming and brightening",
    "r_dra": "a Mira variable: a cool giant star that pulsates, growing brighter and fainter with a regular period",
}
NUMBER_WHITELIST = {"16", "2010", "2024", "2025", "2026", "1", "2", "one", "two"}


def _round(v, n=0):
    return None if v is None else (int(round(v)) if n == 0 else round(v, n))


def build_facts(field: str) -> dict:
    obj = json.loads((config.OUT_DIR / field / "objects" / "target.json").read_text(encoding="utf-8"))
    t = config.load_targets()[field]
    f = {"name": obj["name"], "what_it_is": DESCRIPTORS[field]}
    m = obj.get("motion")
    if m and m.get("measured"):
        mm, ref = m["measured"], m["reference"]
        pm_arcsec = mm["pm_total"] / 1000
        f["motion"] = {
            "measured_arcsec_per_year": round(pm_arcsec, 2),
            "reference_arcsec_per_year": round(ref["pm_total"] / 1000, 2),
            "reference_source": "ESA Gaia DR3 catalogue" if "Gaia" in ref["source"] else ref["source"],
            "agreement_percent": m["agreement_pct"],
            "wise_epochs_used": mm["n_epochs"],
            "years_of_wise_data": round(mm["baseline_yr"]),
            "distance_moved_2010_to_2024_arcsec": _round(pm_arcsec * mm["baseline_yr"]),
            "how_measured": "position measured in each WISE image, then a straight-line fit through time",
        }
        if "agreement_with_primary_pct" in ref:
            f["motion"]["moves_like_its_primary_star_eps_Indi_A_percent"] = ref["agreement_with_primary_pct"]
        plx = t.get("parallax_mas")
        if plx:
            f["distance_light_years"] = round(1000.0 / plx * 3.2616, 1)
    s = obj.get("spectrum")
    if s:
        f["spherex_spectrum"] = {"usable": bool(s.get("usable")), "notes": s.get("notes", [])[1:] if s.get("usable") else s.get("notes", [])}
    lc = obj.get("lightcurve")
    if lc:
        v = lc.get("validation", {})
        lcf = {"what_is_plotted": "a relative brightness index from the outer glow of the star image (not a magnitude), because the "
                                  "star is too bright for the detectors' cores",
               "notes": lc.get("notes", [])[2:]}
        fo = (v.get("folded") or {})
        if fo.get("W1"):
            lcf["period_found_days"] = _round(fo["W1"]["best_period_d"])
            lcf["known_period_days"] = fo["period_d"]
        f["light_curve"] = lcf
    f["saturated_in"] = (obj.get("flags") or {}).get("saturated_in", [])
    f["what_to_look_for_in_the_movie"] = _look_for(field, f)
    return f


def _look_for(field, f):
    mo = f.get("motion")
    if field == "barnard":
        return f"the bright star slides upward (north) by about {mo['distance_moved_2010_to_2024_arcsec']} arcseconds between 2010 and 2024"
    if field == "wise0855":
        return (f"a faint dot that crawls to the right (west) by about {mo['distance_moved_2010_to_2024_arcsec']} arcseconds between 2010 "
                "and 2024, visible at 4.6 micrometres but invisible at shorter wavelengths")
    if field == "eps_indi_b":
        return f"a dot moving down and to the left (south-east) by about {mo['distance_moved_2010_to_2024_arcsec']} arcseconds between 2010 and 2024"
    if field == "r_dra":
        return "the star stays in place but its glow swells and shrinks as it pulsates"
    if field == "rw_aur":
        return "the star stays in place but its infrared glow changes from year to year"
    return ""


def facts_hash(facts: dict) -> str:
    blob = json.dumps({"model": MODEL, "system": SYSTEM, "lang": LANG_INSTRUCTION, "facts": facts}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------ guard
_NUM = re.compile(r"(?<![\w.])[-−]?\d+(?:[.,]\d+)?")


def numbers_in(text: str) -> list[str]:
    return [n.replace("−", "-").replace(",", ".") for n in _NUM.findall(text)]


def check_text(text: str, facts: dict) -> list[str]:
    """Problems found: numbers not supported by the facts, forbidden words, too long."""
    problems = []
    blob = json.dumps(facts, ensure_ascii=False)
    fact_nums = [float(x) for x in numbers_in(blob)]
    for n in numbers_in(text):
        if n.lstrip("-") in NUMBER_WHITELIST:
            continue
        v = float(n)
        nd = len(n.split(".")[1]) if "." in n else 0          # written precision
        ok = any(round(fv, nd) == v or round(abs(fv), nd) == abs(v) for fv in fact_nums)
        if not ok:
            problems.append(f"number {n} not in facts")
    low = text.lower()
    for bad in ("discover", "planet x", "kəşf"):
        if bad in low and "candidate" not in low:
            problems.append(f"forbidden word '{bad}'")
    if len(text.split()) > MAX_WORDS + 10:
        problems.append(f"too long ({len(text.split())} words)")
    return problems


# ------------------------------------------------------------------ generation
def _client():
    import anthropic
    if not os.environ.get("ANTHROPIC_API_KEY"):
        env = config.REPO_DIR / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                k, _, v = line.partition("=")
                if k.strip() == "ANTHROPIC_API_KEY" and v.strip():
                    os.environ["ANTHROPIC_API_KEY"] = v.strip().strip('"').strip("'")
    return anthropic.Anthropic()


def generate(client, facts: dict, lang: str) -> tuple[str | None, list[str], str]:
    import anthropic
    user = f"FACTS JSON:\n{json.dumps(facts, ensure_ascii=False, indent=1)}\n\n{LANG_INSTRUCTION[lang]}"
    last_problems, served_by = [], MODEL
    for attempt in range(2):
        msg = user if attempt == 0 else user + "\n\nYour previous draft broke a rule: " + "; ".join(last_problems) + ". Fix it."
        try:
            r = client.beta.messages.create(
                model=MODEL, max_tokens=4000, system=SYSTEM,
                betas=["server-side-fallback-2026-07-01"], fallbacks="default",
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": msg}],
            )
        except anthropic.APIStatusError as e:
            return None, [f"API error {e.status_code}: {e.message}"], served_by
        except anthropic.APIConnectionError:
            return None, ["network error"], served_by
        if r.stop_reason == "refusal":
            return None, ["refused"], served_by
        served_by = r.model
        text = " ".join(b.text for b in r.content if b.type == "text").strip()
        last_problems = check_text(text, facts)
        if not last_problems:
            return text, [], served_by
    return None, last_problems, served_by


def run(fields=None, dry_run=False, force=False):
    from .validate import load_object, save_object
    client = None
    for f in fields or config.ALL_TARGETS:
        facts = build_facts(f)
        h = facts_hash(facts)
        out_dir = config.OUT_DIR / f
        (out_dir / "copilot_facts.json").write_text(json.dumps(facts, indent=1, ensure_ascii=False), encoding="utf-8")
        obj = load_object(f)
        old = obj.get("copilot") or {}
        if dry_run:
            print(f"== {f} (facts_hash {h}) ==\n" + json.dumps(facts, indent=1, ensure_ascii=False))
            continue
        if not force and old.get("facts_hash") == h and old.get("en") and old.get("az"):
            print(f"{f}: facts unchanged ({h}) -> kept")
            continue
        client = client or _client()
        res = {}
        for lang in ("en", "az"):
            text, problems, served = generate(client, facts, lang)
            res[lang] = text
            res[lang + "_model"] = served
            if problems:
                print(f"{f} [{lang}] PROBLEMS: {problems}")
        obj["copilot"] = {"en": res["en"], "az": res["az"], "model": MODEL, "facts_hash": h,
                          "served_by": {"en": res["en_model"], "az": res["az_model"]},
                          "generated_from": f"science/out/{f}/copilot_facts.json", "ai_generated": True,
                          "audio_en": None, "audio_az": None}
        save_object(f, obj)
        print(f"== {f} ==\nEN: {res['en']}\nAZ: {res['az']}\n")
