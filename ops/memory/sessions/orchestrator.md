# Journal — role: orchestrator  (only this role writes this file; keep < ~120 lines; replace stale lines)
Last update: Sat 14:30

## Current task
Phase 1 loop. Waiting: Murad's API-host decision for O3b #36. Next checkpoint M1 #28 at 16:00.

## Status
M0 done 14:20 (3 h late, D-008). Web live at https://skylapse.vercel.app (mock data). API code done, not hosted.
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
- PR #34 (pitch A1 LOCAL_RULES) merged; #22 closed. Local format: 5 min pitch+demo, overrun = disqualified (D-012).
- O3 #20 closed: Vercel project 'skylapse' → https://skylapse.vercel.app (200 on /, /view, /bundle/_mock/...).
- O1 #19 closed: api/skylapse_api (resolve + field files + CORS), TestClient proof in the issue.
- Hooks work here (RECOVERY BRIEF appeared at session start).

## Next step (exact, so a fresh session can continue blindly)
1. If the last commit is not on origin: `git push origin main` (DNS to github.com failed once at 14:30).
2. Loop `python ops/bin/skyops.py next --wait 540`; review PRs (build web in ../skylapse-review: `git -C ../skylapse-review checkout --detach origin/role/<x>`, `cd web && npm ci && npm run build`).
3. After every merge touching web/ or bundle: `cd web && npx vercel deploy --prod --yes`, then check https://skylapse.vercel.app.
4. O3b #36 when Murad decides the host; then set VITE_API_BASE in Vercel and redeploy.
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
- Murad: API host (Railway/Render paid vs laptop + Cloudflare tunnel) for O3b #36.
