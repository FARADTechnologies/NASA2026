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
MAX_EPOCHS = 2000  # near the ecliptic poles unWISE has hundreds of epochs (NEP: 400-800)
MAX_LIVE_EPOCHS = 32


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
            tmo = 30.0 if not deadline else max(2.0, min(30.0, deadline - time.time()))
            r = requests.get(URL, params=dict(ra=f"{ra:.6f}", dec=f"{dec:.6f}", size=size, band=band, epoch=epoch),
                             timeout=tmo, headers={"User-Agent": UA})
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


def _status(ra, dec, band, epoch, timeout=20.0) -> int:
    try:
        r = requests.get(URL, params=dict(ra=f"{ra:.6f}", dec=f"{dec:.6f}", size=8, band=band, epoch=epoch), timeout=timeout,
                         headers={"User-Agent": UA})
        return r.status_code
    except requests.RequestException:
        return 0


def last_epoch(ra: float, dec: float, band: int = 2, guess: int = 22) -> int | None:
    """Index of the last unWISE epoch at this position (tiny 8 px probes; gallop then bisect). None if byw.tools fails."""
    ok = lambda e: _status(ra, dec, band, e) == 200  # noqa: E731
    if _status(ra, dec, band, 0) != 200:
        return None
    lo, hi = 0, None
    e = guess
    while e < MAX_EPOCHS:
        if ok(e):
            lo, e = e, e * 2 + 1
        else:
            hi = e
            break
    if hi is None:
        return lo
    while hi - lo > 1:
        m = (lo + hi) // 2
        lo, hi = (m, hi) if ok(m) else (lo, m)
    return lo


def select_epochs(last: int, nmax: int = MAX_LIVE_EPOCHS) -> list[int]:
    """All epochs 0..last, or nmax evenly spaced ones (always including the first and the last)."""
    if last + 1 <= nmax:
        return list(range(last + 1))
    return sorted({int(round(i * last / (nmax - 1))) for i in range(nmax)})


def bisection_order(n=23) -> list[int]:
    """0, n-1, middle, quarters, ... — every prefix spans the full time range. n may be an int or an explicit epoch list."""
    if not isinstance(n, int):
        lst = list(n)
        return [lst[i] for i in bisection_order(len(lst))] if lst else []
    out, seen, spans = [0, n - 1], {0, n - 1}, [(0, n - 1)]
    while spans:
        nxt = []
        for a, b in spans:
            if b - a > 1:
                m = (a + b) // 2
                if m not in seen:
                    out.append(m)
                    seen.add(m)
                nxt += [(a, m), (m, b)]
        spans = nxt
    return out


def fetch(field: str, ra: float, dec: float, size_px: int = 256, bands=(2, 1), deadline: float | None = None,
          refresh: bool = False, order: list[int] | None = None) -> list[dict]:
    """Download all epochs of each band (one band after the other, 2 workers sharing an epoch counter; HTTP 500 = end) into
    CACHE/wise/<field>/, merge into index.csv, return read_index(). Bands already in the index are not fetched again.
    order: epochs to try, in this order (e.g. bisection_order() so a deadline-cut fetch still spans 2010-2024)."""
    have = {r["band"] for r in read_index(field)}
    todo = list(bands) if refresh else [b for b in bands if b not in have]
    if not todo:
        return read_index(field)
    d = CACHE / "wise" / field
    d.mkdir(parents=True, exist_ok=True)
    results = []
    for band in todo:
        seq = list(order) if order else list(range(80))
        state = {"next": 0, "end": MAX_EPOCHS, "fails": 0, "ok": 0}
        lock = threading.Lock()

        def worker():
            while True:
                with lock:
                    while state["next"] < len(seq) and seq[state["next"]] >= state["end"]:
                        state["next"] += 1
                    if state["next"] >= len(seq) or (state["fails"] >= 2 and state["ok"] == 0) or state["fails"] >= 6:
                        return
                    ep = seq[state["next"]]
                    state["next"] += 1
                dest = d / f"w{band}_e{ep:02d}.fits"
                st = _get(ra, dec, size_px, band, ep, dest, deadline)
                if st == "end" and not order:  # sequential mode: is it really the end, or one missing epoch?
                    nxt = d / f"w{band}_e{ep + 1:02d}.fits"
                    if _get(ra, dec, size_px, band, ep + 1, nxt, deadline) == "ok":
                        st = "missing"
                elif st == "end":  # explicit epoch list (live): epochs come from last_epoch(), so 500 = missing epoch
                    st = "missing"
                with lock:
                    if st == "end":
                        state["end"] = min(state["end"], ep)
                    elif st == "ok":
                        state["ok"] += 1
                        results.append((ep, band, dest))
                    elif st == "missing":
                        log.info("WISE %s band %s epoch %s: no data (HTTP 500), skipped", field, band, ep)
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
