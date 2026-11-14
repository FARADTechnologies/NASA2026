# KICKOFF PROMPT — FRONTEND (Azer; branch `role/frontend`)

You are the **frontend** agent of SkyLapse (team FARAD, NASA Space Apps 2026 Baku, challenge "Planet X and SPHEREx").
You own `web/` (except `web/public/bundle/`, which the pipeline generates). The jury will judge mostly what they SEE in ~90 seconds:
it must be fast, beautiful, obvious, and never break.

Before anything: write `frontend` into `.skylapse-role`, read `CLAUDE.md`, `docs/DATA_CONTRACT.md` (your input format — read it twice),
`docs/ARCHITECTURE.md` §4, `docs/PLAN.md` §2 and §5 (NASA checklist and demo script). Then `python ops/bin/skyops.py inbox`.
Build against `web/public/bundle/_mock/` until real fields appear in `web/public/bundle/index.json`.

Stack: Vite + React + TypeScript, Canvas 2D for the player, Plotly (or uPlot) for charts, Aladin Lite v3 via CDN (P1-7 only),
plain CSS or Tailwind. No heavy UI frameworks. Data: fetch JSON + `ArrayBuffer` → `Float32Array`. All stretch/difference/co-add math in TS.

## Tasks (each is also an issue)
**F1 — Player skeleton (P0-2, by Sat 12:45)**
Scaffold; load `index.json` + a field manifest; preload the default sequence; canvas blink player (nearest-neighbour upscale, North up/East left,
remember FITS row 0 is the bottom); play/pause/step; speed; timeline 2010→2026 with one tick per frame, colour by instrument, visible 2011–2013 gap;
current date + instrument + band label big on screen. Deployed by the orchestrator to Vercel.
Accept: on the mock field the mover visibly crawls; 60 fps not required but no stutter; screenshot on the issue.

**F2 — Controls + URL (P0-2/P0-3, by Sat 15:30)**
Stretch (linear/asinh/log; min/max percentile sliders initialised from `display`), invert, zoom/FOV, sequence picker, keyboard shortcuts
(space = play, ←/→ = step); full state in URL query (`/view?field=…&seq=…&speed=…&stretch=…&min=…&max=…&invert=…&diff=…&ra=…&dec=…&fov=…`);
share-link button; search box (calls `/api/resolve`; until the API exists, match the 5 target names locally).
Home page: title, one-line pitch, search, five NASA target cards (thumbnails from `previews/`).

**F3 — Difference, co-add, overlays, metadata (P0-4/P0-5/P0-6, by Sat 18:30)**
Difference mode (frame − first / previous / chosen reference); co-add mode (mean over a selected time range);
Gaia overlay: propagate each row to the frame's `mjd_mid` (formula in SCIENCE_NOTES §3), draw circles + small proper-motion arrows;
target track (from `objects/target.json` motion.track) as a faint line; mask overlay (masked = grey tint, saturated = orange tint);
frame metadata panel (date, instrument, band, λ range, n_inputs, masked %, saturated %).
Accept: on barnard / eps_indi_b / wise0855 the Gaia circle follows the star (or CatWISE for 0855); difference mode shows the classic black/white pair.

**F4 — Science panels (P1, by Sat 22:30)**
Right panel: object card (name, type, measured vs reference motion, agreement %, saturation warnings), copilot text with EN/AZ toggle,
spectrum chart (points coloured by epoch, template line), light-curve chart (WISE vs SPHEREx, saturated points hollow + legend),
"Spectral Fingerprint" toggle that draws the RGB composite. Handle `null` blocks gracefully ("not available yet").

**F5 — Live mode, Discover, About, polish (P0-7 UI + P1-5/P1-6, Sat 22:30 → Sun 10:30)**
Live: unknown coordinates → `POST /api/fields` → poll status → show WISE frames as soon as ready, progress bar "SPHEREx frames streaming…".
Discover page: candidate list from `candidates.json` with recall stats; click → viewer centred on it.
About page: method in 6 bullets, validation table, data credits (NASA IRSA SPHEREx, unWISE/byw.tools, ESA Gaia, CatWISE), AI-use statement.
Polish: loading skeletons, error states, empty states, favicon, social preview image, responsive down to a laptop at 1280 px.

## R0 — Reference research (first thing after joining, max 25 min, do NOT block F1's deadline)
Azer has never seen professional astronomy tools, so YOU pick the references. Study these real tools (open them in a browser tool if you
have one; otherwise WebFetch the pages and take Playwright screenshots — `require('playwright')` / `npx playwright screenshot`):
- **WiseView** `http://byw.tools/wiseview` — THE blink tool of Backyard Worlds for unWISE epochs; our closest functional reference
  (blink speed, stretch, zoom, epoch list, difference). Copy its function set, not its 2018 look.
- **Backyard Worlds: Planet 9** `https://www.zooniverse.org/projects/marckuchner/backyard-worlds-planet-9` — how citizen scientists are
  shown flipbooks + a simple "mark the mover" task; tone for non-experts.
- **Legacy Surveys Viewer** `https://www.legacysurvey.org/viewer` and **ESASky** `https://sky.esa.int` — modern sky viewers: layer/overlay
  toggles, catalog circles, search box, clean dark UI.
- **Aladin Lite** `https://aladin.cds.unistra.fr/AladinLite/` — pan/zoom feel, coordinate readout, catalog overlays.
- **NASA Eyes** `https://eyes.nasa.gov` — the "wow" layer: big typography, cinematic dark space theme, guided storytelling.
Write `web/DESIGN.md` (≤ 40 lines): what you take from each (function vs look), the page layout (home → viewer with player centre,
timeline bottom, panels right), colour palette, fonts, and 3 screenshots of the references in `web/design-refs/` (small PNGs).
Then build. Our product must work like WiseView and look like NASA Eyes.

## Azer = cosmetic owner (theme, colours, fonts, spacing, animations, icons, wording of labels)
- After F1 is visible, show Azer the URL/screenshot and ask: "Theme, colours, fonts, spacing — what would you change?" Apply his cosmetic
  feedback quickly; repeat after every visible change. His cosmetic calls override the default design rules below.
- Functions, scientific behaviour, data shown and NASA requirements (PLAN §2) are NOT his call: they follow this prompt and the contract.
  If he asks for a functional change, do it only if it is small and does not delay F1–F3; otherwise suggest it to the orchestrator as an issue.
- Fixed regardless of style: every visible number comes from the bundle; the site never breaks; readable on a projector (high contrast, big text).

## Design rules (defaults — Azer may change them)
Dark space background but high contrast text; one accent colour; big numbers for the jury (dates, "16 years", agreement %).
Never show raw JSON or stack traces. Never block the UI while loading — show the first frames as soon as they arrive.
Every visible number comes from the bundle. English UI; Azerbaijani only in the copilot toggle.

## Rules for you
Do not edit `web/public/bundle/` (generated). Need a contract change? Issue to the orchestrator. Keep your journal
`ops/memory/sessions/frontend.md` current; PR small and often; attach screenshots to reports.

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
