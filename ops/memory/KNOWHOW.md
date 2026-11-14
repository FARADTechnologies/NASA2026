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
[orchestrator] Railway var SKYLAPSE_CACHE had been mangled by Git Bash into "C:/Program Files/Git/data/cache" (live cache NOT on the volume, wiped on every deploy). Fixed Sat 23:40 to /data/cache. ALWAYS `export MSYS_NO_PATHCONV=1` before railway CLI calls with /paths.
[orchestrator] After API redeploy with pipeline fix #67: live wise_ready in 88 s (23 W2 frames) at 8.8′ (was ~6 min). Pre-warmed demo coordinate: 150.5 2.5.
[orchestrator] Organizers' Claude API (tunnel) = Anthropic Messages API (+ OpenAI-compatible /v1/chat/completions). claude-opus-5-5 there emits a long `thinking` block: send `"thinking": {"type": "disabled"}` and max_tokens ≥ 4000, else the answer is empty (stop_reason max_tokens). Base URL + key ONLY in env (ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY): the tunnel URL changes on restart.
[orchestrator] Sun 00:00: API v0.3.0 (pipeline #87 WISE-only, no TAP): live wise_ready 11 s, done 20 s.
[pipeline] Live unWISE epoch count varies by position (23 typical, ~427 at the NEP); HTTP 500 can mean one missing epoch, not the end. live.py probes the last epoch and fetches <=32 evenly spaced.
[science] Never cite literature values from memory: R Dra period '245.6 d (GCVS)' was unverified; AAVSO VSX gives 246.12 d (CDS/VizieR often down — use vsx.aavso.org).
[orchestrator] GitHub's PR merge ignores .gitattributes merge=union → KNOWHOW.md conflicts on PRs; fix: merge origin/main into the role branch locally (union applies) and push, then merge the PR.
