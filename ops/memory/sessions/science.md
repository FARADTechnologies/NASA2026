# Journal — role: science  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sat 14 Nov ~15:00 Baku

## Current task
#9 S2 — SPHEREx spectra (claimed Sat ~15:20). #8 S1 done + submitted (PR #44, status:review). Queue after: #10 S3, #11 S5, #12 S4.

## Status
S2 nearly done: spectra.py works for all 5 targets; final full run + commit/PR/submit pending.
- S2 results: WISE 0855 undetected <2.4 µm & CH4 band, detected 4.4–4.9 µm (30 clean May-2025 images; later images blended with a
  G=16.3 star <9"). eps Indi B full T-dwarf spectrum (324 images). Barnard/R Dra/RW Aur saturated → usable:false, no points.
- Flux scale: 9 CatWISE stars, D4/W1 = 1.01±0.03, D6/W2 = 1.03±0.03 (`spectra-calib`).

## Done (with proof)
- `python -m skylapse_science validate` (run from `science/` with `science/.venv`) → 9 s, writes
  `science/out/<field>/objects/target.json` (motion block), `out/<field>/astrometry_epochs.csv`, `out/validation/<field>_pm.png`, `science/VALIDATION.md`.
- Barnard (-784, 10366) ±(15,17) vs Gaia (-802, 10362); 36/46 epochs; rms 0.37".
- eps Indi B (3991, -2514) ±(9,7) vs Gaia B (3982, -2467); vs Gaia A (3967, -2536) 99.3 %; 46/46 epochs; rms 0.20".
- WISE 0855 (-8129, 673) ±(15,7) vs Kirkpatrick+2021 (-8124, 673); 23 W2 epochs (W1 too faint); rms 0.17".
- Sanity: fitted 2010 position of WISE 0855 = 133.79519, -7.24512 ≈ NASA challenge coordinate (133.795130, -7.245147).

## Next step (exact, so a fresh session can continue blindly)
- If S2 not yet submitted: `cd science && .venv/Scripts/python.exe -m skylapse_science spectra` (6 min), check out/png/*.png,
  commit science/ + journal, push role/science (PR #44 updates automatically), `skyops.py submit 9 --file report.md --pr <PR #44 url>`.
- Then `python ops/bin/skyops.py next --wait 540` → likely #10 S3 light curves (R Dra / RW Aur saturated: decide by M2 18:30;
  options in SCIENCE_NOTES §7: NEOWISE single-exposure profile-fit photometry, wing index, or honest fallback).

## Files touched
- science/skylapse_science/{__init__,__main__,config,astrometry,validate}.py, science/requirements.txt, science/VALIDATION.md, science/out/**

## Gotchas / know-how (local to this role; durable ones also go to ops/memory/KNOWHOW.md)
- Python: system Python 3.14 has no astropy → use `science/.venv/Scripts/python.exe` (created with pip install -r science/requirements.txt).
- unWISE saturated cores = exact 0 pixels (hole ~6 px, junk pixels inside, corrupted 2-px rim). Epochs 0–6 (2010–2015) of Barnard have flat
  cores without a hole. Wing Moffat fit works (<0.3" vs Gaia). Partial holes (<15 px) are unreliable → rejected.
- Weights matter: bright unsaturated epochs need a systematic floor (0.10"); without it one bad 2010 epoch biased Barnard to 98.3 %.
- Fitted parallax is biased for eps Indi B (37 vs 271 mas): seasonal (scan-direction) centroid offsets ~0.25". Cancels in PM. Never quote WISE parallax.
- WISE 0855 is invisible in most W1 epochs (S/N<5 or centroid runs away) → W2 only.
- eps Ind A is outside the WISE cutout (402" vs 352" half-width) → co-motion check uses Gaia A.
- SPHEREx: raw files (with EPSF, 33x33 at 5x oversampling, 441 zones) are in $SKYLAPSE_DATA/raw/spherex; WCS key "A" maps cutout px
  → detector px. Neighbour search must use the target's SPHEREx-era position (movers!), not 2016. Aperture photometry of WISE 0855
  gave a FALSE short-wave detection (blend) — always forced-PSF + blend flag.
- eps Indi B T-dwarf peak is 3.9–4.2 µm, not 4.6 (CO absorption at 4.6). Don't say "bright at 4.6" for T dwarfs.

## Open questions / waiting on
- none. Pipeline `merge-science` copies science/out into the bundle (D-009).
