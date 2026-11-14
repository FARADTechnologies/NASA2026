# Journal — role: science  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sat 14 Nov ~15:00 Baku

## Current task
#8 S1 — proper-motion validation (P0-9) → DONE, PR open, submitted. Next in queue: #9 S2 spectra, #10 S3 light curves, #11 S5 copilot.

## Status
S1 done: Barnard 99.8 %, eps Indi B 99.0 % (99.3 % vs eps Ind A), WISE 0855 99.9 %.

## Done (with proof)
- `python -m skylapse_science validate` (run from `science/` with `science/.venv`) → 9 s, writes
  `science/out/<field>/objects/target.json` (motion block), `out/<field>/astrometry_epochs.csv`, `out/validation/<field>_pm.png`, `science/VALIDATION.md`.
- Barnard (-784, 10366) ±(15,17) vs Gaia (-802, 10362); 36/46 epochs; rms 0.37".
- eps Indi B (3991, -2514) ±(9,7) vs Gaia B (3982, -2467); vs Gaia A (3967, -2536) 99.3 %; 46/46 epochs; rms 0.20".
- WISE 0855 (-8129, 673) ±(15,7) vs Kirkpatrick+2021 (-8124, 673); 23 W2 epochs (W1 too faint); rms 0.17".
- Sanity: fitted 2010 position of WISE 0855 = 133.79519, -7.24512 ≈ NASA challenge coordinate (133.795130, -7.245147).

## Next step (exact, so a fresh session can continue blindly)
- `python ops/bin/skyops.py next` → take #9 (S2 spectra) or whatever it returns. S2: new `science/skylapse_science/spectra.py`,
  SPHEREx slim files in `$SKYLAPSE_DATA/slim/spherex/<target>/<band>/`, index.csv there; IMAGE−ZODI, VARIANCE, FLAGS, WCS-WAVE.

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

## Open questions / waiting on
- none. Pipeline `merge-science` copies science/out into the bundle (D-009).
