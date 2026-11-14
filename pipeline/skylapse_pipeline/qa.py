"""QA: animated GIF of a manifest sequence (reads the bundle exactly like the viewer does) -> data/qa/<field>_<seq>.gif."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .config import BUNDLE, QA_DIR
from .export import stretch_u8


def make_gif(field: str, seq_id: str = "thermal46", root: Path = BUNDLE, scale: int = 3, ms: int = 350) -> Path:
    from PIL import Image, ImageDraw

    fdir = Path(root) / field
    man = json.loads((fdir / "manifest.json").read_text(encoding="utf-8"))
    frames = {f["id"]: f for f in man["frames"]}
    seq = next(s for s in man["sequences"] if s["id"] == seq_id)
    w, h = man["grid"]["width"], man["grid"]["height"]
    # one common stretch per instrument (median of per-frame percentiles) so brightness is comparable across frames
    imgs = []
    for fid in seq["frames"]:
        fr = frames[fid]
        a = np.fromfile(fdir / fr["file"], dtype="<f4").reshape(h, w)
        fin = a[np.isfinite(a) & (a != 0)]
        med = float(np.median(fin)) if fin.size else 0.0
        sig = float(1.4826 * np.median(np.abs(fin - med))) if fin.size else 1.0
        u8 = stretch_u8(a, {"p01": med - 2 * sig, "p999": med + 40 * sig})[::-1]
        im = Image.fromarray(u8, "L").resize((w * scale, h * scale), Image.NEAREST).convert("RGB")
        dr = ImageDraw.Draw(im)
        dr.rectangle([0, 0, w * scale, 16], fill=(0, 0, 0))
        dr.text((4, 2), f"{field}  {fr['instrument']} {fr['band']}  {fr['date']}  n={fr['n_inputs']}", fill=(255, 255, 0))
        c = (w * scale // 2, h * scale // 2)
        dr.line([c[0] - 8, c[1], c[0] - 3, c[1]], fill=(255, 0, 0))
        dr.line([c[0] + 3, c[1], c[0] + 8, c[1]], fill=(255, 0, 0))
        imgs.append(im)
    QA_DIR.mkdir(parents=True, exist_ok=True)
    out = QA_DIR / f"{field}_{seq_id}.gif"
    imgs[0].save(out, save_all=True, append_images=imgs[1:], duration=ms, loop=0)
    return out
