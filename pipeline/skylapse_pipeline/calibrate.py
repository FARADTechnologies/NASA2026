"""Per-image calibration.

SPHEREx: data = IMAGE - ZODI (IMAGE is not zodi-subtracted). Flag bits are read from the FLAGS header (MSKNnnnn = name,
MSKMnnnn = value); never hardcoded. SOURCE is NOT masked. OVERFLOW (+NONLINEAR) = saturation.
WISE (unWISE time-resolved): NaN -> bad; saturation = pixels above a per-band threshold (W1 ~8 mag, W2 ~6.7 mag stars).
"""
from __future__ import annotations

import warnings

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

warnings.filterwarnings("ignore", module="astropy.wcs")
from astropy import log as _alog  # noqa: E402

_alog.setLevel("WARNING")

# Reject list = the one NASA used for the all-sky cube (docs/SCIENCE_NOTES.md §1). SOURCE and OUTLIER are NOT masked.
BAD_FLAGS = {"TRANSIENT", "SUR_ERROR", "NONFUNC", "DICHROIC", "MISSING_DATA", "HOT", "COLD", "PHANMISS", "NONLINEAR", "PERSIST",
             "CROSSTALK", "STREAK", "BLOOM", "SNOWBALL", "HALO", "SATELLITE_HALO"}
SAT_FLAGS = {"OVERFLOW"}  # saturation: marked (mask bit1); the pixel is kept for display when its value is finite
# unWISE nanomaggies per pixel: peak of a PSF (FWHM ~6") at 2.75"/px is ~18% of total flux.
# W1 = 8.0 -> 10**((22.5-8)/2.5) = 6.3e5 nmgy -> peak ~1.1e5; W2 = 6.7 -> 2.1e6 -> peak ~3.8e5. Use 0.6x as a safe threshold.
WISE_SAT = {1: 6.5e4, 2: 2.2e5}

BAD_BIT, SAT_BIT = 1, 2  # contract mask bits (bit0 masked, bit1 saturated)


def flag_bits(header) -> dict:
    out = {}
    for k in header:
        if k.startswith("MSKN"):
            m = header.get("MSKM" + k[4:])
            if m is not None:
                out[str(header[k]).strip()] = int(m)
    return out


def load_spherex(path, want_lambda: bool = True) -> dict:
    with fits.open(path, memmap=False) as h:
        img = h["IMAGE"].data.astype(np.float32)
        zodi = h["ZODI"].data.astype(np.float32)
        var = h["VARIANCE"].data.astype(np.float32)
        flags = h["FLAGS"].data.astype(np.int64)
        bits = flag_bits(h["FLAGS"].header)
        wcs = WCS(h["IMAGE"].header)
        lam = None
        if want_lambda:
            lam = spherex_lambda(h, img.shape)
    bad_val = sum(v for n, v in bits.items() if n in BAD_FLAGS)
    sat_val = sum(v for n, v in bits.items() if n in SAT_FLAGS)
    data = img - zodi
    sat = (flags & sat_val) != 0
    bad = ((flags & bad_val) != 0) | ~np.isfinite(data) | ~np.isfinite(var) | (var <= 0)
    return dict(data=data, var=var, bad=bad, sat=sat, wcs=wcs, lam=lam, shape=img.shape)


def spherex_lambda(hdul, shape):
    """[min, max] central wavelength (um) over the cutout (corners + centre) from the WAVE-TAB WCS."""
    try:
        w = WCS(hdul["IMAGE"].header, fobj=hdul, key="W")
        w.sip = None
        ny, nx = shape
        xs = np.array([0, nx - 1, 0, nx - 1, nx / 2])
        ys = np.array([0, 0, ny - 1, ny - 1, ny / 2])
        lam = []
        for x, y in zip(xs, ys):
            res = w.pixel_to_world(x, y)
            v = res[0] if isinstance(res, (list, tuple)) else res
            lam.append(float(v.to_value("um")))
        return float(min(lam)), float(max(lam))
    except Exception:  # noqa: BLE001
        return None


def load_wise(path, band: int) -> dict:
    with fits.open(path, memmap=False) as h:
        data = h[0].data.astype(np.float32)
        hdr = h[0].header
        wcs = WCS(hdr)
    bad = ~np.isfinite(data)
    sat = np.isfinite(data) & (data > WISE_SAT[band])
    # grow saturation by 1 px so the flat core + its edge are flagged
    if sat.any():
        from scipy.ndimage import binary_dilation

        sat = binary_dilation(sat, iterations=1)
    return dict(data=data, bad=bad, sat=sat, wcs=wcs, mjdmin=float(hdr["MJDMIN"]), mjdmax=float(hdr["MJDMAX"]), shape=data.shape)
