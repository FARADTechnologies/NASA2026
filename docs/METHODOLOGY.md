# SkyLapse — methodology and validation

**Short answer for the jury:** we reviewed how moving infrared objects are found today — **A** human blinking of WISE images
(Backyard Worlds / WiseView), **B** automated WISE motion catalogs (CatWISE2020, unTimely), **C** NASA SPHEREx and its IRSA archive
tools. Their common **gap X**: no public tool joins WISE's 14-year time baseline with SPHEREx's 102-band spectra. **D = SkyLapse**
does that, measures what moves, and shows it as a movie. Working prototype: **https://skylapse.vercel.app**.

## A — Human blinking: Backyard Worlds: Planet 9 and WiseView
- Volunteers blink unWISE time-resolved images of the same patch of sky and spot faint dots that move [1, 2, 3].
- **Strength:** the human eye finds faint, unusual movers that catalogs miss; the project's first brown dwarf came this way [1].
- **Limits:** WISE only (3.4 and 4.6 µm, two colours), no spectra, motion is judged by eye (not measured).

## B — Automated WISE motion catalogs: CatWISE2020 and unTimely
- CatWISE2020 measures positions and proper motions of faint sources over the whole sky from WISE/NEOWISE data [4]; unTimely is a
  time-domain catalog built from the time-resolved unWISE coadds [5].
- **Strength:** whole sky, automatic, faint sources.
- **Limits:** no spectra, and catalog motions can fail for blended or unusual objects. **Our own example:** for ε Indi B
  (a brown-dwarf pair next to a very bright star) CatWISE2020 lists (0.90, −0.68) ″/yr, about **1.1 ″/yr**, while Gaia DR3 gives
  **4.7 ″/yr** (`docs/SCIENCE_NOTES.md` §7). In the five fields we built, CatWISE lists 881 sources faster than 0.3 ″/yr and
  none of them is confirmed by a Gaia source moving the same way (`science/DISCOVERY.md`).

## C — NASA SPHEREx and the IRSA archive tools
- SPHEREx maps the whole sky in 102 spectral bands from 0.75 to 5.0 µm [6]; IRSA serves its images and offers cutout,
  spectrophotometry and source-discovery tools. A spectral library for ultracool dwarfs from SPHEREx already exists [7].
- **Strength:** a spectrum for every pixel of the sky — e.g. methane in cold brown dwarfs.
- **Limits:** its own record is only about one year, so even the fastest nearby objects move only ~1–2 of its 6.15″ pixels;
  saturated bright stars; no time-lapse viewer that joins it with older surveys.

## X — The gap
**No public tool joins the 14-year WISE/NEOWISE baseline (2010–2024) with SPHEREx's spectra (2025–2026).** Motion needs time,
spectra need SPHEREx: today a user must combine A, B and C by hand.

## D — SkyLapse (what we built)
1. **Collect** every unWISE time-resolved WISE/NEOWISE epoch (2010–2024) [3] and every SPHEREx image (DR1 + QR3) of the field.
2. **Clean:** SPHEREx zodiacal light subtracted, bad pixels masked using each image's own flag names, saturation flagged — never
   shown as real brightness.
3. **Combine** everything on one sky grid and play it as a **16-year movie**, with Gaia DR3 [8] / CatWISE overlays.
4. **Measure:** proper motions (position in every WISE epoch, straight-line fit), a blind search for movers with epoch-by-epoch
   verification, SPHEREx spectra by forced PSF photometry at the moving position, and saturation-aware light curves.
5. **Explain:** short English and Azerbaijani texts written only from the measured facts, with an automatic check that every
   number in a text is one we measured; nothing is called a "discovery", only a "candidate".

Live prototype: **https://skylapse.vercel.app** — all five NASA test targets play from a static bundle (the demo does not depend
on archive servers being online). Code: this repository (`pipeline/`, `science/`, `web/`).

## Validation (our measured numbers)
| test | result | reference value | source file |
|---|---|---|---|
| Barnard's Star proper motion | 10395 ± 17 mas/yr, **99.8 %** agreement | Gaia DR3 [8]: 10393 mas/yr | `science/VALIDATION.md` |
| ε Indi B proper motion | 4717 ± 10 mas/yr, **99.0 %**; moves with its star ε Indi A to **99.3 %** | Gaia DR3: 4684 mas/yr | `science/VALIDATION.md` |
| WISE 0855−0714 proper motion | 8157 ± 15 mas/yr, **99.9 %** | Kirkpatrick et al. 2021 [9]: 8152 mas/yr | `science/VALIDATION.md` |
| Blind search for movers (5 fields) | known movers **3**, recovered **3**, false candidates **0** | Gaia DR3 + literature | `science/DISCOVERY.md` |
| WISE 0855 SPHEREx spectrum | not detected below 2.4 µm (−0.009 ± 0.009 mJy); detected at 4.4–4.9 µm (0.62 ± 0.08 mJy, S/N 7) | expected for a ~250 K Y dwarf [10] | `science/SPECTRA.md` |
| SPHEREx flux scale | SPHEREx / WISE = 1.01 ± 0.03 (3.4 µm), 1.03 ± 0.03 (4.6 µm), 9 stars | WISE photometry (CatWISE2020 [4]) | `science/out/validation/spectra_calibration.json` |
| R Draconis pulsation | best period **246 d** (W1) / **247 d** (W2) | AAVSO VSX: 246.12 d [11] | `science/LIGHTCURVES.md` |
| RW Aurigae variability | 0.24 / 0.40 mag rms vs a constant comparison star 0.03 / 0.05; index vs NEOWISE photometry r = 0.93 / 0.98 | NEOWISE single exposures [12] | `science/LIGHTCURVES.md` |

