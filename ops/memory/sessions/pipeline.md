# Journal — role: pipeline  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sun 15 Nov ~12:20 Baku (Kanan's PC)

## Current task
URGENT (human, freeze lifted until 14:30): live fields had EMPTY star catalogues. Fix in PR #127; asked orchestrator (#128) to
merge + 2-line API patch (needs_rebuild in init/submit) + redeploy. Then test via API: 113.7870 -7.2450, Luhman 16, 195.5 +28.5.

## Status
Local test PASS (Gaia/CatWISE full via VizieR CfA mirror, frames scaled, fast movers). Waiting for redeploy.
After API test: report timings + screenshots, tell Murad in Azerbaijani.

## Done (with proof)
- T1: `python -m skylapse_pipeline inventory` (run from `pipeline/` with `../.venv/Scripts/python.exe`) prints WISE epochs per band
  and SPHEREx images per detector per time bin for all 5 targets (wise0855 23/23 + 258 imgs in 3 bins, r_dra 48/48 + 2493 in 9 bins).
- T2: `build --field wise0855` → web/public/bundle/wise0855 (64 frames, 30 s). validate_bundle PASS.
  Target measured at predicted position in all 23 W2 epochs (15–27σ) and D6 t01/t02 (16/21σ); moves 47 px = 130" 2010→2026.
  QA: pipeline/qa/wise0855_thermal46.gif, pipeline/qa/wise0855_zoom.png.

## Next step (exact, so a fresh session can continue blindly)
- FEATURE FREEZE active (human, Sun ~11:40): only bug fixes. pitch/video movies stay as they are (catalogue-motion ring) — do NOT regenerate.
- All issues T1–T9 closed, all PRs merged. Loop: `.venv/Scripts/python.exe ops/bin/skyops.py next --wait 540`.

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
