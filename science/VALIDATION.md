# SkyLapse — proper-motion validation (S1, P0-9)

Generated 2026-11-14 10:37 UTC by `python -m skylapse_science validate` (science/skylapse_science/astrometry.py). Per-epoch measurements: `science/out/<field>/astrometry_epochs.csv`; plots: `science/out/validation/<field>_pm.png`.

| target | measured μα* , μδ (mas/yr) | measured μ (mas/yr) | reference μα* , μδ (mas/yr) | reference | agreement | epochs used (W1+W2) | baseline | rms |
|---|---|---|---|---|---|---|---|---|
| Barnard's Star | -784 ± 15 , 10366 ± 17 | **10395 ± 17** | -802 , 10362 | Gaia DR3 4472832130942575872 | **99.8 %** | 36 (20+16) of 46 | 14.0 yr | 0.37" |
| ε Indi B | 3991 ± 9 , -2514 ± 7 | **4717 ± 10** | 3982 , -2467 | Gaia DR3 6412596012146801152 (eps Ind B, Ba+Bb photocentre) | **99.0 %** | 46 (23+23) of 46 | 14.0 yr | 0.20" |
| WISE 0855−0714 | -8129 ± 15 , 673 ± 7 | **8157 ± 15** | -8124 , 673 | Kirkpatrick et al. 2021, ApJS 253, 7 (via SIMBAD) | **99.9 %** | 23 (0+23) of 46 | 14.0 yr | 0.17" |

Agreement = 100 × (1 − |μ_measured − μ_reference| / |μ_reference|), using the full 2-D vector difference.

**ε Indi co-motion check:** ε Indi B (measured in WISE) vs its primary star ε Indi A (Gaia DR3 6412595290592307840 (eps Ind A): 3967, -2536 mas/yr) → **99.3 %** agreement: B moves with A across the sky (they are a bound system ~400" apart). Gaia's own value for B differs from A by ~70 mas/yr, most likely because Gaia's 34-month baseline catches part of the ~11-yr orbit of the Ba+Bb pair, while our 14-yr WISE baseline averages over it (interpretation, not tested here).

## Method
1. Data: unWISE time-resolved epoch coadds (byw.tools, W1 3.4 µm and W2 4.6 µm, 2.75"/px), each in its native TAN WCS (not the resampled viewer grid); epoch time = middle of MJDMIN..MJDMAX.
2. Start from the SIMBAD J2000 position propagated linearly to each epoch; centroid with photutils `centroid_2dg` in an 11×11 px box after subtracting a sigma-clipped local background (iterated 3×). Saturated cores (Barnard's Star: unWISE writes a ~6 px hole of zeros) are masked with a 2-px rim and a circular Moffat profile is fitted to the unsaturated wings.
3. Rejected: S/N < 5, centroid > 3 px from the prediction, failed/partial saturated fits, and 3σ outliers (never < 1"). Per-epoch error = statistical (FWHM / 2.355 / S/N) ⊕ systematic floor (0.10"; 0.30" wing fits; 0.60" flat saturated cores).
4. Tangent-plane offsets (ξ, η) around the 2018.0 position → weighted least squares for position, μα*, μδ and parallax (parallax factors from Earth's barycentric position; WISE is in low Earth orbit). Errors: 1000× bootstrap over epochs.
5. References: Gaia DR3 (ESA) for Barnard's Star and ε Indi B/A; WISE 0855−0714 is not in Gaia → Kirkpatrick et al. 2021 (ApJS 253, 7, via SIMBAD). CatWISE2020's motion for ε Indi B is known to be wrong (~1.1"/yr) and is not used.

Caveats: parallax is a nuisance parameter here, not a result — WISE scan-direction centroid offsets alternate between the two observing seasons and bias it (e.g. ε Indi B). Barnard's Star perspective acceleration (~1 mas/yr²) is ignored. SPHEREx (6.15" px, ~1 yr) adds no useful leverage for these motions; its epochs are shown on the track as model positions.

Fitted parallax (nuisance, for transparency): Barnard's Star 575 ± 38 mas (reference 547); ε Indi B 37 ± 20 mas (reference 271); WISE 0855−0714 371 ± 49 mas (reference 439)
