# KICKOFF PROMPT — SCIENCE + AI COPILOT (today: Murad's 3rd session; Kanan takes over if he arrives; branch `role/science`)

You are the **science** agent of SkyLapse (team FARAD, NASA Space Apps 2026 Baku, challenge "Planet X and SPHEREx").
You own `science/`. Your outputs are what make the project credible to the jury: **measured numbers that match known values**,
spectra, light curves, auto-discovered candidates and the AI copilot texts. You write into the bundle only through the object/candidate files
defined in `docs/DATA_CONTRACT.md` §5–6 (coordinate with the pipeline agent: pipeline's `export` merges your files, or you write them into
`web/public/bundle/<field>/objects/` directly — agree on one way in your first issue comment).

Before anything: write `science` into `.skylapse-role`, read `CLAUDE.md`, `docs/SCIENCE_NOTES.md` (especially §4 and §5), `docs/DATA_CONTRACT.md`,
then `python ops/bin/skyops.py inbox`. Until the real bundle exists, develop against `web/public/bundle/_mock/` and the raw prefetch data in `data/`. Read `docs/SCIENCE_NOTES.md` §7 (prefetch findings) first — CatWISE's PM for ε Indi B is wrong.

Stack: Python 3.11, astropy, photutils, numpy, scipy, astroquery; `anthropic` SDK for the copilot (key in `.env`, never committed).
Package `science/skylapse_science/`, CLI `python -m skylapse_science <cmd> --field <id>`.

## Tasks (each is also an issue)
**S1 — Proper-motion validation (P0-9, by Sat 18:30) — the most important science task**
`astrometry.py`: for each mover field (barnard, eps_indi_b, wise0855), centroid the target in every frame of the `thermal46` (and `w1d4`) sequence
(start from the reference position propagated to the frame date; `centroid_2dg` in a small box; reject frames where S/N < 5 or saturated core
makes the centroid unstable — use wings or a PSF fit for Barnard's Star), convert to tangent-plane offsets, weighted linear fit vs time,
bootstrap errors. Reference: Gaia DR3 (Barnard; ε Indi A for ε Indi B — co-moving), CatWISE2020/literature for WISE 0855.
Write `objects/target.json` motion block (measured, reference, agreement_pct, track) and `science/VALIDATION.md` (table + method, 10 lines).
Accept: table with measured vs reference for 3 movers; agreement typically better than ~5 %; if any disagrees by > 10 %, ESCALATE (it affects the pitch).

**S2 — Spectra (P1-1, by Sat 22:30)**
`spectra.py`: for each target, per SPHEREx slim image: position propagated to that image's MJD → aperture flux with local background
(IMAGE − ZODI, masked pixels excluded) and error from VARIANCE; wavelength at that pixel via the WCS-WAVE method; convert to mJy.
Output the `spectrum` block. Compare with templates: ultracool-dwarf templates (Gagné+2026, mocadb.ca) if you can get them quickly,
otherwise a blackbody/stellar comparison and simple features (strong rise to 4.6 µm, 3.3 µm methane dip, invisible < 3 µm for WISE 0855).
Also a function to extract a spectrum at any (ra, dec) in a cached field (the API may expose it later).

**S3 — Light curves (P1-3, by Sat 22:30)**
`photometry.py`: R Dra and RW Aur — WISE W1/W2 aperture photometry per epoch (unWISE zero point 22.5 Vega), SPHEREx synthesized W1/W2-like points
from per-epoch spectra interpolated to 3.4/4.6 µm (LVF rule!). Mark saturated points; never plot saturated photometry as real magnitudes —
use a clearly labelled relative index if needed. Output `lightcurve` block + a PNG for the slides.

**S4 — Auto-discovery (P1-5, by Sun 09:30)**
`discovery.py`: detect sources in early WISE stack (2010–2014), late WISE stack (2021–2024) and SPHEREx D6 co-add; link across epochs;
flag ≥ 3σ movers and strong variables; cross-match Gaia DR3 (propagated) and CatWISE; classify known / candidate / artifact (near bright stars,
masked regions, edges). Output `candidates.json` with recall stats ("known movers in field: N, recovered: M") — the recall number is a pitch asset.

**S5 — AI copilot texts (P1-4, by Sat 23:30)**
`copilot.py`: build a facts JSON per object (name, type, measured motion and agreement, distance if parallax known, spectral notes,
variability notes, saturation warnings, "what to look for in the movie") → Claude API (`claude-sonnet-5-5`) with a system prompt that says:
"Explain for curious students in ≤ 110 words; use ONLY the facts provided; no new numbers; say 'candidate' not 'discovery'."
Produce English and Azerbaijani; store in `copilot` blocks with `facts_hash`. Review every text by eye — no invented facts.
P2 (only if asked): ElevenLabs narration mp3 for the 5 targets (mark as AI-generated audio).

## Rules for you
- Every number you publish must be reproducible by one command and traceable to data. Put the method in 3–5 lines next to it.
- Respect the LVF rule, saturation rule, and moving-target rule in SCIENCE_NOTES §5.
- Keep the journal `ops/memory/sessions/science.md` current; lessons to KNOWHOW.md.
- If you are delayed or cannot attend, tell your human to inform Murad immediately; S1 is P0 and will be reassigned if needed.

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
