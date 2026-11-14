# SkyLapse — light curves of the NASA variability targets (S3, P1-3)

Reproduce: `cd science && .venv/Scripts/python.exe -m skylapse_science lightcurves` (~10 s). Output: `lightcurve` block in
`science/out/<field>/objects/target.json`, details in `science/out/<field>/lightcurve_analysis.json`, plots `science/out/png/<field>_lightcurve.png`.
NEOWISE / AllWISE single-exposure rows are cached in `science/data_cache/` (IRSA `neowiser_p1bs_psd`, `allwise_p3as_mep`, 5" cones).

## The problem
R Draconis and RW Aurigae are far too bright: their cores are saturated in every unWISE epoch (written as zeros) and in SPHEREx
(OVERFLOW / empty cores). Magnitudes from the core would be fiction, so none are published.

## Method: relative wing index (both stars)
1. For each unWISE epoch (W1 3.4 µm, W2 4.6 µm; native WCS) take the median of each 1-px ring of the star's outer PSF wings, from
   r_in to r_in + 6 px, minus a sigma-clipped background (25–35 px). r_in = 2 px beyond the saturated core (90th percentile of the
   core radius over all epochs): RW Aur 5 px, R Dra 11 px (W1) / 13 px (W2). Ring medians ignore field stars; epochs with zeros inside
   the rings or without coverage are skipped.
2. Index = −2.5 log10(sum of ring medians / its median over all epochs). It is a **relative** index (0 = median), not a magnitude.

## Validation
- **Noise floor:** a constant comparison star (Gaia G = 10.95) in the RW Aur frames: 0.03 mag rms (W1), 0.05 (W2), vs 0.24 / 0.40 mag
  rms for RW Aur.
- **RW Aur vs NEOWISE profile-fit photometry** (per-visit medians; the profile fit uses the unsaturated wings of moderately saturated
  stars): correlation 0.93 (W1) and 0.98 (W2) over 23 visits.
- **R Dra period:** a period search (100–1000 d) on the index finds 246 d (W1) and 247 d (W2); the AAVSO VSX period is 246.12 d.
  WISE visits the star about every 6 months, so an alias near 710 d fits almost as well: the data are consistent with the known
  period but could not single it out alone. Folded on 246.12 d, one sine wave explains 76 % of the W1 index variation.
- R Dra's NEOWISE profile-fit magnitudes (W1 ≈ 0, W2 ≈ −1) scatter by up to ~2 mag within single visits: beyond the saturation
  correction, not used.

## Not possible
SPHEREx synthesized 3.4 / 4.6 µm points (per-epoch spectra interpolated to a fixed wavelength, LVF rule): both stars are saturated
in SPHEREx (spectra.py, `usable: false`).
