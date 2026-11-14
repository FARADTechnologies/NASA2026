# SkyLapse — SPHEREx spectra (S2, P1-1)

Reproduce: `cd science && .venv/Scripts/python.exe -m skylapse_science spectra` (all 5 targets, ~6 min) and
`... -m skylapse_science spectra-calib` (flux-scale check). Output: `spectrum` block in `science/out/<field>/objects/target.json`,
per-image table `science/out/<field>/spectrum_points.csv`, plots `science/out/png/<field>_spectrum.png`.

## Method
1. Every SPHEREx L2 cutout of the field (DR1 + QR3, D1–D6, 0.75–5.0 µm): IMAGE − ZODI (zodiacal light removed), VARIANCE for errors,
   FLAGS bit names read from the header; reject list = SCIENCE_NOTES §1 (SOURCE is never masked; OVERFLOW = saturation).
2. Source position propagated to each image's MJD-AVG (moving-target rule) — WISE 0855 moves ~1.3 SPHEREx pixels per year.
3. Forced PSF photometry: the archive effective PSF (EPSF extension of the raw cutout, zone nearest to the detector position) is fitted
   for the target **and** every Gaia DR3 / CatWISE2020 neighbour within 4 px (+3), plus a constant, by weighted linear least squares.
   Errors from the covariance, inflated by the reduced χ² when > 1.
4. Blends: a neighbour closer than 1.5 px (9.2") whose fitted flux is > 10 % of the target's (or of its 3σ limit) cannot be separated
   at 6.15" pixels → the point is flagged and not used. Saturated pixels (OVERFLOW) or empty (NaN) cores → flagged / no point.
5. Wavelength of each point = LVF wavelength at the target pixel from the spectral WCS (IRSA quick-look method).
   Binned spectrum: inverse-variance mean of unflagged points in log-spaced bins (R ≈ 40).

## Flux-scale check (validity)
For 9 isolated CatWISE stars in three fields, median SPHEREx flux / CatWISE flux = **1.01 ± 0.03** (3.2–3.6 µm vs W1) and
**1.03 ± 0.03** (4.4–4.8 µm vs W2). Details: `science/out/validation/spectra_calibration.json`.

## Results
| target | result |
|---|---|
| WISE 0855−0714 | Not detected below 2.4 µm and in the 3.3 µm methane band; detected at 4.4–4.9 µm (S/N ≈ 7); steep rise from 4 to 4.6 µm. Only the 30 May-2025 images are clean: from Oct 2025 the dwarf passes within 9" of a G = 16.3 background star (blend, flagged). Without the blend handling a false "detection" below 2.4 µm appears. |
| ε Indi B (Ba+Bb) | Full T-dwarf spectrum from 324 clean images: peaks at 1.1–1.3, 1.6, 2.1 µm, deep methane band at 3.2–3.5 µm, brightest at 3.9–4.2 µm, CO dip at 4.4–4.9 µm. The two dwarfs (0.7" apart) are blended. |
| Barnard's Star, R Draconis, RW Aurigae | Saturated (OVERFLOW or empty core) in most images → no spectrum published (`usable: false`); the per-image table is kept for transparency. |

Templates: the Gagné et al. 2026 SPHEREx brown-dwarf templates (mocadb.ca) were not fetched in time; a blackbody of the literature
temperature is drawn for comparison only and is labelled as such.
