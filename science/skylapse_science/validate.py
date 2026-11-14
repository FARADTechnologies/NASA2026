"""`python -m skylapse_science validate` — S1 proper-motion validation for the 3 NASA movers.

Writes:
  science/out/<field>/objects/target.json   (motion block; other blocks kept if the file already exists)
  science/out/<field>/astrometry_epochs.csv (every epoch, used or rejected, with the reason)
  science/out/validation/<field>_pm.png     (track + residuals, for slides)
  science/VALIDATION.md                     (table + method)
"""
from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone

import numpy as np

from . import astrometry as A
from . import config


def object_path(field: str):
    return config.OUT_DIR / field / "objects" / "target.json"


def load_object(field: str) -> dict:
    p = object_path(field)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    t = config.load_targets()[field]
    return {"id": "target", "name": config.DISPLAY_NAMES[field], "kind": config.KINDS[field],
            "ra": round(t["ra_2018"], 7), "dec": round(t["dec_2018"], 7), "epoch": 2018.0,
            "motion": None, "spectrum": None, "lightcurve": None, "copilot": None,
            "flags": {"saturated_in": [], "warnings": []}}


def save_object(field: str, obj: dict) -> None:
    p = object_path(field)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")


def write_epochs_csv(field: str, res: dict) -> None:
    p = config.OUT_DIR / field / "astrometry_epochs.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    xi, eta = A.to_tangent(np.array([e.ra for e in res["epochs"]]), np.array([e.dec for e in res["epochs"]]), res["ra0"], res["dec0"])
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["band", "epoch", "mjd", "jyear", "ra", "dec", "xi_arcsec", "eta_arcsec", "resid_xi", "resid_eta",
                    "snr", "sigma_arcsec", "saturated", "used", "reason"])
        for e, x, y in zip(res["epochs"], xi, eta):
            rx = ry = float("nan")
            if np.isfinite(e.ra):
                mra, mdec = A.model_position(res, e.mjd)
                mx, my = A.to_tangent(mra, mdec, res["ra0"], res["dec0"])
                rx, ry = x - mx, y - my
            w.writerow([f"W{e.band}", e.epoch, f"{e.mjd:.5f}", f"{config.jyear(e.mjd):.4f}", f"{e.ra:.7f}", f"{e.dec:.7f}",
                        f"{x:.3f}", f"{y:.3f}", f"{rx:.3f}", f"{ry:.3f}", f"{e.snr:.1f}", f"{e.sigma_arcsec:.3f}",
                        int(e.saturated), int(e.used), e.reason])


