"""unWISE time-resolved epochs (byw.tools). Reads the prefetch cache first; downloads only what is missing.

byw.tools: <1 s per request, HTTP 500 = past the last epoch, max 2 concurrent requests (be polite).
"""
from __future__ import annotations

import csv
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .config import CACHE, WISE_DIR, get_logger

log = get_logger("fetch_wise")
URL = "http://byw.tools/cutout"
UA = "skylapse-pipeline/0.2 (NASA Space Apps 2026 hackathon)"
MAX_EPOCHS = 80


def wise_dir(field: str) -> Path:
    d = WISE_DIR / field
    return d if (d / "index.csv").is_file() else CACHE / "wise" / field


def read_index(field: str) -> list[dict]:
    """Rows: epoch, band (1|2), MJDMIN, MJDMAX, path. Empty list if nothing cached."""
    d = wise_dir(field)
    idx = d / "index.csv"
    if not idx.is_file():
        return []
    out = []
    with idx.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            p = d / r["file"]
            if p.is_file():
                out.append(dict(epoch=int(r["epoch"]), band=int(r["band"]), mjdmin=float(r["MJDMIN"]), mjdmax=float(r["MJDMAX"]),
                                path=p))
    return sorted(out, key=lambda r: (r["band"], r["epoch"]))


def _valid(path: Path) -> bool:
    try:
        from astropy.io import fits

        with fits.open(path) as h:
            return h[0].data is not None and "MJDMIN" in h[0].header
    except Exception:  # noqa: BLE001
        return False


def _get(ra, dec, size, band, epoch, dest: Path, deadline: float | None):
    """Returns 'ok', 'end' (HTTP 500 = no such epoch) or 'fail'."""
    if dest.is_file() and _valid(dest):
        return "ok"
    for attempt in range(3):
        if deadline and time.time() > deadline:
            return "fail"
        try:
            r = requests.get(URL, params=dict(ra=f"{ra:.6f}", dec=f"{dec:.6f}", size=size, band=band, epoch=epoch),
                             timeout=30, headers={"User-Agent": UA})
            if r.status_code == 500:
                return "end"
            if r.status_code == 200 and r.content[:6] == b"SIMPLE":
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".part")
                tmp.write_bytes(r.content)
                tmp.replace(dest)
                return "ok"
        except requests.RequestException as e:
            log.warning("byw.tools band %s epoch %s: %s", band, epoch, e)
        time.sleep(2 * (attempt + 1))
    return "fail"


def fetch(field: str, ra: float, dec: float, size_px: int = 256, bands=(2, 1), deadline: float | None = None) -> list[dict]:
    """Download all epochs for the bands into CACHE/wise/<field>/ (2 workers, one per band), write index.csv, return read_index()."""
    if read_index(field):
        return read_index(field)
    d = CACHE / "wise" / field
    d.mkdir(parents=True, exist_ok=True)

    def one_band(band):
        rows = []
        for ep in range(MAX_EPOCHS):
            dest = d / f"w{band}_e{ep:02d}.fits"
            st = _get(ra, dec, size_px, band, ep, dest, deadline)
            if st == "end":
                break
            if st == "ok":
                rows.append((ep, band, dest))
        return rows

    with ThreadPoolExecutor(max_workers=2) as ex:
        results = [r for rows in ex.map(one_band, bands) for r in rows]
    from astropy.io import fits

    with (d / "index.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["epoch", "band", "MJDMIN", "MJDMAX", "file"])
        for ep, band, p in sorted(results, key=lambda x: (x[1], x[0])):
            h = fits.getheader(p)
            w.writerow([ep, band, h["MJDMIN"], h["MJDMAX"], p.name])
    log.info("WISE %s: %d files fetched", field, len(results))
    return read_index(field)
