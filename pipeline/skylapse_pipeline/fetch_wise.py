"""unWISE time-resolved epochs (byw.tools). Reads the prefetch cache first; downloads only what is missing.

byw.tools: <1 s per request, HTTP 500 = past the last epoch, max 2 concurrent requests (be polite).
"""
from __future__ import annotations

import csv
import threading
import time
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


def fetch(field: str, ra: float, dec: float, size_px: int = 256, bands=(2, 1), deadline: float | None = None,
          refresh: bool = False) -> list[dict]:
    """Download all epochs of each band (one band after the other, 2 workers sharing an epoch counter; HTTP 500 = end) into
    CACHE/wise/<field>/, merge into index.csv, return read_index(). Bands already in the index are not fetched again."""
    have = {r["band"] for r in read_index(field)}
    todo = list(bands) if refresh else [b for b in bands if b not in have]
    if not todo:
        return read_index(field)
    d = CACHE / "wise" / field
    d.mkdir(parents=True, exist_ok=True)
    results = []
    for band in todo:
        state = {"next": 0, "end": MAX_EPOCHS, "fails": 0, "ok": 0}
        lock = threading.Lock()

        def worker():
            while True:
                with lock:
                    ep = state["next"]
                    if ep >= state["end"] or (state["fails"] >= 2 and state["ok"] == 0) or state["fails"] >= 6:
                        return
                    state["next"] += 1
                dest = d / f"w{band}_e{ep:02d}.fits"
                st = _get(ra, dec, size_px, band, ep, dest, deadline)
                with lock:
                    if st == "end":
                        state["end"] = min(state["end"], ep)
                    elif st == "ok":
                        state["ok"] += 1
                        results.append((ep, band, dest))
                    else:
                        state["fails"] += 1

        ths = [threading.Thread(target=worker) for _ in range(2)]
        for t in ths:
            t.start()
        for t in ths:
            t.join()
        # drop anything at/after the detected end (a worker may have raced past it)
        results[:] = [r for r in results if not (r[1] == band and r[0] >= state["end"])]
    from astropy.io import fits

    rows = [(r["epoch"], r["band"], Path(r["path"])) for r in read_index(field)] + [(e, b, Path(p)) for e, b, p in results]
    with (d / "index.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["epoch", "band", "MJDMIN", "MJDMAX", "file"])
        for ep, band, p in sorted(set(rows), key=lambda x: (x[1], x[0])):
            h = fits.getheader(p)
            w.writerow([ep, band, h["MJDMIN"], h["MJDMAX"], Path(p).name])
    log.info("WISE %s: %d files fetched for bands %s", field, len(results), todo)
    return read_index(field)
