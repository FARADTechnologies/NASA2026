# SkyLapse — verified numbers for the Market Potential / Impact slide (S9)

Rule for pitch: use only the numbers in the "say this" column; each has a source you can open. No market sizes or money figures
are claimed (decision D-022: market value without money). Checked Sun 15 Nov, ~02:00 Baku.

## 1. Speed and reach
| say this | number | source / how measured |
|---|---|---|
| **Any sky position becomes a 14-year WISE movie in about half a minute** | fresh field (8.8′): WISE ready in **11–23 s**, finished in **20–33 s** (range of two independent tests; up to 38 s seen) | orchestrator, API v0.3.0, Sun 00:00: wise_ready 11 s / done 20 s (`ops/memory/KNOWHOW.md`); science, Sun ~02:00: new field at RA 201.365°, Dec −43.019° → 23 s / 33 s, 50 frames (25 W1 + 25 W2, 2010-01-27 → 2024-07-10), not cached. Pipeline T9 (#78) adds a 4-position table. |
| **Works anywhere on the sky** | WISE/NEOWISE and SPHEREx are both all-sky surveys | WISE mission description (Wright et al. 2010, AJ 140, 1868); SPHEREx: 102 bands, whole sky (`docs/SCIENCE_NOTES.md` §1; `docs/METHODOLOGY.md` refs [6], [13]). |
| **14 years of WISE per field: 23 to 48 snapshots** | 23 epochs (most fields; 25 at the live test position), **48** near the north ecliptic pole (R Dra) | `$SKYLAPSE_DATA/raw/wise/<target>/index.csv`; live manifest above. |
| **Plus every SPHEREx visit (2025–2026)** for the 5 NASA targets | 258 (WISE 0855) to 2,493 (R Dra) SPHEREx images per target | prefetch `SUMMARY.md` (`docs/SCIENCE_NOTES.md` §7). Live fields are WISE-only today (free-tier memory, D-015). |
| **Two languages** | English + Azerbaijani explanations for every target | `science/out/<field>/objects/target.json` → `copilot`. |

## 2. Trust (validation — same numbers as `science/QA_FACTS.md`)
| say this | number | source |
|---|---|---|
| **Measured motions match Gaia and the literature to better than 99 %** | 99.8 % (Barnard), 99.0 % (ε Indi B), 99.9 % (WISE 0855) | `science/VALIDATION.md` |
| **Blind search found all 3 NASA movers, with zero false alarms** | known movers 3, recovered 3, false candidates 0 (5 fields) | `science/DISCOVERY.md` |
| **Recovers a star's pulse through saturation** | R Dra period 246 d (W1) / 247 d (W2) vs 246.12 d (AAVSO VSX) | `science/LIGHTCURVES.md` |

## 3. Cost basis (no money figures)
| say this | fact | source |
|---|---|---|
| **All data are free and open** | NASA SPHEREx (IRSA), NASA WISE/NEOWISE (unWISE via byw.tools), ESA Gaia DR3, CatWISE2020 | credits on https://skylapse.vercel.app/about |
| **Runs on free hosting** | website on Vercel's free tier; API on Railway trial credits, no paid plan ("budget = 0") | D-015 in `ops/memory/DECISIONS.md` |
| **The 5 NASA targets need no server at all** | precomputed static bundle (~82 MB) served with the website | `web/public/bundle/`; D-015 |
| **Updating a target with new SPHEREx data is a rebuild, not new work** | pipeline + `python -m skylapse_science <cmd>` commands rerun on new data | `docs/ARCHITECTURE.md`; science commands in `science/*.md` |

## 4. The manual alternative — an ESTIMATE (state it as such)
What one person does today to "blink" one field across WISE + SPHEREx without SkyLapse. Measured inputs are marked (m); the rest are
our assumptions.
| step | per field | basis |
|---|---|---|
| Find which WISE epochs cover the position, download each | 23–48 epochs × 2 bands = **46–96 images** | (m) epoch counts above |
| Query SPHEREx and download its images | TAP query ≈ **35 s** (m) + ≈ **10 s per cutout** (m) × 258 images (WISE 0855) ≈ **45 min** one at a time | (m) `docs/SCIENCE_NOTES.md` §1, §7 |
| Subtract zodiacal light, mask flags, reproject both surveys onto one grid, find a common brightness scale | assumed **≥ 1 hour** for someone who already knows Astropy (code we wrote once) | assumption |
| Blink, mark the moving dot, measure positions, compare with Gaia | assumed **30–60 min** | assumption |
| **Total** | **roughly 2–3 hours per field for an expert**, vs **≈ 0.5 min** in SkyLapse (WISE part) — **more than 200× faster** (120–180 min ÷ 0.5 min) | estimate; the SkyLapse number is measured |

Do not present the 200× as measured: say "hours of expert work become half a minute".
