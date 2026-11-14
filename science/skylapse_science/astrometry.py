"""S1 — proper-motion validation on the native-WCS unWISE time-resolved epochs.

Method (also in science/VALIDATION.md):
1. For every WISE epoch (W1 and W2) predict the target pixel from the SIMBAD J2000 position + proper motion
   propagated to the epoch's mid MJD; cut a small box, subtract a sigma-clipped local background,
   and measure the centroid with photutils `centroid_2dg` (iterated twice, box recentred).
   Saturated cores (Barnard) are handled by fitting only the unsaturated wings (core pixels masked).
2. Reject epochs with S/N < 5, a centroid that ran away (> 3 px from the prediction) or a failed fit.
3. Convert RA/Dec to tangent-plane offsets (xi, eta) in arcsec around the 2018.0 reference position.
4. Weighted least squares for xi0, eta0, mu_alpha*, mu_delta and parallax (parallax factor from Earth's
   barycentric position; WISE is in low Earth orbit), with 3-sigma iterative clipping.
5. Errors: bootstrap over epochs (1000 resamples).
"""
from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, asdict

import numpy as np
from astropy.coordinates import get_body_barycentric
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.time import Time
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS
from photutils.centroids import centroid_2dg

from . import config

warnings.simplefilter("ignore", AstropyWarning)
warnings.simplefilter("ignore", RuntimeWarning)

MAS_PER_DEG = 3.6e6
WISE_FWHM_PX = {1: 6.1 / 2.75, 2: 6.4 / 2.75}
BOX_HALF = 5                          # 11x11 px box (30") — PSF FWHM is ~2.3 px
RNG_SEED = 20261114
SYS_FLOOR = 0.10            # arcsec, unsaturated epochs
SYS_FLOOR_SAT_HOLE = 0.30   # arcsec, saturated core (zero hole) -> Moffat wing fit
SYS_FLOOR_FLAT = 0.60       # arcsec, very bright flat-topped core without a hole (early unWISE epochs of Barnard's Star)
FLAT_CORE_LEVEL = 5.0e4     # unWISE Vega nanomaggies per pixel; eps Ind B peaks at ~2e4, Barnard at 1-3e5


@dataclass
class Epoch:
    band: int
    epoch: int
    mjd: float
    ra: float
    dec: float
    x: float
    y: float
    snr: float
    sigma_arcsec: float
    saturated: bool
    used: bool = True
    reason: str = ""


# ---------------------------------------------------------------- geometry helpers
def propagate(t: dict, mjd: float) -> tuple[float, float]:
    """SIMBAD J2000 position + linear proper motion -> (ra, dec) at mjd (deg). Parallax ignored."""
    dt = config.jyear(mjd) - 2000.0
    dec = t["dec_j2000"] + t["pmdec_masyr"] * dt / MAS_PER_DEG
    ra = t["ra_j2000"] + t["pmra_masyr"] * dt / (MAS_PER_DEG * math.cos(math.radians(t["dec_j2000"])))
    return ra, dec


def to_tangent(ra, dec, ra0, dec0):
    """Gnomonic projection -> (xi, eta) in arcsec."""
    ra, dec, ra0, dec0 = map(np.radians, (ra, dec, ra0, dec0))
    cosc = np.sin(dec0) * np.sin(dec) + np.cos(dec0) * np.cos(dec) * np.cos(ra - ra0)
    xi = np.cos(dec) * np.sin(ra - ra0) / cosc
    eta = (np.cos(dec0) * np.sin(dec) - np.sin(dec0) * np.cos(dec) * np.cos(ra - ra0)) / cosc
    return np.degrees(xi) * 3600.0, np.degrees(eta) * 3600.0


def from_tangent(xi, eta, ra0, dec0):
    xi, eta = np.radians(np.asarray(xi) / 3600.0), np.radians(np.asarray(eta) / 3600.0)
    ra0, dec0 = math.radians(ra0), math.radians(dec0)
    rho = np.hypot(xi, eta)
    c = np.arctan(rho)
    with np.errstate(invalid="ignore", divide="ignore"):
        dec = np.where(rho == 0, dec0, np.arcsin(np.cos(c) * math.sin(dec0) + eta * np.sin(c) * math.cos(dec0) / np.where(rho == 0, 1, rho)))
        ra = ra0 + np.arctan2(xi * np.sin(c), rho * math.cos(dec0) * np.cos(c) - eta * math.sin(dec0) * np.sin(c))
    return np.degrees(ra) % 360.0, np.degrees(dec)


