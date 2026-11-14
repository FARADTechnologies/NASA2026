"""Gaia DR3 and CatWISE2020 cones. Prefetch CSVs first; live fields query ESA (sync TAP) and IRSA TAP."""
from __future__ import annotations

import csv
import io
import time
from pathlib import Path

import requests

from .config import CACHE, CATALOG_DIR, get_logger

log = get_logger("catalogs")
ESA_SYNC = "https://gea.esac.esa.int/tap-server/tap/sync"
IRSA_TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
GAIA_Q = """SELECT TOP 3000 source_id, ra, dec, ref_epoch, parallax, pmra, pmdec, phot_g_mean_mag, bp_rp, ruwe
FROM gaiadr3.gaia_source WHERE 1 = CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {r}))"""
CATWISE_Q = """SELECT source_name, ra, dec, meanobsmjd, ra_pm, dec_pm, pmra, pmdec, sigpmra, sigpmdec, w1mpro, w2mpro, par_pm, w1sat, w2sat
FROM catwise_2020 WHERE 1 = CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {r}))"""


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _post(url, q, timeout):
    for attempt in range(3):
        try:
            r = requests.post(url, data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q), timeout=timeout)
            if r.status_code == 200 and not r.text.lstrip().startswith("<"):
                return r.text
            log.warning("%s HTTP %s", url, r.status_code)
        except requests.RequestException as e:
            log.warning("%s: %s", url, e)
        time.sleep(3 * (attempt + 1))
    return None


def _cached(field: str, name: str) -> Path | None:
    for d in (CATALOG_DIR, CACHE / "catalogs"):
        p = d / f"{field}_{name}.csv"
        if p.is_file():
            return p
    return None


def load_gaia(field: str, ra=None, dec=None, radius_deg=0.12, timeout=60) -> list[dict]:
    p = _cached(field, "gaia_dr3")
    if p is None and ra is not None:
        txt = _post(ESA_SYNC, GAIA_Q.format(ra=ra, dec=dec, r=radius_deg), timeout)
        if txt:
            p = CACHE / "catalogs" / f"{field}_gaia_dr3.csv"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(txt, encoding="utf-8")
    return _read_csv(p) if p else []


def load_catwise(field: str, ra=None, dec=None, radius_deg=0.12, timeout=60) -> list[dict]:
    p = _cached(field, "catwise2020")
    if p is None and ra is not None:
        txt = _post(IRSA_TAP, CATWISE_Q.format(ra=ra, dec=dec, r=radius_deg), timeout)
        if txt:
            p = CACHE / "catalogs" / f"{field}_catwise2020.csv"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(txt, encoding="utf-8")
    return _read_csv(p) if p else []


def gaia_json(rows: list[dict]) -> dict:
    """Contract §4: pm in mas/yr (x cos dec), mag = G, color = BP-RP, ref_epoch 2016.0."""
    out = []
    for r in rows:
        ra, dec = _f(r["ra"]), _f(r["dec"])
        if ra is None or dec is None:
            continue
        out.append([str(r["source_id"]), round(ra, 7), round(dec, 7), _r(_f(r.get("pmra")), 3), _r(_f(r.get("pmdec")), 3),
                    _r(_f(r.get("parallax")), 3), _r(_f(r.get("phot_g_mean_mag")), 3), _r(_f(r.get("bp_rp")), 3)])
    return {"catalog": "Gaia DR3", "ref_epoch": 2016.0, "columns": ["id", "ra", "dec", "pmra", "pmdec", "parallax", "mag", "color"],
            "rows": out}


def catwise_json(rows: list[dict]) -> dict:
    """CatWISE2020: positions at MJD 57170 (ra_pm/dec_pm, epoch 2015.4), pm arcsec/yr -> mas/yr, mag = W2, color = W1-W2."""
    out = []
    for r in rows:
        ra, dec = _f(r.get("ra_pm")) or _f(r["ra"]), _f(r.get("dec_pm")) or _f(r["dec"])
        if ra is None or dec is None:
            continue
        pmra, pmdec = _f(r.get("pmra")), _f(r.get("pmdec"))
        w1, w2 = _f(r.get("w1mpro")), _f(r.get("w2mpro"))
        par = _f(r.get("par_pm"))
        out.append([r["source_name"], round(ra, 7), round(dec, 7), _r(pmra * 1000 if pmra is not None else None, 1),
                    _r(pmdec * 1000 if pmdec is not None else None, 1), _r(par * 1000 if par is not None else None, 1), _r(w2, 3),
                    _r(w1 - w2 if w1 is not None and w2 is not None else None, 3)])
    return {"catalog": "CatWISE2020", "ref_epoch": 2015.4, "columns": ["id", "ra", "dec", "pmra", "pmdec", "parallax", "mag", "color"],
            "rows": out, "notes": ["positions at MJD 57170 (ra_pm, dec_pm); proper motions converted from arcsec/yr"]}


def _r(v, nd):
    return None if v is None else round(v, nd)
