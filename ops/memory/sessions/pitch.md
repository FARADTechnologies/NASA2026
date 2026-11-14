# Journal — role: pitch  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sun 15 Nov 00:30 Baku

## Current task
#75 answered (pipeline movies in pitch/video). #72 A7 submitted partial (deck v3 built, backup video done; rehearsal = Amal). **AMAL OWNS THE SLIDES NOW — never edit/regenerate the deck** (she said so Sun 00:25).
None claimed. Waiting for the queue; #64 (QA R2) and #24 (mentors, partial) in review. #27 A6 needs a human `approved` label (Sun).

## Status
All Saturday pitch deliverables done. Gaps depend on other agents: light curves R Dra/RW Aur (S3 #10), AI copilot texts (S5 #11), Gaia clutter fix deploy (#65 / #62).

## Done (with proof)
- A1 #22 LOCAL_RULES (5:00 total pitch+demo, overtime = DQ; 7 English slides via link; AI disclosed; AI media watermarked).
- A2 #23 pitch/STORY.md (7 slides, 1:30 demo, script 350 words, Amal read-aloud 3:00), pitch/FACTS.md (F1–F12, sources).
- A5 #26 QA_ANSWERS (28), AI_USE, REFERENCES, VIDEO_STORYBOARD, PROJECT_PAGE draft, SLIDES.md.
- Deck v2 = pitch/slides/SkyLapse_FARAD_v2.pptx (real screenshots slide 4, validation table slide 5). LIVE on Drive link (same link, uploaded as new version):
  https://docs.google.com/presentation/d/1IdgZwwna3FG_qA31ovPNDHE3TScZNbb8/edit?usp=sharing
- QA: R1 (mock) #25, R2/R2b real targets #64 → docs/QA.md. Bugs: #45 fixed, #65 (Gaia clutter, fix on role/frontend not deployed), #66 (empty panels).
- Validation: Barnard 99.8 %, ε Indi B 99.0 % (+99.3 % co-motion with A), WISE 0855 99.9 % (science/VALIDATION.md).
- A3 #24: Vugar Aliyev notes in pitch/MENTOR_NOTES.md, sent to orchestrator #52.

## Next step (exact, so a fresh session can continue blindly)
0. DO NOT touch the deck. Facts go to pitch/FACTS.md; offer them to Amal, she edits slides herself.
1. `python ops/bin/skyops.py next --wait 540` loop.
2. When target.json has `lightcurve`/`copilot` (check: curl https://skylapse.vercel.app/bundle/<field>/objects/target.json) → QA R3,
   DONE Sun 00:20: light curves + copilot EN/AZ live; deck v3 (pitch/slides/SkyLapse_FARAD_v3.pptx) + backup video pitch/video/SkyLapse_demo_backup.mp4 (1:22) sent to Amal.
3. Sun 11:00 Tural Salmanov rehearsal (A3 session 2 + A6): full timed run ≤ 4:40 on the live site; fill MENTOR_NOTES session 2.
4. A6 (#27, after `approved`): final PROJECT_PAGE fields, video link, repo public link, test every link in a private window, submit by 14:30 with Murad.

## Files touched
docs/LOCAL_RULES.md, docs/QA.md, pitch/* (STORY, FACTS, QA_ANSWERS, AI_USE, REFERENCES, VIDEO_STORYBOARD, PROJECT_PAGE, SLIDES, MENTOR_NOTES, slides/, qa/)

## Gotchas / know-how
- HARD LIMIT 5:00 pitch+demo (target 4:40). Never say "discovered"/"Planet X found".
- Deck rebuild: pptxgenjs in scratchpad (`npm install pptxgenjs@3.12.0`, NODE_PATH), render check via PowerPoint COM; screenshots via headless Edge
  `msedge --headless=new --window-size=1600,900 --force-device-scale-factor=2 --virtual-time-budget=15000 --screenshot=out.png URL` (timeout ≥ 200 s).
- Drive: upload new deck as NEW VERSION of the same file → link unchanged (file name stays "v1", cosmetic).
- git fetch can take minutes (bundle files); merges of main conflict on journal/KNOWHOW → keep ours / keep both.
- skyops sometimes "error connecting to api.github.com" → transient, just re-run.
- Messages to Amal: Azerbaijani (Latin), bold italic, action first.

## Open questions / waiting on
- Science: S3 #10 light curves, S5 #11 copilot. Frontend: #62 deploy (fixes #65), #66.
- Venue unknowns: HDMI/Wi-Fi, 15:30 submission mechanics, Global Nominee count. F9 Backyard Worlds wording, F10 SRDA 1000+, F11 rebuild command.