def parallax_factors(mjd: np.ndarray, ra: float, dec: float):
    """Return (P_alpha*, P_delta) such that offset = parallax * P (same units as parallax)."""
    pos = get_body_barycentric("earth", Time(np.asarray(mjd), format="mjd", scale="tdb"))
    X, Y, Z = (pos.x.to_value("AU"), pos.y.to_value("AU"), pos.z.to_value("AU"))
    a, d = math.radians(ra), math.radians(dec)
    pa = X * math.sin(a) - Y * math.cos(a)
    pd = X * math.cos(a) * math.sin(d) + Y * math.sin(a) * math.sin(d) - Z * math.cos(d)
    return pa, pd


# ---------------------------------------------------------------- centroiding
def _centroid_one(img: np.ndarray, x0: float, y0: float, sat_level: float | None):
    """Return (x, y, snr, saturated) or None. x0/y0 are 0-based pixel coords."""
    ny, nx = img.shape
    ix, iy = int(round(x0)), int(round(y0))
    if ix - BOX_HALF - 6 < 0 or iy - BOX_HALF - 6 < 0 or ix + BOX_HALF + 6 >= nx or iy + BOX_HALF + 6 >= ny:
        return None
    # local background from a 23x23 annulus-ish region
    big = img[iy - BOX_HALF - 6: iy + BOX_HALF + 7, ix - BOX_HALF - 6: ix + BOX_HALF + 7]
    _, bkg, rms = sigma_clipped_stats(big, sigma=3.0, maxiters=5)
    x, y = x0, y0
    saturated = False
    for _ in range(3):
        ix, iy = int(round(x)), int(round(y))
        if ix - BOX_HALF < 0 or iy - BOX_HALF < 0 or ix + BOX_HALF >= nx or iy + BOX_HALF >= ny:
            return None
        box = img[iy - BOX_HALF: iy + BOX_HALF + 1, ix - BOX_HALF: ix + BOX_HALF + 1] - bkg
        mask = ~np.isfinite(box)
        if sat_level is not None:
            core = box + bkg >= sat_level
            if core.any():
                saturated = True
                mask |= core
        if mask.sum() > box.size * 0.5:
            return None
        try:
            cx, cy = centroid_2dg(np.where(mask, 0.0, box), mask=mask)
        except Exception:
            return None
        if not (np.isfinite(cx) and np.isfinite(cy)):
            return None
        x, y = ix - BOX_HALF + cx, iy - BOX_HALF + cy
    # S/N in a 2-pixel-radius aperture
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    ap = (xx - x) ** 2 + (yy - y) ** 2 <= 2.0 ** 2
    flux = np.nansum(img[ap] - bkg)
    snr = flux / (rms * math.sqrt(ap.sum())) if rms > 0 else 0.0
    return x, y, float(snr), saturated