def plot(field: str, res: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    out = config.OUT_DIR / "validation"
    out.mkdir(parents=True, exist_ok=True)
    used = [e for e in res["epochs"] if e.used]
    xi, eta = A.to_tangent(np.array([e.ra for e in used]), np.array([e.dec for e in used]), res["ra0"], res["dec0"])
    ty = np.array([config.jyear(e.mjd) for e in used])
    tm = np.linspace(ty.min() - 0.2, ty.max() + 2.8, 400)
    mjd_m = 51544.5 + (tm - 2000.0) * 365.25
    mpos = [A.model_position(res, m) for m in mjd_m]
    mx, my = A.to_tangent(np.array([p[0] for p in mpos]), np.array([p[1] for p in mpos]), res["ra0"], res["dec0"])
    ref = res["ref"]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
    ax[0].plot(mx, my, "-", color="#888", lw=1, label="fit (proper motion + parallax)")
    for b, c in ((1, "#2b7bba"), (2, "#d7301f")):
        k = [i for i, e in enumerate(used) if e.band == b]
        ax[0].plot(xi[k], eta[k], "o", ms=4, color=c, label=f"WISE W{b} epochs ({len(k)})")
    ax[0].invert_xaxis()
    ax[0].set_xlabel("east offset ξ (arcsec)")
    ax[0].set_ylabel("north offset η (arcsec)")
    ax[0].set_title(f"{config.DISPLAY_NAMES[field]}: measured track 2010–2024")
    ax[0].legend(fontsize=8)
    ax[0].set_aspect("equal", adjustable="datalim")
    rx, ry = [], []
    for e, x, y in zip(used, xi, eta):
        a, d = A.model_position(res, e.mjd)
        px, py = A.to_tangent(a, d, res["ra0"], res["dec0"])
        rx.append(x - px)
        ry.append(y - py)
    ax[1].axhline(0, color="#888", lw=0.8)
    ax[1].plot(ty, rx, "o", ms=4, label="Δξ")
    ax[1].plot(ty, ry, "s", ms=4, label="Δη")
    ax[1].set_xlabel("year")
    ax[1].set_ylabel("residual (arcsec)")
    m = res["fit"]
    ax[1].set_title(f"μ = {res['pm_total']:.0f} ± {res['pm_total_err']:.0f} mas/yr  vs  {math.hypot(ref['pmra'], ref['pmdec']):.0f} "
                    f"({ref['source'].split(' (')[0]})  → {res['agreement_pct']:.1f} %", fontsize=8)
    ax[1].legend(fontsize=8)
    ax[1].text(0.02, 0.03, f"rms {m['rms_arcsec']:.2f}\"  (WISE pixel = 2.75\")", transform=ax[1].transAxes, fontsize=8)
    fig.tight_layout()
    fig.savefig(out / f"{field}_pm.png", dpi=130)
    plt.close(fig)


def write_validation_md(results: dict[str, dict]) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# SkyLapse — proper-motion validation (S1, P0-9)",
        "",
        f"Generated {now} by `python -m skylapse_science validate` (science/skylapse_science/astrometry.py). "
        "Per-epoch measurements: `science/out/<field>/astrometry_epochs.csv`; plots: `science/out/validation/<field>_pm.png`.",
        "",
        "| target | measured μα* , μδ (mas/yr) | measured μ (mas/yr) | reference μα* , μδ (mas/yr) | reference | agreement | epochs used (W1+W2) | baseline | rms |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for f, r in results.items():
        m, ref = r["fit"], r["ref"]
        nw1 = sum(1 for e in r["epochs"] if e.used and e.band == 1)
        nw2 = sum(1 for e in r["epochs"] if e.used and e.band == 2)
        lines.append(
            f"| {config.DISPLAY_NAMES[f]} | {m['pmra']:.0f} ± {m['pmra_err']:.0f} , {m['pmdec']:.0f} ± {m['pmdec_err']:.0f} "
            f"| **{r['pm_total']:.0f} ± {r['pm_total_err']:.0f}** | {ref['pmra']:.0f} , {ref['pmdec']:.0f} | {ref['source']} "
            f"| **{r['agreement_pct']:.1f} %** | {m['n_epochs']} ({nw1}+{nw2}) of {len(r['epochs'])} | {m['t_span_yr']:.1f} yr | {m['rms_arcsec']:.2f}\" |")
    eb = results.get("eps_indi_b")
    lines += ["", "Agreement = 100 × (1 − |μ_measured − μ_reference| / |μ_reference|), using the full 2-D vector difference.", ""]
    if eb and "comoving_primary" in eb["ref"]:
        a = eb["ref"]["comoving_primary"]
        ag = A.agreement_pct(eb["fit"]["pmra"], eb["fit"]["pmdec"], a["pmra"], a["pmdec"])
        lines += [f"**ε Indi co-motion check:** ε Indi B (measured in WISE) vs its primary star ε Indi A ({a['source']}: "
                  f"{a['pmra']:.0f}, {a['pmdec']:.0f} mas/yr) → **{ag:.1f} %** agreement: B moves with A across the sky "
                  "(they are a bound system ~400\" apart). Gaia's own value for B differs from A by ~70 mas/yr, most likely because Gaia's 34-month "
                  "baseline catches part of the ~11-yr orbit of the Ba+Bb pair, while our 14-yr WISE baseline averages over it (interpretation, not tested here).", ""]
    lines += [
        "## Method",
        "1. Data: unWISE time-resolved epoch coadds (byw.tools, W1 3.4 µm and W2 4.6 µm, 2.75\"/px), each in its native TAN WCS "
        "(not the resampled viewer grid); epoch time = middle of MJDMIN..MJDMAX.",
        "2. Start from the SIMBAD J2000 position propagated linearly to each epoch; centroid with photutils `centroid_2dg` in an 11×11 px "
        "box after subtracting a sigma-clipped local background (iterated 3×). Saturated cores (Barnard's Star: unWISE writes a ~6 px hole "
        "of zeros) are masked with a 2-px rim and a circular Moffat profile is fitted to the unsaturated wings.",
        "3. Rejected: S/N < 5, centroid > 3 px from the prediction, failed/partial saturated fits, and 3σ outliers (never < 1\"). "
        "Per-epoch error = statistical (FWHM / 2.355 / S/N) ⊕ systematic floor (0.10\"; 0.30\" wing fits; 0.60\" flat saturated cores).",
        "4. Tangent-plane offsets (ξ, η) around the 2018.0 position → weighted least squares for position, μα*, μδ and "
        "parallax (parallax factors from Earth's barycentric position; WISE is in low Earth orbit). Errors: 1000× bootstrap over epochs.",
        "5. References: Gaia DR3 (ESA) for Barnard's Star and ε Indi B/A; WISE 0855−0714 is not in Gaia → Kirkpatrick et al. 2021 "
        "(ApJS 253, 7, via SIMBAD). CatWISE2020's motion for ε Indi B is known to be wrong (~1.1\"/yr) and is not used.",
        "",
        "Caveats: parallax is a nuisance parameter here, not a result — WISE scan-direction centroid offsets alternate between the two "
        "observing seasons and bias it (e.g. ε Indi B). Barnard's Star perspective acceleration (~1 mas/yr²) is ignored. "
        "SPHEREx (6.15\" px, ~1 yr) adds no useful leverage for these motions; its epochs are shown on the track as model positions.",
    ]
    meas_plx = {f: (r["fit"]["plx"], r["fit"]["plx_err"], r["ref"].get("parallax")) for f, r in results.items()}
    lines += ["", "Fitted parallax (nuisance, for transparency): " + "; ".join(
        f"{config.DISPLAY_NAMES[f]} {p:.0f} ± {pe:.0f} mas (reference {rp:.0f})" for f, (p, pe, rp) in meas_plx.items() if rp)]
    (config.SCIENCE_DIR / "VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(fields: list[str] | None = None) -> dict[str, dict]:
    fields = fields or config.MOVERS
    results = {}
    for f in fields:
        r = A.validate_target(f)
        results[f] = r
        obj = load_object(f)
        obj["motion"] = A.motion_block(r)
        flags = obj.get("flags") or {"saturated_in": [], "warnings": []}
        nsat = sum(1 for e in r["epochs"] if e.saturated)
        if nsat:
            if "WISE" not in flags["saturated_in"]:
                flags["saturated_in"].append("WISE")
            w = f"Saturated core in {nsat} of {len(r['epochs'])} WISE epochs; positions from the unsaturated wings."
            flags["warnings"] = [x for x in flags["warnings"] if not x.startswith("Saturated core in")] + [w]
        obj["flags"] = flags
        save_object(f, obj)
        write_epochs_csv(f, r)
        plot(f, r)
        print(f"{f:11s} mu=({r['fit']['pmra']:8.1f}, {r['fit']['pmdec']:8.1f}) |mu|={r['pm_total']:7.1f}±{r['pm_total_err']:.1f} "
              f"ref=({r['ref']['pmra']:.1f}, {r['ref']['pmdec']:.1f}) agreement={r['agreement_pct']:.2f}% n={r['fit']['n_epochs']}")
    if set(fields) == set(config.MOVERS):
        write_validation_md(results)
    return results
