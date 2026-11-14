# PROJECT STATE — written ONLY by the orchestrator. Keep under ~70 lines. Update at every checkpoint and after big changes.
Last update: Sun 00:40 by orchestrator

## Milestone
M0 14:20 · M1 14:55 · M2+M3 checkpoint posted late (Sat 23:25, issue #30) — agents stalled ~16:00–23:00 (shared usage limit).
Next: **M4 FEATURE FREEZE Sun 10:30** (tag v1.0) · Sun 11:00 rehearsals (A6) · repo public ~13:00 · submit by 14:30.

## Machines
- Orchestrator, pipeline, science now run on **Kanan's computer** (same paths C:\Users\Murad\Downloads\...). Murad's computer is no longer used.
- On this computer: use `python3` (plain `python` is a broken venv); in PowerShell use `npx.cmd` (npx.ps1 is blocked by the execution policy).
- Frontend (Azer) and pitch (Amal) restarted at home.

## Deployed
- Web: **https://skylapse.vercel.app** — deploy ONLY with `python3 ops/bin/deploy_web.py` (Vercel login OK on this computer).
- API v0.3.0: https://api-production-02611b3c.up.railway.app (Railway trial, D-015), reached as `/api/*`; live WISE-only 11–38 s; optional live copilot `/api/copilot` (env-only config, D-021). CLI logged in + linked on this computer.
  Redeploy: `MSYS_NO_PATHCONV=1 npx @railway/cli up --detach --service api` (needs `railway link` to project skylapse-api after login).
- Repo: https://github.com/FARADTechnologies/NASA2026 — private until Sun ~13:00. PRs merged with merge commits (D-016).

## Bundle
- 5 real fields, validator PASS 8/8, 70 MB. Science S1 motion, S2 spectra, S3 light curves, S4 candidates merged via `python3 ops/bin/merge_science.py` (D-017).
- Copilot (S5) EN+AZ in the bundle (merged 23:35). Backup movies: pitch/video/ (T8 #71 ✅).

## Who is doing what (open issues)
- orchestrator: review loop; M4 freeze #31 Sun 10:30 (tag v1.0); SUB #32
- pipeline (Kanan's PC, `skylapse-pipeline`): all done (T1–T8); idle
- science (Kanan's PC, `skylapse-science`): all done (S1–S5); idle
- frontend (Azer, home): F9 #70 truthful light-curve axis + period line, Discover recall, ε heading (P0)
- pitch (Amal, home): A7 #72 deck v3 + backup recording + timed rehearsal (P0) · A6 #27 Sun 11:00 (human)
- captain Deneme: FARADTechnologies

## Status of P0 / P1
P0-1…P0-6 ✅ · P0-7 live ✅ (wise_ready 88 s after fix, D-020) · P0-8 ✅ · P0-9 ✅ in UI (99.8 / 99.0 / 99.9 %) · P0-10 ◐ (deck v2)
P1-1 spectra ✅ · P1-2 RGB ✅ · P1-3 light curves ✅ data (R Dra 246 d vs 245.6 d), axis label fix #70 · P1-4 copilot ✅ EN+AZ live (D-018) · P1-5 Discover ◐ (recall 3/3, 0 false) · P1-6 About ✅
Cut (D-019): P1-7 Aladin, all P2.

## Blockers / risks
- Local rule: pitch + demo = 5 min, overrun = disqualified (D-012). Demo live step must use a pre-warmed coordinate (`150.5 2.5`).
- Venue Wi-Fi flaky → phone hotspot + offline backup movies/video (#71, #72).
- Railway trial credits could run out → fallbacks in D-015.
- No ANTHROPIC_API_KEY on this computer → copilot via offline fallback (D-018).

## Next 3 priorities (tonight)
1. ✅ done 23:40: API redeployed, live 88 s, cache on volume. Backup movies on main (pitch/video).
2. Frontend #70 (truthful light-curve axis — validity) → merge, deploy, QA round 3.
3. Pitch #72 deck v3 + backup recording + one timed rehearsal.
