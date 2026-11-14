# Journal — role: pipeline  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sun 15 Nov 00:45 Baku (2nd computer, user knany)

## Current task
#78 T9 live API test + demo pre-warm: done, submitted (review). Fixes merged: PR #87 (WISE-only no TAP hang), PR #100 (NEP epochs, missing epoch).
#71 T8 movies submitted earlier (PR #73).

## Status
Autonomous loop ON. Live via API: wise_ready 10-20 s, done 15-33 s. Demo fields cached: Luhman 16 (162.3057 -53.3177),
Teegarden (43.2716 16.8623), Kapteyn (77.9651 -45.0470), fov 8.8. Table: pipeline/qa/live_api_test.md. Pitch told (#104).

## Done (with proof)
- T1: `python -m skylapse_pipeline inventory` (run from `pipeline/` with `../.venv/Scripts/python.exe`) prints WISE epochs per band
  and SPHEREx images per detector per time bin for all 5 targets (wise0855 23/23 + 258 imgs in 3 bins, r_dra 48/48 + 2493 in 9 bins).
- T2: `build --field wise0855` → web/public/bundle/wise0855 (64 frames, 30 s). validate_bundle PASS.
  Target measured at predicted position in all 23 W2 epochs (15–27σ) and D6 t01/t02 (16/21σ); moves 47 px = 130" 2010→2026.
  QA: pipeline/qa/wise0855_thermal46.gif, pipeline/qa/wise0855_zoom.png.

## Next step (exact, so a fresh session can continue blindly)
- `.venv/Scripts/python.exe ops/bin/skyops.py next --wait 540` (plain `python` is broken on this computer).
- When science writes motion.track into the bundle: rerun `cd pipeline && ../.venv/Scripts/python.exe -m skylapse_pipeline movies`.

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
- Live: unWISE epochs per position vary (23 typical, ~427 at NEP) → live probes last epoch, fetches <=32 evenly spaced; HTTP 500 can be one missing epoch.
- API caches live fields by RA/Dec rounded 4 dp + fov 0.1; site default fov 8.8. Stale cached fields: ask orchestrator (SKYLAPSE_STALE_FIELDS).
- Science handoff: data/derived/<field>/spherex_images.csv + data/derived/<field>/frames/<id>.fits (grid WCS + MASK ext).

## Open questions / waiting on
- objects/target.json is a minimal stub (reference PM only); science overwrites it — build never overwrites an existing one.
