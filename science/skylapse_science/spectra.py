"""S2 — SPHEREx spectra from per-image aperture photometry at the (moving) target position.

Method (summary also written into the spectrum block notes):
- For every slim SPHEREx cutout (IMAGE, FLAGS, VARIANCE, ZODI, WCS-WAVE) of the field: position of the source propagated
  to the image's MJD-AVG (SIMBAD/Gaia proper motion; parallax ignored, < 0.1 px).
- IMAGE - ZODI; aperture r = 2 px (12.3") with exact pixel overlap; local background = sigma-clipped median in a 4-7 px annulus.
  Error from VARIANCE (aperture sum + background-mean term).
- Pixels with any "reject" flag (header MSKN names; list from SCIENCE_NOTES §1) inside the aperture -> point flagged.
  OVERFLOW (saturation) inside the aperture -> point flagged + saturated. NaN inside the aperture -> no point (saturated core).
- Flux density: sum(MJy/sr) x pixel solid angle (from the WCS) / encircled energy at r = 2 px (from the archive EPSF; ~0.96).
- Wavelength at the source pixel from the spectral WCS (`WCS(header, fobj=hdul, key="W")`, SIP off) — IRSA quick-look method.
- Binned spectrum: inverse-variance weighted mean of unflagged points in log-spaced wavelength bins (R ~ 40).
"""
from __future__ import annotations

import csv
import json
import math
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS, FITSFixedWarning
from photutils.aperture import CircularAnnulus, CircularAperture

from . import config
from astropy import log as _alog

_alog.setLevel("WARNING")

warnings.simplefilter("ignore", AstropyWarning)
warnings.simplefilter("ignore", FITSFixedWarning)
warnings.simplefilter("ignore", RuntimeWarning)

AP_R = 2.0
ANN_R = (4.0, 7.0)
# Encircled energy within r = 2 native px, median over the 441 EPSF zones of 3 archive images per detector
# (computed from the raw files' EPSF extension, normalised to the 33x33 oversampled stamp = +-3.3 px).
EE_R2 = {1: 0.973, 2: 0.969, 3: 0.962, 4: 0.961, 5: 0.958, 6: 0.958}
REJECT = ["TRANSIENT", "SUR_ERROR", "NONFUNC", "DICHROIC", "MISSING_DATA", "HOT", "COLD", "PHANMISS", "NONLINEAR",
          "PERSIST", "CROSSTALK", "STREAK", "BLOOM", "SNOWBALL", "HALO", "SATELLITE_HALO"]
MAS_PER_DEG = 3.6e6


def flag_bits(header) -> dict[str, int]:
    """Bit values by name from MSKNnnnn / MSKMnnnn header keywords (never hardcode bit numbers)."""
    names = {}
    for k in header.keys():
        if k.startswith("MSKN"):
            idx = k[4:]
            val = header.get("MSKM" + idx)
            names[str(header[k]).strip()] = int(val) if val is not None else (1 << int(idx))
    return names


def _propagate(ra, dec, pmra, pmdec, ref_year, mjd):
    dt = config.jyear(mjd) - ref_year
    d = dec + pmdec * dt / MAS_PER_DEG
    r = ra + pmra * dt / (MAS_PER_DEG * math.cos(math.radians(dec)))
    return r, d


