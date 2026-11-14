"""Offline backup movies for the pitch: pitch/video/<field>_thermal46.mp4 (+ a <= 4 MB GIF).

Reads the bundle exactly like the viewer (row 0 = South → flipped so North is up, East left), one asinh stretch per
instrument (median of the per-frame display percentiles) so brightness does not flicker, a big date label, a WISE/SPHEREx
badge and a ring on the target. Ring position: objects/target.json motion.track (interpolated) if present, else the
reference proper motion propagated from the 2018.0 position (labelled "predicted from catalogue motion").
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .config import BUNDLE, REPO
from .grid import grid_wcs, world_to_grid
from .resolve import julian_year, propagate

OUT = REPO / "pitch" / "video"
SIZE = 1080
COLORS = {"WISE": (90, 170, 255), "SPHEREx": (255, 150, 60)}


def _font(px):
    from PIL import ImageFont

    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _stretch(a, lo, hi):
    x = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)
    y = np.arcsinh(x / 0.03) / np.arcsinh(1 / 0.03)
    return (np.clip(y, 0, 1) * 255).astype(np.uint8)


def _target_xy(man, obj, frame, wcs):
    m = (obj or {}).get("motion") or {}
    tr = [p for p in (m.get("track") or []) if p.get("ra") is not None]
    mjd = frame["mjd_mid"]
    if len(tr) >= 2:
        t = np.array([p["mjd"] for p in tr])
        ra = np.interp(mjd, t, [p["ra"] for p in tr])
        dec = np.interp(mjd, t, [p["dec"] for p in tr])
        src = "measured track"
    else:
        ref = m.get("reference") or {}
        if obj is None or ref.get("pmra") is None:
            return None, None
        ra, dec = propagate(obj["ra"], obj["dec"], ref["pmra"], ref["pmdec"] or 0.0, obj.get("epoch", 2018.0), julian_year(mjd))
        src = "predicted from catalogue motion"
    x, y = world_to_grid(wcs, ra, dec)
    return (float(x[0]), float(y[0])), src


def render_frames(field: str, seq_id: str = "thermal46", root: Path = BUNDLE, size: int = SIZE):
    from PIL import Image, ImageDraw

    fdir = Path(root) / field
    man = json.loads((fdir / "manifest.json").read_text(encoding="utf-8"))
    frames = {f["id"]: f for f in man["frames"]}
    seq = next(s for s in man["sequences"] if s["id"] == seq_id)
    w, h = man["grid"]["width"], man["grid"]["height"]
    wcs = grid_wcs(man["grid"])
    op = fdir / "objects" / "target.json"
    obj = json.loads(op.read_text(encoding="utf-8")) if op.is_file() else None
    # common stretch per instrument
    lims = {}
    for inst in ("WISE", "SPHEREx"):
        ds = [frames[i]["display"] for i in seq["frames"] if frames[i]["instrument"] == inst]
        if ds:
            lims[inst] = (float(np.median([d["p50"] for d in ds])) - 0.5 * float(np.median([d["p50"] - d["p01"] for d in ds])),
                          float(np.median([d["p999"] for d in ds])))
    k = size / w
    f_big, f_mid, f_small = _font(size // 14), _font(size // 30), _font(size // 42)
    title = man["title"]
    out = []
    for fid in seq["frames"]:
        fr = frames[fid]
        a = np.fromfile(fdir / fr["file"], dtype="<f4").reshape(h, w)
        lo, hi = lims[fr["instrument"]]
        img = Image.fromarray(_stretch(a, lo, hi)[::-1], "L").resize((size, size), Image.BICUBIC).convert("RGB")
        dr = ImageDraw.Draw(img)
        xy, src = _target_xy(man, obj, fr, wcs)
        if xy is not None:
            cx, cy = xy[0] * k, (h - 1 - xy[1]) * k  # flip y: row 0 = South
            r = 9 * k
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 255, 140), width=max(3, size // 300))
        col = COLORS[fr["instrument"]]
        pad = size // 40
        dr.rectangle([0, 0, size, size // 9], fill=(0, 0, 0))
        dr.text((pad, pad // 2), fr["date"][:7].replace("-", " · "), font=f_big, fill=(255, 255, 255))
        l0, l1 = fr["lambda_um"]
        lam = f"{l0:.1f} µm" if abs(l1 - l0) < 0.05 else f"{l0:.1f}–{l1:.1f} µm"
        badge = f"{fr['instrument']} {fr['band']}  {lam}"
        bw = dr.textlength(badge, font=f_mid)
        dr.rounded_rectangle([size - bw - 3 * pad, pad, size - pad, pad + size // 22], radius=size // 80, fill=col)
        dr.text((size - bw - 2 * pad, pad + size // 200), badge, font=f_mid, fill=(0, 0, 0))
        dr.rectangle([0, size - size // 16, size, size], fill=(0, 0, 0))
        foot = f"{title}  ·  {w * man['grid']['pixel_scale_arcsec'] / 60:.1f}′ field  ·  N up, E left"
        if xy is not None:
            foot += f"  ·  ring: {src}"
        dr.text((pad, size - size // 16 + size // 90), foot, font=f_small, fill=(220, 220, 220))
        # N/E arrows (bottom-right, above footer)
        ax, ay, L = size - 3 * pad, size - size // 16 - 3 * pad, size // 18
        dr.line([ax, ay, ax, ay - L], fill=(255, 255, 255), width=3)
        dr.line([ax, ay, ax - L, ay], fill=(255, 255, 255), width=3)
        dr.text((ax - size // 120, ay - L - size // 30), "N", font=f_small, fill=(255, 255, 255))
        dr.text((ax - L - size // 30, ay - size // 80), "E", font=f_small, fill=(255, 255, 255))
        out.append(img)
    return out


def make_movie(field: str, seq_id: str = "thermal46", root: Path = BUNDLE, fps: float = 4.0, out_dir: Path = OUT) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    imgs = render_frames(field, seq_id, root)
    res = {"field": field, "frames": len(imgs)}
    try:
        import imageio.v2 as iio

        mp4 = out_dir / f"{field}_{seq_id}.mp4"
        hold = imgs + [imgs[-1]] * int(fps)  # hold the last frame 1 s
        with iio.get_writer(mp4, fps=fps, codec="libx264", quality=7, pixelformat="yuv420p", macro_block_size=8) as wr:
            for im in hold:
                wr.append_data(np.asarray(im))
        res["mp4"] = str(mp4)
    except Exception as e:  # noqa: BLE001  (no ffmpeg → GIF only)
        res["mp4_error"] = repr(e)
    gif = out_dir / f"{field}_{seq_id}.gif"
    for side, ncol in ((480, 64), (400, 48), (320, 32)):
        small = [im.resize((side, side)).quantize(ncol) for im in imgs]
        small[0].save(gif, save_all=True, append_images=small[1:], duration=int(1000 / fps), loop=0, optimize=True)
        if gif.stat().st_size <= 4e6:
            break
    res["gif"] = str(gif)
    return res
