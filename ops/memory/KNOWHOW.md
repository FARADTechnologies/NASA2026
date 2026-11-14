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
[orchestrator] API = Railway project skylapse-api, service api, volume /data. Redeploy: `npx @railway/cli up --detach --service api` from repo root. Git Bash: set MSYS_NO_PATHCONV=1 for '/data'-style args. Dockerfile path is set by service var RAILWAY_DOCKERFILE_PATH=api/Dockerfile (railway.json dockerfilePath was ignored). Web reaches it via the /api/* rewrite in web/vercel.json.
[pipeline] System Python 3.14 has no astropy: pipeline uses repo-local `.venv` (gitignored); run `cd pipeline && ../.venv/Scripts/python.exe -m skylapse_pipeline …`.
[pipeline] Venue network: `git push` of an 11 MB bundle gave HTTP 408; `git -c http.postBuffer=524288000 push` works better. GitHub API had TLS timeouts at 14:20.
[pipeline] SPHEREx IMAGE header WCS has SIP; use WCS(IMAGE header).all_world2pix. Wavelength: WCS(hdr, fobj=hdul, key="W") with .sip=None.
[pipeline] Bundle frames: NaN pixels are written as 0 with mask bit0 set; mask_file is null when a frame has no masked/saturated pixel.
[orchestrator] Vercel Hobby BLOCKS deploys when the last git commit author is not on the Vercel team (squash-merged PRs from Azer/Amal). Always deploy with `python ops/bin/deploy_web.py` (deploys a git-free copy of web/).
[orchestrator] PRs are merged with MERGE COMMITS (since Sat 14:55; squash caused journal conflicts). Still: after your PR is merged, `git fetch origin && git merge origin/main`, and open a NEW PR for later commits.
[pipeline] On the 2nd computer (user knany) plain `python` resolves to a broken hermes venv (python311.dll missing): run skyops with `.venv/Scripts/python.exe ops/bin/skyops.py …`.
[science] On the 2nd computer `python` on PATH is a broken venv; run skyops with `py ops/bin/skyops.py` and science code with science/.venv/Scripts/python.exe.
[orchestrator] Kanan's computer: plain `python` is a broken venv → use `python3` (also for skyops: `python3 ops/bin/skyops.py ...`). In PowerShell tabs use `npx.cmd` (npx.ps1 blocked by execution policy).
[orchestrator] Live coordinates take ~6 min to first frames at the default 8.8′ FOV on the free Railway tier (Sat 23:19). In the demo use a pre-warmed coordinate (`150.5 2.5` is cached), never a new one.
