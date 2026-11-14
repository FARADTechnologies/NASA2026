"""S4 — auto-discovery of moving sources across 14 years of WISE (W2, 4.6 um), with recall against known movers.

Method:
1. All unWISE epochs of a field share one pixel grid. Median-stack the FIRST year (2010) and the LAST year (2023-24) of W2
   epochs (single-year windows so that fast movers are not smeared; a 2010-2014 stack would smear Barnard's Star by 40").
2. Detect sources in both stacks (DAOStarFinder, 5 sigma above a sigma-clipped background).
3. Link: early/late detections within 1 px are stationary. Unmatched early x unmatched late pairs with 1.2 px < separation
   < 70 px and similar flux become trial tracks; each is VERIFIED in every individual epoch (centroid within 1.5 px of the
   linear prediction, S/N > 4). Tracks seen in >= 60 % of epochs are kept (greedy, one-to-one, best first).
4. Proper motion of each kept track: per-epoch centroids + the same weighted fit as S1 (astrometry.fit_motion: position,
   proper motion, parallax; bootstrap errors). Mover if mu / err >= 3.
5. Cross-match the 2018 position with Gaia DR3 and CatWISE2020 (propagated with their own proper motions, 3"):
   known = matched to a catalogue high-proper-motion source; artifact = within 45" of a saturated star, near the frame edge,
   or inconsistent motion; otherwise candidate (never 'discovery').
6. Recall: known movers in the field = Gaia DR3 / CatWISE2020 sources with mu > 300 mas/yr (CatWISE: mu > 5 sigma, nb = 1,
   clean ab_flags, |w2mpro - w2mpro_pm| < 0.5, parallax not negative at > 3 sigma, not within 60" of a star that saturates
   (Gaia G < 9 or W2 < 8) whose halo makes ghosts), inside the
   usable frame and bright enough to detect (Gaia G < 19 or CatWISE W2 < 15.5) + the NASA target; recovered = has a kept
   track within 3" whose proper motion agrees within 30 %.
"""
from __future__ import annotations

import csv
import json
import math
import warnings

import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS
from photutils.centroids import centroid_2dg
from photutils.detection import DAOStarFinder

from . import astrometry as A
from . import config

warnings.simplefilter("ignore", AstropyWarning)
warnings.simplefilter("ignore", RuntimeWarning)

MATCH_STATIC_PX = 1.0
MAX_MOVE_PX = 70            # 192" over 14 yr = 13.7"/yr
VERIFY_TOL_PX = 1.5
VERIFY_FRAC = 0.6
EDGE_PX = 12
BRIGHT_ZONE_ARCSEC = 45.0
KNOWN_PM_MIN = 300.0        # mas/yr
MIN_MOVER_PM = 150.0        # mas/yr: >= 2" over 14 yr, well above the per-epoch systematic floor
PX = 2.75


def load_cube(field: str, band: int = 2):
    wdir = config.RAW / "wise" / field
    rows = [r for r in csv.DictReader(open(wdir / "index.csv", encoding="utf-8")) if int(r["band"]) == band]
    imgs, mjds, wcs = [], [], None
    for r in rows:
        with fits.open(wdir / r["file"]) as h:
            imgs.append(h[0].data.astype(float))
            wcs = wcs or WCS(h[0].header)
        mjds.append(0.5 * (float(r["MJDMIN"]) + float(r["MJDMAX"])))
    return np.array(imgs), np.array(mjds), wcs


def detect(img: np.ndarray, nsigma=5.0):
    _, med, std = sigma_clipped_stats(img, sigma=3.0, maxiters=5)
    finder = DAOStarFinder(fwhm=2.4, threshold=nsigma * std, exclude_border=True)
    tab = finder(img - med)
    if tab is None:
        return np.zeros((0, 3)), std
    cols = tab.colnames
    xs = tab["x_centroid" if "x_centroid" in cols else "xcentroid"]
    ys = tab["y_centroid" if "y_centroid" in cols else "ycentroid"]
    det = np.array([xs, ys, tab["flux"]], dtype=float).T
    return _refine_saturated(img, det), std


