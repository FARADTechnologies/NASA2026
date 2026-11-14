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
- DONE: names + timing (3:00 read-aloud) recorded; #23 submitted.
- Then `python ops/bin/skyops.py next --wait 540` → likely A4 QA (#25) once a deployed URL exists, or A5 (#26: QA_ANSWERS, AI_USE, REFERENCES first — no site needed).

## Files touched
- docs/LOCAL_RULES.md, pitch/STORY.md, pitch/FACTS.md, ops/memory/sessions/pitch.md

## Gotchas / know-how (local to this role; durable ones also go to ops/memory/KNOWHOW.md)
- HARD LIMIT: 5:00 for presentation + demo together, over time = disqualified. Target 4:40. Q&A 5:00 separate.
- Max 7 slides, English, shared via link. AI images/videos need watermark; never AI NASA logos/flags/patches.
- Push may be rejected (orchestrator commits to role/pitch, e.g. team.json) → `git pull --rebase origin role/pitch` then push.
- Messages to Amal: Azerbaijani (Latin), bold italic, action first.

## Open questions / waiting on
- (names: Amal Mirzayev, Hasan Dadashzada, Murad Qaramollayev, Azer Valiyev, Kanan Pashazada)
- Science: [X %] PM agreement (S1 #8) → FACTS F6. Orchestrator: deployed URL (for QA A4 + screenshots).
- Unknowns at venue: HDMI/Wi-Fi, submission mechanics, Global Nominee count.
## Update ~15:35 — A5 #26 in progress
- Done: QA_ANSWERS (25), AI_USE, REFERENCES, VIDEO_STORYBOARD, slides v1 (pitch/slides/SkyLapse_FARAD_v1.pptx, validated + rendered via PowerPoint COM).
- Slides link (Drive, public view): see pitch/SLIDES.md. Next: after deploy → real screenshots on slide 4, then re-submit #26 as done.
- Tooling: pptxgenjs in scratchpad (`npm install pptxgenjs@3.12.0`); no LibreOffice → render PNGs with PowerPoint COM (powershell Slides.Item(i).Export).
## Update ~16:00
- A4 #25 R1 done on mock (docs/QA.md), bug #45 (phone layout). #41 merged main (e4ca0d8; earlier "c3b3c4b" answer corrected).
- Site: https://skylapse.vercel.app (mock only). API resolve works. Next: A3 Vugar Aliyev mentor ~16:00 (Amal), QA R2 + slide-4 screenshots when real fields land.
- Gotcha: `git fetch` can take minutes (bundle files) → run merges in background / long timeout; journal + KNOWHOW conflict on merge → keep ours for journal, both sides for KNOWHOW.
## Update ~16:05 — A3 #24 claimed
- pitch/MENTOR_NOTES.md has 5+5 questions. Waiting for Amal's notes from Vugar Aliyev → fill notes, `ask --to orchestrator`, push. Tural session Sun 11:00.
## Update ~16:20
- A3 #24 submitted partial: Vugar notes in MENTOR_NOTES.md, orchestrator told (#52). Tural Salmanov Sun ~11:00 (full rehearsal).
- Slide 6 users changed (generator updated) → Drive copy is OUTDATED until next rebuild (do it together with real screenshots; Amal re-uploads).
- Drafted pitch/PROJECT_PAGE.md (A6 prep, all Space Apps fields). Next: `next --wait 540`; QA R2 + screenshots when real fields land.
## Update ~17:35
- Real bundle live (5 targets). QA R2 logged in docs/QA.md; bugs #65 (Gaia clutter, P1), #66 (empty panels, P2), #45 still open.
- Validation: Barnard 99.8 %, ε Indi B 99.0 % (+99.3 % co-motion with A), WISE 0855 99.9 % → FACTS F6, STORY, QA_ANSWERS, PROJECT_PAGE, deck.
- Deck v2 built (real screenshots). Screenshot recipe: headless Edge `msedge --headless=new --window-size=1600,900 --force-device-scale-factor=2 --virtual-time-budget=15000 --screenshot=out.png URL` (timeout ≥ 200 s), crop with PIL.
- DONE: Amal uploaded v2 as a new Drive version; shared link serves v2 content (checked ~19:00). Drive file name still says v1 (cosmetic).
## Update ~17:50
- #64 A4b submitted (QA R2/R2b, deck v2, FACTS). #45 fixed by frontend. Open: #65, #66. v2 live on the Drive link.
- Next: `next --wait 540`; when S3 (#10) / S5 (#11) land → QA R3, slide 5 RW Aur/R Dra row, demo copilot step, AZ copilot screenshot.
