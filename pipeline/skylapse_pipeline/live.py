"""Live runner for new coordinates (P0-7).

build_live_field(ra, dec, fov_arcmin, out_dir, progress_cb) builds a contract-valid field incrementally:
  1. WISE W2+W1 epochs (byw.tools, 2 workers) + Gaia/CatWISE in parallel  -> manifest (state "wise_ready")
  2. SPHEREx TAP index, then cutouts per detector in order D6, D3, D1, D4, D2, D5 -> manifest rewritten after each ("spherex_partial")
  3. final manifest ("done"). Errors never raise: they go to status.json (state "error" only if WISE failed).
A status.json {state, progress, message, manifest_url, updated_utc} is kept next to manifest.json for the API.
"""
from __future__ import annotations

import hashlib
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import fetch_spherex, fetch_wise
from .build import FieldBuilder
from .config import BUNDLE, PIX_ARCSEC, get_logger
from .export import utcnow, write_json

log = get_logger("live")
DET_ORDER = ["D6", "D3", "D1", "D4", "D2", "D5"]


def live_id(ra: float, dec: float, fov: float) -> str:
    h = hashlib.sha1(f"{ra:.5f},{dec:.5f},{fov:.2f}".encode()).hexdigest()[:6]
    return f"live_{ra:08.4f}_{'p' if dec >= 0 else 'm'}{abs(dec):07.4f}_{h}".replace(".", "d")


def allw_rows(fw1, w2_rows):
    try:
        return fw1.result(timeout=0.1)
    except Exception:  # noqa: BLE001
        return w2_rows


def finish_catalogs(b, fid, wise_rows) -> str:
    """Make sure the catalogues are loaded (one more try each if a service failed), rescale the WISE frames if Gaia arrived
    late, add the fast-moving known stars. Returns a short human-readable note for the status message."""
    gaia_ok = lambda: b.catalog_status.get("gaia", {}).get("state") == "ok"  # noqa: E731
    had_gaia = gaia_ok() and len(b.ref_xy[0]) > 0
    for name in ("gaia", "catwise"):
        if b.catalog_status.get(name, {}).get("state") != "ok":
            try:
                b.load_catalogs(True, (name,), 20)
            except Exception as e:  # noqa: BLE001
                log.warning("live %s retry %s: %r", fid, name, e)
    if gaia_ok() and not had_gaia and len(b.ref_xy[0]) > 0 and wise_rows:  # Gaia came late: redo the scaling
        for band in (2, 1):
            rows = [r for r in wise_rows if r["band"] == band]
            if rows:
                b.add_wise(rows)
    try:
        b._write_catalogs(("gaia", "catwise"))  # final, complete rewrite of both overlay files
    except Exception as e:  # noqa: BLE001
        log.warning("live %s catalogue write: %r", fid, e)
    try:
        b.write_fast_movers()
    except Exception as e:  # noqa: BLE001
        log.warning("live %s fast movers: %r", fid, e)
    bad = [k for k, v in b.catalog_status.items() if v.get("state") != "ok"]
    if bad:
        return "star catalogue temporarily unavailable (" + ", ".join("Gaia DR3" if k == "gaia" else "CatWISE2020" for k in bad) + ")"
    return (b.fast_movers or {}).get("note", "")


def pick_per_bin(rows: list[dict], intervals, k: int) -> list[dict]:
    """At most k images per time bin, spread evenly in time (IRSA cutouts take 10-60 s each; a full field can be 400 images)."""
    from .epochs import assign

    out = []
    for ti in range(len(intervals)):
        rs = sorted((r for r in rows if assign(0.5 * (r["t_start"] + r["t_end"]), intervals) == ti), key=lambda r: r["t_start"])
        if len(rs) > k:
            step = len(rs) / k
            rs = [rs[int(i * step)] for i in range(k)]
        out += rs
    return out


