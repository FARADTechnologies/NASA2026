# PROJECT STATE — written ONLY by the orchestrator. Keep under ~70 lines. Update at every checkpoint and after big changes.
Last update: Sat 14:55 by orchestrator

## Milestone
Current: M0 Kickoff (done 14:20, 3 h late — see D-008). Next: M1 Walking skeleton at **16:00** (re-planned).
Re-planned: M1 16:00 · M2 19:30 · M3 22:30 · M4 FREEZE Sun 10:30 · Submit Sun 14:30.

## Deployed
- Web: **https://skylapse.vercel.app** (Vercel CLI deploy from Murad's PC: `cd web && npx vercel deploy --prod --yes`; mock data until real fields land)
- API: code on main (O1 #19 ✅, `api/README.md`); host not deployed yet → O3b #36 (needs Murad: Railway/Render or laptop+tunnel)
- Repo: https://github.com/FARADTechnologies/NASA2026 — private until Sun ~13:00

## Bundle
- `web/public/bundle/_mock/` (mock root, field `mock_mover`) on main — validator PASS. Real fields: none yet.
- Validator: `python ops/bin/validate_bundle.py` (every bundle merge must PASS).
- Science→bundle: science writes `science/out/<field>/…`; pipeline `merge-science` copies (D-009).

## Who is doing what (issue numbers)
- orchestrator (Murad, `skylapse_kit_v4`): O0 #1 ✅ · O1 API #19 ✅ · O3 web deploy #20 ✅ · O3b API host #36 (human) · O2 live jobs #21 (after T5) · checkpoints #28–#32
- pipeline (Murad 2nd session, `C:\Users\Murad\Downloads\skylapse-pipeline`): T1 #2 → T2 #3 → T3 #4 → T4 #5 → T5 #6 → T6 #7
- science (Murad 3rd session, `C:\Users\Murad\Downloads\skylapse-science`; Kanan absent): S1 #8 (P0) → S2 #9 → S3 #10 → S5 #11 → S4 #12 (after T3)
- frontend (Azer, AzarValiyev): F0–F3 #13–#16 ✅ (merged PR #35, viewer core on mock) → F4 #17 → F5 #18
- pitch (Amal, JustEyml): A1 #22 ✅ (LOCAL_RULES: 5 min pitch+demo, D-012) · A2 #23 · A3 #24 · A4 #25 (after deploy) · A5 #26 · A6 #27 (Sun 11:00, human)
- captain Deneme: FARADTechnologies

## Status of P0 items
P0-1 bundle ☐ (T1–T3) · P0-2 viewer ◐ (on mock) · P0-3 search/URL ☐ (F2, O1) · P0-4 difference ☐ (F3) · P0-5 Gaia overlay ☐ (F3)
P0-6 metadata/flags ☐ (T4, F3) · P0-7 live coords ☐ (T5, O2, F5) · P0-8 deploy ◐ (web ✅, API ☐) · P0-9 PM validation ☐ (S1) · P0-10 pitch ☐ (A2, A5, A6)

## Blockers / risks
- 3 h late start: M1 needs pipeline T1+T2 in < 2 h. Fallback: WISE-only wise0855 at M1.
- Three agents on Murad's account → usage-limit risk; science → Sonnet if the warning appears.
- R Dra / Barnard saturated in SPHEREx (SCIENCE_NOTES §7): light curve method decision by 19:30 (S3).

## Next 3 priorities
1. Pipeline T1/T2 → real wise0855 bundle by 16:00.
2. Frontend F1 player on mock → deploy on Vercel (O3) by 16:00.
3. O1 API resolve; S1 validation numbers by 19:30.