def measure_image(path: Path, ra, dec, pmra=0.0, pmdec=0.0, ref_year=2000.0, neighbours=None, epsf=None) -> dict:
    """Photometry of one SPHEREx cutout at the propagated position. Returns a dict with a 'status'.
    With `epsf` (EpsfLibrary) the flux is a forced PSF fit of the target + `neighbours` (deblended); the aperture flux is
    kept as `flux_ap`. neighbours: list of (ra, dec, pmra, pmdec, ref_year)."""
    with fits.open(path) as h:
        hd = h["IMAGE"].header
        mjd = float(hd.get("MJD-AVG") or hd.get("MJD-OBS"))
        det = int(hd.get("DETECTOR"))
        img = h["IMAGE"].data.astype(float) - h["ZODI"].data.astype(float)
        var = h["VARIANCE"].data.astype(float)
        flags = h["FLAGS"].data.astype(np.int64)
        bits = flag_bits(h["FLAGS"].header) or flag_bits(hd)
        w = WCS(hd)
        r, d = _propagate(ra, dec, pmra, pmdec, ref_year, mjd)
        x, y = (float(v) for v in w.world_to_pixel_values(r, d))
        base = {"file": path.name, "mjd": round(mjd, 5), "detector": f"D{det}", "x": round(x, 2), "y": round(y, 2)}
        ny, nx = img.shape
        if not (ANN_R[1] <= x < nx - ANN_R[1] - 1 and ANN_R[1] <= y < ny - ANN_R[1] - 1):
            return {**base, "status": "edge"}
        sw = WCS(hd, fobj=h, key="W")
        sw.sip = None
        wl, bw = sw.pixel_to_world_values(x, y)
        wl, bw = float(wl), float(bw)
        try:
            detx, dety = (float(v) for v in WCS(hd, key="A").pixel_to_world_values(x, y))
        except Exception:
            detx = dety = 1019.5
        nb_xy = []
        for (nra, ndec, npmra, npmdec, nref) in (neighbours or []):
            a, b = _propagate(nra, ndec, npmra, npmdec, nref, mjd)
            nx_, ny_ = (float(v) for v in w.world_to_pixel_values(a, b))
            if math.hypot(nx_ - x, ny_ - y) <= PSF_FIT_R + 3:
                nb_xy.append((nx_, ny_))
    ap = CircularAperture((x, y), AP_R)
    ann = CircularAnnulus((x, y), *ANN_R)
    apm = ap.to_mask(method="exact")
    a_img, a_var, a_flg = apm.get_values(img), apm.get_values(var), apm.multiply(flags, fill_value=0)
    wts = apm.get_values(np.ones_like(img))
    reject_val = sum(bits.get(n, 0) for n in REJECT)
    overflow_val = bits.get("OVERFLOW", 0)
    core = apm.to_image(img.shape) > 0
    flg_in = np.bitwise_or.reduce(flags[core]) if core.any() else 0
    if not np.all(np.isfinite(a_img)):
        return {**base, "lambda_um": round(wl, 4), "status": "nan_core", "saturated": bool(flg_in & overflow_val)}
    annm = ann.to_mask(method="center").to_image(img.shape) > 0
    good_ann = annm & np.isfinite(img) & ((flags & reject_val) == 0)
    if good_ann.sum() < 10:
        return {**base, "lambda_um": round(wl, 4), "status": "no_background"}
    _, bkg, bstd = sigma_clipped_stats(img[good_ann], sigma=3.0, maxiters=5)
    s = float(np.sum((a_img - bkg) * wts))
    npix = float(np.sum(wts))
    e2 = float(np.sum(a_var * wts ** 2)) + npix ** 2 * (bstd ** 2) / good_ann.sum()
    area_sr = float(w.proj_plane_pixel_area().to_value("sr")) if hasattr(w.proj_plane_pixel_area(), "to_value") else \
        float(w.proj_plane_pixel_area()) * (math.pi / 180) ** 2
    to_mjy = area_sr * 1e9 / EE_R2[det]            # MJy/sr * sr -> MJy -> mJy (1e9), aperture-corrected
    sat = bool(flg_in & overflow_val)
    rej = bool(flg_in & reject_val)
    out = {**base, "lambda_um": round(wl, 4), "bandwidth_um": round(bw, 4), "flux": s * to_mjy,
           "err": math.sqrt(max(e2, 0)) * to_mjy, "flux_ap": s * to_mjy, "saturated": sat, "flagged": sat or rej,
           "flag_names": sorted(n for n, v in bits.items() if v and (flg_in & v)), "status": "ok", "method": "aperture",
           "n_neighbours": len(nb_xy)}
    close_nb_flux = None
    if nb_xy:
        out["nearest_neighbour_px"] = round(min(math.hypot(a - x, b - y) for a, b in nb_xy), 2)
    if epsf is not None:
        psf = epsf.get(det, detx, dety)
        if psf is not None:
            good = np.isfinite(img) & np.isfinite(var) & (var > 0) & ((flags & reject_val) == 0)
            fit = _forced_psf(img, var, good, psf, x, y, nb_xy)
            if fit is not None:
                f, e, amps = fit
                k = area_sr * 1e9                       # PSF model normalised to unit total flux: no aperture correction
                out.update({"flux": f * k, "err": e * k, "method": "psf"})
                close = [amps[i] for i, (a, b) in enumerate(nb_xy) if math.hypot(a - x, b - y) < BLEND_R]
                if close:
                    close_nb_flux = max(close) * k
                    out["close_neighbour_flux"] = close_nb_flux
    # Blend rule: a neighbour closer than 1.5 px (9.2") cannot be separated at 6.15" pixels; the fit leaks flux between the
    # two. Flag it when that neighbour is not negligible: fitted flux > 10 % of the target flux (or of its 3-sigma limit).
    if close_nb_flux is not None and close_nb_flux > 0.1 * max(abs(out["flux"]), 3 * out["err"]):
        out["flagged"] = True
        out["blended"] = True
        out["flag_names"] = out["flag_names"] + ["BLENDED(neighbour < 1.5 px, > 10 % of target)"]
    elif close_nb_flux is None and nb_xy and out["nearest_neighbour_px"] < BLEND_R:
        out["flagged"] = True                           # aperture fallback: cannot judge the neighbour's brightness
        out["blended"] = True
        out["flag_names"] = out["flag_names"] + ["BLENDED(neighbour < 1.5 px)"]
    return out


