"""Contract-valid MOCK bundle (docs/DATA_CONTRACT.md, schema 1.0) for frontend development.

Writes web/public/bundle/_mock/ — a separate bundle root with its own index.json and one field `mock_mover`:
  * 192x192 grid, 2.75"/px, TAN WCS
  * 23 "WISE" epochs per band W1/W2 (May 2010, Nov 2010, hibernation gap, then 2014-2024 every ~6 months)
  * 3 "SPHEREx" time clusters x detectors D1..D6 (2025-2026)
  * Gaussian noise, ~30 static stars, one saturated star (flat core in WISE, NaN core in SPHEREx), one variable star,
    one fast Gaia star (~1"/yr) and the TARGET: a cold "brown dwarf" mover crossing ~57 px in 16 years
    (faint in W1/D1-D3, bright in W2/D5/D6)
  * catalogs (gaia.json without the target, catwise.json with it), objects/target.json + objects/c002.json, candidates.json

Everything here is FAKE data. Only numpy + Pillow are needed.
Run:  python pipeline/skylapse_pipeline/mock.py [--out web/public/bundle/_mock]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import shutil
from pathlib import Path

import numpy as np

SCHEMA = "1.0"
W = H = 192
SCALE = 2.75  # arcsec / px
RA0, DEC0 = 150.1000, 2.2000  # field centre (fake, COSMOS-like)
CRPIX = 96.5  # FITS 1-based centre
CD = SCALE / 3600.0
FIELD = "mock_mover"
MJD0 = dt.date(1858, 11, 17)

# Target motion (pixels per Julian year in grid x/y, 0-based; x grows to the WEST because CD1_1 < 0)
PM_PX = (3.6, 0.3)
T_REF = 2018.0
BANDS_LAMBDA = {"W1": (3.4, 3.4), "W2": (4.6, 4.6), "D1": (0.75, 1.1), "D2": (1.1, 1.6), "D3": (1.6, 2.4),
                "D4": (2.4, 3.8), "D5": (3.8, 4.4), "D6": (4.4, 5.0)}
TARGET_FLUX = {"W1": 2.5, "W2": 40.0, "D1": 0.0, "D2": 0.0, "D3": 0.4, "D4": 3.0, "D5": 22.0, "D6": 36.0}


# ----------------------------------------------------------------------------- helpers
def mjd_of(d: dt.date) -> float:
    return float((d - MJD0).days)


def date_of(mjd: float) -> str:
    return (MJD0 + dt.timedelta(days=mjd)).isoformat()


def jyear(mjd: float) -> float:
    return 2000.0 + (mjd - 51544.5) / 365.25


def pix2world(x0: float, y0: float) -> tuple[float, float]:
    """0-based pixel -> (ra, dec) degrees, gnomonic (TAN) with CD = diag(-s, s)."""
    xi = math.radians(-CD * (x0 + 1 - CRPIX))
    eta = math.radians(CD * (y0 + 1 - CRPIX))
    a0, d0 = math.radians(RA0), math.radians(DEC0)
    den = math.cos(d0) - eta * math.sin(d0)
    ra = a0 + math.atan2(xi, den)
    dec = math.atan2(math.sin(d0) + eta * math.cos(d0), math.hypot(xi, den))
    return (math.degrees(ra) % 360.0, math.degrees(dec))


def target_xy(t: float) -> tuple[float, float]:
    c = CRPIX - 1
    return (c + PM_PX[0] * (t - T_REF), c + PM_PX[1] * (t - T_REF))


def pm_mas(px_per_yr_x: float, px_per_yr_y: float) -> tuple[float, float]:
    """grid pixel motion -> (pmra*cosdec, pmdec) in mas/yr (x grows west => pmra negative)."""
    return (-px_per_yr_x * SCALE * 1000.0, px_per_yr_y * SCALE * 1000.0)


def gauss(img: np.ndarray, x: float, y: float, amp: float, sigma: float) -> None:
    r = int(math.ceil(4 * sigma))
    xi, yi = int(round(x)), int(round(y))
    x1, x2 = max(0, xi - r), min(W, xi + r + 1)
    y1, y2 = max(0, yi - r), min(H, yi + r + 1)
    if x1 >= x2 or y1 >= y2:
        return
    yy, xx = np.mgrid[y1:y2, x1:x2]
    img[y1:y2, x1:x2] += amp * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma ** 2))


# ----------------------------------------------------------------------------- epochs
def wise_epochs() -> list[tuple[float, float]]:
    """(mjd_start, mjd_end) of 23 epochs: 2 in 2010, then 21 from Dec 2013 to Apr 2024 (~6-month cadence)."""
    starts = [mjd_of(dt.date(2010, 5, 8)), mjd_of(dt.date(2010, 11, 10))]
    base = mjd_of(dt.date(2013, 12, 15))
    for k in range(21):
        starts.append(base + k * 182.6)
    return [(s, s + 3.1) for s in starts]


def spherex_clusters() -> list[tuple[float, float]]:
    return [(60800.0, 60802.0), (60980.0, 61022.0), (61151.0, 61174.0)]


# ----------------------------------------------------------------------------- scene
def make_scene(rng: np.random.Generator):
    stars = []  # (x, y, flux_w2, colour w1-w2 like, pm_px_x, pm_px_y)
    while len(stars) < 30:
        x, y = rng.uniform(8, W - 8), rng.uniform(8, H - 8)
        if math.hypot(x - 95.5, y - 95.5) < 6:
            continue
        stars.append([x, y, float(rng.lognormal(2.6, 0.9)), float(rng.normal(0.1, 0.15)),
                      float(rng.normal(0, 0.004)), float(rng.normal(0, 0.004))])
    saturated = [40.0, 150.0, 6000.0, 0.0, 0.0, 0.0]
    variable = [150.0, 40.0, 60.0, 0.3, 0.0, 0.0]
    fast = [130.0, 150.0, 80.0, 0.05, -0.18, 0.31]  # ~1"/yr Gaia star
    return stars, saturated, variable, fast


def band_flux(flux_w2: float, colour: float, band: str) -> float:
    """Ordinary stars: roughly flat-ish SED, brighter toward short wavelengths when colour is small."""
    lam = sum(BANDS_LAMBDA[band]) / 2
    return flux_w2 * (4.6 / lam) ** (1.2 - 2.0 * colour)


def render(band: str, instrument: str, mjd: float, rng, scene, n_inputs: int):
    stars, sat, var, fast = scene
    t = jyear(mjd)
    sigma_psf = 1.1 if instrument == "WISE" else 2.0
    noise = 1.0 if instrument == "WISE" else 0.7 / math.sqrt(max(1, n_inputs) / 4)
    img = rng.normal(0.0, noise, (H, W)).astype(np.float64)
    for x, y, f, c, px, py in stars:
        gauss(img, x + px * (t - 2016), y + py * (t - 2016), band_flux(f, c, band), sigma_psf)
    x, y, f, c, px, py = fast
    gauss(img, x + px * (t - 2016), y + py * (t - 2016), band_flux(f, c, band), sigma_psf)
    x, y, f, c, _, _ = var
    phase = math.sin(2 * math.pi * (mjd - 55000) / 245.0)
    gauss(img, x, y, band_flux(f, c, band) * (1 + 0.6 * phase), sigma_psf)
    tx, ty = target_xy(t)
    gauss(img, tx, ty, TARGET_FLUX[band], sigma_psf)
    # saturated star
    x, y, f, c, _, _ = sat
    gauss(img, x, y, band_flux(f, c, band), sigma_psf * 1.6)
    mask = np.zeros((H, W), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    core = (xx - x) ** 2 + (yy - y) ** 2 <= (3.5 if instrument == "WISE" else 4.5) ** 2
    mask[core] |= 2
    if instrument == "WISE":
        img[core] = min(img[core].max(), 1500.0)  # flat clipped core
    else:
        img[core] = np.nan  # NaN core like real saturated SPHEREx pixels
        # a fake cosmic-ray streak and a few hot pixels (masked)
        r0 = int(rng.integers(20, 170))
        cols = np.arange(10, 60)
        rows = np.clip((r0 + 0.4 * (cols - 10)).astype(int), 0, H - 1)
        mask[rows, cols] |= 1
        img[rows, cols] += 30
        hot = rng.integers(0, H, (12, 2))
        mask[hot[:, 0], hot[:, 1]] |= 1
        img[hot[:, 0], hot[:, 1]] += 80
    return img.astype("<f4"), mask


def percentiles(img: np.ndarray) -> dict:
    v = img[np.isfinite(img)]
    p = np.percentile(v, [1, 50, 99, 99.9])
    return {"p01": round(float(p[0]), 3), "p50": round(float(p[1]), 3), "p99": round(float(p[2]), 3),
            "p999": round(float(p[3]), 3)}


def save_preview(img: np.ndarray, disp: dict, path: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        return
    lo, hi = disp["p01"], disp["p999"]
    a = np.nan_to_num(img, nan=hi)
    a = np.clip((a - lo) / max(1e-6, hi - lo), 0, 1)
    a = np.arcsinh(10 * a) / np.arcsinh(10)
    Image.fromarray((np.flipud(a) * 255).astype(np.uint8)).save(path)  # flip: FITS row 0 = south


# ----------------------------------------------------------------------------- build
def build(out: Path) -> None:
    rng = np.random.default_rng(20261114)
    scene = make_scene(rng)
    if out.exists():
        shutil.rmtree(out)
    fdir = out / FIELD
    for sub in ("frames", "previews", "catalogs", "objects"):
        (fdir / sub).mkdir(parents=True, exist_ok=True)

    frames = []

    def add_frame(fid, instrument, band, m0, m1, n_inputs, src, notes):
        mid = round((m0 + m1) / 2, 3)
        img, mask = render(band, instrument, mid, rng, scene, n_inputs)
        (fdir / "frames" / f"{fid}.f32").write_bytes(img.tobytes())
        (fdir / "frames" / f"{fid}.mask.u8").write_bytes(mask.tobytes())
        disp = percentiles(img)
        save_preview(img, disp, fdir / "previews" / f"{fid}.png")
        frames.append({
            "id": fid, "instrument": instrument, "band": band, "lambda_um": list(BANDS_LAMBDA[band]),
            "mjd_start": round(m0, 3), "mjd_end": round(m1, 3), "mjd_mid": mid, "date": date_of(mid),
            "n_inputs": n_inputs, "file": f"frames/{fid}.f32", "mask_file": f"frames/{fid}.mask.u8",
            "dtype": "float32", "units": "relative", "display": disp,
            "quality": {"masked_frac": round(float((mask & 1).mean()), 5), "saturated_frac": round(float(((mask & 2) > 0).mean()), 5),
                        "notes": notes},
            "source_files": [src],
        })

    for e, (m0, m1) in enumerate(wise_epochs()):
        for b in (1, 2):
            add_frame(f"wise_w{b}_e{e:02d}", "WISE", f"W{b}", m0, m1, 1, f"MOCK byw.tools epoch {e} band {b}",
                      ["MOCK DATA", "saturated star at lower left (flat core)"])
    for t, (m0, m1) in enumerate(spherex_clusters()):
        for d in range(1, 7):
            n = int(rng.integers(5, 12))
            add_frame(f"spx_d{d}_t{t:02d}", "SPHEREx", f"D{d}", m0 + 0.2 * d, m1 - 0.2 * (6 - d), n,
                      f"MOCK SPHEREx dr1+qr3 {n} images", ["MOCK DATA", "SPHEREx pixels are 6.15\"; resampled to 2.75\"",
                                                           "saturated star: NaN core (OVERFLOW)"])

    by_id = {f["id"]: f for f in frames}

    def seq(ids):
        return sorted(ids, key=lambda i: by_id[i]["mjd_mid"])

    wise_n = len(wise_epochs())
    sequences = [
        {"id": "thermal46", "label": "4.6 µm — WISE W2 + SPHEREx D6", "default": True,
         "frames": seq([f"wise_w2_e{e:02d}" for e in range(wise_n)] + [f"spx_d6_t{t:02d}" for t in range(3)])},
        {"id": "w1d4", "label": "3.4 µm — WISE W1 + SPHEREx D4", "default": False,
         "frames": seq([f"wise_w1_e{e:02d}" for e in range(wise_n)] + [f"spx_d4_t{t:02d}" for t in range(3)])},
        {"id": "spherex6", "label": "SPHEREx only — D1…D6", "default": False,
         "frames": seq([f"spx_d{d}_t{t:02d}" for t in range(3) for d in range(1, 7)])},
    ]
    rgb = [{"id": f"fingerprint_t{t:02d}", "label": f"Spectral fingerprint (D1/D3/D6), cluster {t} (MOCK)",
            "r": f"spx_d6_t{t:02d}", "g": f"spx_d3_t{t:02d}", "b": f"spx_d1_t{t:02d}"} for t in range(3)]

    # ---------------- catalogs
    stars, sat, var, fast = scene
    gaia_rows = []
    for i, (x, y, f, c, px, py) in enumerate(stars + [sat, var, fast]):
        ra, dec = pix2world(x, y)  # positions are at epoch 2016.0 by construction
        pmra, pmdec = pm_mas(px, py)
        g = round(22.5 - 2.5 * math.log10(max(f, 0.1)) - 4.0, 2)
        gaia_rows.append([f"MOCK{4000000000000000000 + i}", round(ra, 7), round(dec, 7), round(pmra, 2), round(pmdec, 2),
                          round(float(abs(rng.normal(2, 1.5))), 3), g, round(1.0 + 3 * c, 2)])
    gaia = {"catalog": "Gaia DR3 (MOCK)", "ref_epoch": 2016.0,
            "columns": ["id", "ra", "dec", "pmra", "pmdec", "parallax", "mag", "color"], "rows": gaia_rows}
    tx15, ty15 = target_xy(2015.4)
    tra15, tdec15 = pix2world(tx15, ty15)
    t_pmra, t_pmdec = pm_mas(*PM_PX)
    cat_rows = [["MOCK J1000+0212", round(tra15, 7), round(tdec15, 7), round(t_pmra, 1), round(t_pmdec, 1), None, 14.2, 3.1]]
    for i, (x, y, f, c, px, py) in enumerate(stars[:20]):
        ra, dec = pix2world(x + px * (2015.4 - 2016), y + py * (2015.4 - 2016))
        pmra, pmdec = pm_mas(px, py)
        cat_rows.append([f"MOCK CWISE{i:03d}", round(ra, 7), round(dec, 7), round(pmra, 1), round(pmdec, 1), None,
                         round(22.5 - 2.5 * math.log10(max(f, 0.1)), 2), round(c, 2)])
    catwise = {"catalog": "CatWISE2020 (MOCK)", "ref_epoch": 2015.4,
               "columns": ["id", "ra", "dec", "pmra", "pmdec", "parallax", "mag", "color"], "rows": cat_rows}
    (fdir / "catalogs" / "gaia.json").write_text(json.dumps(gaia), encoding="utf-8")
    (fdir / "catalogs" / "catwise.json").write_text(json.dumps(catwise), encoding="utf-8")

    # ---------------- objects
    track = []
    for fid in sequences[0]["frames"]:
        fr = by_id[fid]
        x, y = target_xy(jyear(fr["mjd_mid"]))
        ra, dec = pix2world(x, y)
        track.append({"mjd": fr["mjd_mid"], "ra": round(ra, 7), "dec": round(dec, 7), "instrument": fr["instrument"]})
    pm_tot = math.hypot(t_pmra, t_pmdec)
    lam = np.linspace(0.75, 5.0, 64)
    bd = np.where(lam < 2.9, 0.0, 0.42 * np.exp(-((lam - 4.65) / 0.45) ** 2)) - np.where(abs(lam - 3.3) < 0.15, 0.02, 0)
    bd = np.clip(bd + np.where(lam > 2.9, 0.01, 0), 0, None)
    spec_pts = []
    for k, l in enumerate(lam):
        cl = k % 3
        spec_pts.append({"lambda_um": round(float(l), 3), "flux": round(float(bd[k] + rng.normal(0, 0.02)), 4), "err": 0.02,
                         "mjd": spherex_clusters()[cl][0] + 1, "detector": f"D{min(6, 1 + int(np.searchsorted([1.1, 1.6, 2.4, 3.8, 4.4], l)))}",
                         "flagged": bool(k == 50)})
    tl = np.linspace(0.75, 5.0, 120)
    tf = np.clip(np.where(tl < 2.9, 0.0, 0.42 * np.exp(-((tl - 4.65) / 0.45) ** 2)), 0, None)
    lc = []
    for e, (m0, m1) in enumerate(wise_epochs()):
        mid = (m0 + m1) / 2
        lc.append({"mjd": round(mid, 3), "instrument": "WISE", "band": "W2", "mag": round(13.9 + float(rng.normal(0, 0.04)), 3),
                   "err": 0.05, "saturated": False})
        lc.append({"mjd": round(mid, 3), "instrument": "WISE", "band": "W1", "mag": round(17.4 + float(rng.normal(0, 0.15)), 3),
                   "err": 0.2, "saturated": e == 3})
    for t, (m0, m1) in enumerate(spherex_clusters()):
        lc.append({"mjd": (m0 + m1) / 2, "instrument": "SPHEREx", "band": "W2-synth", "mag": round(13.95 + float(rng.normal(0, 0.06)), 3),
                   "err": 0.08, "saturated": False})
    ra_t, dec_t = pix2world(CRPIX - 1, CRPIX - 1)
    target = {
        "id": "target", "name": "MOCK Brown Dwarf J1000+0212", "kind": "brown_dwarf",
        "ra": round(ra_t, 7), "dec": round(dec_t, 7), "epoch": T_REF,
        "motion": {
            "measured": {"pmra": round(t_pmra * 1.004), "pmdec": round(t_pmdec * 0.99), "pm_total": round(pm_tot * 1.003), "err": 55,
                         "unit": "mas/yr", "n_epochs": len(track)},
            "reference": {"source": "CatWISE2020 (MOCK)", "pmra": round(t_pmra), "pmdec": round(t_pmdec), "unit": "mas/yr"},
            "agreement_pct": 99.7, "track": track,
        },
        "spectrum": {"unit_flux": "mJy", "points": spec_pts,
                     "template": {"name": "Y1 template (MOCK)", "lambda_um": [round(float(v), 3) for v in tl],
                                  "flux": [round(float(v), 4) for v in tf]},
                     "notes": ["MOCK DATA", "Undetected below 3 µm", "Methane absorption near 3.3 µm"]},
        "lightcurve": {"points": lc, "notes": ["MOCK DATA", "W1 epoch 3 flagged as saturated only to test hollow markers"]},
        "copilot": {
            "en": "MOCK TEXT. This faint dot is a cold brown dwarf candidate in a fake test field. It is almost invisible in "
                  "short-wavelength light but glows at 4.6 microns, which is typical for very cold objects. In the movie it "
                  "crawls steadily across the field over 16 years.",
            "az": "TEST MƏTNİ. Bu zəif nöqtə saxta test sahəsində soyuq qəhvəyi cırtdan namizədidir. Qısa dalğalarda demək olar "
                  "ki, görünmür, amma 4.6 mikronda parlayır — bu, çox soyuq obyektlər üçün tipikdir. Filmdə 16 il ərzində sahə "
                  "boyunca yavaş-yavaş hərəkət edir.",
            "model": "mock", "facts_hash": "mock", "audio_en": None, "audio_az": None},
        "flags": {"saturated_in": [], "warnings": ["MOCK DATA — not a real object"]},
    }
    cx, cy = 60.0, 50.0
    cra, cdec = pix2world(cx, cy)
    c002 = {"id": "c002", "name": "Candidate c002 (MOCK)", "kind": "candidate", "ra": round(cra, 7), "dec": round(cdec, 7),
            "epoch": T_REF,
            "motion": {"measured": {"pmra": -950, "pmdec": 120, "pm_total": 958, "err": 140, "unit": "mas/yr", "n_epochs": 14},
                       "reference": None, "agreement_pct": None, "track": []},
            "spectrum": None, "lightcurve": None, "copilot": None,
            "flags": {"saturated_in": [], "warnings": ["MOCK DATA", "low S/N"]}}
    (fdir / "objects" / "target.json").write_text(json.dumps(target, ensure_ascii=False), encoding="utf-8")
    (fdir / "objects" / "c002.json").write_text(json.dumps(c002, ensure_ascii=False), encoding="utf-8")

    sra, sdec = pix2world(sat[0] + 6, sat[1] + 2)
    candidates = {"method": "16-yr cross-epoch linking, ≥3σ motion (MOCK)",
                  "stats": {"known_movers_in_field": 2, "recovered": 2, "new_candidates": 1},
                  "items": [
                      {"id": "c001", "ra": track[len(track) // 2]["ra"], "dec": track[len(track) // 2]["dec"],
                       "pm_total": round(pm_tot), "err": 55, "class": "known",
                       "match": {"gaia": None, "catwise": "MOCK J1000+0212"}, "score": 0.97, "object_file": "objects/target.json"},
                      {"id": "c002", "ra": round(cra, 7), "dec": round(cdec, 7), "pm_total": 958, "err": 140, "class": "candidate",
                       "match": {"gaia": None, "catwise": None}, "score": 0.62, "object_file": "objects/c002.json"},
                      {"id": "c003", "ra": round(sra, 7), "dec": round(sdec, 7), "pm_total": 4100, "err": 2500, "class": "artifact",
                       "match": {"gaia": None, "catwise": None}, "score": 0.08, "object_file": None},
                  ]}
    (fdir / "candidates.json").write_text(json.dumps(candidates, ensure_ascii=False), encoding="utf-8")

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "schema_version": SCHEMA, "field_id": FIELD, "title": "MOCK mover field (fake data)",
        "center": {"ra": RA0, "dec": DEC0, "epoch": T_REF},
        "grid": {"width": W, "height": H, "pixel_scale_arcsec": SCALE,
                 "wcs": {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRVAL1": RA0, "CRVAL2": DEC0, "CRPIX1": CRPIX,
                         "CRPIX2": CRPIX, "CD1_1": -round(CD, 9), "CD1_2": 0.0, "CD2_1": 0.0, "CD2_2": round(CD, 9)}},
        "frames": sorted(frames, key=lambda f: (f["mjd_mid"], f["id"])),
        "sequences": sequences, "rgb_composites": rgb, "objects": ["target", "c002"],
        "catalogs": {"gaia": "catalogs/gaia.json", "catwise": "catalogs/catwise.json"},
        "candidates": "candidates.json",
        "credits": ["MOCK DATA generated by pipeline/skylapse_pipeline/mock.py — not real observations"],
        "build": {"pipeline_version": "mock-1.0", "generated_utc": now, "spherex_releases": ["mock"]},
    }
    (fdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    index = {"schema_version": SCHEMA, "generated_utc": now,
             "fields": [{"field_id": FIELD, "title": "MOCK mover field (fake data)", "kind": "showcase", "ra": RA0, "dec": DEC0,
                         "thumb": f"{FIELD}/previews/wise_w2_e00.png", "tags": ["mock", "motion", "brown dwarf"]}]}
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"mock bundle written to {out}  ({len(frames)} frames, {size / 1e6:.1f} MB)")


def main(argv=None):
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(root / "web" / "public" / "bundle" / "_mock"))
    a = ap.parse_args(argv)
    build(Path(a.out))


if __name__ == "__main__":
    main()