def _refine_saturated(img, det):
    """Saturated stars appear as a ring of peaks around a zero hole. Each hole (15-400 zero pixels, not touching the frame
    edge = not a coverage gap) becomes ONE detection at the S1 wing-fit centre with flux = -1 (saturated: flux unknown);
    ring peaks around it are dropped."""
    from scipy.ndimage import label
    out = []
    lab, n = label(img == 0)
    for k in range(1, n + 1):
        yy, xx = np.nonzero(lab == k)
        if not (15 <= xx.size <= 400) or xx.min() == 0 or yy.min() == 0 or xx.max() == img.shape[1] - 1 or yy.max() == img.shape[0] - 1:
            continue
        r = A._wing_fit(img, float(xx.mean()), float(yy.mean()))
        x, y = (r[0], r[1]) if isinstance(r, tuple) else (float(xx.mean()), float(yy.mean()))
        out.append((x, y, -1.0))
    for x, y, f in det:
        ix, iy = int(round(x)), int(round(y))
        sub = img[max(iy - 4, 0): iy + 5, max(ix - 4, 0): ix + 5]
        if (sub == 0).sum() >= 3:
            continue                           # ring peak of a saturated star (already represented by its hole)
        if any(math.hypot(x - a, y - b) < (6.0 if g < 0 else 2.0) for a, b, g in out):
            continue
        out.append((x, y, f))
    return np.array(out) if out else np.zeros((0, 3))


def detect_window(cube, sel_stack, k_single, t_stack, t_single):
    """Union of detections in a 1-year median stack and in one single epoch (fast movers smear in the stack).
    Rows: x, y, flux (-1 = saturated), time (Julian year of the image the position comes from)."""
    d1, s1 = detect(np.median(cube[sel_stack], axis=0))
    d2, _ = detect(cube[k_single])
    out = [(r[0], r[1], r[2], t_stack) for r in d1]
    for r in d2:
        if not any(math.hypot(r[0] - a[0], r[1] - a[1]) < 2.0 for a in out):
            out.append((r[0], r[1], r[2], t_single))
    return (np.array(out) if out else np.zeros((0, 4))), s1


def centroid_at(img, x, y, half=3):
    ix, iy = int(round(x)), int(round(y))
    if ix - half - 4 < 0 or iy - half - 4 < 0 or ix + half + 4 >= img.shape[1] or iy + half + 4 >= img.shape[0]:
        return None
    big = img[iy - half - 4: iy + half + 5, ix - half - 4: ix + half + 5]
    _, bkg, rms = sigma_clipped_stats(big, sigma=3.0, maxiters=3)
    raw = img[iy - half: iy + half + 1, ix - half: ix + half + 1]
    if (raw == 0).sum() >= 3:                                       # saturated core: wing fit (as in S1)
        r = A._wing_fit(img, x, y)
        return (r[0], r[1], 1000.0) if isinstance(r, tuple) else None
    if np.nanmax(raw) > A.FLAT_CORE_LEVEL:                           # flat saturated core without a hole: S1 centroid
        r = A._centroid_one(img, x, y, None)
        return (r[0], r[1], max(r[2], 100.0)) if r else None
    box = raw - bkg
    if not np.isfinite(box).all():
        return None
    try:
        cx, cy = centroid_2dg(box)
    except Exception:
        return None
    if not (np.isfinite(cx) and np.isfinite(cy)):
        return None
    yy, xx = np.mgrid[0:box.shape[0], 0:box.shape[1]]
    ap = (xx - cx) ** 2 + (yy - cy) ** 2 <= 4
    snr = float(box[ap].sum() / (rms * math.sqrt(ap.sum()))) if rms > 0 else 0.0
    return ix - half + cx, iy - half + cy, snr


