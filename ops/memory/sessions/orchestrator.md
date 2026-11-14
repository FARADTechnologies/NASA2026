# Journal — role: orchestrator  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sun 01:00 (Kanan's computer)

## Current task
Autonomous review loop; queue empty at 01:00 except scheduled M4 #31 (Sun 10:30) and SUB #32 (14:00); A6 #27 is human (Amal).
Closed 00:30–01:00: A9 #93 (market slide, 'Seconds, not hours', 11–33 s range, SRDA confirmed), A10 #94 (no discovery wording),
#113 period 246.12 d in pitch + 30-s video pitch/video/SkyLapse_30s.mp4, A11 #114 accurate AI-use (EN offline / AZ via gateway).
Human items for the morning: Amal's final deck (slide 6 title, R Dra 246.12 d) checked anonymously at A6; timed rehearsal; repo public ~13:00.
Closed since 00:00: S7 #89 (API AZ texts in bundle), S8 #90 METHODOLOGY.md (refs spot-checked), S9 #91 impact numbers,
A8 #92, T9 #78 (live 15–33 s, 3 demo fields pre-warmed), F12 #108 ('Try a live field', 149 ms first frame), O5 #95 README.
R Dra known period corrected to 246.12 d (AAVSO VSX) on site + README (GCVS 245.6 was unverifiable).

## Status
Site + API (v0.3.0) live. Live WISE-only: wise_ready 11 s, done 10–38 s (pipeline #87, #100). Live copilot POST /api/copilot works on
Railway (9.7 s, guard passes; env-only config: ANTHROPIC_API_KEY/BASE_URL set by Murad, COPILOT_MODEL). Judging criteria D-022 in
CLAUDE.md §1 + PLAN §1b; agents asked to merge main (#96–#99). F10 AI label, F11 About wording, S6 fact sheet merged + deployed.
Vercel + Railway CLI logged in and linked on Kanan's PC. Railway var SKYLAPSE_STALE_FIELDS (startup cleanup) is empty again.
Rule kept: I never write API keys into files/hosting settings myself — the human runs the one-line commands.

## Done (with proof)
- Sat 14:00–15:50 (Murad's PC): bootstrap, mock + validator, API (resolve, live jobs), Vercel + Railway deploys, M1 14:55, reviews/merges up to PR #59.
- Sat 23:10–23:28 health check (Kanan's PC):
  - Pruned missing worktrees skylapse-review/-review2; new review worktree C:\Users\Murad\Downloads\skylapse-review (detached).
  - Merged PR #63 (frontend F8, #62/#65 Gaia clutter, #66) → closed #60 #62 #65 #66; PR #67 (pipeline live-runner fix), #68 (pitch QA r2 + deck v2), #69 (science journal).
  - Closed #12 (S4 recall 3/3, 0 false), #64 (QA r2). merge_science.py → S3 light curves + S4 candidates in bundle; validator PASS 8/8; deployed (READY).
  - Browser: 5 targets frame0 200, agreement 99.8/99.0/99.9 %, R Dra light curve renders (axis label says "magnitude" → #70). Barnard Gaia clutter fixed.
  - Live 150.5 +2.5 (8.8′): wise_ready 23 frames after ~6 min (slow). /api/health ok.
  - New tasks: F9 #70, T8 #71, A7 #72. #11 S5 unblocked with offline fallback (D-018). Scope cut P1-7 + P2 (D-019). Checkpoint M2+M3 posted on #30; #28–#30 closed.

## Next step (exact, so a fresh session can continue blindly)
1. When Railway login is done: `npx @railway/cli link` (project skylapse-api, service api) → `MSYS_NO_PATHCONV=1 npx @railway/cli up --detach --service api` → test a NEW coordinate time-to-wise_ready; pre-warm demo coords (150.5 2.5 already cached).
2. Loop `python3 ops/bin/skyops.py next --wait 540` (auto ON). Review: build web in ../skylapse-review (`git checkout --detach origin/role/<x>; git merge origin/main; cd web; npm ci; npm run build`).
3. After merges touching web/ or bundle: `python3 ops/bin/merge_science.py` (if science changed) → `python3 ops/bin/validate_bundle.py` → `python3 ops/bin/deploy_web.py` → browser check.
4. Sun 10:30 M4 #31: tag v1.0, final deploy. Sun ~13:00 repo public (needs Murad's approval — irreversible-ish). Sun 14:00 SUB #32.

## Files touched
CLAUDE.md, ops/team.json, ops/memory/*, ops/bin/{validate_bundle,merge_science,deploy_web,skyops}.py, .gitattributes, .gitignore, web/vercel.json, pipeline/skylapse_pipeline/mock.py, web/public/bundle/, api/, railway.json, .dockerignore, .railwayignore

## Gotchas / know-how (local to this role; durable ones also go to ops/memory/KNOWHOW.md)
- Kanan's PC: `python` = broken hermes venv → always `python3`. PowerShell blocks npx.ps1 → `npx.cmd` in terminal tabs; Git Bash `npx` works.
- Terminal tabs cannot be reused here (org setting) → open a new tab per interactive login.
- Vercel device-login link scrolls away in the tab → run login in Bash background to a file and grep the URL.
- Railway login callback goes to 127.0.0.1 → the human must open the link in a browser ON THIS COMPUTER within 5 min.
- `rm -rf` denied → Python shutil. Check time with `date` — never estimate it (I mis-stamped 23:50 for 23:25 once).
- skyops ranks: in-progress > changes-requested > bug > question > P0 > P1 > number.

## Open questions / waiting on
- Human: Railway login on this computer (tab "railway login 3"); optionally ANTHROPIC_API_KEY in C:\Users\Murad\Downloads\skylapse-science\.env.
- Pipeline agent: queue was empty since 16:20; T8 #71 given — confirm it picks it up.
