"""Bundle writers (docs/DATA_CONTRACT.md 1.0): frames .f32 / .mask.u8, previews .png, catalogs, manifest, index."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

import numpy as np

from .config import SCHEMA

MJD0 = dt.date(1858, 11, 17)


def utcnow() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def mjd_to_date(mjd: float) -> str:
    return (MJD0 + dt.timedelta(days=float(mjd))).isoformat()


def write_json(path: Path, obj, indent=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=indent, allow_nan=False), encoding="utf-8")
    os.replace(tmp, path)


def write_frame(fdir: Path, fid: str, data: np.ndarray, mask: np.ndarray | None) -> tuple[str, str | None]:
    """data: row 0 = South (FITS order). NaN -> 0 (background level) and the pixel is flagged in the mask."""
    (fdir / "frames").mkdir(parents=True, exist_ok=True)
    d = np.asarray(data, dtype="<f4").copy()
    m = np.zeros(d.shape, np.uint8) if mask is None else mask.astype(np.uint8).copy()
    bad = ~np.isfinite(d)
    m[bad] |= 1
    d[bad] = 0.0
    rel = f"frames/{fid}.f32"
    d.tofile(fdir / rel)
    mrel = None
    if m.any():
        mrel = f"frames/{fid}.mask.u8"
        m.tofile(fdir / mrel)
    else:
        p = fdir / f"frames/{fid}.mask.u8"
        if p.exists():
            p.unlink()
    return rel, mrel


def stretch_u8(data: np.ndarray, disp: dict) -> np.ndarray:
    lo, hi = disp["p01"], disp["p999"]
    span = max(hi - lo, 1e-9)
    x = np.clip((np.nan_to_num(data, nan=lo) - lo) / span, 0, 1)
    soft = 0.02
    y = np.arcsinh(x / soft) / np.arcsinh(1 / soft)
    return (np.clip(y, 0, 1) * 255).astype(np.uint8)


def write_preview(fdir: Path, fid: str, data: np.ndarray, disp: dict) -> str:
    from PIL import Image

    (fdir / "previews").mkdir(parents=True, exist_ok=True)
    img = stretch_u8(data, disp)[::-1]  # PNG row 0 = top = North
    rel = f"previews/{fid}.png"
    Image.fromarray(img, mode="L").save(fdir / rel, optimize=True)
    return rel


def write_rgb_preview(fdir: Path, cid: str, chans: list[np.ndarray], disps: list[dict]) -> str:
    from PIL import Image

    (fdir / "previews").mkdir(parents=True, exist_ok=True)
    img = np.dstack([stretch_u8(c, d) for c, d in zip(chans, disps)])[::-1]
    rel = f"previews/{cid}.png"
    Image.fromarray(img, mode="RGB").save(fdir / rel, optimize=True)
    return rel


def update_index(root: Path, entry: dict):
    p = root / "index.json"
    idx = {"schema_version": SCHEMA, "generated_utc": utcnow(), "fields": []}
    if p.is_file():
        try:
            idx = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    fields = [f for f in idx.get("fields", []) if f.get("field_id") != entry["field_id"]]
    fields.append(entry)
    order = {k: i for i, k in enumerate(["wise0855", "barnard", "eps_indi_b", "r_dra", "rw_aur"])}
    fields.sort(key=lambda f: (order.get(f["field_id"], 99), f["field_id"]))
    idx.update(schema_version=SCHEMA, generated_utc=utcnow(), fields=fields)
    write_json(p, idx, indent=1)
