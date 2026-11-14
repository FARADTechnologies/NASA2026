# Journal — role: pitch  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sat 14 Nov ~14:35 Baku

## Current task
#23 A2 — pitch/STORY.md (story, 7-slide outline, 5-min script). Submitted once Amal times a read-aloud.

## Status
A1 #22 submitted (PR #34). A2 #23 claimed; STORY.md + FACTS.md written and pushed to PR #34; waiting for Amal's timed read-aloud + member full names.

## Done (with proof)
- Joined repo: folder = working copy on role/pitch (origin FARADTechnologies/NASA2026). gh login JustEyml.
- A1: docs/LOCAL_RULES.md filled from Amal's notes (commit fdcbe32), PR #34, submitted #22. Orchestrator told in #33.
- A2: pitch/STORY.md (story, 7 slides in organizers' order, 1:30 demo, script 350 words), pitch/FACTS.md (F1–F12 with sources).

## Next step (exact, so a fresh session can continue blindly)
- Get from Amal: full names of members for slide 1; her timed read-aloud of STORY.md §4 + demo → write time into STORY.md, submit #23.
- Then `python ops/bin/skyops.py next --wait 540` → likely A4 QA (#25) once a deployed URL exists, or A5 (#26: QA_ANSWERS, AI_USE, REFERENCES first — no site needed).

## Files touched
- docs/LOCAL_RULES.md, pitch/STORY.md, pitch/FACTS.md, ops/memory/sessions/pitch.md

## Gotchas / know-how (local to this role; durable ones also go to ops/memory/KNOWHOW.md)
- HARD LIMIT: 5:00 for presentation + demo together, over time = disqualified. Target 4:40. Q&A 5:00 separate.
- Max 7 slides, English, shared via link. AI images/videos need watermark; never AI NASA logos/flags/patches.
- Push may be rejected (orchestrator commits to role/pitch, e.g. team.json) → `git pull --rebase origin role/pitch` then push.
- Messages to Amal: Azerbaijani (Latin), bold italic, action first.

## Open questions / waiting on
- Amal: member full names; timed read-aloud.
- Science: [X %] PM agreement (S1 #8) → FACTS F6. Orchestrator: deployed URL (for QA A4 + screenshots).
- Unknowns at venue: HDMI/Wi-Fi, submission mechanics, Global Nominee count.
