# Ask SkyLapse v2 — integrating FARAD's general-automation-system (decision, Sun 15 Nov 15:20)
Source: github.com/FARADTechnologies/general-automation-system (our team, YUNEX 2026, 3rd place): domain-agnostic action layer —
agent-core (model loop, task ledger, guards, session hub), services/agent + gateway, thin web clients (/app, /stage), domain packs.

## Architecture (chosen)
1. **Separate Railway service `ask`** built from that repo (`services/agent` + `gateway`), with a new domain pack `skylapse`
   (this branch: `ask-v2/domains/skylapse/`). The existing SkyLapse API (`api/`, Railway service `api`) and the static site stay untouched.
2. **No Bridge/core-bank:** SkyLapse has no private system to protect. "Read" capabilities fetch public facts from the static bundle
   (`/bundle/<field>/manifest.json`, `objects/*.json`, `candidates.json`); "ui" capabilities only change viewer state.
3. **UI state:** the agent publishes actions to its session hub; the SkyLapse web client (`?ask=v2` only) subscribes over WebSocket and
   applies them through the same `commandBridge` used by v1 (one whitelisted action list for v1 and v2).
4. **Guards reused:** actions must come from the user's words (agent-core guards); numbers only from the user's words or bundle facts;
   unknown targets rejected; every step narrated (speech synthesis) and logged. Questions about the current view are answered ONLY from
   the facts returned by the read capabilities.
5. **Voice:** push-to-talk from apps/web with `stt-hints.json` (object names); try-command chips from `try-commands.json`.
6. **/stage mirror** (phone → projector) comes for free from the session hub once 1–5 work.

## What is needed and why it is NOT on main today
- agent-core supports `read` and `prepare` kinds; a small `ui` kind (no side effects, risk R0) must be added.
- The agent loop needs a model endpoint. The organizers' Claude tunnel has been unreachable since ~12:00 (NXDOMAIN), so v2 cannot be
  tested end-to-end before the 15:30 decision. A separate service + WebSocket client in < 20 min would put the 16:05 demo at risk.
- **Decision (15:30):** v1 stays the default on main (offline parser guaranteed; Claude path when the tunnel works). v2 continues on
  this branch behind `?ask=v2`; the domain pack below is complete and reviewed.

## Domain pack coverage (`ask-v2/domains/skylapse/`)
Navigation (home/viewer/Discover/About) · open target / name / RA-Dec / live field · sequence, compare (off/2010/previous/chosen),
add (co-add), stretch, invert, zoom, speed, play/pause/step, jump to year, overlays, full screen, theme, share link · spectrum,
light curve, explanation EN/AZ · Discover candidates · facts about the current view (read-only).
