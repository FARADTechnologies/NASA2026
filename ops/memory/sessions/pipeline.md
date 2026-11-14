# Journal — role: pipeline  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sat 14 Nov 15:00 Baku

## Current task
#4 T3 build-all (+ #5 T4, #6 T5, #7 T6 implemented in the same code) — final rebuild running, then one PR for T1–T6.

## Status
All 5 fields build and PASS per field (wise0855 64, barnard 64, eps_indi_b 68, r_dra 112, rw_aur 64 frames). Root FAILs only on size
(~83 MB incl. orchestrator _mock 12.6 MB) → asked orchestrator in #49. #38 answered (merged main d15eeee).
Live runner: WISE-ready in 83 s on a fresh coordinate (M101 area), SPHEREx frames then stream in per detector.

## Done (with proof)
- T1: `python -m skylapse_pipeline inventory` (run from `pipeline/` with `../.venv/Scripts/python.exe`) prints WISE epochs per band
  and SPHEREx images per detector per time bin for all 5 targets (wise0855 23/23 + 258 imgs in 3 bins, r_dra 48/48 + 2493 in 9 bins).
- T2: `build --field wise0855` → web/public/bundle/wise0855 (64 frames, 30 s). validate_bundle PASS.
  Target measured at predicted position in all 23 W2 epochs (15–27σ) and D6 t01/t02 (16/21σ); moves 47 px = 130" 2010→2026.
  QA: pipeline/qa/wise0855_thermal46.gif, pipeline/qa/wise0855_zoom.png.

## Next step (exact, so a fresh session can continue blindly)
- After build-all + validate: commit bundle + code, push (`git -c http.postBuffer=524288000 push`), open PR role/pipeline→main,
  submit #2–#7 reports (inventory output, validation, GIFs in pipeline/qa/, saturation fractions, live timing).
- Then: answer to #49 (size), help science with data/derived/<field>/ products, T7 only when asked.

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
