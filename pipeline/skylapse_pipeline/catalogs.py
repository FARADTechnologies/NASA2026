"""Gaia DR3 and CatWISE2020 cones. Prefetch CSVs first; live fields race ESA/IRSA TAP against VizieR mirrors (first
answer wins, brightest 2000 rows). A failed query is reported as "unavailable", never as an empty catalogue, never cached."""
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
GAIA_Q = """SELECT TOP 2000 source_id, ra, dec, ref_epoch, parallax, pmra, pmdec, phot_g_mean_mag, bp_rp, ruwe
FROM gaiadr3.gaia_source WHERE 1 = CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra}, {dec}, {r}))
ORDER BY phot_g_mean_mag"""
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


def _post(url, q, timeout, tries=2):
    """ADQL sync query -> CSV text, or None. `tries` attempts with a short pause."""
    for attempt in range(tries):
        try:
            r = requests.post(url, data=dict(REQUEST="doQuery", LANG="ADQL", FORMAT="csv", QUERY=q), timeout=timeout)
            if r.status_code == 200 and not r.text.lstrip().startswith("<"):
                return r.text
            log.warning("%s HTTP %s", url, r.status_code)
        except requests.RequestException as e:
            log.warning("%s: %s", url, str(e)[:150])
        if attempt + 1 < tries:
            time.sleep(2)
    return None


# CDS VizieR mirrors (plain HTTP "asu-tsv"). On 15 Nov the CDS main site and ESA/IRSA TAP failed while CfA and IDIA worked.
VIZIER = ["https://vizier.cfa.harvard.edu/viz-bin/asu-tsv", "https://vizier.idia.ac.za/viz-bin/asu-tsv",
          "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"]
VIZ_GAIA = dict(source="I/355/gaiadr3", sort="Gmag", cols="Source,RA_ICRS,DE_ICRS,pmRA,pmDE,Plx,Gmag,BP-RP,RUWE",
                rename={"Source": "source_id", "RA_ICRS": "ra", "DE_ICRS": "dec", "pmRA": "pmra", "pmDE": "pmdec", "Plx": "parallax",
                        "Gmag": "phot_g_mean_mag", "BP-RP": "bp_rp", "RUWE": "ruwe"})
# VizieR CatWISE pm is arcsec/yr like IRSA's, so catwise_json converts both the same way
# NOTE: on the VizieR mirrors any "-out=" column list returns 0 CatWISE rows; "-out.all" works (2000 rows ~5 s, ~1.2 MB)
VIZ_CATWISE = dict(source="II/365/catwise", sort="W2mproPM", cols=None,
                   rename={"Name": "source_name", "RA_ICRS": "ra", "DE_ICRS": "dec", "RAPMdeg": "ra_pm", "DEPMdeg": "dec_pm",
                           "MJD": "meanobsmjd", "pmRA": "pmra", "pmDE": "pmdec", "W1mproPM": "w1mpro", "W2mproPM": "w2mpro",
                           "plx1": "par_pm"})
MAX_ROWS = 2000


def _vizier(spec: dict, ra, dec, radius_deg, timeout) -> list[dict] | None:
    """Cone from the first VizieR mirror that answers with a table. Returns rows (maybe empty) or None if all mirrors fail."""
    params = {"-source": spec["source"], "-c": f"{ra:.6f} {dec:+.6f}", "-c.rd": f"{radius_deg:.5f}", "-out.max": str(MAX_ROWS),
              "-sort": spec["sort"], "-oc.form": "d"}
    if spec["cols"]:
        params["-out"] = spec["cols"]
    # build the query by hand: VizieR does not match "II%2F365%2Fcatwise" (requests' encoding of "/"), and "-out.all" takes no "="
    qs = "&".join(f"{k}={requests.utils.quote(v, safe='/,')}" for k, v in params.items()) + ("" if spec["cols"] else "&-out.all")
    for url in VIZIER:
        try:
            r = requests.get(f"{url}?{qs}", timeout=timeout)
            if r.status_code != 200 or not r.text.lstrip().startswith("#"):
                log.warning("VizieR %s HTTP %s", url.split("/")[2], r.status_code)
                continue
            lines = [ln for ln in r.text.splitlines() if ln.strip() and not ln.startswith("#")]
            out = []
            if lines:
                hdr = [h.strip() for h in lines[0].split("\t")]
                for ln in lines[3:]:  # header, units, dashes
                    vals = [v.strip() for v in ln.split("\t")]
                    if len(vals) == len(hdr):
                        out.append({spec["rename"].get(h, h): v for h, v in zip(hdr, vals)})
            log.info("VizieR %s %s: %d rows", url.split("/")[2], spec["source"], len(out))
            return out
        except requests.RequestException as e:
            log.warning("VizieR %s: %s", url.split("/")[2], str(e)[:150])
    return None


