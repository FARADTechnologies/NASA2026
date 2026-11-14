# Journal — role: pipeline  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sat 14 Nov 16:45 Baku

## Current task
None. T1–T6 (#2–#7) submitted; PR #59 MERGED into main (11:20 UTC). #49 answered: _mock is sized separately; keep D1–D6.
Human asked to pause: `skyops.py pause` was run (Sat ~16:45). Queue was empty (3× NO_TASK).

## Status
PAUSED. validate_bundle 8/8 PASS (5 real fields + _mock). Live runner tested on 4 fresh coordinates (all PASS).

## Done (with proof)
- T1: `python -m skylapse_pipeline inventory` (run from `pipeline/` with `../.venv/Scripts/python.exe`) prints WISE epochs per band
  and SPHEREx images per detector per time bin for all 5 targets (wise0855 23/23 + 258 imgs in 3 bins, r_dra 48/48 + 2493 in 9 bins).
- T2: `build --field wise0855` → web/public/bundle/wise0855 (64 frames, 30 s). validate_bundle PASS.
  Target measured at predicted position in all 23 W2 epochs (15–27σ) and D6 t01/t02 (16/21σ); moves 47 px = 130" 2010→2026.
  QA: pipeline/qa/wise0855_thermal46.gif, pipeline/qa/wise0855_zoom.png.

## Next step (exact, so a fresh session can continue blindly)
- When the human says continue: `python ops/bin/skyops.py resume`, then `python ops/bin/skyops.py next --wait 540` and follow it.
- On review changes: fix, rebuild (`cd pipeline && ../.venv/Scripts/python.exe -m skylapse_pipeline build-all`, ~6 min), validate, push.

## Files touched
- pipeline/skylapse_pipeline/{config,resolve,fetch_wise,fetch_spherex,catalogs,grid,calibrate,epochs,coadd,scale,export,build,qa,__main__}.py
- web/public/bundle/index.json, web/public/bundle/wise0855/

## Gotchas / know-how (local to this role; durable ones also go to ops/memory/KNOWHOW.md)
- System Python is 3.14 without astropy → local `.venv` (gitignored) with astropy/scipy/pillow/matplotlib/reproject/photutils.
- Data root auto-detected: SKYLAPSE_DATA env, else repo data/, else C:/Users/Murad/Downloads/skylapse-data/data. Derived/logs/qa → repo data/.
- Reprojection is our own (all_world2pix map + scipy map_coordinates), not reproject_interp — faster, SIP-aware.
- Frames: NaN → 0 and mask bit0; mask file only written when non-empty (mask_file null otherwise).
- Scaling: bg-subtract, then match Gaia ref-star aperture fluxes to the WISE epoch nearest 2018.0 (D1–D4→W1, D5–D6→W2).
- unWISE: exact 0 = no coverage (r_dra has 7 empty epochs → skipped, listed in manifest build.skipped_frames); small 0 islands = blanked saturated cores → sat bit.
- byw.tools was slow on Sat (~4–6 s/request) → live fetches W2 first, then rest of W2 + W1 in background.
- Science handoff: data/derived/<field>/spherex_images.csv + data/derived/<field>/frames/<id>.fits (grid WCS + MASK ext).

## Open questions / waiting on
- objects/target.json is a minimal stub (reference PM only); science overwrites it — build never overwrites an existing one.
