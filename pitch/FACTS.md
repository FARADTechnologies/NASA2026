# FACTS — every number/claim used in slides, script and project page, with its source
Rule: a fact is usable on stage only when Status = ✅ (source is a repo file with pipeline/science output, or a cited public reference).
| # | Fact (as said on stage) | Source file / reference | Status |
|---|---|---|---|
| F1 | SPHEREx observes in 102 spectral bands, whole sky every ~6 months | docs/PLAN.md §6; docs/SCIENCE_NOTES.md §1; NASA SPHEREx mission page | ✅ (mission fact) |
| F2 | SPHEREx own record ≈ 1 year → nearby movers move 1–2 px | docs/SCIENCE_NOTES.md §4 last line | ✅ |
| F3 | WISE/NEOWISE watched the sky 2010–2024 at 4.6 µm (W2); 23 epochs in our movie | science/VALIDATION.md (W2 = 23 epochs, 14.0 yr baseline); deployed site wise0855 = 26 frames (23 WISE + 3 SPHEREx) | ✅ |
| F4 | WISE 0855 moves ≈ 130″ (≈ 2′) over 2010→2026; T ≈ 250 K, coldest known brown dwarf | docs/SCIENCE_NOTES.md §4 | ✅ (literature); ⏳ our measured value |
| F5 | Barnard ≈ 166″, ε Indi B ≈ 75″ over the baseline | docs/SCIENCE_NOTES.md §4 | ✅ (literature) |
| F6 | Measured motion vs reference: Barnard 99.8 % (10395 ± 17 vs Gaia 10393 mas/yr), ε Indi B 99.0 % (4717 ± 10 vs 4684), WISE 0855 99.9 % (8157 ± 15 vs 8152, Kirkpatrick+2021) → "better than 99 percent" | science/VALIDATION.md | ✅ |
| F6b | ε Indi B moves with ε Indi A: 99.3 % agreement, ~400″ apart → bound system | science/VALIDATION.md | ✅ |
| F6c | ε Indi B SPHEREx spectrum: methane band 3.2–3.5 µm at 19 % of the 4 µm peak → classic T-dwarf shape | deployed site eps_indi_b panel; science/SPECTRA.md | ✅ |
| F7 | All 5 NASA targets load and play on the deployed site | docs/QA.md round 2 (Sat ~17:00) | ✅ (light curves for R Dra/RW Aur still pending, S3 #10) |
| F8 | Barnard and R Dra are saturated in ~all SPHEREx images (we flag this honestly) | docs/SCIENCE_NOTES.md §7 | ✅ |
| F9 | Backyard Worlds volunteers found brown dwarfs by blinking WISE images | NASA challenge text / backyardworlds.org | ⏳ verify exact wording in challenge text |
| F10 | SRDA community 1000+ members | docs/PLAN.md §6 | ⏳ confirm with Murad/Amal |
| F11 | New SPHEREx data weekly; field rebuild = one command | docs/PLAN.md §6; pipeline README (to confirm command) | ⏳ confirm command exists |
| F12 | Data: NASA SPHEREx (DR1+QR3), NASA WISE/NEOWISE unWISE epochs, CatWISE2020; partner: ESA Gaia DR3 | docs/SCIENCE_NOTES.md §1–3 | ✅ |
