# KNOW-HOW — one line per lesson, prefixed with your role. Append only. Newest at the bottom.
[seed] IRSA SPHEREx TAP query by position takes ~35 s; cutout ~30 s and ~4 MB each; no CORS → backend only.
[seed] Cutout URL: https://irsa.ipac.caltech.edu/{uri}?center={ra},{dec}d&size={deg}; ~5% transient failures → retry with backoff.
[seed] byw.tools/cutout?ra=&dec=&size=&band=&epoch= returns unWISE epoch FITS in <1 s; HTTP 500 = past last epoch; max 2 concurrent.
[seed] SPHEREx IMAGE is NOT zodi-subtracted: always IMAGE − ZODI. Do not mask the SOURCE flag. OVERFLOW = saturation.
[seed] Read flag bit names from the image header; never hardcode bit numbers.
[seed] Barnard's Star has moved ~4.5' since J2000: centre fields at the position propagated to 2018.0.
[seed] LVF: same star in two SPHEREx images is usually at two different wavelengths → not variability.
[seed] WISE 0855 is not in Gaia; use CatWISE2020 / literature for its reference proper motion.
[science] unWISE epoch coadds write saturated cores as exact 0 (hole ~6 px for Barnard, 2016+ epochs); fit the wings (Moffat), never centroid the hole box.
[science] Fitted WISE parallaxes are biased by seasonal scan-direction centroid offsets (~0.25" for bright sources); PM is fine. Do not quote WISE parallax.
[science] Science Python env: science/.venv (pip install -r science/requirements.txt); system Python 3.14 has no astropy.
[pitch] LOCAL RULE Baku: presentation+demo = 5:00 TOTAL (overtime = disqualified), Q&A 5:00, max 7 English slides shared by link; AI media need watermark.
[orchestrator] Web deploy = Vercel CLI from Murad's PC: `cd web && npx vercel deploy --prod --yes` → https://skylapse.vercel.app (project 'skylapse'; Git auto-deploy NOT connected: Vercel GitHub app is not installed on FARADTechnologies). Redeploy after every merge to main.