def measure_target(target_id: str) -> list[Epoch]:
    t = config.load_targets()[target_id]
    wdir = config.RAW / "wise" / target_id
    rows = [l.strip().split(",") for l in open(wdir / "index.csv", encoding="utf-8")][1:]
    out: list[Epoch] = []
    for r in rows:
        epoch, band, mjdmin, mjdmax, fname = int(r[0]), int(r[1]), float(r[2]), float(r[3]), r[6]
        mjd = 0.5 * (mjdmin + mjdmax)
        with fits.open(wdir / fname) as h:
            img = h[0].data.astype(float)
            w = WCS(h[0].header)
        ra_p, dec_p = propagate(t, mjd)
        x0, y0 = (float(v) for v in w.world_to_pixel_values(ra_p, dec_p))
        res = _wing_fit(img, x0, y0)                 # saturated core (exact-zero hole in unWISE)?
        if res == "nohole":
            res = _centroid_one(img, x0, y0, None)
        elif res is None:
            out.append(Epoch(band, epoch, mjd, np.nan, np.nan, np.nan, np.nan, 0.0, np.nan, True, False,
                             "saturated core, wing fit failed"))
            continue
        if res is None:
            out.append(Epoch(band, epoch, mjd, np.nan, np.nan, np.nan, np.nan, 0.0, np.nan, False, False, "centroid failed / off image"))
            continue
        x, y, snr, saturated = res
        ra, dec = w.pixel_to_world_values(x, y)
        fwhm_arcsec = WISE_FWHM_PX[band] * 2.75
        stat = fwhm_arcsec / (2.355 * max(snr, 1e-3))
        core = img[max(int(round(y)) - 2, 0):max(int(round(y)) + 3, 0), max(int(round(x)) - 2, 0):max(int(round(x)) + 3, 0)]
        flat_core = (not saturated) and core.size > 0 and bool(np.nanmax(core) > FLAT_CORE_LEVEL)
        # per-epoch error = statistical (+) systematic floor (unWISE epoch astrometry / scan-direction offsets ~0.1")
        floor = SYS_FLOOR_SAT_HOLE if saturated else (SYS_FLOOR_FLAT if flat_core else SYS_FLOOR)
        sigma = math.hypot(stat, floor)
        saturated = saturated or bool(flat_core)
        e = Epoch(band, epoch, mjd, float(ra), float(dec), x, y, snr, sigma, saturated)
        if math.hypot(x - x0, y - y0) > 3.0:
            e.used, e.reason = False, f"centroid {math.hypot(x - x0, y - y0):.1f} px from prediction"
        elif snr < 5:
            e.used, e.reason = False, f"S/N {snr:.1f} < 5"
        out.append(e)
    return out


def _wing_fit(img, x0, y0, R=12):
    """Saturated stars: unWISE sets the saturated core to exactly 0 (a hole ~6 px wide for Barnard's Star).
    Mask the hole (+1 px of non-linear rim) and fit a circular Moffat profile + constant to the unsaturated wings.
    Returns "nohole" when there is no hole (not saturated; normal centroiding is used), None when the fit fails."""
    from scipy.ndimage import binary_dilation, binary_fill_holes, label
    from scipy.optimize import least_squares
    ny, nx = img.shape
    ix, iy = int(round(x0)), int(round(y0))
    if ix - R < 0 or iy - R < 0 or ix + R >= nx or iy + R >= ny:
        return None
    box = img[iy - R: iy + R + 1, ix - R: ix + R + 1]
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
    zero = (box == 0) & (xx ** 2 + yy ** 2 <= 8 ** 2)
    if zero.sum() < 3:
        return "nohole"
    lab, _ = label(zero)
    # the hole = largest zero region near the prediction
    ids, counts = np.unique(lab[lab > 0], return_counts=True)
    hole = binary_fill_holes(binary_dilation(lab == ids[np.argmax(counts)], iterations=1)) & binary_fill_holes(zero | (lab == ids[np.argmax(counts)]))
    hole = binary_fill_holes(lab == ids[np.argmax(counts)]) | hole
    if hole.sum() < 15:                             # partial / irregular hole: centre is unreliable
        return None
    hx, hy = xx[hole].mean(), yy[hole].mean()
    # drop the hole, interior junk pixels and a 2-px corrupted rim; fit the wings only
    mask = binary_dilation(hole, iterations=2) | ~np.isfinite(box) | (xx ** 2 + yy ** 2 > R ** 2)
    xs, ys, vs = xx[~mask].astype(float), yy[~mask].astype(float), box[~mask]
    peak = float(np.nanmax(vs))

    def model(p):
        cx, cy, amp, alpha, beta, c = p
        return amp * (1 + ((xs - cx) ** 2 + (ys - cy) ** 2) / alpha ** 2) ** (-beta) + c

    p0 = [hx, hy, peak * 3, 2.5, 2.0, float(np.nanmedian(vs))]
    try:
        r = least_squares(lambda p: (model(p) - vs) / np.sqrt(np.abs(vs) + peak * 1e-3), p0,
                          bounds=([hx - 3, hy - 3, 0, 0.5, 0.8, -np.inf], [hx + 3, hy + 3, np.inf, 15, 10, np.inf]))
    except Exception:
        return None
    cx, cy = r.x[0], r.x[1]
    if math.hypot(cx - hx, cy - hy) > 2.0:          # wing fit and hole centre disagree -> distrust
        return None
    return ix + cx, iy + cy, 1000.0, True


