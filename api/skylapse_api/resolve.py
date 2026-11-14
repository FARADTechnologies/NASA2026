"""Name / coordinate resolution for /api/resolve (stdlib only).

Order: coordinate parsing (degrees or sexagesimal) -> local table of the 5 NASA targets -> CDS Sesame (+ mirrors) -> SIMBAD TAP mirrors.
Every network answer is cached in memory and on disk (cache/resolve.json). Services were flaky on 13-14 Nov (SCIENCE_NOTES §7).
"""
from __future__ import annotations

import json
import os
import re
import threading
import urllib.parse
import urllib.request
from pathlib import Path

TIMEOUT = float(os.environ.get("RESOLVE_TIMEOUT_S", "8"))
UA = "SkyLapse/0.1 (NASA Space Apps 2026 project)"

# J2000 positions; `field` = precomputed bundle field id. Barnard's J2000 position is ~4.5' from where the star is now —
# the frontend should open the bundle field (`field`) for these targets.
LOCAL = [
    {"field": "barnard", "name": "Barnard's Star", "ra": 269.4520769, "dec": 4.6933649,
     "aliases": ["barnard", "barnards star", "barnard star", "gj 699", "gl 699", "v2500 oph"]},
    {"field": "eps_indi_b", "name": "Epsilon Indi B", "ra": 331.0438, "dec": -56.7827,
     "aliases": ["eps indi b", "epsilon indi b", "eps ind b", "epsilon indi ba", "eps indi ba", "ε indi b", "epsilon indi bab"]},
    {"field": "wise0855", "name": "WISE 0855−0714", "ra": 133.795130, "dec": -7.245147,
     "aliases": ["wise 0855", "wise 0855-0714", "wise0855", "wise j085510.83-071442.5", "wise j0855-0714", "wise 0855−0714"]},
    {"field": "rw_aur", "name": "RW Aurigae", "ra": 76.9564, "dec": 30.4014,
     "aliases": ["rw aur", "rw aurigae", "rwaur"]},
    {"field": "r_dra", "name": "R Draconis", "ra": 248.1675, "dec": 66.7548,
     "aliases": ["r dra", "r draconis", "rdra"]},
]

SESAME = [
    "https://cds.unistra.fr/cgi-bin/nph-sesame/-oxp/SNV?{q}",
    "https://vizier.cfa.harvard.edu/viz-bin/nph-sesame/-oxp/SNV?{q}",
    "https://vizier.idia.ac.za/viz-bin/nph-sesame/-oxp/SNV?{q}",
]
SIMBAD_TAP = [
    "https://simbad.cfa.harvard.edu/simbad/sim-tap/sync",
    "https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
]

_cache: dict[str, dict] = {}
_lock = threading.Lock()
_cache_file: Path | None = None