def _catalogs(field):
    gaia, cw = [], []
    with open(config.RAW / "catalogs" / f"{field}_gaia_dr3.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            gaia.append({"id": r["source_id"], "ra": float(r["ra"]), "dec": float(r["dec"]), "pmra": float(r["pmra"] or 0),
                         "pmdec": float(r["pmdec"] or 0), "epoch": 2016.0, "g": float(r["phot_g_mean_mag"] or 99),
                         "pm_sig": 99.0 if r["pmra"] else 0.0})
    with open(config.RAW / "catalogs" / f"{field}_catwise2020.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pmra, pmdec = float(r["pmra"]) * 1000, float(r["pmdec"]) * 1000
            s = math.hypot(float(r["sigpmra"]) * 1000, float(r["sigpmdec"]) * 1000)
            cw.append({"id": r["source_name"], "ra": float(r["ra_pm"]), "dec": float(r["dec_pm"]), "pmra": pmra, "pmdec": pmdec,
                       "epoch": config.jyear(57170.0), "w2": float(r["w2mpro"] or 99), "nb": int(r["nb"] or 9),
                       "ab_clean": (r["ab_flags"] or "00").strip("0") == "",
                       "phot_ok": abs(float(r["w2mpro"] or 99) - float(r["w2mpro_pm"] or 0)) < 0.5,
                       "par_ok": float(r["par_pm"] or 0) > -3 * float(r["par_pmsig"] or 1e9),   # negative parallax = bad astrometry
                       "pm_sig": math.hypot(pmra, pmdec) / s if s > 0 else 0.0})
    return gaia, cw


def _at(src, year):
    dt = year - src["epoch"]
    dec = src["dec"] + src["pmdec"] * dt / 3.6e6
    ra = src["ra"] + src["pmra"] * dt / (3.6e6 * math.cos(math.radians(src["dec"])))
    return ra, dec


def _sep(a1, d1, a2, d2):
    return math.hypot((a1 - a2) * math.cos(math.radians(d2)), d1 - d2) * 3600


def find_tracks(field):
    cube, mjds, wcs = load_cube(field, 2)
    years = np.array([config.jyear(m) for m in mjds])
    early_sel = years < years.min() + 1.0
    late_sel = years > years.max() - 1.0
    k0, k1 = int(np.argmin(years)), int(np.argmax(years))
    E, std_e = detect_window(cube, early_sel, k0, years[early_sel].mean(), years[k0])
    L, std_l = detect_window(cube, late_sel, k1, years[late_sel].mean(), years[k1])
    te, tl = years[early_sel].mean(), years[late_sel].mean()
    ny, nx = cube.shape[1:]
    # stationary matches
    used_e, used_l, static = set(), set(), []
    for j, (xl, yl, fl, _) in enumerate(L):
        d = np.hypot(E[:, 0] - xl, E[:, 1] - yl) if len(E) else np.array([])
        if d.size and d.min() < MATCH_STATIC_PX:
            i = int(np.argmin(d))
            used_e.add(i)
            used_l.add(j)
            static.append((i, j))
    eu = [i for i in range(len(E)) if i not in used_e]
    lu = [j for j in range(len(L)) if j not in used_l]
    trials = []
    for i in eu:
        for j in lu:
            sep = math.hypot(L[j, 0] - E[i, 0], L[j, 1] - E[i, 1])
            if not (1.2 < sep < MAX_MOVE_PX):
                continue
            if E[i, 2] > 0 and L[j, 2] > 0 and not (0.33 < L[j, 2] / E[i, 2] < 3.0):   # skip test if saturated
                continue
            trials.append((i, j))
    verified = []
    for i, j in trials:
        dt = L[j, 3] - E[i, 3]
        vx = (L[j, 0] - E[i, 0]) / dt
        vy = (L[j, 1] - E[i, 1]) / dt
        hits, pts = 0, []
        for k in range(len(mjds)):
            px, py = E[i, 0] + vx * (years[k] - E[i, 3]), E[i, 1] + vy * (years[k] - E[i, 3])
            c = centroid_at(cube[k], px, py)
            if c and math.hypot(c[0] - px, c[1] - py) < VERIFY_TOL_PX and c[2] > 4:
                hits += 1
                pts.append((k, c))
        frac = hits / len(mjds)
        if frac >= VERIFY_FRAC:
            verified.append({"i": i, "j": j, "frac": frac, "pts": pts})
    verified.sort(key=lambda t: -t["frac"])
    taken_e, taken_l, tracks = set(), set(), []
    for t in verified:
        if t["i"] in taken_e or t["j"] in taken_l:
            continue
        taken_e.add(t["i"])
        taken_l.add(t["j"])
        tracks.append(t)
    return {"cube": cube, "mjds": mjds, "years": years, "wcs": wcs, "E": E, "L": L, "static": static, "tracks": tracks,
            "n_trials": len(trials), "te": te, "tl": tl, "shape": (ny, nx)}


def fit_track(track, mjds, wcs):
    eps = []
    for k, (x, y, snr) in track["pts"]:
        ra, dec = wcs.pixel_to_world_values(x, y)
        sig = math.hypot(2.7 * 2.75 / (2.355 * max(snr, 1)), A.SYS_FLOOR)
        eps.append(A.Epoch(2, k, float(mjds[k]), float(ra), float(dec), x, y, snr, sig, False))
    mid = eps[len(eps) // 2]
    fit = A.fit_motion(eps, mid.ra, mid.dec, fit_plx=True, n_boot=300)
    pm = math.hypot(fit["pmra"], fit["pmdec"])
    err = float(np.std(fit["boot_pmtot"]))
    res = {"target": "track", "epochs": eps, "fit": fit, "ra0": mid.ra, "dec0": mid.dec}
    ra18, dec18 = A.model_position(res, 58119.0)                      # 2018.0
    return {"ra": ra18, "dec": dec18, "pmra": fit["pmra"], "pmdec": fit["pmdec"], "pm": pm, "err": err,
            "n_epochs": fit["n_epochs"], "rms": fit["rms_arcsec"]}


def halo_centres(field, gaia, cw):
    """Stars bright enough to saturate in WISE: Gaia G < 9, CatWISE W2 < 8, and the NASA target itself."""
    t = config.load_targets()[field]
    tr, td = A.propagate(t, 58119.0)
    out = [g for g in gaia if g["g"] < 9.0] + [c for c in cw if c["w2"] < 8.0]
    out.append({"ra": tr, "dec": td, "pmra": 0.0, "pmdec": 0.0, "epoch": 2018.0})
    return out


def known_movers(field, wcs, shape, gaia, cw):
    """Catalogue high-proper-motion sources usable for recall. CatWISE entries inside the halo (60") of a saturated star
    (Gaia G < 9) are ghosts of that star's wings and are excluded (the star itself is kept)."""
    ny, nx = shape
    out = []
    bright = halo_centres(field, gaia, cw)
    for src, cat in [(g, "gaia") for g in gaia] + [(c, "catwise") for c in cw]:
        pm = math.hypot(src["pmra"], src["pmdec"])
        if pm < KNOWN_PM_MIN:
            continue
        # CatWISE reliability: >5 sigma motion, single component, no artifact flag, consistent static vs motion photometry
        if cat == "catwise" and (src["pm_sig"] < 5 or src["w2"] > 15.5 or src["nb"] != 1 or not src["ab_clean"]
                                 or not src["phot_ok"] or not src["par_ok"]):
            continue
        if cat == "gaia" and src["g"] > 19:
            continue
        ra, dec = _at(src, 2018.0)
        x, y = wcs.world_to_pixel_values(ra, dec)
        if not (EDGE_PX < x < nx - EDGE_PX and EDGE_PX < y < ny - EDGE_PX):
            continue
        if cat == "catwise" and any(_sep(ra, dec, *_at(b, 2018.0)) < 60 for b in bright) and                 not any(_sep(ra, dec, *_at(b, 2018.0)) < 3 for b in bright):
            continue
        if any(_sep(ra, dec, *_at(o[0], 2018.0)) < 3 for o in out):     # same object in both catalogues
            continue
        out.append((src, cat, pm))
    t = config.load_targets()[field]
    tr, td = A.propagate(t, 58119.0)
    if math.hypot(t["pmra_masyr"], t["pmdec_masyr"]) >= KNOWN_PM_MIN and not any(_sep(tr, td, *_at(o[0], 2018.0)) < 5 for o in out):
        out.append(({"id": "NASA target " + field, "ra": tr, "dec": td, "pmra": t["pmra_masyr"], "pmdec": t["pmdec_masyr"],
                     "epoch": 2018.0}, "simbad", math.hypot(t["pmra_masyr"], t["pmdec_masyr"])))
    return out


def run_field(field):
    T = find_tracks(field)
    wcs, shape = T["wcs"], T["shape"]
    gaia, cw = _catalogs(field)
    zones = []
    for g in halo_centres(field, gaia, cw):
        x, y = wcs.world_to_pixel_values(*_at(g, 2018.0))
        zones.append((float(x), float(y)))
    items = []
    for n, t in enumerate(T["tracks"]):
        f = fit_track(t, T["mjds"], wcs)
        x, y = (float(v) for v in wcs.world_to_pixel_values(f["ra"], f["dec"]))
        signif = f["pm"] / f["err"] if f["err"] > 0 else 0.0
        gm = min(gaia, key=lambda g: _sep(f["ra"], f["dec"], *_at(g, 2018.0)), default=None)
        cm = min(cw, key=lambda c: _sep(f["ra"], f["dec"], *_at(c, 2018.0)), default=None)
        g_ok = gm if gm and _sep(f["ra"], f["dec"], *_at(gm, 2018.0)) < 3 else None
        c_ok = cm if cm and _sep(f["ra"], f["dec"], *_at(cm, 2018.0)) < 3 else None
        near_bright = any(math.hypot(x - zx, y - zy) * PX < BRIGHT_ZONE_ARCSEC for zx, zy in zones)
        near_edge = not (EDGE_PX < x < shape[1] - EDGE_PX and EDGE_PX < y < shape[0] - EDGE_PX)
        t_ = config.load_targets()[field]
        is_target = _sep(f["ra"], f["dec"], *A.propagate(t_, 58119.0)) < 5
        if signif < 3 or f["pm"] < MIN_MOVER_PM:
            continue
        # a catalogue match counts only if its motion agrees (within 30 % or 3 sigma)
        cat_pm, cat_disagree = None, False
        for m in (g_ok, c_ok):
            if m:
                cpm = math.hypot(m["pmra"], m["pmdec"])
                if abs(cpm - f["pm"]) < max(0.3 * cpm, 3 * f["err"]):
                    cat_pm = cpm
                    break
                cat_disagree = True
        if is_target and near_bright:
            near_bright = False                 # the saturated target is its own "bright star"
        if is_target or cat_pm:
            cls = "known"
        elif near_bright or near_edge or f["rms"] > 1.0 or cat_disagree:
            cls = "artifact"
        else:
            cls = "candidate"
        reasons = [r for r, c in (("near a saturated star", near_bright), ("near frame edge", near_edge),
                                  ("poor track fit", f["rms"] > 1.0),
                                  ("catalogue star at this position does not move like this", cat_disagree and not cat_pm)) if c]
        items.append({"id": f"c{len(items) + 1:03d}", "ra": round(f["ra"], 6), "dec": round(f["dec"], 6), "epoch": 2018.0,
                      "pm_total": round(f["pm"], 1), "err": round(f["err"], 1), "pmra": round(f["pmra"], 1),
                      "pmdec": round(f["pmdec"], 1), "significance_sigma": round(signif, 1), "class": cls,
                      "kind": "mover", "is_nasa_target": is_target,
                      "match": {"gaia": g_ok["id"] if g_ok else None, "catwise": c_ok["id"] if c_ok else None},
                      "catalog_pm": round(cat_pm, 1) if cat_pm else None,
                      "score": round(t["frac"], 2), "n_epochs": f["n_epochs"], "track_rms_arcsec": round(f["rms"], 2),
                      "notes": reasons, "object_file": "objects/target.json" if is_target else None})
    km = known_movers(field, wcs, shape, gaia, cw)
    recovered, rec_list = 0, []
    for src, cat, pm in km:
        ra, dec = _at(src, 2018.0)
        hit = next((it for it in items if _sep(it["ra"], it["dec"], ra, dec) < 3 and abs(it["pm_total"] - pm) < 0.3 * pm), None)
        recovered += hit is not None
        rec_list.append({"catalog": cat, "id": src["id"], "pm_catalog": round(pm, 1), "recovered": hit is not None,
                         "pm_measured": hit["pm_total"] if hit else None, "item": hit["id"] if hit else None})
    raw, conf = 0, 0
    for c in cw:                                   # transparency: how noisy is the raw CatWISE high-motion list here?
        pmc = math.hypot(c["pmra"], c["pmdec"])
        if pmc < KNOWN_PM_MIN:
            continue
        cx, cy = wcs.world_to_pixel_values(*_at(c, 2018.0))
        if not (EDGE_PX < cx < shape[1] - EDGE_PX and EDGE_PX < cy < shape[0] - EDGE_PX):
            continue
        raw += 1
        conf += any(_sep(c["ra"], c["dec"], *_at(g, c["epoch"])) < 3 and abs(math.hypot(g["pmra"], g["pmdec"]) - pmc) < 0.3 * pmc
                    for g in gaia)
    stats = {"known_movers_in_field": len(km), "recovered": recovered,
             "catwise_raw_high_pm_in_frame": raw, "catwise_raw_high_pm_confirmed_by_gaia": conf,
             "new_candidates": sum(1 for it in items if it["class"] == "candidate"),
             "artifacts": sum(1 for it in items if it["class"] == "artifact"),
             "sources_early": int(len(T["E"])), "sources_late": int(len(T["L"])), "stationary": len(T["static"]),
             "trial_tracks": T["n_trials"], "verified_tracks": len(T["tracks"])}
    out = {"method": "WISE W2 2010 vs 2023-24 stacks, detection 5 sigma, epoch-by-epoch track verification (>= 60 % of 23 "
                     "epochs), proper-motion fit, >= 3 sigma movers, Gaia DR3 + CatWISE2020 cross-match",
           "stats": stats, "known_movers": rec_list, "items": items,
           "caveat": "A 'candidate' is an unconfirmed moving source that is not in Gaia DR3 or CatWISE2020 with a matching motion. "
                     "It needs follow-up; it is not a discovery."}
    p = config.OUT_DIR / field / "candidates.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def run(fields=None):
    for f in fields or config.MOVERS:
        out = run_field(f)
        s = out["stats"]
        print(f"{f}: known movers {s['known_movers_in_field']}, recovered {s['recovered']}, candidates {s['new_candidates']}, "
              f"artifacts {s['artifacts']} | sources {s['sources_early']}/{s['sources_late']}, trials {s['trial_tracks']}, "
              f"verified {s['verified_tracks']}")
        for k in out["known_movers"]:
            print("   known:", k)
        for it in out["items"]:
            print("   item:", it["id"], it["class"], it["pm_total"], "+-", it["err"], it["match"], it["notes"])
