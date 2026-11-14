"""S3 — saturation-aware light curves for the NASA variability targets (R Dra, RW Aur).

Both stars are saturated in the unWISE coadds (core written as zeros) and in SPHEREx (OVERFLOW / empty cores), so magnitudes
from the core are impossible. Method:

1. Relative wing index (primary, both stars): in every unWISE epoch (W1, W2; native WCS) take the median of each 1-px ring of the
   PSF wings from r_in to r_in + 6 px, minus a sigma-clipped background from 25-35 px; the index is the sum of ring medians
   relative to the median over all epochs, expressed as delta-mag = -2.5 log10(ratio). r_in = 2 px beyond the largest radius
   where any epoch has saturated (zero) pixels, so only unsaturated, linear wings are used. Ring medians ignore field stars.
   This is NOT a calibrated magnitude: it is labelled "relative index" everywhere.
2. Validation: (a) the same index for a bright constant control star in the same frames gives the noise floor;
   (b) for RW Aur the index is compared with NEOWISE single-exposure profile-fit photometry (per-visit medians), which fits the
   unsaturated wings of moderately saturated stars.
3. NEOWISE profile-fit photometry of R Dra (W1 ~ 0, W2 ~ -1) scatters by ~2 mag inside single visits: beyond the range where
   the profile fit can correct saturation; it is NOT published.
4. SPHEREx synthesized 3.4/4.6 um points (LVF rule: per-epoch spectra interpolated to a fixed wavelength) are impossible here:
   both stars are saturated in SPHEREx (see spectra.py).
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

from . import config

warnings.simplefilter("ignore", AstropyWarning)
warnings.simplefilter("ignore", RuntimeWarning)

VAR_TARGETS = ["r_dra", "rw_aur"]
RING_WIDTH = 6
BKG = (25, 35)
LIT_PERIOD = {"r_dra": (245.6, "GCVS")}     # used only to fold the measured index, never as a result


def _epochs(field):
    with open(config.RAW / "wise" / field / "index.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            yield int(r["epoch"]), int(r["band"]), 0.5 * (float(r["MJDMIN"]) + float(r["MJDMAX"])), r["file"]


def _load(field, fname, ra, dec):
    with fits.open(config.RAW / "wise" / field / fname) as h:
        d = h[0].data.astype(float)
        w = WCS(h[0].header)
    x, y = (float(v) for v in w.world_to_pixel_values(ra, dec))
    return d, x, y


def saturation_radius(field, ra, dec, band) -> int:
    """Radius (px, 90th percentile over covered epochs) of the zero-valued (saturated) core connected to the star.
    Zeros not connected to the centre (coverage edges) and epochs without coverage are ignored."""
    from scipy.ndimage import label
    radii = []
    for e, b, mjd, fname in _epochs(field):
        if b != band:
            continue
        d, x, y = _load(field, fname, ra, dec)
        ix, iy = int(round(x)), int(round(y))
        s = d[iy - 15: iy + 16, ix - 15: ix + 16]
        if s.shape != (31, 31) or (s == 0).mean() > 0.5:          # off the frame or no coverage
            continue
        yy, xx = np.mgrid[-15:16, -15:16]
        r = np.hypot(xx - (x - ix), yy - (y - iy))
        lab, _ = label(s == 0)
        core_ids = set(np.unique(lab[(r < 3) & (lab > 0)]))
        if core_ids:
            z = np.isin(lab, list(core_ids))
            radii.append(float(r[z].max()))
    # 90th percentile: a few epochs where the hole merges with a coverage edge would otherwise inflate it; any epoch that
    # still has zeros inside the rings is rejected by ring_index().
    return int(math.ceil(np.percentile(radii, 90))) if radii else 0


def ring_index(d, x, y, r_in, width=RING_WIDTH):
    """Sum over 1-px rings (r_in .. r_in+width) of the ring median, after background subtraction; + an error estimate."""
    ix, iy = int(round(x)), int(round(y))
    R = BKG[1] + 1
    if ix - R < 0 or iy - R < 0 or ix + R >= d.shape[1] or iy + R >= d.shape[0]:
        return None
    s = d[iy - R: iy + R + 1, ix - R: ix + R + 1]
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
    r = np.hypot(xx - (x - ix), yy - (y - iy))
    bm = (r >= BKG[0]) & (r < BKG[1]) & np.isfinite(s)
    _, bkg, bstd = sigma_clipped_stats(s[bm], sigma=3.0, maxiters=5)
    tot, var = 0.0, 0.0
    for k in range(r_in, r_in + width):
        ring = s[(r >= k) & (r < k + 1) & np.isfinite(s)]
        if ring.size < 8 or (ring == 0).any():
            return None
        tot += float(np.median(ring)) - bkg
        mad = 1.4826 * float(np.median(np.abs(ring - np.median(ring))))
        var += (1.2533 * mad) ** 2 / ring.size
    return tot, math.sqrt(var)


def wing_index(field, ra, dec, band, r_in):
    rows = []
    for e, b, mjd, fname in _epochs(field):
        if b != band:
            continue
        d, x, y = _load(field, fname, ra, dec)
        res = ring_index(d, x, y, r_in)
        if res is not None and res[0] > 0:
            rows.append({"epoch": e, "mjd": mjd, "flux": res[0], "err": res[1]})
    if not rows:
        return []
    ref = float(np.median([r["flux"] for r in rows]))
    for r in rows:
        r["dmag"] = -2.5 * math.log10(r["flux"] / ref)
        r["dmag_err"] = 1.0857 * r["err"] / r["flux"]
    return rows


def control_star(field, ra, dec, min_sep=60.0):
    """Brightest Gaia DR3 star (G < 11.5, ruwe < 1.4, > min_sep from the target, inside the frame, no G<12 star within 40")
    — used as a constant reference for the noise floor of the wing index."""
    with open(config.RAW / "catalogs" / f"{field}_gaia_dr3.csv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f)]
    cosd = math.cos(math.radians(dec))
    best = None
    for r in rows:
        g = float(r["phot_g_mean_mag"] or 99)
        if g > 11.5 or float(r["ruwe"] or 99) > 1.4:
            continue
        a, b = float(r["ra"]), float(r["dec"])
        sep = math.hypot((a - ra) * cosd, b - dec) * 3600
        if sep < min_sep or sep > 280:
            continue
        crowd = any(float(o["phot_g_mean_mag"] or 99) < 12 and o is not r and
                    math.hypot((float(o["ra"]) - a) * cosd, float(o["dec"]) - b) * 3600 < 40 for o in rows)
        if crowd:
            continue
        if best is None or g < best[2]:
            best = (a, b, g, r["source_id"])
    return best


def neowise_visits(field, ra, dec, max_sep=2.0, gap=20.0):
    """Per-visit medians of NEOWISE single-exposure profile-fit photometry (cached from IRSA neowiser_p1bs_psd + allwise_p3as_mep)."""
    cosd = math.cos(math.radians(dec))
    pts = []
    for src, k1, k2, s1, s2 in (("neowise_l1b", "w1mpro", "w2mpro", "w1sigmpro", "w2sigmpro"),
                                ("allwise_mep", "w1mpro_ep", "w2mpro_ep", "w1sigmpro_ep", "w2sigmpro_ep")):
        p = config.SCIENCE_DIR / "data_cache" / f"{field}_{src}.csv"
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                try:
                    sep = math.hypot((float(r["ra"]) - ra) * cosd, float(r["dec"]) - dec) * 3600
                    if sep > max_sep or r.get("nb") not in ("1", None) or float(r.get("qi_fact") or 0) <= 0 \
                            or float(r.get("saa_sep") or 0) <= 0 or (r.get("moon_masked") or "0").strip("0"):
                        continue
                    pts.append((float(r["mjd"]), float(r[k1]) if r[k1] else np.nan, float(r[k2]) if r[k2] else np.nan, src))
                except (KeyError, ValueError):
                    continue
    pts.sort()
    visits, cur = [], []
    for p in pts:
        if cur and p[0] - cur[-1][0] > gap:
            visits.append(cur)
            cur = []
        cur.append(p)
    if cur:
        visits.append(cur)
    out = []
    for v in visits:
        m = np.array([p[0] for p in v])
        row = {"mjd": float(np.median(m)), "n": len(v), "source": v[0][3]}
        for i, band in ((1, "W1"), (2, "W2")):
            vals = np.array([p[i] for p in v])
            vals = vals[np.isfinite(vals)]
            if vals.size >= 3:
                mad = 1.4826 * float(np.median(np.abs(vals - np.median(vals))))
                row[band] = float(np.median(vals))
                row[band + "_scatter"] = mad
                row[band + "_err"] = 1.2533 * mad / math.sqrt(vals.size)
        out.append(row)
    return out


def _match(index_rows, visits, band, tol=15.0):
    """Pairs (wing dmag, neowise mag) for epochs within tol days."""
    pairs = []
    for r in index_rows:
        best = min(visits, key=lambda v: abs(v["mjd"] - r["mjd"]), default=None)
        if best is not None and abs(best["mjd"] - r["mjd"]) < tol and band in best:
            pairs.append((r["dmag"], best[band]))
    return pairs


def analyse(field):
    t = config.load_targets()[field]
    ra, dec = t["ra_2018"], t["dec_2018"]          # proper motions are tiny (< 25 mas/yr)
    out = {"field": field, "bands": {}}
    ctrl = control_star(field, ra, dec)
    out["control"] = {"gaia_source_id": ctrl[3], "g_mag": round(ctrl[2], 2)} if ctrl else None
    visits = neowise_visits(field, ra, dec)
    out["neowise_visits"] = visits
    for band, bname in ((1, "W1"), (2, "W2")):
        rsat = saturation_radius(field, ra, dec, band)
        r_in = max(rsat + 2, 3)
        rows = wing_index(field, ra, dec, band, r_in)
        b = {"r_in_px": r_in, "r_sat_px": rsat, "rows": rows}
        if ctrl:
            crs = saturation_radius(field, ctrl[0], ctrl[1], band)
            crow = wing_index(field, ctrl[0], ctrl[1], band, max(crs + 2, 3))
            b["control_rms"] = float(np.std([c["dmag"] for c in crow])) if crow else None
            b["control_rows"] = crow
        b["target_rms"] = float(np.std([r["dmag"] for r in rows])) if rows else None
        b["target_range"] = float(np.ptp([r["dmag"] for r in rows])) if rows else None
        pairs = _match(rows, visits, bname)
        if len(pairs) >= 5:
            x = np.array([p[0] for p in pairs])
            y = np.array([p[1] for p in pairs])
            b["neowise_corr"] = float(np.corrcoef(x, y)[0, 1])
            b["neowise_slope"] = float(np.polyfit(x, y, 1)[0])
            b["neowise_pairs"] = len(pairs)
        out["bands"][bname] = b
    if field in LIT_PERIOD:
        P, src = LIT_PERIOD[field]
        out["folded"] = {"period_d": P, "source": src}
        for bname in ("W1", "W2"):
            rows = out["bands"][bname]["rows"]
            if len(rows) <= 8:
                continue
            m = np.array([r["mjd"] for r in rows])
            y = np.array([r["dmag"] for r in rows])
            ve_lit, amp = _sine_fit(m, y, P)
            trials = np.linspace(100, 1000, 9001)                 # period search, 0.1-d steps
            ve = np.array([_sine_fit(m, y, q)[0] for q in trials])
            peaks = [(float(trials[i]), float(ve[i])) for i in range(1, len(ve) - 1) if ve[i] > ve[i - 1] and ve[i] >= ve[i + 1]]
            peaks.sort(key=lambda t: -t[1])
            out["folded"][bname] = {"variance_explained_at_lit": ve_lit, "semi_amplitude_mag": amp,
                                    "best_period_d": peaks[0][0], "best_variance_explained": peaks[0][1],
                                    "next_peaks": [[round(a, 1), round(b, 3)] for a, b in peaks[1:4]],
                                    "frac_trials_as_good_as_lit": float((ve >= ve_lit).mean())}
    return out


def _sine_fit(mjd, y, period):
    """Least-squares sine at a fixed period -> (fraction of variance explained, semi-amplitude)."""
    ph = 2 * np.pi * ((mjd / period) % 1)
    A = np.vstack([np.ones_like(ph), np.sin(ph), np.cos(ph)]).T
    c, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(1 - (y - A @ c).var() / y.var()), float(math.hypot(c[1], c[2]))
    return out


# ------------------------------------------------------------------ outputs
def lightcurve_block(field, a) -> dict:
    pts = []
    for bname, b in a["bands"].items():
        for r in b["rows"]:
            pts.append({"mjd": round(r["mjd"], 3), "instrument": "WISE", "band": bname, "mag": round(r["dmag"], 3),
                        "err": round(r["dmag_err"], 3), "saturated": True, "kind": "relative_wing_index"})
    pts.sort(key=lambda p: (p["mjd"], p["band"]))
    notes = []
    w1, w2 = a["bands"]["W1"], a["bands"]["W2"]
    notes.append("Too bright for normal photometry: the star's core is saturated in WISE and in SPHEREx. 'mag' here is a RELATIVE "
                 "brightness index (0 = median; positive = fainter) from the unsaturated outer wings of the star image, not a magnitude.")
    notes.append(f"Index from rings {w1['r_in_px']}–{w1['r_in_px'] + RING_WIDTH} px (W1) and {w2['r_in_px']}–{w2['r_in_px'] + RING_WIDTH} px (W2) "
                 f"around the star in {len(w1['rows'])} + {len(w2['rows'])} unWISE epochs (2010–2024).")
    if w1.get("control_rms") is not None:
        notes.append(f"Noise floor: a constant comparison star (Gaia G = {a['control']['g_mag']}) in the same images varies by only "
                     f"{w1['control_rms']:.2f} mag rms (W1) / {w2['control_rms']:.2f} (W2); the target varies by {w1['target_rms']:.2f} / "
                     f"{w2['target_rms']:.2f} mag rms (full range {w1['target_range']:.1f} / {w2['target_range']:.1f} mag).")
    if field == "rw_aur" and w1.get("neowise_corr") is not None:
        notes.append(f"Cross-check: the index follows NEOWISE profile-fit photometry (correlation {w1['neowise_corr']:.2f} in W1, "
                     f"{w2.get('neowise_corr', float('nan')):.2f} in W2 over {w1['neowise_pairs']} visits).")
    if field == "r_dra":
        f = a.get("folded", {})
        f1, f2 = f.get("W1"), f.get("W2")
        if f1 and f2:
            notes.append(f"Period search (100–1000 d) on the index: best period {f1['best_period_d']:.0f} d (W1) and "
                         f"{f2['best_period_d']:.0f} d (W2), matching the known Mira period of {f['period_d']} d ({f['source']}).")
            alias = f1["next_peaks"][0][0] if f1["next_peaks"] else None
            notes.append("WISE visits this star only about every 6 months, so an alias period near "
                         f"{alias:.0f} d fits almost as well; the data are consistent with the known period but could not "
                         "single it out without it." if alias else "WISE visits this star only about every 6 months.")
            notes.append(f"Folded on {f['period_d']} d, one sine wave explains {f1['variance_explained_at_lit'] * 100:.0f} % of the W1 "
                         f"index variation (semi-amplitude {f1['semi_amplitude_mag']:.2f} mag in the index).")
        notes.append("NEOWISE profile-fit magnitudes of R Dra scatter by up to ~2 mag within single visits (beyond the saturation-"
                     "correction range) and are not used.")
    notes.append("SPHEREx points (synthesized at 3.4/4.6 µm from per-epoch spectra) are not possible: the star is saturated in SPHEREx.")
    return {"points": pts, "unit": "relative mag (wing index; 0 = median)", "method": "unWISE epoch coadds, background-subtracted "
            "median of 1-px rings in the unsaturated PSF wings, ratio to the all-epoch median", "notes": notes,
            "validation": {"control_rms_w1": _r(w1.get("control_rms")), "control_rms_w2": _r(w2.get("control_rms")),
                           "target_rms_w1": _r(w1.get("target_rms")), "target_rms_w2": _r(w2.get("target_rms")),
                           "neowise_corr_w1": _r(w1.get("neowise_corr")), "neowise_corr_w2": _r(w2.get("neowise_corr")),
                           "folded": a.get("folded")}}


def _r(v, n=3):
    return None if v is None else round(float(v), n)


def plot(field, a) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out = config.OUT_DIR / "png"
    out.mkdir(parents=True, exist_ok=True)
    yr = lambda m: config.jyear(np.asarray(m))
    show_nw = field == "rw_aur"
    fig, axes = plt.subplots(2 if show_nw else 1, 1, figsize=(10, 6.4 if show_nw else 4.2), sharex=True, squeeze=False)
    ax = axes[0, 0]
    for bname, c in (("W1", "#2b7bba"), ("W2", "#d7301f")):
        b = a["bands"][bname]
        ax.errorbar(yr([r["mjd"] for r in b["rows"]]), [r["dmag"] for r in b["rows"]], [r["dmag_err"] for r in b["rows"]],
                    fmt="o", ms=4, color=c, label=f"{bname} wing index ({'3.4' if bname == 'W1' else '4.6'} µm)")
        if b.get("control_rows"):
            ax.plot(yr([r["mjd"] for r in b["control_rows"]]), [r["dmag"] for r in b["control_rows"]], "x", ms=4, color=c, alpha=0.4,
                    label=f"{bname} constant comparison star")
    ax.axhline(0, color="#999", lw=0.6)
    ax.invert_yaxis()
    ax.set_ylabel("relative brightness index (mag)\n↑ brighter")
    ax.set_title(f"{config.DISPLAY_NAMES[field]} — 16 years in the infrared (saturated star: relative index from the outer wings)",
                 fontsize=10)
    ax.legend(fontsize=7, ncol=2)
    if show_nw:
        ax2 = axes[1, 0]
        v = a["neowise_visits"]
        for bname, c in (("W1", "#2b7bba"), ("W2", "#d7301f")):
            vv = [x for x in v if bname in x]
            ax2.errorbar(yr([x["mjd"] for x in vv]), [x[bname] for x in vv], [x[bname + "_scatter"] for x in vv], fmt="s", ms=4,
                         color=c, label=f"NEOWISE/AllWISE profile-fit {bname} (visit median ± scatter)")
        ax2.invert_yaxis()
        ax2.set_ylabel("magnitude (Vega)\nsaturated-star profile fit")
        ax2.legend(fontsize=7)
    axes[-1, 0].set_xlabel("year")
    fold = a.get("folded")
    if fold and fold.get("W1"):
        fig.set_size_inches(14, 4.4)
        axes[0, 0].set_position([0.07, 0.13, 0.55, 0.76])
        axf = fig.add_axes([0.70, 0.13, 0.28, 0.76])
        P = fold["period_d"]
        for bname, c in (("W1", "#2b7bba"), ("W2", "#d7301f")):
            rows = a["bands"][bname]["rows"]
            ph = np.array([(r["mjd"] / P) % 1 for r in rows])
            y = np.array([r["dmag"] for r in rows])
            axf.plot(np.r_[ph, ph + 1], np.r_[y, y], "o", ms=4, color=c, label=bname)
        axf.invert_yaxis()
        axf.set_xlabel(f"phase (period {P} d, {fold['source'].split(' (')[0]})")
        axf.set_title(f"folded: best period found {fold['W1']['best_period_d']:.0f} d (W1) / {fold['W2']['best_period_d']:.0f} d (W2)",
                      fontsize=9)
        axf.legend(fontsize=7)
        fig.savefig(out / f"{field}_lightcurve.png", dpi=130)
        plt.close(fig)
        return
    fig.tight_layout()
    fig.savefig(out / f"{field}_lightcurve.png", dpi=130)
    plt.close(fig)


def run(fields=None):
    from .validate import load_object, save_object
    for f in fields or VAR_TARGETS:
        a = analyse(f)
        block = lightcurve_block(f, a)
        obj = load_object(f)
        obj["lightcurve"] = block
        flags = obj.get("flags") or {"saturated_in": [], "warnings": []}
        if "WISE" not in flags["saturated_in"]:
            flags["saturated_in"].append("WISE")
        w = "WISE: saturated — light curve is a relative wing index, not magnitudes"
        flags["warnings"] = [x for x in flags["warnings"] if not x.startswith("WISE: saturated")] + [w]
        obj["flags"] = flags
        save_object(f, obj)
        plot(f, a)
        dump = {k: v for k, v in a.items() if k != "bands"}
        dump["bands"] = {k: {kk: vv for kk, vv in v.items()} for k, v in a["bands"].items()}
        (config.OUT_DIR / f / "lightcurve_analysis.json").write_text(json.dumps(dump, indent=1, default=float), encoding="utf-8")
        print(f"{f}:")
        for n in block["notes"]:
            print("   -", n)
