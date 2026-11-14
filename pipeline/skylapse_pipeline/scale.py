"""Display scaling (docs/SCIENCE_NOTES.md §5): sigma-clipped background subtraction, then a multiplicative factor so the
median flux of bright, unsaturated, low-proper-motion Gaia stars matches a reference frame. Units = "relative"."""
from __future__ import annotations

import numpy as np
from astropy.stats import sigma_clipped_stats

from .grid import world_to_grid

APER_R = 3.0  # px (8.25") — covers WISE (6") and resampled SPHEREx (~9") PSF cores
EDGE = 8


def subtract_background(data: np.ndarray) -> tuple[np.ndarray, float, float]:
    fin = np.isfinite(data)
    if fin.sum() < 50:
        return data, 0.0, 1.0
    _, med, std = sigma_clipped_stats(data[fin], sigma=3.0, maxiters=5)
    return (data - med).astype(np.float32), float(med), float(std if std > 0 else 1.0)


def select_ref_stars(gaia_rows: list[dict], wcs, shape, avoid_xy=None, gmin=11.0, gmax=17.5, pm_max=100.0, nmax=40):
    """Return (x, y) arrays of reference stars on the grid."""
    sel = []
    for r in gaia_rows:
        try:
            g = float(r["phot_g_mean_mag"])
            pm = np.hypot(float(r["pmra"] or 0), float(r["pmdec"] or 0))
            ruwe = float(r.get("ruwe") or 1.0)
        except (TypeError, ValueError):
            continue
        if not (gmin <= g <= gmax) or pm > pm_max or ruwe > 1.4 or g != g:
            continue
        sel.append((g, float(r["ra"]), float(r["dec"])))
    if not sel:
        return np.array([]), np.array([])
    sel.sort()
    ra = np.array([s[1] for s in sel])
    dec = np.array([s[2] for s in sel])
    x, y = world_to_grid(wcs, ra, dec)
    ny, nx = shape
    ok = (x > EDGE) & (x < nx - EDGE) & (y > EDGE) & (y < ny - EDGE)
    if avoid_xy is not None:
        ok &= np.hypot(x - avoid_xy[0], y - avoid_xy[1]) > 12
    x, y = x[ok], y[ok]
    # drop crowded stars (another selected star within 4 px)
    keep = []
    for i in range(len(x)):
        d = np.hypot(x - x[i], y - y[i])
        if np.sum(d < 4) == 1:
            keep.append(i)
    keep = keep[:nmax]
    return x[keep], y[keep]


def aperture_fluxes(data: np.ndarray, mask: np.ndarray, xs, ys) -> np.ndarray:
    ny, nx = data.shape
    yy, xx = np.mgrid[0:ny, 0:nx]
    out = []
    for x, y in zip(xs, ys):
        x0, y0 = int(round(x)), int(round(y))
        sl = (slice(max(y0 - 5, 0), y0 + 6), slice(max(x0 - 5, 0), x0 + 6))
        r = np.hypot(xx[sl] - x, yy[sl] - y)
        ap = r <= APER_R
        vals = data[sl][ap]
        if mask is not None and np.any(mask[sl][ap]):
            out.append(np.nan)
        elif not np.all(np.isfinite(vals)):
            out.append(np.nan)
        else:
            out.append(float(vals.sum()))
    return np.array(out)


def scale_factor(data, mask, ref_flux, xs, ys, min_stars=3):
    """Median of ref/frame flux ratios over stars detected in both (> 0). Returns (factor, n_stars)."""
    if len(xs) == 0:
        return None, 0
    f = aperture_fluxes(data, mask, xs, ys)
    ok = np.isfinite(f) & np.isfinite(ref_flux) & (f > 0) & (ref_flux > 0)
    if ok.sum() < min_stars:
        return None, int(ok.sum())
    ratios = ref_flux[ok] / f[ok]
    return float(np.median(ratios)), int(ok.sum())


def display_percentiles(data: np.ndarray, mask: np.ndarray | None = None) -> dict:
    vals = data[np.isfinite(data)] if mask is None else data[np.isfinite(data) & (mask == 0)]
    if vals.size < 10:
        vals = data[np.isfinite(data)]
    if vals.size == 0:
        return {"p01": 0.0, "p50": 0.0, "p99": 1.0, "p999": 1.0}
    p = np.percentile(vals, [1, 50, 99, 99.9])
    p = [float(round(v, 5)) for v in p]
    for i in range(1, 4):
        p[i] = max(p[i], p[i - 1])
    if p[3] - p[0] <= 0:
        p[3] = p[0] + 1.0
    return {"p01": p[0], "p50": p[1], "p99": p[2], "p999": p[3]}
