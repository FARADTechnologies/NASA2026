"""SPHEREx image index (IRSA TAP) + cutouts (IRSA cutout service) with slim copies (EPSF dropped).

Reads the prefetch cache (slim/spherex/<field>/index.csv + <band>/<file>) first. For new fields: TAP sync query (~35 s),
then cutouts with <= 10 parallel workers, retries with backoff, resumable (valid files are skipped).
"""
from __future__ import annotations

import csv
import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from .config import CACHE, SPHEREX_SLIM, get_logger

log = get_logger("fetch_spherex")
UA = "skylapse-pipeline/0.2 (NASA Space Apps 2026 hackathon)"
IRSA_TAP = "https://irsa.ipac.caltech.edu/TAP/sync"
IRSA = "https://irsa.ipac.caltech.edu"
MAX_WORKERS = 10
QUERY = """SELECT a.uri, p.energy_bandpassname AS band, p.time_bounds_lower AS t_start, p.time_bounds_upper AS t_end,
 p.obsid, p.energy_bounds_lower, p.energy_bounds_upper
FROM spherex.artifact a JOIN spherex.plane p ON a.planeid = p.planeid
WHERE 1 = CONTAINS(POINT('ICRS', {ra}, {dec}), p.poly)
ORDER BY p.time_bounds_lower"""


def release_of(uri: str) -> str:
    parts = uri.split("/")
    for key in ("dr1", "qr3", "qr2", "qr"):
        if key in parts:
            return key
    return "unknown"


def spherex_dir(field: str) -> Path:
    d = SPHEREX_SLIM / field
    return d if (d / "index.csv").is_file() else CACHE / "spherex" / field


def read_index(field: str, only_present: bool = True) -> list[dict]:
    """Rows: band (D1..D6), t_start, t_end, filename, release, path, cutout_url. Only files on disk if only_present."""
    d = spherex_dir(field)
    idx = d / "index.csv"
    if not idx.is_file():
        return []
    out = []
    with idx.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            band = r.get("band_short") or r["band"].replace("SPHEREx-", "")
            p = d / band / r["filename"]
            if only_present and not p.is_file():
                continue
            out.append(dict(band=band, t_start=float(r["t_start"]), t_end=float(r["t_end"]), filename=r["filename"],
                            release=r.get("release") or release_of(r["uri"]), path=p, cutout_url=r.get("cutout_url", "")))
    return out


def _tap_csv(query: str, timeout: float = 120) -> str:
    last = None
    for attempt in range(3):
        try:
            r = requests.post(IRSA_TAP, data=dict(QUERY=query, FORMAT="csv", LANG="ADQL", REQUEST="doQuery"), timeout=timeout,
                              headers={"User-Agent": UA})
            if r.status_code == 200 and not r.text.lstrip().startswith("<"):
                return r.text
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except requests.RequestException as e:
            last = repr(e)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"IRSA TAP failed: {last}")


def query_index(field: str, ra: float, dec: float, size_deg: float, timeout: float = 120) -> list[dict]:
    """TAP query -> CACHE/spherex/<field>/index.csv (same columns the prefetch used). Returns read_index(only_present=False)."""
    d = CACHE / "spherex" / field
    idx = d / "index.csv"
    if not idx.is_file():
        rows = list(csv.DictReader(io.StringIO(_tap_csv(QUERY.format(ra=ra, dec=dec), timeout))))
        d.mkdir(parents=True, exist_ok=True)
        for r in rows:
            r["band_short"] = r["band"].replace("SPHEREx-", "")
            r["release"] = release_of(r["uri"])
            r["filename"] = r["uri"].rsplit("/", 1)[-1]
            r["cutout_url"] = f"{IRSA}/{r['uri']}?center={ra},{dec}d&size={size_deg}"
        fields = list(rows[0].keys()) if rows else ["uri", "band", "t_start", "t_end", "band_short", "release", "filename", "cutout_url"]
        with idx.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        log.info("SPHEREx %s: %d images in archive", field, len(rows))
    return read_index(field, only_present=False)


def _valid_slim(path: Path) -> bool:
    try:
        from astropy.io import fits

        with fits.open(path) as h:
            names = [x.name for x in h]
            return all(n in names for n in ("IMAGE", "FLAGS", "VARIANCE", "ZODI"))
    except Exception:  # noqa: BLE001
        return False


def download_one(row: dict, deadline: float | None = None) -> bool:
    """Download a cutout and write the slim copy (no EPSF) to row['path']. Retries 4x with backoff."""
    from astropy.io import fits

    dest: Path = row["path"]
    if dest.is_file() and _valid_slim(dest):
        return True
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt, wait in enumerate([3, 10, 30, 60]):
        if deadline and time.time() > deadline:
            return False
        try:
            r = requests.get(row["cutout_url"], timeout=120, headers={"User-Agent": UA})
            if r.status_code == 200 and r.content[:6] == b"SIMPLE":
                with fits.open(io.BytesIO(r.content)) as h:
                    keep = fits.HDUList([x.copy() for x in h if x.name != "EPSF"])
                    tmp = dest.with_suffix(".part")
                    keep.writeto(tmp, overwrite=True)
                tmp.replace(dest)
                return True
            log.warning("cutout %s: HTTP %s", row["filename"], r.status_code)
        except Exception as e:  # noqa: BLE001
            log.warning("cutout %s attempt %d: %s", row["filename"], attempt, e)
        time.sleep(wait)
    return False


def download(rows: list[dict], deadline: float | None = None, on_done=None, workers: int = MAX_WORKERS) -> int:
    """Download rows in parallel (<= 10). on_done(row, ok) is called per file. Returns number of files OK."""
    ok = 0
    with ThreadPoolExecutor(max_workers=min(workers, MAX_WORKERS)) as ex:
        futs = {ex.submit(download_one, r, deadline): r for r in rows}
        for f in as_completed(futs):
            good = bool(f.result())
            ok += good
            if on_done:
                on_done(futs[f], good)
    return ok
