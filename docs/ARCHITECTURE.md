# ARCHITECTURE — SkyLapse

## 1. Principles (decided — do not reopen without escalation)
1. **Static-first.** The 5 NASA targets and showcase fields are precomputed into a static bundle served with the website.
   The site must fully work with the API switched off. Live API is an add-on for new coordinates.
2. **One contract.** Pipeline/science write `docs/DATA_CONTRACT.md` format; web reads it. Mock data first, real data replaces it.
3. **Python for data, TypeScript for UI.** No data processing in the browser except display stretch/difference/co-add of ready frames.
4. **Simple tech the team already knows** + Claude Code. No databases, no auth, no microservices.

## 2. Repository layout
```
skylapse/
  CLAUDE.md  AGENTS.md  GEMINI.md  README.md  .env.example  .gitignore
  docs/            PLAN, ARCHITECTURE, DATA_CONTRACT, SCIENCE_NOTES, OPS_PROTOCOL, LOCAL_RULES, QA
  ops/             memory/ (PROJECT_STATE, DECISIONS, KNOWHOW, sessions/<role>.md), bin/skyops.py, team.json
  .claude/         settings.json, hooks/ (session_start.py, stop_check.py, pre_compact.py)
  pipeline/        skylapse_pipeline/ (python package) + tests/
     fetch_spherex.py  fetch_wise.py  catalogs.py  resolve.py
     calibrate.py (zodi, flags, saturation)  grid.py (common WCS, reproject)  epochs.py (time clusters)
     coadd.py  scale.py (cross-instrument display scaling)  export.py (bundle writer)  mock.py (contract-valid fake bundle)
     cli.py  → `python -m skylapse_pipeline build --field wise0855` / `build-all` / `mock`
  science/         skylapse_science/: astrometry.py (centroids, PM fit), photometry.py (light curves), spectra.py,
                   templates.py, discovery.py (cross-epoch linking, candidates), copilot.py (facts → LLM text)
  api/             FastAPI app: resolve, live field jobs (background thread + disk cache), copilot proxy
  web/             Vite + React + TypeScript app; web/public/bundle/ (generated, committed)
  pitch/           STORY.md, SLIDES.md, DEMO_SCRIPT.md, QA_ANSWERS.md, PROJECT_PAGE.md, REFERENCES.md, AI_USE.md, video/
  data/            (gitignored) raw/, slim/, cache/  ← prefetch zip is unpacked here
```

## 3. Pipeline (Python 3.11; astropy, astroquery, reproject, photutils, numpy, scipy, requests)
Per field:
1. `resolve` → target position, proper motion → field centre propagated to 2018.0.
2. `fetch_wise` → byw.tools epochs W1/W2 (size ≥ field + margin). Cache in `data/raw/wise/<field>/`.
3. `fetch_spherex` → TAP list → cutouts (parallel ≤ 10, retries, resume) → slim copies. Cache in `data/slim/spherex/<field>/`.
   If the prefetch zip exists, use it and fetch only what is missing.
4. `catalogs` → Gaia DR3 + CatWISE2020 cone (radius = half-diagonal of field).
5. `calibrate` → SPHEREx: IMAGE − ZODI, mask from flag names, saturation (OVERFLOW) mask; WISE: NaN/saturation mask.
6. `grid` → common TAN grid (default 192×192 px at 2.75" = 8.8'; configurable `--fov-arcmin`); `reproject_interp` for data, nearest for masks.
7. `epochs` → SPHEREx time clusters (gap > 30 d; optional `--bin-days`).
8. `coadd` → per detector per epoch inverse-variance weighted mean; record λ range and n_inputs.
9. `scale` → background subtraction + cross-instrument scaling on reference stars; percentiles for display.
10. `export` → frames .f32 (+ .mask.u8), previews .png, catalogs json, manifest.json, index.json — exactly per contract.
Science step (separate package, reads pipeline intermediates + bundle): astrometry → objects/*.json motion; spectra; light curves;
discovery → candidates.json; copilot texts. Then `export` merges science outputs into the bundle.
Performance budget: WISE part < 1 min/field; SPHEREx part 5–15 min/field from IRSA (that is why bundles are precomputed).

## 4. Web (Vite + React + TypeScript; Canvas 2D; Plotly or uPlot for charts; Aladin Lite v3 from CDN for the context map)
Routes: `/` (hero, search, 5 NASA targets as cards, link to Discover), `/view?field=&ra=&dec=&fov=&seq=&speed=&stretch=&min=&max=&invert=&diff=&overlay=`
(main viewer), `/discover`, `/about`.
Viewer layout:
- Centre: canvas blink player (nearest-neighbour upscaling, crosshair, click → object/spectrum), overlays (Gaia circles at the frame's epoch,
  proper-motion vectors, target track, flag/saturation mask tint).
- Below: timeline 2010 → 2026 with ticks per frame, instrument colour (WISE vs SPHEREx), hibernation gap 2011–2013 visible; play/pause/step; speed.
- Left/top controls: search, sequence picker, stretch (linear/asinh/log, min/max percentile sliders), invert, difference (vs first/previous/chosen),
  co-add range, FOV, Spectral Fingerprint toggle, share link.
- Right panel: object card (name, measured vs reference motion, agreement %, saturation warnings), copilot text EN/AZ, spectrum chart,
  light-curve chart, frame metadata (date, instrument, band, λ range, n_inputs, masked %, saturated %).
Data loading: fetch manifest → fetch all frames of the active sequence as ArrayBuffer → Float32Array; stretch per frame on the CPU (sizes are tiny).
Live fields: poll `/api/fields/{id}/status`, render frames as they arrive, show progress and "SPHEREx frames streaming…".
Design: dark, calm, legible; one accent colour; big readable numbers for the jury; English UI; Azerbaijani only for copilot text.

## 5. API (FastAPI, Python 3.11)
- `/api/resolve` (Sesame/SIMBAD + "ra dec" parsing, sexagesimal and degrees).
- `/api/fields` live jobs: background worker runs pipeline steps 1–10 for a small FOV; WISE first (status `wise_ready`), SPHEREx D6 then D3, D1…;
  writes the same bundle structure under `cache/fields/<id>/`; static file serving of that folder.
- `/api/copilot` (P2): server-side LLM call; keys from env.
- CORS: allow the web origin.

## 6. Deployment
- Web + bundle: Vercel (or Netlify / GitHub Pages). Build `web/`, serve `web/public/bundle` as static. Custom domain optional.
  After first deploy, submit the domain to the FortiGuard web-filter classification form (Space Apps guide recommends it).
- API: a small always-on instance (Railway / Render paid tier / Fly.io) with a persistent disk for the cache. Env: API keys.
  Emergency fallback for the pitch: run the API on a laptop and expose it via a Cloudflare tunnel.
- Repo: private until Sunday ~13:00, then public (the project link must be public with no login).
- Tag `v1.0` at feature freeze; the pitch uses that deploy.

## 7. Keys, models and limits
- Keys available: Anthropic (Claude), Google (Gemini), OpenAI, ElevenLabs. Store in `.env` / hosting env only. Never in git, never in the browser.
- Copilot model: `claude-sonnet-5-5` for precomputed texts; live endpoint may use `claude-haiku-5-5`. Fallback: any other provider's key.
- Claude Code subscription limits: use Sonnet for routine coding, Opus for orchestration/hard debugging. If a Pro limit is hit, continue in Codex,
  or the orchestrator may switch Claude Code to an API key (watch spend). Spread heavy work across machines through issues.