Agreement = 100 × (1 − |μ_measured − μ_reference| / |μ_reference|), full 2-D vector difference. Per-claim method and caveat:
`science/QA_FACTS.md`. **Caveats:** Barnard's Star, R Dra and RW Aur are saturated (positions from the image wings; light curves
are a relative index, not magnitudes); the R Dra period has a ~713 d alias because WISE visits every ~6 months; WISE parallaxes
are not a result. Every number is reproduced by one command (`python -m skylapse_science validate | spectra | lightcurves | discover`).

## References (each link checked on 15 Nov 2026)
1. Kuchner, M. J., Faherty, J. K., Schneider, A. C., et al. 2017, *The First Brown Dwarf Discovered by the Backyard Worlds: Planet 9
   Citizen Science Project*, ApJ Letters. arXiv:[1705.02919](https://arxiv.org/abs/1705.02919), doi:[10.3847/2041-8213/aa7200](https://doi.org/10.3847/2041-8213/aa7200)
2. Caselden, D., Westin, P., III, Meisner, A., Kuchner, M., Colin, G. 2018, *WiseView: Visualizing motion and variability of faint
   WISE sources*, Astrophysics Source Code Library, [ascl:1806.004](https://ascl.net/1806.004)
3. Meisner, A. M., Lang, D., Schlegel, D. J. 2018, *Time-resolved WISE/NEOWISE Coadds*, AJ 156, 69.
   arXiv:[1710.02526](https://arxiv.org/abs/1710.02526), doi:[10.3847/1538-3881/aacbcd](https://doi.org/10.3847/1538-3881/aacbcd)
4. Marocco, F., et al. 2021, *The CatWISE2020 Catalog*, ApJS.
   arXiv:[2012.13084](https://arxiv.org/abs/2012.13084), doi:[10.3847/1538-4365/abd805](https://doi.org/10.3847/1538-4365/abd805)
5. Meisner, A. M., et al. 2023, *unTimely: a Full-sky, Time-Domain unWISE Catalog*, AJ.
   arXiv:[2209.14327](https://arxiv.org/abs/2209.14327), doi:[10.3847/1538-3881/aca2ab](https://doi.org/10.3847/1538-3881/aca2ab)
6. Doré, O., et al. 2014, *Cosmology with the SPHEREX All-Sky Spectral Survey*, arXiv:[1412.4872](https://arxiv.org/abs/1412.4872)
7. Gagné, J., et al. 2026, *A SPHEREx Pipeline and Spectral Library for Ultracool Dwarfs*, arXiv:[2604.22012](https://arxiv.org/abs/2604.22012)
8. Gaia Collaboration, Vallenari, A., et al. 2023, *Gaia Data Release 3: Summary of the content and survey properties*, A&A.
   arXiv:[2208.00211](https://arxiv.org/abs/2208.00211), doi:[10.1051/0004-6361/202243940](https://doi.org/10.1051/0004-6361/202243940)
9. Kirkpatrick, J. D., et al. 2021, *The Field Substellar Mass Function Based on the Full-sky 20-pc Census of 525 L, T, and Y Dwarfs*,
   ApJS 253, 7. arXiv:[2011.11616](https://arxiv.org/abs/2011.11616), doi:[10.3847/1538-4365/abd107](https://doi.org/10.3847/1538-4365/abd107)
10. Luhman, K. L. 2014, *Discovery of a ~250 K Brown Dwarf at 2 pc from the Sun*, ApJ 786, L18.
    arXiv:[1404.6501](https://arxiv.org/abs/1404.6501), doi:[10.1088/2041-8205/786/2/L18](https://doi.org/10.1088/2041-8205/786/2/L18)
11. AAVSO International Variable Star Index (VSX), entry for R Dra (period 246.12 d): [vsx.aavso.org](https://vsx.aavso.org/index.php?view=results.get&ident=R+Dra)
12. Mainzer, A., et al. 2014, *Initial Performance of the NEOWISE Reactivation Mission*, ApJ 792, 30.
    arXiv:[1406.6025](https://arxiv.org/abs/1406.6025), doi:[10.1088/0004-637X/792/1/30](https://doi.org/10.1088/0004-637X/792/1/30)
13. Wright, E. L., et al. 2010, *The Wide-field Infrared Survey Explorer (WISE): Mission Description and Initial On-orbit
    Performance*, AJ 140, 1868. arXiv:[1008.0031](https://arxiv.org/abs/1008.0031), doi:[10.1088/0004-6256/140/6/1868](https://doi.org/10.1088/0004-6256/140/6/1868)
14. Astropy Collaboration 2022, *The Astropy Project: … Latest Major Release (v5.0) of the Core Package*, ApJ.
    arXiv:[2206.14220](https://arxiv.org/abs/2206.14220), doi:[10.3847/1538-4357/ac7c74](https://doi.org/10.3847/1538-4357/ac7c74)
