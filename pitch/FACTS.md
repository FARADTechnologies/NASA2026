# FACTS — every number/claim used in slides, script and project page, with its source
Rule: a fact is usable on stage only when Status = ✅ (source is a repo file with pipeline/science output, or a cited public reference).
| # | Fact (as said on stage) | Source file / reference | Status |
|---|---|---|---|
| F1 | SPHEREx observes in 102 spectral bands, whole sky every ~6 months | docs/PLAN.md §6; docs/SCIENCE_NOTES.md §1; NASA SPHEREx mission page | ✅ (mission fact) |
| F2 | SPHEREx own record ≈ 1 year → nearby movers move 1–2 px | docs/SCIENCE_NOTES.md §4 last line | ✅ |
| F3 | WISE/NEOWISE watched the sky 2010–2024 at 4.6 µm (W2); 23 epochs in our movie | science/VALIDATION.md (W2 = 23 epochs, 14.0 yr baseline); deployed site wise0855 = 26 frames (23 WISE + 3 SPHEREx) | ✅ |
| F4 | WISE 0855 moves ≈ 130″ (≈ 2′) over 2010→2026 (16 yr, literature); OUR measured: 8157 ± 15 mas/yr → 114″ over 2010→2024 (14 yr). T ≈ 250 K (≈ −20 °C), coldest known brown dwarf | docs/SCIENCE_NOTES.md §4; science/VALIDATION.md; science/QA_FACTS.md | ✅ — never mix the two sets: "16 years" ↔ 130″/166″/75″, "14 years measured" ↔ 114″/146″/66″ |
| F5 | Barnard ≈ 166″, ε Indi B ≈ 75″ over 2010→2026 (16 yr, literature); measured 2010→2024: 146″ / 66″ | docs/SCIENCE_NOTES.md §4; science/QA_FACTS.md | ✅ (same rule as F4) |
| F6 | Measured motion vs reference: Barnard 99.8 % (10395 ± 17 vs Gaia 10393 mas/yr), ε Indi B 99.0 % (4717 ± 10 vs 4684), WISE 0855 99.9 % (8157 ± 15 vs 8152, Kirkpatrick+2021) → "better than 99 percent" | science/VALIDATION.md | ✅ |
| F6b | ε Indi B moves with ε Indi A: 99.3 % agreement, ~400″ apart → bound system | science/VALIDATION.md | ✅ |
| F6c | ε Indi B SPHEREx spectrum: methane band 3.2–3.5 µm at 19 % of the 4 µm peak → classic T-dwarf shape | deployed site eps_indi_b panel; science/SPECTRA.md | ✅ |
| F7 | All 5 NASA targets load and play on the deployed site | docs/QA.md round 2 (Sat ~17:00) | ✅ incl. light curves (R Dra 246/247 d vs 245.6 d; RW Aur index vs NEOWISE r = 0.93/0.98) — see F13, F14 |
| F8 | Barnard and R Dra are saturated in ~all SPHEREx images (we flag this honestly) | docs/SCIENCE_NOTES.md §7 | ✅ |
| F9 | Backyard Worlds volunteers found brown dwarfs by blinking WISE images | NASA challenge text / backyardworlds.org | ⏳ verify exact wording in challenge text |
| F10 | SRDA community 1000+ members | docs/PLAN.md §6 | ⏳ confirm with Murad/Amal |
| F11 | New SPHEREx data weekly; field rebuild = one command | docs/PLAN.md §6; pipeline README (to confirm command) | ⏳ confirm command exists |
| F13 | R Draconis: period from our brightness index 246 d (W1) / 247 d (W2) vs known 245.6 d (GCVS); index is a RELATIVE wing index (star saturated) — 6-month WISE sampling also allows a ~713 d alias | deployed web/public/bundle/r_dra/objects/target.json `lightcurve.notes`; science/out/png/r_dra_lightcurve.png | ✅ (say "matches the known period", never "we found the period") |
| F14 | RW Aurigae varies 0.24 / 0.40 mag rms (W1/W2) vs 0.035 / 0.05 for a constant comparison star (7–8× noise); index follows NEOWISE photometry r = 0.93 / 0.98 | web/public/bundle/rw_aur/objects/target.json `lightcurve` | ✅ |
| F15 | Blind auto-discovery recovered 3 / 3 NASA movers with 0 false candidates in 5 fields | science/DISCOVERY.md; candidates.json stats | ✅ |
| F16 | AI copilot texts EN + AZ live for the targets, generated only from computed facts ("Written by AI only from the measured facts above") | deployed site panel; science S5 #11 | ✅ |
| F12 | Data: NASA SPHEREx (DR1+QR3), NASA WISE/NEOWISE unWISE epochs, CatWISE2020; partner: ESA Gaia DR3 | docs/SCIENCE_NOTES.md §1–3 | ✅ |
