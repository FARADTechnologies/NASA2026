# Journal — role: science  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sat 14 Nov ~20:45 Baku

## Current task
PAUSED by Murad (Sat ~20:45 Baku). Accepted: #8 S1, #9 S2, #10 S3. In review: #12 S4 (PR #61). BLOCKED: #11 S5 copilot —
waiting for ANTHROPIC_API_KEY in C:/Users/Murad/Downloads/skylapse-science/.env (still missing at pause time).

## Status
- S4: recall 3/3 known movers (Barnard 10405, eps Indi B 4713, WISE 0855 8155 mas/yr), 0 false candidates in 5 fields.
  Raw CatWISE >300 mas/yr in frames: 881, none confirmed by Gaia → reliability cuts documented in science/DISCOVERY.md.
- S5: copilot.py done (facts JSON, number guard, facts_hash). `python -m skylapse_science copilot --dry-run` shows facts.
- S3: RW Aur wing index vs NEOWISE corr 0.93/0.98; R Dra period 246/247 d vs GCVS 245.6 (alias ~713 d).
- S2: WISE 0855 undetected <2.4 µm, detected 4.4–4.9 µm; eps Indi B T-dwarf spectrum; flux scale 1.01/1.03.

## Done (with proof)
- `python -m skylapse_science validate` (run from `science/` with `science/.venv`) → 9 s, writes
  `science/out/<field>/objects/target.json` (motion block), `out/<field>/astrometry_epochs.csv`, `out/validation/<field>_pm.png`, `science/VALIDATION.md`.
- Barnard (-784, 10366) ±(15,17) vs Gaia (-802, 10362); 36/46 epochs; rms 0.37".
- eps Indi B (3991, -2514) ±(9,7) vs Gaia B (3982, -2467); vs Gaia A (3967, -2536) 99.3 %; 46/46 epochs; rms 0.20".
- WISE 0855 (-8129, 673) ±(15,7) vs Kirkpatrick+2021 (-8124, 673); 23 W2 epochs (W1 too faint); rms 0.17".
- Sanity: fitted 2010 position of WISE 0855 = 133.79519, -7.24512 ≈ NASA challenge coordinate (133.795130, -7.245147).

## Next step (exact, so a fresh session can continue blindly)
- On resume: `python ops/bin/skyops.py auto on` (only if Murad says so), then `skyops.py next --wait 540`.
- If .env exists: `cd science && .venv/Scripts/python.exe -m skylapse_science copilot`, read every EN/AZ text against
  out/<field>/copilot_facts.json, commit, push (PR #61 or new PR), `skyops.py submit 11` with all 10 texts in the report.
- If #12 gets review comments: fix in science/skylapse_science/discovery.py, rerun `discover` for all 5 fields, resubmit.

## Files touched
- science/skylapse_science/{__init__,__main__,config,astrometry,validate,spectra,photometry,copilot,discovery}.py,
  science/{VALIDATION,SPECTRA,LIGHTCURVES,DISCOVERY}.md,
  science/requirements.txt, science/data_cache/*.csv, science/out/**

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

- unWISE R Dra: some epochs are all-zero (no coverage) or have coverage-edge zeros merging with the core → use the zero region
  connected to the centre and a 90th-percentile radius. AllWISE MEP has no qual_frame column (NEOWISE L1b does).

- CatWISE2020 high-pm lists are full of junk near bright stars/fast movers: use nb=1, ab_flags clean, w2mpro≈w2mpro_pm,
  par_pm not negative, outside saturated-star halos. Saturated movers: detect via zero holes + S1 wing fit.

## Open questions / waiting on
- S5 waits for ANTHROPIC_API_KEY in .env (Murad). Pipeline `merge-science` copies science/out into the bundle (D-009).
