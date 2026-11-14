# "What powers SkyLapse?" — NASA data + technical readiness slide (content for Amal)
Amal places this in her deck herself. Every item is from a repo file or the live site (sources in brackets; F-numbers → `pitch/FACTS.md`).
Checked Sun 15 Nov ~02:40 Baku.

---

## 1. Data sources (what we actually use)
| Source | What | Wavelength | Dates |
|---|---|---|---|
| **NASA SPHEREx** (DR1 + QR3, via NASA/IPAC IRSA) | spectral images, 102 bands, 6 detectors D1–D6, 6.15″ pixels | **0.75 – 5.0 µm** | 2025 – 2026 |
| **NASA WISE / NEOWISE** (time-resolved unWISE coadds) | one image per epoch, 2.75″ pixels | **W1 3.4 µm, W2 4.6 µm** | **2010 – 2024** (23 epochs; 48 near the ecliptic pole) |
| **CatWISE2020** (from WISE) | motion catalogue — overlay only, *not* used as a motion reference | — | — |
| **ESA Gaia DR3** (partner agency) | star positions + motions: overlay moved to each frame's date, and our reference values | visible | — |
[docs/SCIENCE_NOTES.md §1–3; live manifest.json; docs/METHODOLOGY.md]

## 2. Tools we actually use
- **Python 3.11 + Astropy** (WCS, reprojection to one sky grid), **astroquery**, **reproject**, **photutils** (centroids, source detection), NumPy, SciPy.
- **FastAPI** server (name lookup, live fields) on Railway · **React + TypeScript + Vite** website on Vercel (Canvas 2D player).
- **Anthropic Claude** — coding assistants + plain-language EN/AZ explanations from our measured facts only (disclosed, see AI slide).
[docs/ARCHITECTURE.md; pitch/REFERENCES.md; pitch/AI_USE.md]

## 3. Checks our implementation performs (automatic)
1. **Zodiacal light removed** from every SPHEREx image (IMAGE − ZODI) and **bad pixels masked** using each image's own flag names.
2. **Saturation detected and labelled** (SPHEREx OVERFLOW flag, WISE empty cores) — never shown as real brightness. Barnard's Star: saturated in 356 of 357 SPHEREx images → no spectrum shown.
3. **Moving-target rule:** the object's position is moved to each image's own date before measuring it.
4. **Same-wavelength rule:** SPHEREx sees a star at different wavelengths in different images, so brightness is only compared at the same wavelength.
5. **Motion with error bars:** straight-line fit through every WISE epoch, 1000× bootstrap errors, compared with Gaia / literature.
6. **Blind search with checks:** a candidate must be seen in ≥ 60 % of epochs and move ≥ 3σ; cross-matched with Gaia DR3 / CatWISE → labelled known / candidate / artifact.
7. **AI text guard:** every number in an AI explanation is checked automatically against our measured facts; "discovery" and "Planet X" are blocked.
8. **Bundle validator** must pass before any data reaches the website.
[docs/SCIENCE_NOTES.md §5; science/QA_FACTS.md #1, #8, #14, #15; science/DISCOVERY.md; docs/METHODOLOGY.md D]

## 4. A real result — with dates and wavelengths beside it (WISE 0855−0714, coldest known brown dwarf, ~250 K)
| Measurement | Data used (dates · wavelength) | Result |
|---|---|---|
| **Motion across the sky** | WISE W2 **4.6 µm**, 23 epochs **4 May 2010 → 17 Apr 2024** | **8157 ± 15 mas/yr** vs 8152 published (Kirkpatrick et al. 2021) → **99.9 %** |
| **Infrared "fingerprint"** | SPHEREx **0.75–5.0 µm**, clean images of **30 May 2025** | **invisible below 2.4 µm**, **detected at 4.4–4.9 µm** (0.62 ± 0.08 mJy, S/N 7) → exactly what a ~250 K object should do |
| **Movie** | WISE W1/W2 2010–2024 + SPHEREx D1–D6 **May 2025 → May 2026** | 26-frame, 16-year movie; it crawls ~2′ west |
[science/VALIDATION.md; science/SPECTRA.md; science/QA_FACTS.md #4, #9; live https://skylapse.vercel.app/bundle/wise0855/manifest.json]

Slide-friendly version of the result (one line):
**WISE 0855 · WISE 4.6 µm, 2010–2024 → 8.16″/yr, 99.9 % match · SPHEREx 4.4–4.9 µm, May 2025 → seen only at long wavelengths, as a 250 K world should be.**

## 5. What our workflow improves over existing tools (short)
- **Today:** WISE blink tools have no spectra; motion catalogues can be wrong (CatWISE: ε Indi B 1.1″/yr vs true 4.7″/yr); SPHEREx tools have only ~1 year of data and no time-lapse. [docs/METHODOLOGY.md; F20]
- **SkyLapse:** one sky grid for both missions → 16-year movie + measured motion + spectrum + plain-language explanation, in a browser.
- **Speed:** any sky position becomes a 14-year WISE movie in about **half a minute** — hours of expert work, by our estimate. [F17, F21]
- **Trust:** 99.0–99.9 % agreement on NASA's three moving targets; blind search 3 / 3, 0 false alarms. [F6, F15]

## Speaker notes (≈ 30 s, 75 words)
> "What powers SkyLapse? NASA data: SPHEREx from 0.75 to 5 microns, 2025 to 2026, and fourteen years of WISE at 3.4 and 4.6 microns, with ESA Gaia as reference. Our code removes zodiacal light, masks bad and saturated pixels, and measures motion with error bars. Example: WISE 0855 — 8.16 arcseconds a year, a 99.9 percent match, and SPHEREx sees it only at long wavelengths, exactly like a 250-kelvin world."