def build_live_field(ra: float, dec: float, fov_arcmin: float = 6.0, out_dir: Path | str = BUNDLE / "_live", progress_cb=None,
                     field_id: str | None = None, wise_limit_s: float = 70.0, total_limit_s: float = 900.0,
                     detectors=DET_ORDER, title: str | None = None, max_per_bin: int = 4) -> dict:
    t0 = time.time()
    out_dir = Path(out_dir)
    fid = field_id or live_id(ra, dec, fov_arcmin)
    fdir = out_dir / fid
    fdir.mkdir(parents=True, exist_ok=True)
    n_px = max(32, int(round(fov_arcmin * 60 / PIX_ARCSEC / 2)) * 2)
    status = {"field_id": fid, "state": "queued", "progress": 0.0, "message": "", "manifest_url": None}

    def report(state, progress, msg=""):
        status.update(state=state, progress=round(progress, 3), message=msg, updated_utc=utcnow(),
                      elapsed_s=round(time.time() - t0, 1))
        if (fdir / "manifest.json").is_file():
            status["manifest_url"] = f"{fid}/manifest.json"
        try:
            write_json(fdir / "status.json", status)
        except Exception:  # noqa: BLE001
            pass
        log.info("live %s: %s %.0f%% %s", fid, state, progress * 100, msg)
        if progress_cb:
            try:
                progress_cb(state, progress, msg)
            except Exception:  # noqa: BLE001
                pass

    report("queued", 0.0, f"grid {n_px}x{n_px} px ({fov_arcmin}')")
    b = FieldBuilder(fid, ra, dec, title or f"Live field {ra:.4f}, {dec:+.4f}", kind="live", tags=["live"], out_root=out_dir,
                     n_px=n_px)

    # ---- 1. WISE W2 (default 4.6 um sequence) + catalogs in parallel; W1 follows in the background
    ex = ThreadPoolExecutor(max_workers=3)
    size_px = n_px + 24
    try:
        fcat = ex.submit(b.load_catalogs, True, ("gaia",), 30)  # Gaia: needed for scaling
        fcw = ex.submit(b.load_catalogs, True, ("catwise",), 30)  # CatWISE: overlay only, never waited for here
        last = fetch_wise.last_epoch(ra, dec, 2)
        epochs = fetch_wise.select_epochs(last if last is not None else 22)
        log.info("live %s: last unWISE epoch %s -> fetching %d epochs", fid, last, len(epochs))
        rows = fetch_wise.fetch(fid, ra, dec, size_px=size_px, bands=(2,), deadline=t0 + wise_limit_s,
                                order=fetch_wise.bisection_order(epochs))
        try:
            fcat.result(timeout=max(3.0, min(t0 + wise_limit_s, time.time() + 15) - time.time()))
        except Exception as e:  # noqa: BLE001  (timeout: frames stay unscaled; catalogs land later)
            log.warning("live %s catalogs not ready: %r", fid, e)
        if not rows:
            report("error", 0.0, "no WISE epochs could be fetched (byw.tools unreachable?)")
            ex.shutdown(wait=False)
            return status
        b.add_wise(rows)
        b.write(status="wise_ready")
        report("wise_ready", 0.3, f"{len(rows)} WISE W2 frames")
    except Exception as e:  # noqa: BLE001
        log.error("live %s WISE stage failed: %s\n%s", fid, e, traceback.format_exc())
        report("error", 0.0, f"WISE stage failed: {e}")
        ex.shutdown(wait=False)
        return status
    n_w2 = len(rows)
    fw1 = ex.submit(fetch_wise.fetch, fid, ra, dec, size_px, (2, 1), t0 + total_limit_s, True, epochs)  # rest of W2 + W1

    def catwise_done():
        try:
            fcw.result(timeout=0.1)
        except Exception:  # noqa: BLE001
            pass

    if not detectors:  # WISE-only mode (API, D-015): no SPHEREx TAP query at all; finish W1 / missing W2 within the time limit
        try:
            allw = fw1.result(timeout=max(1.0, t0 + total_limit_s - time.time()))
            have = set(b.frames)
            for band in (2, 1):
                if any(r["band"] == band and f"wise_w{band}_e{r['epoch']:02d}" not in have for r in allw):
                    b.add_wise([r for r in allw if r["band"] == band])
        except Exception as e:  # noqa: BLE001  (timeout: keep what we have)
            log.warning("live %s W1: %r", fid, e)
        catwise_done()
        ex.shutdown(wait=False)
        msg = finish_catalogs(b, fid, allw_rows(fw1, rows))
        try:
            b.write(status="done")
        except Exception as e:  # noqa: BLE001
            log.error("live %s final write: %s", fid, e)
        status["catalogs"] = {k: v.get("state") for k, v in b.catalog_status.items()}
        status["fast_movers"] = (b.fast_movers or {}).get("n", 0)
        report("done", 1.0, f"{len(b.frames)} WISE frames in {time.time() - t0:.0f}s (SPHEREx live is off) · {msg}")
        return status

    # ---- 2. SPHEREx
    try:
        size_deg = round(n_px * PIX_ARCSEC / 3600 * 1.05 + 0.01, 3)
        idx = fetch_spherex.query_index(fid, ra, dec, size_deg, timeout=min(180, max(30, total_limit_s - (time.time() - t0))))
        try:  # W1 frames (fetched while TAP was running)
            allw = fw1.result(timeout=max(1.0, min(180.0, t0 + total_limit_s - time.time())))
            w2 = [r for r in allw if r["band"] == 2]
            w1 = [r for r in allw if r["band"] == 1]
            if len(w2) > n_w2:
                b.add_wise(w2)
            if w1:
                b.add_wise(w1)
                b.write(status="spherex_partial")
        except Exception as e:  # noqa: BLE001
            log.warning("live %s W1: %r", fid, e)
        b.set_spherex_index(idx)
        report("spherex_partial", 0.35, f"{len(idx)} SPHEREx images in archive")
        dets = [d for d in detectors if any(r["band"] == d for r in idx)]
        for k, det in enumerate(dets):
            if time.time() - t0 > total_limit_s:
                report("spherex_partial", 0.35 + 0.65 * k / max(len(dets), 1), "time limit reached; stopping SPHEREx")
                break
            rows = pick_per_bin([r for r in idx if r["band"] == det], b.intervals, max_per_bin)
            n_ok = fetch_spherex.download(rows, deadline=t0 + total_limit_s)
            b.add_spherex([det])
            b.write(status="spherex_partial")
            report("spherex_partial", 0.35 + 0.65 * (k + 1) / len(dets), f"{det}: {n_ok}/{len(rows)} images")
    except Exception as e:  # noqa: BLE001
        log.error("live %s SPHEREx stage failed: %s\n%s", fid, e, traceback.format_exc())
        status["spherex_error"] = str(e)

    try:  # late WISE epochs (slow byw.tools): add whatever the background pass has finished by now
        allw = fw1.result(timeout=max(1.0, min(60.0, t0 + total_limit_s + 60 - time.time())))
        have = set(b.frames)
        new = [r for r in allw if f"wise_w{r['band']}_e{r['epoch']:02d}" not in have]
        for band in (2, 1):
            if any(r["band"] == band for r in new):
                b.add_wise([r for r in allw if r["band"] == band])
    except Exception as e:  # noqa: BLE001
        log.warning("live %s late WISE: %r", fid, e)
    ex.shutdown(wait=False)
    note = finish_catalogs(b, fid, allw_rows(fw1, []))
    status["catalogs"] = {k: v.get("state") for k, v in b.catalog_status.items()}
    try:
        b.write(status="done")
        b.write_science_csv()
    except Exception as e:  # noqa: BLE001
        log.error("live %s final write: %s", fid, e)
    report("done", 1.0, f"{len(b.frames)} frames in {time.time() - t0:.0f}s · {note}")
    return status


def needs_rebuild(field_dir) -> bool:
    """True if a cached live field must NOT be served from cache: its star catalogue failed or was built before catalogue
    status existed (old runner: rows [] with no "status" key, i.e. unknown). Used by the API in submit() and at startup."""
    import json
    from pathlib import Path

    p = Path(field_dir) / "catalogs" / "gaia.json"
    if not (Path(field_dir) / "manifest.json").is_file():
        return False  # not built (yet); the normal queue logic applies
    try:
        g = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return True
    st = (g.get("status") or {}).get("state")
    if st is None:
        return not g.get("rows")  # old field: empty rows = catalogue failed
    return st != "ok"