PSF_FIT_R = 4.0       # native px (24.6") fitting radius around the target
BLEND_R = 1.5         # native px (9.2"): a catalogue neighbour closer than this makes the point "blended" (flagged)


class EpsfLibrary:
    """Archive EPSF grids (from the raw cutouts, which keep the EPSF extension), one table per detector per field.
    get(det, detx, dety) returns the 33x33 (5x oversampled) EPSF of the zone nearest to that detector position."""

    def __init__(self, field: str):
        self.tables = {}
        root = config.RAW / "spherex" / field
        for det in range(1, 7):
            for f in sorted((root / f"D{det}").glob("*.fits"))[:1]:
                try:
                    with fits.open(f) as h:
                        t = h["EPSF"].data
                        self.tables[det] = (np.array(t["XCENTER"], float), np.array(t["YCENTER"], float),
                                            np.array([np.array(p, float).reshape(33, 33) for p in t["EPSF"]]))
                except Exception:
                    pass

    def get(self, det, detx, dety):
        if det not in self.tables:
            return None
        xc, yc, stamps = self.tables[det]
        return stamps[int(np.argmin((xc - detx) ** 2 + (yc - dety) ** 2))]


def _psf_image(psf, shape, x, y, over=5):
    """Sample an effective PSF (pixel-integrated, `over`x oversampled, centred on the stamp) at native pixel centres for a
    source at (x, y); normalised so that the native samples of a centred source sum to 1."""
    from scipy.ndimage import map_coordinates
    n = psf.shape[0]
    c = (n - 1) / 2
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    u = (xx - x) * over + c
    v = (yy - y) * over + c
    inside = (u >= 0) & (u <= n - 1) & (v >= 0) & (v <= n - 1)
    m = np.zeros(shape)
    m[inside] = map_coordinates(psf, [v[inside], u[inside]], order=1)
    g = np.arange(int(c) % over, n, over)
    return m / psf[np.ix_(g, g)].sum()


def _forced_psf(img, var, good, psf, x, y, nb_xy):
    """Weighted linear LSQ: img = a0*PSF(target) + sum a_i*PSF(neighbour_i) + const, within PSF_FIT_R of the target."""
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    reg = good & ((xx - x) ** 2 + (yy - y) ** 2 <= PSF_FIT_R ** 2)
    if reg.sum() < 15:
        return None
    cols = [_psf_image(psf, img.shape, x, y)[reg]]
    for (nx_, ny_) in nb_xy:
        cols.append(_psf_image(psf, img.shape, nx_, ny_)[reg])
    cols.append(np.ones(int(reg.sum())))
    A = np.array(cols).T
    wgt = 1 / np.sqrt(var[reg])
    Aw = A * wgt[:, None]
    try:
        p, *_ = np.linalg.lstsq(Aw, img[reg] * wgt, rcond=None)
        cov = np.linalg.pinv(Aw.T @ Aw)
    except np.linalg.LinAlgError:
        return None
    res = (img[reg] - A @ p) * wgt
    chi2 = float(np.sum(res ** 2) / max(int(reg.sum()) - len(p), 1))
    return float(p[0]), math.sqrt(max(cov[0, 0], 0) * max(chi2, 1.0)), [float(v) for v in p[1:-1]]


