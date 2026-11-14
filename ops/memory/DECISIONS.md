# DECISIONS — append-only, orchestrator writes. Format: D-NNN | time | decision | why | who
D-001 | Fri 23:55 | Challenge: Planet X and SPHEREx; product name SkyLapse | selected in the local application form | Deneme
D-002 | Sat 01:30 | Concept B: 16-yr time machine + spectral fingerprint + auto-discovery + AI copilot, layered (core first) | best expected score on all 5 criteria with this jury | Deneme
D-003 | Sat 01:30 | Static-first architecture; live API only for new coordinates | IRSA cutouts take ~30 s each and have no CORS | Deneme
D-004 | Sat 01:30 | WISE epochs from byw.tools unWISE time-resolved cutouts; SPHEREx DR1+QR3 via IRSA TAP/cutouts | tested; fastest reliable sources | Deneme
D-005 | Sat 01:30 | Gaia DR3 (ESA) is our Space Agency Partner data; no bolt-on partner data | Relevance criterion penalises superficial data use | Deneme
D-006 | Sat 01:30 | GitHub Issues = message bus between agents; orchestrator = Murad's main Claude Code | zero-build, phone notifications, history | Deneme
D-007 | Sat 01:30 | Never claim discoveries or Planet X; say "candidates" | validity + credibility in Q&A | Deneme
D-008 | Sat 14:10 | Bootstrap started 14:00 (3 h late): M1 → 16:00, M2 → 19:30; M3 22:30, M4 Sun 10:30, submit 14:30 unchanged. Issue deadlines re-planned | kit session started late | orchestrator (Murad)
D-009 | Sat 14:10 | Science→bundle handoff: science writes science/out/<field>/objects/*.json + candidates.json; pipeline export / `merge-science` copies them into web/public/bundle/<field>/ | keeps one writer per bundle folder, no merge conflicts | orchestrator
D-010 | Sat 14:10 | S1 measures PM on prefetch WISE epoch FITS in native WCS (not the resampled grid), so science does not wait for pipeline T3 | removes a critical-path dependency; native WCS is more accurate | orchestrator
D-011 | Sat 14:40 | Mock bundle is a separate bundle root web/public/bundle/_mock/ (own index.json, field mock_mover); top-level index.json lists real fields only | frontend can fall back to the mock while real fields land | orchestrator
D-012 | Sat 14:45 | Local format: pitch+demo 5 min total (overrun = disqualified), Q&A 5 min, max 7 English slides shared by link; rehearse to ≤4:40; live demo ≤60 s inside the 5 min, backup video ready | LOCAL_RULES.md from Amal | orchestrator
