"""Common TAN grid (North up, East left) and reprojection helpers.

Reprojection = one coordinate map per input image (grid pixel -> sky -> input pixel, SIP-aware via all_world2pix), then
scipy map_coordinates: bilinear for data (NaN propagates => masked), nearest for masks. Equivalent to reproject_interp.
"""
from __future__ import annotations

import warnings
from functools import lru_cache

import numpy as np
from astropy.wcs import WCS, FITSFixedWarning
from scipy.ndimage import map_coordinates

from .config import GRID_N, PIX_ARCSEC

warnings.filterwarnings("ignore", category=FITSFixedWarning)


def make_grid(ra: float, dec: float, n: int = GRID_N, pix_arcsec: float = PIX_ARCSEC) -> dict:
    cd = pix_arcsec / 3600.0
    c = (n + 1) / 2.0  # FITS 1-based centre (96.5 for 192)
    wcs = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRVAL1": round(ra, 7), "CRVAL2": round(dec, 7), "CRPIX1": c, "CRPIX2": c,
           "CD1_1": -round(cd, 10), "CD1_2": 0.0, "CD2_1": 0.0, "CD2_2": round(cd, 10)}
    return {"width": n, "height": n, "pixel_scale_arcsec": pix_arcsec, "wcs": wcs}


def grid_wcs(grid: dict) -> WCS:
    w = WCS(naxis=2)
    g = grid["wcs"]
    w.wcs.ctype = [g["CTYPE1"], g["CTYPE2"]]
    w.wcs.crval = [g["CRVAL1"], g["CRVAL2"]]
    w.wcs.crpix = [g["CRPIX1"], g["CRPIX2"]]
    w.wcs.cd = np.array([[g["CD1_1"], g["CD1_2"]], [g["CD2_1"], g["CD2_2"]]])
    w.pixel_shape = (grid["width"], grid["height"])
    return w


def _grid_world(dst_wcs: WCS, shape):
    key = (tuple(dst_wcs.wcs.crval), tuple(dst_wcs.wcs.crpix), tuple(np.ravel(dst_wcs.wcs.cd)), tuple(shape))
    return _grid_world_cached(key)


@lru_cache(maxsize=16)
def _grid_world_cached(key):
    crval, crpix, cd, shape = key
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval, w.wcs.crpix = list(crval), list(crpix)
    w.wcs.cd = np.array(cd).reshape(2, 2)
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    ra, dec = w.all_pix2world(xx.ravel(), yy.ravel(), 0)
    return ra, dec


class Mapper:
    """Maps input-image arrays onto the destination grid."""

    def __init__(self, src_wcs: WCS, src_shape, dst_wcs: WCS, shape):
        ra, dec = _grid_world(dst_wcs, shape)
        x, y = src_wcs.all_world2pix(ra, dec, 0)
        self.shape = tuple(shape)
        self.coords = np.vstack([y, x])
        ny, nx = src_shape
        self.inside = ((x > -0.5) & (x < nx - 0.5) & (y > -0.5) & (y < ny - 0.5)).reshape(shape)

    def data(self, arr: np.ndarray) -> np.ndarray:
        out = map_coordinates(arr.astype(np.float64), self.coords, order=1, mode="nearest", cval=np.nan).reshape(self.shape)
        out[~self.inside] = np.nan
        return out.astype(np.float32)

    def mask(self, arr: np.ndarray) -> np.ndarray:
        out = map_coordinates(arr.astype(np.float32), self.coords, order=0, mode="nearest").reshape(self.shape)
        out[~self.inside] = 0
        return out.astype(np.uint8)


def world_to_grid(wcs: WCS, ra, dec):
    """0-based pixel coordinates (x, y) on the grid."""
    x, y = wcs.all_world2pix(np.atleast_1d(ra), np.atleast_1d(dec), 0)
    return x, y