def field_files(field: str) -> list[Path]:
    root = config.SLIM / "spherex" / field
    return sorted(root.glob("D?/*.fits"))


def neighbours_for(field: str, ra: float, dec: float, pmra: float, pmdec: float, ref_year: float, radius=40.0, exclude=2.5,
                   mjd_ref=61000.0):
    """Gaia DR3 + CatWISE2020 sources within `radius` arcsec of the source during the SPHEREx era (both propagated to
    mjd_ref ~ 2025.8), excluding the source itself (matched at the catalogue's own epoch). CatWISE adds red objects that
    Gaia misses; CatWISE rows with a Gaia source within 3" are dropped (duplicates)."""
    out, gaia_pos = [], []
    sr, sd = _propagate(ra, dec, pmra, pmdec, ref_year, mjd_ref)
    cosd = math.cos(math.radians(sd))

    def sep(a1, d1, a2, d2):
        return math.hypot((a1 - a2) * cosd, d1 - d2) * 3600

    p = config.RAW / "catalogs" / f"{field}_gaia_dr3.csv"
    if p.exists():
        tr, td = _propagate(ra, dec, pmra, pmdec, ref_year, 57388.5)            # target at 2016.0 (Gaia epoch)
        with open(p, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                gra, gdec = float(r["ra"]), float(r["dec"])
                gpa, gpd = float(r["pmra"] or 0), float(r["pmdec"] or 0)
                if sep(gra, gdec, tr, td) <= exclude:
                    continue
                na, nd = _propagate(gra, gdec, gpa, gpd, 2016.0, mjd_ref)
                if sep(na, nd, sr, sd) > radius:
                    continue
                out.append((gra, gdec, gpa, gpd, 2016.0))
                gaia_pos.append((na, nd))
    p = config.RAW / "catalogs" / f"{field}_catwise2020.csv"
    if p.exists():
        cy = config.jyear(57170.0)
        tr2, td2 = _propagate(ra, dec, pmra, pmdec, ref_year, 57170.0)
        with open(p, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                cra, cdec = float(r["ra_pm"]), float(r["dec_pm"])
                cpa, cpd = float(r["pmra"]) * 1000, float(r["pmdec"]) * 1000
                if sep(cra, cdec, tr2, td2) <= exclude + 1.0:
                    continue
                na, nd = _propagate(cra, cdec, cpa, cpd, cy, mjd_ref)
                if sep(na, nd, sr, sd) > radius:
                    continue
                if any(sep(g[0], g[1], na, nd) < 3.0 for g in gaia_pos):
                    continue
                out.append((cra, cdec, cpa, cpd, cy))
    return out


def extract_spectrum(field: str, ra: float, dec: float, pmra: float = 0.0, pmdec: float = 0.0, ref_year: float = 2016.0,
                     files: list[Path] | None = None, deblend: bool = True) -> list[dict]:
    """Spectrum of any source in a cached field (e.g. for the API). pm in mas/yr (pmra includes cos dec), ref_year Julian.
    deblend=True: forced EPSF fit of the source + catalogue neighbours (needs raw files with EPSF); otherwise aperture."""
    nb = neighbours_for(field, ra, dec, pmra, pmdec, ref_year) if deblend else None
    lib = EpsfLibrary(field) if deblend else None
    if lib is not None and not lib.tables:
        lib = None
    return [measure_image(p, ra, dec, pmra, pmdec, ref_year, nb, lib) for p in (files or field_files(field))]


def bin_spectrum(points: list[dict], n_bins: int = 72, lo=0.74, hi=5.02) -> list[dict]:
    edges = np.geomspace(lo, hi, n_bins + 1)
    good = [p for p in points if p["status"] == "ok" and not p["flagged"] and p["err"] > 0]
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        sel = [p for p in good if a <= p["lambda_um"] < b]
        if not sel:
            continue
        f = np.array([p["flux"] for p in sel])
        e = np.array([p["err"] for p in sel])
        wgt = 1 / e ** 2
        mean = float(np.sum(wgt * f) / np.sum(wgt))
        err = float(1 / math.sqrt(np.sum(wgt)))
        if len(sel) >= 4:                                    # inflate by the scatter if it is larger than the formal error
            chi2 = float(np.sum(wgt * (f - mean) ** 2) / (len(sel) - 1))
            err *= math.sqrt(max(chi2, 1.0))
        out.append({"lambda_um": round(float(math.sqrt(a * b)), 4), "flux": round(mean, 4), "err": round(err, 4),
                    "n": len(sel), "snr": round(mean / err, 1) if err > 0 else None})
    return out


def band_snr(binned: list[dict], lo: float, hi: float) -> tuple[float, float, float]:
    """Weighted mean flux, error and S/N of the binned spectrum between lo and hi microns."""
    sel = [b for b in binned if lo <= b["lambda_um"] < hi]
    if not sel:
        return float("nan"), float("nan"), float("nan")
    f = np.array([b["flux"] for b in sel])
    e = np.array([b["err"] for b in sel])
    w = 1 / e ** 2
    m = float(np.sum(w * f) / np.sum(w))
    er = float(1 / math.sqrt(np.sum(w)))
    return m, er, m / er


def blackbody_mjy(lam_um, teff, scale=1.0):
    h, c, k = 6.62607015e-34, 2.99792458e8, 1.380649e-23
    lam = np.asarray(lam_um) * 1e-6
    nu = c / lam
    return scale * (2 * h * nu ** 3 / c ** 2) / np.expm1(h * nu / (k * teff))


# ------------------------------------------------------------------ per target
TARGET_TEFF = {  # literature-level effective temperatures, used ONLY to draw a comparison blackbody
    "wise0855": (250, "Y dwarf, ~250 K (Luhman 2014)"),
    "eps_indi_b": (1100, "T1+T6 brown-dwarf pair, ~1300 K + ~900 K"),
    "barnard": (3200, "M4 V star, ~3200 K"),
    "rw_aur": (4500, "young K-type star with a disk"),
    "r_dra": (2700, "Mira variable (M giant), ~2700 K"),
}


def target_motion(field: str) -> tuple[float, float, float, float, float]:
    t = config.load_targets()[field]
    return t["ra_j2000"], t["dec_j2000"], t["pmra_masyr"], t["pmdec_masyr"], 2000.0


def build(field: str) -> dict:
    ra, dec, pmra, pmdec, ref = target_motion(field)
    pts = extract_spectrum(field, ra, dec, pmra, pmdec, ref)
    binned = bin_spectrum(pts)
    n_tot = len(pts)
    n_ok = sum(1 for p in pts if p["status"] == "ok")
    n_good = sum(1 for p in pts if p["status"] == "ok" and not p["flagged"])
    n_sat = sum(1 for p in pts if p.get("saturated"))
    n_nan = sum(1 for p in pts if p["status"] == "nan_core")
    n_edge = sum(1 for p in pts if p["status"] == "edge")
    n_bl = sum(1 for p in pts if p.get("blended"))
    n_psf = sum(1 for p in pts if p.get("method") == "psf")
    n_sat_any = sum(1 for p in pts if p.get("saturated") or p["status"] == "nan_core")   # union, no double counting
    stats = {"images": n_tot, "measured": n_ok, "unflagged": n_good, "saturated": n_sat, "nan_core": n_nan, "edge": n_edge,
             "blended": n_bl, "psf_fit": n_psf, "saturated_or_empty_core": n_sat_any}
    return {"field": field, "points": pts, "binned": binned, "stats": stats}


def notes_for(field: str, res: dict) -> tuple[list[str], dict | None, list[str]]:
    """Plain, fact-based notes; a comparison curve (template block); warnings for flags.saturated."""
    st, b = res["stats"], res["binned"]
    notes, warn = [], []
    n_on = max(st["images"] - st["edge"], 1)
    sat_frac = st["saturated_or_empty_core"] / n_on
    lo_f, lo_e, lo_snr = band_snr(b, 0.74, 2.4)
    ch4_f, ch4_e, ch4_snr = band_snr(b, 3.2, 3.5)
    pk_f, pk_e, pk_snr = band_snr(b, 4.4, 4.9)
    template = None
    if sat_frac > 0.5:
        notes.append(f"{st['images']} SPHEREx images examined.")
        notes.append(f"Saturated in {st['saturated_or_empty_core']} of {n_on} images (OVERFLOW flag or empty core): "
                     "too bright for SPHEREx, so no spectrum of the star itself is shown.")
        warn.append("SPHEREx: saturated — spectrum not usable")
        return notes, None, warn
    notes.append(f"{st['images']} SPHEREx images; {st['unflagged']} clean measurements used (forced PSF fit of the target and its "
                 "catalogue neighbours on IMAGE − ZODI, position propagated to each image date).")
    if st.get("blended"):
        notes.append(f"{st['blended']} images were left out because a catalogue star was closer than 9\" to the moving target "
                     "(one SPHEREx pixel is 6.15\"; such blends cannot be separated).")
    if field == "wise0855":
        notes.append(f"Below 2.4 µm: {_fmt(lo_f, lo_e)} mJy (S/N {lo_snr:.1f}) — " +
                     ("not detected: invisible at short wavelengths." if lo_snr < 3 else "detected."))
        notes.append(f"4.4–4.9 µm: {_fmt(pk_f, pk_e)} mJy (S/N {pk_snr:.0f}) — detected where the coldest brown dwarfs emit most.")
        if ch4_snr == ch4_snr:
            notes.append(f"3.2–3.5 µm (methane band): {_fmt(ch4_f, ch4_e)} mJy" +
                         (" — not detected: methane absorbs this band." if ch4_snr < 3 else "."))
        notes.append("The flux rises steeply from 4 to 4.6 µm, as expected for an object of only ~250 K.")
    elif field == "eps_indi_b":
        w_f, w_e, _ = band_snr(b, 3.9, 4.2)
        notes.append(f"Peaks at 1.1–1.3, 1.6 and 2.1 µm (water absorption in between), a deep methane band at 3.2–3.5 µm "
                     f"({_fmt(ch4_f, ch4_e)} mJy) and the brightest window at 3.9–4.2 µm ({_fmt(w_f, w_e)} mJy).")
        if w_f > 0:
            notes.append(f"The methane band is at {ch4_f / w_f * 100:.0f} % of the 4 µm peak and the flux drops again at 4.4–4.9 µm "
                         f"({_fmt(pk_f, pk_e)} mJy; carbon monoxide): the classic shape of a T dwarf.")
        notes.append("Ba and Bb (0.7\" apart) are blended in SPHEREx's 6\" pixels: this is their combined spectrum.")
    if sat_frac > 0.05:
        notes.append(f"{st['saturated']} of {st['images']} images have OVERFLOW (saturation) in the aperture; those points are flagged.")
        warn.append(f"SPHEREx: partially saturated ({st['saturated']} images)")
    teff, why = TARGET_TEFF[field]
    lam = np.geomspace(0.75, 5.0, 120)
    bb = blackbody_mjy(lam, teff)
    ref_sel = [x for x in b if 4.4 <= x["lambda_um"] < 4.9] or b
    if ref_sel:
        k = np.mean([x["flux"] for x in ref_sel]) / np.mean(blackbody_mjy([x["lambda_um"] for x in ref_sel], teff))
        template = {"name": f"Blackbody {teff} K ({why}), scaled at 4.4–4.9 µm — for comparison only",
                    "lambda_um": [round(float(v), 4) for v in lam], "flux": [round(float(v), 5) for v in bb * k]}
        if field == "eps_indi_b":
            notes.append(f"A {teff} K blackbody (dashed) does not fit: molecules (water, methane, CO) carve deep bands into the spectrum.")
    return notes, template, warn


def _fmt(f, e):
    if f != f:
        return "n/a"
    return f"{f:.3f} ± {e:.3f}" if abs(f) < 1 else f"{f:.2f} ± {e:.2f}"


def spectrum_block(field: str, res: dict) -> tuple[dict, list[str]]:
    notes, template, warn = notes_for(field, res)
    pts = []
    for p in res["points"]:
        if p["status"] != "ok":
            continue
        pts.append({"lambda_um": p["lambda_um"], "flux": round(p["flux"], 4), "err": round(p["err"], 4), "mjd": round(p["mjd"], 4),
                    "detector": p["detector"], "flagged": bool(p["flagged"]), "saturated": bool(p["saturated"])})
    pts.sort(key=lambda q: q["lambda_um"])
    binned = res["binned"]
    usable = not any(w.startswith("SPHEREx: saturated") for w in warn)
    if not usable:                       # saturated star: publish no numbers (per-image table stays in spectrum_points.csv)
        pts, binned = [], []
    return {"unit_flux": "mJy", "usable": usable, "points": pts, "binned": binned, "template": template, "notes": notes,
            "stats": res["stats"],
            "method": "SPHEREx L2 cutouts, IMAGE−ZODI; forced EPSF fit of target + Gaia/CatWISE neighbours + constant within 4 px "
                      "(aperture r=2 px fallback), VARIANCE errors, blends < 1.5 px flagged, per-pixel wavelength from WCS-WAVE "
                      "(quick-look), moving position per image"}, warn


def plot(field: str, block: dict) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out = config.OUT_DIR / "png"
    out.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    good = [p for p in block["points"] if not p["flagged"]]
    bad = [p for p in block["points"] if p["flagged"]]
    if good:
        ax.errorbar([p["lambda_um"] for p in good], [p["flux"] for p in good], [p["err"] for p in good], fmt=".", ms=3,
                    color="#9ecae1", alpha=0.6, lw=0.5, label=f"single images ({len(good)})")
    if bad:
        ax.plot([p["lambda_um"] for p in bad], [p["flux"] for p in bad], "x", ms=3, color="#bbb", label=f"flagged ({len(bad)})")
    b = block["binned"]
    if b:
        ax.errorbar([x["lambda_um"] for x in b], [x["flux"] for x in b], [x["err"] for x in b], fmt="o", ms=4, color="#08519c",
                    label="binned (R≈40)")
    if block["template"]:
        ax.plot(block["template"]["lambda_um"], block["template"]["flux"], "--", color="#d7301f", lw=1,
                label=block["template"]["name"].split(" (")[0] + " (comparison)")
    for lo, hi, lab in ((3.2, 3.5, "CH₄"), (4.4, 4.9, "W2 / D6")):
        ax.axvspan(lo, hi, color="#eee", zorder=0)
        ax.text((lo + hi) / 2, 1.0, lab, transform=ax.get_xaxis_transform(), ha="center", va="top", fontsize=8, color="#666")
    if b:
        fl = [x["flux"] for x in b]
        top = max(fl) + 3 * max(x["err"] for x in b)
        ax.set_ylim(min(-0.1 * top, min(fl) - 0.1 * top), top * 1.15)
    ax.axhline(0, color="#999", lw=0.6)
    ax.set_xlabel("wavelength (µm)")
    ax.set_ylabel("flux density (mJy)")
    ax.set_title(f"{config.DISPLAY_NAMES[field]} — SPHEREx spectrum (102 bands, 0.75–5 µm)")
    if ax.get_legend_handles_labels()[0]:
        ax.legend(fontsize=8, loc="upper left")
    if not block["points"] or not good:
        import textwrap
        ax.set_yticks([])
        ax.set_xlim(0.7, 5.05)
        ax.text(0.5, 0.5, "\n".join(textwrap.wrap(block["notes"][-1], 60)), transform=ax.transAxes, ha="center", va="center",
                fontsize=12, color="#444")
    fig.tight_layout()
    p = out / f"{field}_spectrum.png"
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def run(fields: list[str] | None = None) -> None:
    from .validate import load_object, save_object
    for f in fields or config.ALL_TARGETS:
        res = build(f)
        block, warn = spectrum_block(f, res)
        obj = load_object(f)
        obj["spectrum"] = block
        flags = obj.get("flags") or {"saturated_in": [], "warnings": []}
        flags["warnings"] = [x for x in flags["warnings"] if not x.startswith("SPHEREx:")] + warn
        if any("saturated" in x for x in warn) and "SPHEREx" not in flags["saturated_in"]:
            flags["saturated_in"].append("SPHEREx")
        obj["flags"] = flags
        save_object(f, obj)
        png = plot(f, block)
        # full per-image table for reproducibility
        with open(config.OUT_DIR / f / "spectrum_points.csv", "w", newline="", encoding="utf-8") as fh:
            keys = ["file", "mjd", "detector", "x", "y", "lambda_um", "bandwidth_um", "flux", "err", "saturated", "flagged", "status", "flag_names", "method", "flux_ap", "nearest_neighbour_px", "close_neighbour_flux"]
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for p in res["points"]:
                w.writerow({k: (";".join(p[k]) if k == "flag_names" and k in p else p.get(k, "")) for k in keys})
        print(f"{f:11s} {res['stats']}  -> {png.name}")
        for n in block["notes"]:
            print("   -", n)


# ------------------------------------------------------------------ flux-scale check against CatWISE
def calibration_check(fields=("eps_indi_b", "wise0855", "rw_aur"), per_field=6) -> dict:
    """Isolated CatWISE stars (W1 9-13, no brighter-than-W1+3 source within 20", 40-200" from the target): median SPHEREx
    forced-PSF flux at 3.2-3.6 um (D4) / CatWISE W1 flux and at 4.4-4.8 um (D6) / W2 flux. Stars are Rayleigh-Jeans here,
    so a ratio ~1 means the absolute flux scale is right (W1/W2 zero points 309.54 / 171.79 Jy, Vega)."""
    rows_out = []
    for field in fields:
        t = config.load_targets()[field]
        with open(config.RAW / "catalogs" / f"{field}_catwise2020.csv", encoding="utf-8") as fh:
            cat = [(float(r["ra_pm"]), float(r["dec_pm"]), float(r["w1mpro"] or 99), float(r["w2mpro"] or 99),
                    float(r["pmra"]) * 1000, float(r["pmdec"]) * 1000, r["source_name"]) for r in csv.DictReader(fh)]
        sel = []
        for c in cat:
            if not 9.0 < c[2] < 13.0:
                continue
            cosd = math.cos(math.radians(c[1]))
            d = math.hypot((c[0] - t["ra_2018"]) * cosd, c[1] - t["dec_2018"]) * 3600
            if not 40 < d < 200:
                continue
            if all(o is c or o[2] >= c[2] + 3 or math.hypot((o[0] - c[0]) * cosd, o[1] - c[1]) * 3600 > 20 for o in cat):
                sel.append(c)
        sel = sel[:per_field]
        files, lib = field_files(field), EpsfLibrary(field)
        for c in sel:
            ref = config.jyear(57170.0)
            nb = neighbours_for(field, c[0], c[1], c[4], c[5], ref)
            pts = [measure_image(p, c[0], c[1], c[4], c[5], ref, nb, lib) for p in files]
            ok = [p for p in pts if p["status"] == "ok" and not p["flagged"] and p.get("method") == "psf"]

            def med(lo, hi):
                v = [p["flux"] for p in ok if lo <= p["lambda_um"] < hi]
                return float(np.median(v)) if v else float("nan")
            w1, w2 = 309.54e3 * 10 ** (-c[2] / 2.5), 171.79e3 * 10 ** (-c[3] / 2.5)
            rows_out.append({"field": field, "star": "CatWISE " + c[6], "w1": c[2], "w2": c[3],
                             "d4_over_w1": round(med(3.2, 3.6) / w1, 3), "d6_over_w2": round(med(4.4, 4.8) / w2, 3)})
    r1 = [r["d4_over_w1"] for r in rows_out if r["d4_over_w1"] == r["d4_over_w1"]]
    r2 = [r["d6_over_w2"] for r in rows_out if r["d6_over_w2"] == r["d6_over_w2"]]
    summary = {"n_stars": len(rows_out), "d4_over_w1_median": round(float(np.median(r1)), 3), "d4_over_w1_std": round(float(np.std(r1)), 3),
               "d6_over_w2_median": round(float(np.median(r2)), 3), "d6_over_w2_std": round(float(np.std(r2)), 3), "stars": rows_out}
    out = config.OUT_DIR / "validation" / "spectra_calibration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"{len(rows_out)} stars: D4/W1 = {summary['d4_over_w1_median']} ± {summary['d4_over_w1_std']}, "
          f"D6/W2 = {summary['d6_over_w2_median']} ± {summary['d6_over_w2_std']}")
    return summary
