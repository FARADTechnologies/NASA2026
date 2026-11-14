"""Reproject + inverse-variance co-add of SPHEREx images (one detector, one time cluster) and WISE epoch reprojection."""
from __future__ import annotations

import numpy as np

from .calibrate import BAD_BIT, SAT_BIT, load_spherex, load_wise
from .grid import Mapper


def coadd_spherex(rows: list[dict], dst_wcs, shape, log=None) -> dict | None:
    """rows: index rows (path, t_start, t_end, release, filename). Returns dict(data, mask, n_inputs, lam, mjd_*, sources)."""
    num = np.zeros(shape, np.float64)
    den = np.zeros(shape, np.float64)
    sat_cnt = np.zeros(shape, np.int32)
    cov_cnt = np.zeros(shape, np.int32)
    lam_lo, lam_hi, used, mids, t0, t1 = [], [], [], [], [], []
    for r in rows:
        try:
            im = load_spherex(r["path"])
            m = Mapper(im["wcs"], im["shape"], dst_wcs, shape)
        except Exception as e:  # noqa: BLE001
            if log:
                log.warning("skip %s: %s", r["filename"], e)
            continue
        if not m.inside.any():
            continue
        d = np.where(im["bad"], np.nan, im["data"])
        v = np.where(im["bad"], np.nan, im["var"])
        dg, vg, sg = m.data(d), m.data(v), m.mask(im["sat"])
        good = np.isfinite(dg) & np.isfinite(vg) & (vg > 0)
        w = np.zeros(shape)
        w[good] = 1.0 / vg[good]
        num[good] += w[good] * dg[good]
        den[good] += w[good]
        cov_cnt[m.inside] += 1
        sat_cnt[m.inside & (sg > 0)] += 1
        used.append(r)
        mids.append(0.5 * (r["t_start"] + r["t_end"]))
        t0.append(r["t_start"])
        t1.append(r["t_end"])
        if im["lam"]:
            lam_lo.append(im["lam"][0])
            lam_hi.append(im["lam"][1])
    if not used:
        return None
    with np.errstate(invalid="ignore", divide="ignore"):
        data = np.where(den > 0, num / den, np.nan).astype(np.float32)
    mask = np.zeros(shape, np.uint8)
    mask[~np.isfinite(data)] = BAD_BIT
    sat = (sat_cnt > 0) & (sat_cnt * 2 >= cov_cnt)
    mask[sat] |= SAT_BIT
    return dict(data=data, mask=mask, n_inputs=len(used), lam=(min(lam_lo), max(lam_hi)) if lam_lo else None,
                mjd_start=min(t0), mjd_end=max(t1), mjd_mid=float(np.mean(mids)), sources=[r["filename"] for r in used],
                releases=sorted({r["release"] for r in used}))


def reproject_wise(path, band: int, dst_wcs, shape) -> dict:
    im = load_wise(path, band)
    m = Mapper(im["wcs"], im["shape"], dst_wcs, shape)
    data = m.data(np.where(im["bad"], np.nan, im["data"]))
    sat = m.mask(im["sat"])
    mask = np.zeros(shape, np.uint8)
    mask[~np.isfinite(data)] = BAD_BIT
    mask[sat > 0] |= SAT_BIT
    return dict(data=data, mask=mask, mjd_start=im["mjdmin"], mjd_end=im["mjdmax"], mjd_mid=0.5 * (im["mjdmin"] + im["mjdmax"]))
