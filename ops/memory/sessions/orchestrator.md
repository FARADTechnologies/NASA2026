# Journal — role: orchestrator  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sat 15:50

## Current task
Phase 1 autonomous loop (`skyops next`). Next: CHECKPOINT M1 #28 at 16:00 (needs pipeline T2 real wise0855).

## Status
M1 reached 14:55. Web + API live. Waiting on pipeline T3 (5 fields + merge-science).
Pipeline (T1 #2, not claimed yet but writing code) and science (S1 #8 claimed) are running in their worktrees.

## Done (with proof)
- Folder = repo working copy of FARADTechnologies/NASA2026 (kept remote LICENSE; kit README replaced the 1-line placeholder).
- LANGUAGE RULE added to CLAUDE.md §5 (before first push).
- team.json: captain FARADTechnologies, Murad = MuradGaramollayev (orchestrator/pipeline/science), Azer = AzarValiyev, Amal = JustEyml. Kanan has no account in repo.
- Labels; branches role/pipeline, role/science, role/frontend, role/pitch pushed.
- Worktrees: C:\Users\Murad\Downloads\skylapse-pipeline (role/pipeline), C:\Users\Murad\Downloads\skylapse-science (role/science), .skylapse-role written.
  Review worktree: C:\Users\Murad\Downloads\skylapse-review (detached; for building PRs).
- Issues #1–#32 created (+ #36 O3b). Map in ops/tmp/issue_numbers.json and PROJECT_STATE.
- O0 #1 closed: mock.py + validate_bundle.py + _mock bundle on main; validator PASS; negative test FAIL as expected.
- PR #35 (frontend F0–F3) merged after `npm ci && npm run build` + browser check on mock; #13–#16 closed.
- PR #34 (pitch A1) merged; #22 closed. PR #44 S1 merged (#8 closed: 99.8/99.0/99.9 %). PR #42 F4+F5 merged (#17,#18). PR #37 pitch A2+A5 merged (#23,#26).
- O3b #36 closed: Railway API online, /api/* proxied via web/vercel.json.
- 15:00: #45 #47 (frontend bugs) merged via PR #48 #50; pitch A4 #25 (PR #46), A3 #24 (PR #55) merged; Q #33 #43 #49 #52 answered.
- PR #53 pipeline T1+T2 merged, #2 #3 closed → M1 reached 14:55 (wise0855 real movie live). New tasks: F6 #51 demo speed, F7 #54 clarity.
- 15:50: PR #59 pipeline T3–T6 merged (5 real fields, #4–#7 closed); S2 #9 merged; merge_science.py ran (validation 99.8/99.0/99.9 % in UI); O2 #21 closed (live WISE-only on Railway works in UI). Open: F8 #60, Gaia clutter #62, QA r2 #64, S3/S5/S4, checkpoint M2 #29 at 19:30.
- skyops accept now uses merge commits (D-016); validator sizes nested roots separately; deploy_web.py skips _mock once real fields exist. Local format: 5 min pitch+demo, overrun = disqualified (D-012).
- O3 #20 closed: Vercel project 'skylapse' → https://skylapse.vercel.app (200 on /, /view, /bundle/_mock/...).
- O1 #19 closed: api/skylapse_api (resolve + field files + CORS), TestClient proof in the issue.
- Hooks work here (RECOVERY BRIEF appeared at session start).

## Next step (exact, so a fresh session can continue blindly)
0. Usage limit hit at 15:50; auto mode was turned OFF. On resume: `python ops/bin/skyops.py auto on`, then loop `next --wait 540`.
1. If the last commit is not on origin: `git push origin main` (DNS to github.com failed once at 14:30).
2. Loop `python ops/bin/skyops.py next --wait 540`; review PRs (build web in ../skylapse-review: `git -C ../skylapse-review checkout --detach origin/role/<x>`, `cd web && npm ci && npm run build`).
3. After every merge touching web/ or bundle: `python ops/bin/deploy_web.py` (NOT plain vercel deploy: blocked for non-team commit authors), then check https://skylapse.vercel.app.
4. API redeploy: `MSYS_NO_PATHCONV=1 npx @railway/cli up --detach --service api` (repo root). O2 #21 after pipeline T5 #6: WISE-only live, < 300 MB RAM (D-015).
5. CHECKPOINT M1 #28 at 16:00 (real wise0855 bundle from pipeline T2 #3).

## Files touched
CLAUDE.md, ops/team.json, ops/memory/*, .gitattributes, .gitignore, web/.gitignore (Vercel CLI), pipeline/skylapse_pipeline/mock.py, ops/bin/validate_bundle.py, web/public/bundle/_mock/, api/

## Gotchas / know-how (local to this role; durable ones also go to ops/memory/KNOWHOW.md)
- `rm -rf` is denied by settings → use Python shutil for temp cleanup.
- skyops ranks: in-progress > changes-requested > bug > question > P0 > P1 > issue number. Same-agent tasks need no `after` chaining.
- Vercel Git auto-deploy is NOT connected (Vercel GitHub app not on FARADTechnologies) → deploy by CLI after merges.
- Python 3.14 on this machine; astropy not installed globally (mock uses numpy+Pillow only). FastAPI/uvicorn/httpx installed.
- Check the time with `date` — do not estimate it.

## Open questions / waiting on
- Pipeline agent commits code but never claimed T1–T6 (#2–#7): check at M1 that it uses the issue loop.
- New rule: ESC issues → explain to Murad in the 5-part Azerbaijani format (CLAUDE.md §7b); agents asked to merge main (#38–#41).
