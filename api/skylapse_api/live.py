"""Live field jobs (O2, P0-7): POST /api/fields → background build with the pipeline's live runner.

Free hosting (~512 MB RAM, D-015): ONE job at a time, WISE frames only (detectors=[]); SPHEREx stays precomputed for the NASA targets.
Jobs are cached on disk by field id (rounded ra/dec/fov), so a repeated request is instant.
"""
from __future__ import annotations

import json
import queue
import sys
import threading
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "pipeline") not in sys.path:
    sys.path.insert(0, str(ROOT / "pipeline"))

FOV_MIN, FOV_MAX, FOV_DEFAULT = 2.0, 10.0, 6.0
_q: "queue.Queue[tuple[str, float, float, float]]" = queue.Queue(maxsize=20)
_pending: set[str] = set()
_lock = threading.Lock()
_worker: threading.Thread | None = None
FIELDS: Path = ROOT / "cache" / "fields"


def init(fields_dir: Path) -> None:
    global FIELDS
    FIELDS = fields_dir
    FIELDS.mkdir(parents=True, exist_ok=True)


def field_id(ra: float, dec: float, fov: float) -> str:
    from skylapse_pipeline.live import live_id  # same id scheme as the pipeline
    return live_id(round(ra, 4), round(dec, 4), round(fov, 1))


def _write_status(fid: str, state: str, progress: float, message: str = "") -> None:
    d = FIELDS / fid
    d.mkdir(parents=True, exist_ok=True)
    st = {"field_id": fid, "state": state, "progress": progress, "message": message,
          "manifest_url": f"{fid}/manifest.json" if (d / "manifest.json").is_file() else None,
          "updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (d / "status.json").write_text(json.dumps(st), encoding="utf-8")


def read_status(fid: str) -> dict | None:
    st = FIELDS / fid / "status.json"
    if not st.is_file():
        return None
    try:
        s = json.loads(st.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 (file being rewritten)
        time.sleep(0.05)
        s = json.loads(st.read_text(encoding="utf-8"))
    out = {"field_id": fid, "state": s.get("state", "queued"), "progress": s.get("progress", 0.0), "message": s.get("message", "")}
    if (FIELDS / fid / "manifest.json").is_file():
        out["manifest_url"] = f"/api/fields/{fid}/manifest.json"
    else:
        out["manifest_url"] = None
    if out["state"] == "done":
        out["message"] = (out["message"] + " · SPHEREx frames are precomputed only for the NASA targets").strip(" ·")
    with _lock:
        if fid in _pending and out["state"] == "queued":
            out["queue_position"] = list(_pending).index(fid) + 1
    return out


def _run():
    from skylapse_pipeline.live import build_live_field
    while True:
        fid, ra, dec, fov = _q.get()
        try:
            build_live_field(ra, dec, fov, out_dir=FIELDS, field_id=fid, detectors=[], wise_limit_s=80.0, total_limit_s=240.0)
        except Exception as e:  # noqa: BLE001
            _write_status(fid, "error", 0.0, f"live build failed: {e}")
            traceback.print_exc()
        finally:
            with _lock:
                _pending.discard(fid)
            _q.task_done()


def submit(ra: float, dec: float, fov: float | None) -> dict:
    global _worker
    fov = min(FOV_MAX, max(FOV_MIN, float(fov or FOV_DEFAULT)))
    fid = field_id(ra, dec, fov)
    st = read_status(fid)
    if st and st["state"] in ("done", "wise_ready", "spherex_partial"):
        return {"field_id": fid, "status_url": f"/api/fields/{fid}/status", "cached": True}
    with _lock:
        if fid not in _pending:
            if _q.full():
                raise RuntimeError("busy")
            _pending.add(fid)
            _write_status(fid, "queued", 0.0, "waiting for the live builder")
            _q.put((fid, ra, dec, fov))
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run, name="live-builder", daemon=True)
            _worker.start()
    return {"field_id": fid, "status_url": f"/api/fields/{fid}/status", "cached": False}