def init_cache(path: Path) -> None:
    global _cache_file
    _cache_file = path
    try:
        _cache.update(json.loads(path.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        pass


def _save() -> None:
    if _cache_file is None:
        return
    try:
        _cache_file.parent.mkdir(parents=True, exist_ok=True)
        _cache_file.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass


def norm(s: str) -> str:
    s = s.strip().lower().replace("’", "'").replace("−", "-").replace("–", "-")
    s = s.replace("'s", "s").replace("'", "")
    return re.sub(r"\s+", " ", s)


# ----------------------------------------------------------------------------- coordinates
_NUM = r"[+-]?\d+(?:\.\d*)?"
SEXA = re.compile(
    rf"^\s*(?P<h>\d{{1,2}})\s*[h: ]\s*(?P<m>\d{{1,2}})\s*[m: ]\s*(?P<s>\d{{1,2}}(?:\.\d*)?)\s*s?\s*[, ]?\s*"
    rf"(?P<sign>[+-−]?)\s*(?P<d>\d{{1,2}})\s*[d°: ]\s*(?P<am>\d{{1,2}})\s*['m: ]\s*(?P<as>\d{{1,2}}(?:\.\d*)?)\s*(?:\"|''|s)?\s*$",
    re.I)
DEG = re.compile(rf"^\s*({_NUM})\s*(?:d|°)?\s*[, ]\s*({_NUM})\s*(?:d|°)?\s*$", re.I)


def parse_coords(q: str):
    q2 = q.strip().replace("−", "-")
    m = DEG.match(q2)
    if m:
        ra, dec = float(m.group(1)), float(m.group(2))
        if 0 <= ra < 360 and -90 <= dec <= 90:
            return ra, dec
        return None
    m = SEXA.match(q2)
    if m:
        h, mi, s = int(m["h"]), int(m["m"]), float(m["s"])
        d, am, as_ = int(m["d"]), int(m["am"]), float(m["as"])
        if h >= 24 or mi >= 60 or s >= 60 or d > 90 or am >= 60 or as_ >= 60:
            return None
        ra = 15.0 * (h + mi / 60 + s / 3600)
        dec = d + am / 60 + as_ / 3600
        if m["sign"] in ("-", "−"):
            dec = -dec
        return ra, dec
    return None


# ----------------------------------------------------------------------------- network
def _get(url: str, data: bytes | None = None) -> str:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 (fixed https hosts)
        return r.read().decode("utf-8", "replace")


def _sesame(name: str):
    q = urllib.parse.quote(name)
    for tpl in SESAME:
        try:
            xml = _get(tpl.format(q=q))
        except Exception:  # noqa: BLE001
            continue
        ra = re.search(r"<jradeg>\s*([-+0-9.eE]+)\s*</jradeg>", xml)
        de = re.search(r"<jdedeg>\s*([-+0-9.eE]+)\s*</jdedeg>", xml)
        if ra and de:
            on = re.search(r"<oname>\s*(.*?)\s*</oname>", xml)
            host = urllib.parse.urlparse(tpl).netloc
            return {"name": on.group(1) if on else name, "ra": float(ra.group(1)), "dec": float(de.group(1)),
                    "source": f"Sesame ({host})"}
    return None


def _simbad_tap(name: str):
    ident = name.replace("'", "''")
    adql = f"SELECT TOP 1 b.main_id, b.ra, b.dec FROM basic AS b JOIN ident AS i ON i.oidref = b.oid WHERE i.id = '{ident}'"
    body = urllib.parse.urlencode({"request": "doQuery", "lang": "adql", "format": "json", "query": adql}).encode()
    for url in SIMBAD_TAP:
        try:
            js = json.loads(_get(url, body))
            rows = js.get("data") or []
            if rows and rows[0][1] is not None:
                return {"name": rows[0][0], "ra": float(rows[0][1]), "dec": float(rows[0][2]),
                        "source": f"SIMBAD TAP ({urllib.parse.urlparse(url).netloc})"}
        except Exception:  # noqa: BLE001
            continue
    return None


# ----------------------------------------------------------------------------- main entry
def resolve(q: str) -> dict | None:
    """Return {"name","ra","dec","source"} (+ "field" for the 5 NASA targets) or None."""
    if not q or not q.strip():
        return None
    q = q.strip()[:200]
    c = parse_coords(q)
    if c:
        return {"name": f"RA {c[0]:.5f}, Dec {c[1]:+.5f}", "ra": round(c[0], 7), "dec": round(c[1], 7), "source": "coordinates"}
    n = norm(q)
    for t in LOCAL:
        if n == norm(t["name"]) or n in t["aliases"] or n == t["field"]:
            return {"name": t["name"], "ra": t["ra"], "dec": t["dec"], "source": "SkyLapse NASA target list", "field": t["field"]}
    with _lock:
        if n in _cache:
            return _cache[n]
    hit = _sesame(q) or _simbad_tap(q)
    if hit:
        with _lock:
            _cache[n] = hit
            _save()
    return hit
