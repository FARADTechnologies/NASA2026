# PROJECT STATE — written ONLY by the orchestrator. Keep under ~70 lines. Update at every checkpoint and after big changes.
Last update: Sat 15:26 by orchestrator

## Milestone
M0 done 14:20 (3 h late, D-008). **M1 reached 14:55**: https://skylapse.vercel.app/view?field=wise0855 plays the real WISE 0855 movie.
Next: M2 at 19:30 (all P0-1…P0-6 on 5 targets; WISE-live). Then M3 22:30 · M4 FREEZE Sun 10:30 · Submit Sun 14:30.

## Deployed
- Web: **https://skylapse.vercel.app** — deploy ONLY with `python ops/bin/deploy_web.py` (Vercel blocks commits by non-team authors; plain `vercel deploy` fails).
- API: https://api-production-02611b3c.up.railway.app (Railway trial, no card, D-015) — the site reaches it as same-origin `/api/*` (web/vercel.json rewrite).
  Redeploy API: `MSYS_NO_PATHCONV=1 npx @railway/cli up --detach --service api` from repo root. Live jobs = WISE only (512 MB RAM).
- Repo: https://github.com/FARADTechnologies/NASA2026 — private until Sun ~13:00. PRs merged with merge commits (D-016).

## Bundle
- Real fields LIVE: **all 5** (PR #59, 70 MB). Science S1 motion + S2 spectra merged into objects/target.json via `ops/bin/merge_science.py` (D-017).
- `_mock/` stays in git but is not deployed once real fields exist. Validator: `python ops/bin/validate_bundle.py` (must PASS).
- Science→bundle: orchestrator runs `python ops/bin/merge_science.py` + validator, then `python ops/bin/deploy_web.py`.

## Who is doing what (issue numbers)
- orchestrator (Murad, `skylapse_kit_v4`): O0 #1 ✅ · O1 #19 ✅ · O3 #20 ✅ · O3b #36 ✅ · O2 live jobs #21 (after T5) · checkpoints #28–#32
- pipeline (Murad 2nd session, `skylapse-pipeline`): T1–T6 #2–#7 ✅ (PR #59; live runner WISE-ready 83 s)
- science (Murad 3rd session, `skylapse-science`; Kanan absent): S1 #8 ✅ (Barnard 99.8 %, ε Indi B 99.0 %, WISE 0855 99.9 % — science/VALIDATION.md) · S2 #9 ✅ (WISE 0855 spectrum: dark < 3 µm, 0.62 mJy at 4.6 µm) · S3 #10 · S5 #11 · S4 #12 (after T3)
- frontend (Azer): F0–F5 #13–#18 ✅ · bugs #45 ✅ #47 ✅ · F6 #51 ✅ · F7 clarity #54 ✅ · F8 spectrum panel #60 · BUG Gaia clutter #62
- pitch (Amal): A1 #22 ✅ · A2 #23 ✅ · A4 QA r1 #25 ✅ · A5 #26 ✅ (v1, slides pptx) · A3 mentors #24 · A6 #27 (Sun 11:00, human)
- captain Deneme: FARADTechnologies

## Status of P0 items
P0-1 bundle ✅ (5/5 live) · P0-2 viewer ✅ · P0-3 search/URL ✅ (resolve.field) · P0-4 difference ✅ · P0-5 Gaia overlay ✅ (verify on movers)
P0-6 metadata/flags ✅ · P0-7 live coords ☐ (T5, O2) · P0-8 deploy ✅ · P0-9 validation ✅ in UI (99.8 / 99.0 / 99.9 %) · P0-10 pitch ◐ (A2/A5 v1)

## Blockers / risks
- Local rule: pitch + demo = 5 min, overrun = disqualified (D-012). Demo movie load ~5 s → F6 #51.
- Three agents on Murad's account → usage-limit risk; science → Sonnet if the warning appears.
- R Dra / Barnard saturated in SPHEREx: light-curve method decision by 19:30 (S3 #10).
- Railway trial credits could run out → fallbacks in D-015.
- Venue network is flaky (GitHub/DNS drops several times) → demo laptop must use a phone hotspot as backup + offline video.

## Next 3 priorities
1. O2 #21 live WISE-only jobs on Railway (P0-7).
2. Frontend #62 Gaia clutter, F8 #60; pitch QA round 2 on the 5 real targets.
3. Science S3 light curves (R Dra method by 19:30), S5 copilot.
