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


def build_live_field(ra: float, dec: float, fov_arcmin: float = 6.0, out_dir: Path | str = BUNDLE / "_live", progress_cb=None,
                     field_id: str | None = None, wise_limit_s: float = 80.0, total_limit_s: float = 900.0,
                     detectors=DET_ORDER, title: str | None = None) -> dict:
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
    ex = ThreadPoolExecutor(max_workers=2)
    size_px = n_px + 24
    try:
        fcat = ex.submit(b.load_catalogs, True)
        rows = fetch_wise.fetch(fid, ra, dec, size_px=size_px, bands=(2,), deadline=t0 + wise_limit_s)
        try:
            fcat.result(timeout=max(3.0, t0 + wise_limit_s - time.time()))
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
    fw1 = ex.submit(fetch_wise.fetch, fid, ra, dec, size_px, (1,), t0 + total_limit_s)

    # ---- 2. SPHEREx
    try:
        size_deg = round(n_px * PIX_ARCSEC / 3600 * 1.05 + 0.01, 3)
        idx = fetch_spherex.query_index(fid, ra, dec, size_deg, timeout=min(180, max(30, total_limit_s - (time.time() - t0))))
        try:  # W1 frames (fetched while TAP was running)
            w1 = [r for r in fw1.result(timeout=max(1.0, min(120.0, t0 + total_limit_s - time.time()))) if r["band"] == 1]
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
            rows = [r for r in idx if r["band"] == det]
            n_ok = fetch_spherex.download(rows, deadline=t0 + total_limit_s)
            b.add_spherex([det])
            b.write(status="spherex_partial")
            report("spherex_partial", 0.35 + 0.65 * (k + 1) / len(dets), f"{det}: {n_ok}/{len(rows)} images")
    except Exception as e:  # noqa: BLE001
        log.error("live %s SPHEREx stage failed: %s\n%s", fid, e, traceback.format_exc())
        status["spherex_error"] = str(e)

    ex.shutdown(wait=False)
    try:
        b.write(status="done")
        b.write_science_csv()
    except Exception as e:  # noqa: BLE001
        log.error("live %s final write: %s", fid, e)
    report("done", 1.0, f"{len(b.frames)} frames in {time.time() - t0:.0f}s")
    return status