def _race(jobs, timeout):
    """Run (label, fn) jobs in parallel; return (rows, label) of the first that returns a list, else (None, None)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    ex = ThreadPoolExecutor(max_workers=len(jobs))
    futs = {ex.submit(fn): label for label, fn in jobs}
    try:
        for f in as_completed(futs, timeout=timeout):
            try:
                rows = f.result()
            except Exception as e:  # noqa: BLE001
                log.warning("%s failed: %s", futs[f], e)
                continue
            if rows is not None and (rows or all(x.done() for x in futs)):
                return rows, futs[f]
        # every job finished; accept an empty-but-successful answer
        for f, label in futs.items():
            try:
                if f.result() is not None:
                    return f.result(), label
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001  (overall timeout)
        pass
    finally:
        ex.shutdown(wait=False, cancel_futures=True)
    return None, None


def _csv_rows(txt):
    return list(csv.DictReader(io.StringIO(txt))) if txt else None


def _save(field, name, rows):
    p = CACHE / "catalogs" / f"{field}_{name}.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    keys = sorted({k for r in rows for k in r}) if rows else ["ra", "dec"]
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def _cached(field: str, name: str) -> Path | None:
    for d in (CATALOG_DIR, CACHE / "catalogs"):
        p = d / f"{field}_{name}.csv"
        if p.is_file():
            return p
    return None


def _load(field, name, primary_url, primary_q, viz_spec, ra, dec, radius_deg, timeout):
    """Returns (rows, status). status = {"state": "ok"|"unavailable", "source": str|None, "rows": n}.
    A failed query is NEVER returned as an empty catalogue and never cached."""
    p = _cached(field, name)
    if p is not None:
        rows = _read_csv(p)
        return rows, {"state": "ok", "source": "cache", "rows": len(rows)}
    if ra is None:
        return [], {"state": "unavailable", "source": None, "rows": 0}
    rows, src = _race([(primary_url.split("/")[2], lambda: _csv_rows(_post(primary_url, primary_q, timeout))),
                       ("VizieR", lambda: _vizier(viz_spec, ra, dec, radius_deg, timeout))], timeout=2.5 * timeout + 5)
    if rows is None:
        log.warning("%s %s: all catalogue services failed", field, name)
        return [], {"state": "unavailable", "source": None, "rows": 0}
    _save(field, name, rows)
    return rows, {"state": "ok", "source": src, "rows": len(rows)}


def load_gaia_status(field: str, ra=None, dec=None, radius_deg=0.12, timeout=20):
    q = GAIA_Q.format(ra=ra, dec=dec, r=radius_deg)
    return _load(field, "gaia_dr3", ESA_SYNC, q, VIZ_GAIA, ra, dec, radius_deg, timeout)


def load_catwise_status(field: str, ra=None, dec=None, radius_deg=0.12, timeout=20):
    q = CATWISE_Q.format(ra=ra, dec=dec, r=radius_deg)
    return _load(field, "catwise2020", IRSA_TAP, q, VIZ_CATWISE, ra, dec, radius_deg, timeout)


def load_gaia(field: str, ra=None, dec=None, radius_deg=0.12, timeout=20) -> list[dict]:
    return load_gaia_status(field, ra, dec, radius_deg, timeout)[0]


def load_catwise(field: str, ra=None, dec=None, radius_deg=0.12, timeout=20) -> list[dict]:
    return load_catwise_status(field, ra, dec, radius_deg, timeout)[0]


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