# ---------------------------------------------------------------- fitting
def _design(t_yr, pa, pd, fit_plx=True):
    n = len(t_yr)
    cols = 5 if fit_plx else 4
    A = np.zeros((2 * n, cols))
    A[:n, 0] = 1.0
    A[n:, 1] = 1.0
    A[:n, 2] = t_yr
    A[n:, 3] = t_yr
    if fit_plx:
        A[:n, 4] = pa
        A[n:, 4] = pd
    return A


def wls(t_yr, xi, eta, sig, pa, pd, fit_plx=True):
    A = _design(t_yr, pa, pd, fit_plx)
    b = np.concatenate([xi, eta])
    w = 1.0 / np.concatenate([sig, sig])
    p, *_ = np.linalg.lstsq(A * w[:, None], b * w, rcond=None)
    return p, b - A @ p


def fit_motion(epochs: list[Epoch], ra0: float, dec0: float, fit_plx=True, n_boot=1000):
    use = [e for e in epochs if e.used]
    for _ in range(5):                                          # iterative 3-sigma clipping
        mjd = np.array([e.mjd for e in use])
        xi, eta = to_tangent(np.array([e.ra for e in use]), np.array([e.dec for e in use]), ra0, dec0)
        sig = np.array([e.sigma_arcsec for e in use])
        t_yr = np.array([config.jyear(m) - 2018.0 for m in mjd])
        pa, pd = parallax_factors(mjd, ra0, dec0)
        p, res = wls(t_yr, xi, eta, sig, pa, pd, fit_plx)
        n = len(use)
        rr = np.hypot(res[:n], res[n:])
        robust = 1.4826 * float(np.median(rr))
        bad = rr > max(3.0 * robust, 1.0)                          # never clip sub-arcsec residuals
        if not bad.any():
            break
        worst = int(np.argmax(rr))
        use[worst].used, use[worst].reason = False, f"3-sigma clip (residual {rr[worst]:.2f}\")"
        use = [e for e in use if e.used]
    # rescale formal errors so reduced chi2 = 1, then bootstrap
    n = len(use)
    rng = np.random.default_rng(RNG_SEED)
    boots = []
    for _ in range(n_boot):
        k = rng.integers(0, n, n)
        if len(set(k.tolist())) < 6:
            continue
        pb, _ = wls(t_yr[k], xi[k], eta[k], sig[k], pa[k], pd[k], fit_plx)
        boots.append(pb)
    boots = np.array(boots)
    perr = boots.std(axis=0)
    rms = float(np.sqrt(np.mean(res ** 2)))
    return {
        "xi0": p[0], "eta0": p[1], "pmra": p[2] * 1000, "pmdec": p[3] * 1000,
        "plx": (p[4] * 1000) if fit_plx else None,
        "pmra_err": perr[2] * 1000, "pmdec_err": perr[3] * 1000,
        "plx_err": (perr[4] * 1000) if fit_plx else None,
        "boot_pmtot": np.hypot(boots[:, 2], boots[:, 3]) * 1000,
        "n_epochs": n, "rms_arcsec": rms,
        "t_span_yr": float(t_yr.max() - t_yr.min()),
    }


# ---------------------------------------------------------------- references
def reference_for(target_id: str) -> dict:
    """Reference proper motions. Gaia DR3 from the prefetched cone (ESA archive), SIMBAD/literature for WISE 0855."""
    t = config.load_targets()[target_id]
    gaia = _gaia_rows(target_id)
    if target_id == "barnard":
        g = _nearest(gaia, *propagate_to(t, 2016.0))
        return {"source": f"Gaia DR3 {g['source_id']}", "pmra": g["pmra"], "pmdec": g["pmdec"],
                "pmra_err": g["pmra_error"], "pmdec_err": g["pmdec_error"], "parallax": g["parallax"], "unit": "mas/yr"}
    if target_id == "eps_indi_b":
        g = _nearest(gaia, *propagate_to(t, 2016.0))
        # eps Ind A: J2000 330.8403, -56.7860 (SCIENCE_NOTES); its pm ~ (3966, -2536) — find it in the same cone.
        a = _nearest(gaia, 330.8403 + 3.97 * 16 / 3600 / math.cos(math.radians(-56.786)), -56.7860 - 2.54 * 16 / 3600,
                     min_g=None, bright=True)
        return {"source": f"Gaia DR3 {g['source_id']} (eps Ind B, Ba+Bb photocentre)", "pmra": g["pmra"], "pmdec": g["pmdec"],
                "pmra_err": g["pmra_error"], "pmdec_err": g["pmdec_error"], "parallax": g["parallax"], "unit": "mas/yr",
                "comoving_primary": {"source": f"Gaia DR3 {a['source_id']} (eps Ind A)", "pmra": a["pmra"], "pmdec": a["pmdec"],
                                     "parallax": a["parallax"], "g_mag": a["phot_g_mean_mag"]}}
    if target_id == "wise0855":
        return {"source": "Kirkpatrick et al. 2021, ApJS 253, 7 (via SIMBAD)", "pmra": t["pmra_masyr"], "pmdec": t["pmdec_masyr"],
                "pmra_err": None, "pmdec_err": None, "parallax": t["parallax_mas"], "unit": "mas/yr",
                "secondary": _catwise_ref(target_id)}
    raise KeyError(target_id)


