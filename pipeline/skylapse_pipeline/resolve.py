"""Name resolution (SIMBAD CDS -> SIMBAD Harvard mirror -> CDS Sesame) and proper-motion propagation."""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import requests

from .config import get_logger, load_targets, TARGETS

log = get_logger("resolve")
UA = "skylapse-pipeline/0.2 (NASA Space Apps 2026 hackathon)"
SIMBAD_SERVERS = ["simbad.cds.unistra.fr", "simbad.harvard.edu"]
SESAME_URLS = ["https://cds.unistra.fr/cgi-bin/nph-sesame/-oxp/SNV", "https://vizier.idia.ac.za/viz-bin/nph-sesame/-oxp/SNV"]


def julian_year(mjd: float) -> float:
    return 2000.0 + (mjd - 51544.5) / 365.25


def mjd_of_year(year: float) -> float:
    return 51544.5 + (year - 2000.0) * 365.25


def propagate(ra: float, dec: float, pmra: float, pmdec: float, from_year: float, to_year: float):
    """Linear tangent-plane propagation (pmra already x cos dec, mas/yr). Good to << 1" over 30 yr for our targets."""
    dt = to_year - from_year
    ddec = pmdec * dt / 3.6e6
    dra = pmra * dt / 3.6e6 / max(math.cos(math.radians(dec + ddec / 2)), 1e-6)
    return (ra + dra) % 360.0, dec + ddec


def _simbad(name: str):
    from astroquery.simbad import Simbad

    for server in SIMBAD_SERVERS:
        try:
            s = Simbad()
            s.server = server
            s.TIMEOUT = 20
            s.add_votable_fields("pmra", "pmdec", "plx_value")
            tab = s.query_object(name)
            if tab is None or len(tab) == 0:
                continue
            row, cols = tab[0], tab.colnames

            def pick(*cs):
                for c in cs:
                    if c in cols:
                        v = row[c]
                        try:
                            v = float(v)
                            return None if math.isnan(v) else v
                        except (TypeError, ValueError):
                            return None
                return None

            ra, dec = pick("ra", "RA_d"), pick("dec", "DEC_d")
            if ra is None:
                continue
            mid = str(row["main_id"]) if "main_id" in cols else name
            return dict(name=mid, ra=ra, dec=dec, pmra=pick("pmra", "PMRA") or 0.0, pmdec=pick("pmdec", "PMDEC") or 0.0,
                        parallax=pick("plx_value"), epoch=2000.0, source=f"SIMBAD ({server})")
        except Exception as e:  # noqa: BLE001
            log.warning("SIMBAD %s failed for %r: %s", server, name, str(e).splitlines()[0] if str(e) else e)
    return None


def _sesame(name: str):
    for url in SESAME_URLS:
        try:
            r = requests.get(f"{url}?{requests.utils.quote(name)}", timeout=20, headers={"User-Agent": UA})
            res = ET.fromstring(r.text).find(".//Resolver")
            if res is None or res.find("jradeg") is None:
                continue
            pm = res.find("pm")
            pmra = float(pm.find("pmRA").text) if pm is not None and pm.find("pmRA") is not None else 0.0
            pmdec = float(pm.find("pmDE").text) if pm is not None and pm.find("pmDE") is not None else 0.0
            return dict(name=(res.findtext("oname") or name), ra=float(res.findtext("jradeg")), dec=float(res.findtext("jdedeg")),
                        pmra=pmra, pmdec=pmdec, parallax=None, epoch=2000.0, source=f"CDS Sesame ({url.split('/')[2]})")
        except Exception as e:  # noqa: BLE001
            log.warning("Sesame %s failed for %r: %s", url, name, e)
    return None


def resolve(query: str) -> dict:
    """Resolve a name or 'ra dec' (degrees) string. Returns dict(name, ra, dec, pmra, pmdec, epoch, source, ra_2018, dec_2018).
    Known target ids/names come from the prefetch targets.json (no network)."""
    q = query.strip()
    parts = q.replace(",", " ").split()
    if len(parts) == 2:
        try:
            ra, dec = float(parts[0]), float(parts[1])
            return dict(name=f"{ra:.5f} {dec:+.5f}", ra=ra, dec=dec, pmra=0.0, pmdec=0.0, epoch=2000.0, source="coordinates",
                        ra_2018=ra, dec_2018=dec)
        except ValueError:
            pass
    try:
        tg = load_targets()
    except Exception:  # noqa: BLE001
        tg = {}
    ql = q.lower().replace(" ", "")
    for tid, t in tg.items():
        names = {tid, t.get("resolver_name", ""), t.get("simbad_main_id", ""), TARGETS.get(tid, {}).get("title", "")}
        if ql in {n.lower().replace(" ", "") for n in names if n}:
            return dict(name=TARGETS.get(tid, {}).get("title", tid), ra=t["ra_j2000"], dec=t["dec_j2000"], pmra=t["pmra_masyr"] or 0.0,
                        pmdec=t["pmdec_masyr"] or 0.0, epoch=2000.0, source=t["resolver"] + " (prefetch cache)",
                        ra_2018=t["ra_2018"], dec_2018=t["dec_2018"], field_id=tid)
    info = _simbad(q) or _sesame(q)
    if info is None:
        raise LookupError(f"could not resolve {q!r}")
    info["ra_2018"], info["dec_2018"] = propagate(info["ra"], info["dec"], info["pmra"], info["pmdec"], 2000.0, 2018.0)
    return info
