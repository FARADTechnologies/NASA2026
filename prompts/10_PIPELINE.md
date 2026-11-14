# KICKOFF PROMPT — PIPELINE (Murad's second Claude Code session or Codex; branch `role/pipeline`)

You are the **pipeline** agent of SkyLapse (team FARAD, NASA Space Apps 2026 Baku, challenge "Planet X and SPHEREx").
You own `pipeline/` and the generated bundle in `web/public/bundle/`. You are on the **critical path**: the demo cannot exist without your data.

Before anything: write `pipeline` into `.skylapse-role`, then read `CLAUDE.md`, `docs/DATA_CONTRACT.md` (your output format — follow it exactly),
`docs/SCIENCE_NOTES.md` (tested URLs, flags, gotchas), `docs/ARCHITECTURE.md` §3. Then check your issues: `python ops/bin/skyops.py inbox`.
Data from last night's prefetch (finished 14 Nov 02:10, 0 failures): on Murad's computer it is in `C:\Users\Murad\Downloads\skylapse-data`
(read its `SUMMARY.md` first; raw SPHEREx incl. EPSF ≈ 15 GB in `data/raw/spherex/`, slim copies in `data/slim/`, WISE epochs, catalogs,
re-runnable scripts in `scripts/` that skip valid files). Point the pipeline at it (e.g. env var `SKYLAPSE_DATA`) or copy what you need
into this worktree's `data/` (gitignored). Elsewhere: unzip `skylapse_data_v1.zip` into `data/`. Never re-download what exists.
Read `docs/SCIENCE_NOTES.md` §7 (prefetch findings: saturation, image sizes, epoch counts) before writing loaders.

Stack: Python 3.11, astropy, astroquery, reproject, photutils, numpy, scipy, requests, tqdm, Pillow. Package `pipeline/skylapse_pipeline/`,
CLI `python -m skylapse_pipeline <cmd>`. Keep functions small and testable; log to `data/logs/`.

## Tasks (each is also an issue; do them in order; report on the issue when done)
**T1 — Skeleton + loaders (P0-1, by Sat 11:45)**
`resolve.py` (Sesame/SIMBAD + proper-motion propagation to 2018.0), `fetch_wise.py`, `fetch_spherex.py` (resumable, ≤10 parallel, retries, slim copies),
`catalogs.py` (Gaia DR3, CatWISE2020), all reading the prefetch cache first. `config.py` with the 5 targets.
Accept: `python -m skylapse_pipeline inventory` prints, per target, WISE epochs per band and SPHEREx images per detector per time cluster.

**T2 — First real bundle, WISE + SPHEREx D6 for wise0855 (P0-1, by Sat 13:00 — needed for M1 at 13:30)**
`grid.py` (TAN 192×192 at 2.75"/px centred on the 2018.0 position), `calibrate.py` (SPHEREx IMAGE−ZODI, flag mask by header names, OVERFLOW
as saturation), `epochs.py` (time clusters, gap > 30 d), `coadd.py` (inverse-variance mean per detector per cluster), `scale.py`
(sigma-clipped background subtraction; robust scaling on bright unsaturated low-PM Gaia stars to a reference W2 frame), `export.py`.
Accept: `python -m skylapse_pipeline build --field wise0855` writes `web/public/bundle/wise0855/`, `ops/bin/validate_bundle.py` PASSES,
and a quick matplotlib GIF (`data/qa/wise0855_thermal46.gif`) shows the brown dwarf crawling ~2' from 2010 to 2026. Attach the GIF to the issue.

**T3 — All detectors, all 5 targets (P0-1, by Sat 15:30)**
D1–D6 co-adds for every time cluster; sequences `thermal46` (W2+D6), `w1d4` (W1+D4), `spherex6`; masks (`.mask.u8`); previews; catalogs json;
`index.json` with all 5 fields. Accept: `build-all` produces 5 valid fields; GIFs for barnard and eps_indi_b show clear motion;
report saturation fractions for barnard, r_dra, rw_aur.

**T4 — Quality and metadata (P0-6, by Sat 17:30)**
Per-frame `quality` (masked_frac, saturated_frac, notes), `display` percentiles, provenance strings, credits.
Accept: manifest numbers are sane (no NaN in percentiles; frames not all-zero); validate PASS.

**T5 — Live runner for new coordinates (P0-7, by Sat 19:30)**
`live.py`: `build_live_field(ra, dec, fov_arcmin, out_dir, progress_cb)` — WISE first (write manifest after WISE so the viewer can start),
then SPHEREx D6, D3, then the rest, rewriting the manifest as frames arrive. Small FOV (default 6'). Hard time limits; never crash on IRSA errors.
Accept: running it on a random coordinate produces a valid WISE-only manifest in < 90 s and SPHEREx frames appear later; the orchestrator wires it into the API.

**T6 — RGB fingerprint frames + science handoff (P1-2, by Sat 22:00)**
`rgb_composites` per time cluster (D6/D3/D1 → r/g/b); expose per-image intermediates the science agent needs
(list of slim SPHEREx files with MJD and detector per field: `data/derived/<field>/spherex_images.csv`).

**T7 — Showcase fields (P2, only when asked)**: e.g. a field near the north ecliptic pole with many SPHEREx visits.

## Rules for you
- Output must pass `ops/bin/validate_bundle.py`. If the contract seems wrong or insufficient, open an issue for the orchestrator — do not change it.
- Keep total bundle size < 80 MB (192×192 float32 ≈ 147 KB per frame). Do not commit raw FITS.
- Be polite to servers (IRSA ≤ 10 parallel, byw.tools ≤ 2). Cache everything under `data/`.
- Everything reproducible: one command rebuilds a field. Record exact versions/releases in `build`.
- Update your journal `ops/memory/sessions/pipeline.md` after each step; lessons to `ops/memory/KNOWHOW.md`.
- If T2 is not done by 13:00, tell your human immediately so the orchestrator can adapt M1 (e.g. WISE-only first).

## START (do this now, in this order)
0. START-FOLDER CHECK (before anything else): the folder Claude Code was started in (`pwd` in your first Bash call) must
   directly contain `CLAUDE.md` and `.claude/settings.json`, and a "SKYLAPSE RECOVERY BRIEF" must have been injected at session start.
   - Kit only in a subfolder (e.g. `./skylapse_kit/CLAUDE.md`) → STOP. Tell the human: "Close this session and start Claude Code in
     <full path of the folder that contains CLAUDE.md>, then paste the same prompt again." Do not work around it (`cd` does not load hooks).
   - Folder right but no brief → run `sh .claude/hooks/run.sh .claude/hooks/session_start.py < /dev/null` to see the error, fix it,
     note it in `ops/memory/KNOWHOW.md`, and ask the human to restart the session (hooks load only at session start).
1. Confirm in ≤ 6 lines what you understood (your agent id, your first task, your output location).
2. Make sure `.skylapse-role` contains your agent id and that you are on your branch (`git checkout role/<agent>`; create it from `main` if missing).
3. Turn on autonomous mode: `python ops/bin/skyops.py auto on`.
4. Run `python ops/bin/skyops.py next --wait 540` (Bash timeout 600000 ms) and follow the loop in CLAUDE.md §7:
   START → `claim` → work → test → commit/push/PR → `submit` → journal → `next` again. The task list above is your map;
   the GitHub issues are the authoritative queue (they may differ — the issue wins).
5. If your human talks to you, stop and follow them. If `next` says PAUSED, stop and wait.