def propagate_to(t, year):
    mjd = 51544.5 + (year - 2000.0) * 365.25
    return propagate(t, mjd)


def _gaia_rows(target_id):
    import csv
    with open(config.RAW / "catalogs" / f"{target_id}_gaia_dr3.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k, v in r.items():
            if k != "source_id":
                r[k] = float(v) if v not in ("", None) else float("nan")
    return rows


def _nearest(rows, ra, dec, min_g=None, bright=False):
    def sep(r):
        return math.hypot((r["ra"] - ra) * math.cos(math.radians(dec)), r["dec"] - dec) * 3600
    cands = sorted(rows, key=sep)
    if bright:
        cands = [r for r in cands[:20] if r["phot_g_mean_mag"] < 6]
    r = cands[0]
    if sep(r) > 5:
        raise RuntimeError(f"no Gaia match within 5\" (nearest {sep(r):.1f}\")")
    return r


def _catwise_ref(target_id):
    import csv
    try:
        with open(config.RAW / "catalogs" / f"{target_id}_catwise2020.csv", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return None
    t = config.load_targets()[target_id]
    ra, dec = propagate(t, 57170.0)
    best, bsep = None, 1e9
    for r in rows:
        s = math.hypot((float(r["ra"]) - ra) * math.cos(math.radians(dec)), float(r["dec"]) - dec) * 3600
        if s < bsep:
            best, bsep = r, s
    if best is None or bsep > 5:
        return None
    pmra = float(best["pmra"]) * (1000 if abs(float(best["pmra"])) < 50 else 1)
    pmdec = float(best["pmdec"]) * (1000 if abs(float(best["pmdec"])) < 50 else 1)
    return {"source": f"CatWISE2020 {best.get('source_name', '')}".strip(), "pmra": pmra, "pmdec": pmdec}


# ---------------------------------------------------------------- driver
def agreement_pct(mpmra, mpmdec, rpmra, rpmdec):
    """100 * (1 - |mu_measured - mu_reference| / |mu_reference|), vector difference (stricter than comparing totals)."""
    return 100.0 * (1.0 - math.hypot(mpmra - rpmra, mpmdec - rpmdec) / math.hypot(rpmra, rpmdec))


def validate_target(target_id: str) -> dict:
    t = config.load_targets()[target_id]
    epochs = measure_target(target_id)
    ra0, dec0 = t["ra_2018"], t["dec_2018"]
    fit = fit_motion(epochs, ra0, dec0, fit_plx=True)
    ref = reference_for(target_id)
    agree = agreement_pct(fit["pmra"], fit["pmdec"], ref["pmra"], ref["pmdec"])
    pm_tot = math.hypot(fit["pmra"], fit["pmdec"])
    pm_err = float(np.std(fit["boot_pmtot"]))
    return {"target": target_id, "epochs": epochs, "fit": fit, "ref": ref, "agreement_pct": agree,
            "pm_total": pm_tot, "pm_total_err": pm_err, "ra0": ra0, "dec0": dec0}


def model_position(res: dict, mjd: float) -> tuple[float, float]:
    f = res["fit"]
    ty = config.jyear(mjd) - 2018.0
    pa, pd = parallax_factors(np.array([mjd]), res["ra0"], res["dec0"])
    plx = (f["plx"] or 0.0) / 1000
    xi = f["xi0"] + f["pmra"] / 1000 * ty + plx * pa[0]
    eta = f["eta0"] + f["pmdec"] / 1000 * ty + plx * pd[0]
    ra, dec = from_tangent(xi, eta, res["ra0"], res["dec0"])
    return float(ra), float(dec)


def spherex_cluster_mjds(target_id: str, detector: str = "D6", gap_days: float = 30.0) -> list[float]:
    """Mid MJD of each SPHEREx time cluster (gap > 30 d) for one detector, from the prefetch TAP index."""
    import csv
    path = config.SLIM / "spherex" / target_id / "index.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    key = "t_start" if "t_start" in rows[0] else next(k for k in rows[0] if "time" in k or "mjd" in k)
    mjds = sorted(float(r[key]) for r in rows if detector in (r.get("band") or ""))
    clusters, cur = [], []
    for m in mjds:
        if cur and m - cur[-1] > gap_days:
            clusters.append(cur)
            cur = []
        cur.append(m)
    if cur:
        clusters.append(cur)
    return [0.5 * (c[0] + c[-1]) for c in clusters]


def motion_block(res: dict) -> dict:
    f, ref = res["fit"], res["ref"]
    track = []
    for e in sorted(res["epochs"], key=lambda e: (e.mjd, e.band)):
        if e.band != 2:
            continue
        if e.used:
            track.append({"mjd": round(e.mjd, 4), "ra": round(e.ra, 7), "dec": round(e.dec, 7), "instrument": "WISE",
                          "band": "W2", "kind": "measured"})
        else:
            ra, dec = model_position(res, e.mjd)
            track.append({"mjd": round(e.mjd, 4), "ra": round(ra, 7), "dec": round(dec, 7), "instrument": "WISE",
                          "band": "W2", "kind": "model"})
    for m in spherex_cluster_mjds(res["target"]):
        ra, dec = model_position(res, m)
        track.append({"mjd": round(m, 4), "ra": round(ra, 7), "dec": round(dec, 7), "instrument": "SPHEREx",
                      "band": "D6", "kind": "model"})
    track.sort(key=lambda p: p["mjd"])
    reference = {"source": ref["source"], "pmra": round(ref["pmra"], 1), "pmdec": round(ref["pmdec"], 1),
                 "pm_total": round(math.hypot(ref["pmra"], ref["pmdec"]), 1), "unit": "mas/yr"}
    if ref.get("parallax") is not None:
        reference["parallax"] = round(ref["parallax"], 1)
    if "comoving_primary" in ref:
        a = ref["comoving_primary"]
        reference["comoving_primary"] = {"source": a["source"], "pmra": round(a["pmra"], 1), "pmdec": round(a["pmdec"], 1)}
        reference["agreement_with_primary_pct"] = round(agreement_pct(f["pmra"], f["pmdec"], a["pmra"], a["pmdec"]), 1)
    n_w1 = sum(1 for e in res["epochs"] if e.used and e.band == 1)
    n_w2 = sum(1 for e in res["epochs"] if e.used and e.band == 2)
    return {
        "measured": {"pmra": round(f["pmra"], 1), "pmdec": round(f["pmdec"], 1), "pm_total": round(res["pm_total"], 1),
                     "err": round(res["pm_total_err"], 1), "pmra_err": round(f["pmra_err"], 1), "pmdec_err": round(f["pmdec_err"], 1),
                     "parallax": round(f["plx"], 1) if f["plx"] is not None else None,
                     "parallax_err": round(f["plx_err"], 1) if f["plx_err"] is not None else None,
                     "unit": "mas/yr", "n_epochs": f["n_epochs"], "n_epochs_w1": n_w1, "n_epochs_w2": n_w2,
                     "baseline_yr": round(f["t_span_yr"], 2), "rms_arcsec": round(f["rms_arcsec"], 3),
                     "method": "unWISE time-resolved epochs (W1+W2, native WCS), centroid_2dg, WLS fit of position + "
                               "proper motion + parallax, 3-sigma clipping, 1000x bootstrap"},
        "reference": reference,
        "agreement_pct": round(res["agreement_pct"], 1),
        "track": track,
    }


def epochs_table(res: dict) -> list[dict]:
    return [asdict(e) for e in res["epochs"]]
