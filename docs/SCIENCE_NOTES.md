# SCIENCE NOTES — verified data facts, URLs, gotchas
Everything marked ✅ was tested by hand on 13–14 Nov 2026. Do not spend time re-discovering it.
Values marked ≈ are sanity checks from memory/literature; always prefer values queried at runtime.

## 1. SPHEREx (NASA) — data access
- ✅ Releases: use **DR1 + QR3** together (QR2 is superseded). DR1 released Nov 2026; QR3 arrives weekly.
- ✅ Query by position (IRSA TAP, ~35 s per position, sometimes slower):
  ```sql
  SELECT a.uri, p.energy_bandpassname AS band, p.time_bounds_lower AS t_start, p.planeid
  FROM spherex.artifact a JOIN spherex.plane p ON a.planeid = p.planeid
  WHERE 1 = CONTAINS(POINT('ICRS', {ra}, {dec}), p.poly)
  ORDER BY p.time_bounds_lower
  ```
  `band` values: `SPHEREx-D1` … `SPHEREx-D6`. Times are MJD. Endpoint: `https://irsa.ipac.caltech.edu/TAP/sync?FORMAT=csv&QUERY=…`
  or `astroquery.ipac.irsa.Irsa.query_tap`. SIA is also available but lags ingestion by ~1 day.
- ✅ Cutout: `https://irsa.ipac.caltech.edu/{uri}?center={ra},{dec}d&size={deg}` → MEF FITS, ~30 s and ~4 MB each (mostly EPSF).
  **No CORS header → the browser cannot fetch IRSA directly. Always go through our backend.** ~5 % transient failures → retry.
- ✅ Example (WISE 0855): 258 images = D1 36, D2 48, D3 45, D4 36, D5 48, D6 45, in three time clusters:
  MJD 60800–60802 (May 2025), 60980–61022 (Nov–Dec 2025), 61151–61174 (Apr–May 2026). Fields near the ecliptic poles get far more visits.
- MEF extensions: PRIMARY (has VERSION), IMAGE (MJy/sr, **zodiacal light NOT subtracted**), FLAGS (bitmask), VARIANCE ((MJy/sr)²),
  ZODI (model, MJy/sr), EPSF (PSF grid; we drop it in slim copies), WCS-WAVE (wavelength lookup table).
- Pixel scale 6.15"/px. Detectors and wavelengths (resolving power R):
  D1 0.75–1.1 µm (R≈39), D2 1.1–1.6 (R≈41), D3 1.6–2.4 (R≈41), D4 2.4–3.8 (R≈35), D5 3.8–4.4 (R≈112), D6 4.4–5.0 (R≈128).
  Each detector sits behind a **Linear Variable Filter (LVF)**: wavelength changes across the detector, ~17 channels per detector.
- Wavelength of a pixel (✅ IRSA tutorial method, fine for display/quick-look):
  `spectral_wcs = WCS(hdul["IMAGE"].header, fobj=hdul, key="W"); spectral_wcs.sip = None; wl, bw = spectral_wcs.pixel_to_world(x, y)`.
  For science-grade wavelengths the archive recommends the Spectral WCS product (CWAVE/CBAND); quick-look method is OK for a hackathon.
- Flags: bit names are written as keywords in the image header — read them from the header, never hardcode bit numbers.
  **Mask (reject) these** (same list NASA used for the all-sky cube): TRANSIENT, SUR_ERROR, NONFUNC, DICHROIC, MISSING_DATA, HOT, COLD,
  PHANMISS, NONLINEAR, PERSIST, CROSSTALK, STREAK, BLOOM, SNOWBALL, HALO, SATELLITE_HALO.
  **Do NOT mask** SOURCE (it marks real sources!) or OUTLIER blindly. **OVERFLOW = saturation**: keep the pixel for display but mark it.
- Always subtract ZODI from IMAGE before co-adding (zodiacal light changes with season and would look like "change").
- ✅ HiPS all-sky cube (DR1, 102 layers, zodi already removed, 12.9"/px): `https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube`
  (layer index = 17*(detector-1) + (channel-1); layers 50 and 51 are blank). Good for an Aladin context map; it has no time information.
- ✅ Cloud copy: S3 bucket `nasa-irsa-spherex` (us-east-1, anonymous), prefixes `dr1/`, `qr3/`.
- IRSA also offers: Spectrophotometry Tool, Mosaic Tool, Cutout Tool, Source Discovery Tool, MOST (moving object search).
  Our difference: none of them is a public blink/time-lapse viewer and none joins WISE + SPHEREx into one 16-year sequence.
- Brown-dwarf spectra with SPHEREx: Gagné, Faherty et al. 2026, arXiv:2604.22012 — spectra + subtype templates for ~6,000 L0–Y1 dwarfs;
  data at mocadb.ca. They report per-channel S/N > 10 for most objects with W2 ≤ 14.0 (WISE 0855 has W2 ≈ 13.9 → detectable in D5/D6).

## 2. WISE / NEOWISE (NASA) — 16-year time series
- ✅ Time-resolved unWISE coadds, one FITS per epoch: `http://byw.tools/cutout?ra={ra}&dec={dec}&size={pixels}&band={1|2}&epoch={n}`
  → float32 FITS, TAN WCS, header `MJDMIN`/`MJDMAX`, `EPOCH`, `BAND`. < 1 s per request. Pixel 2.75". size=64 returns 65×65.
  Epochs 0..22 for WISE 0855 (MJD 55319 = May 2010 … 60419 = Apr 2024); requests past the last epoch return HTTP 500.
  **The epoch count depends on position:** 23 is typical, but R Dra (near the north ecliptic pole) has 48. Never hardcode 23;
  probe until HTTP 500 and cluster by date.
  WISE hibernated 2011–2013 → gap in the timeline (show it honestly).
- This service is run by Backyard Worlds / AMNH (it powers WiseView). Credit it. Max 2 concurrent requests, cache forever.
- Units: unWISE "Vega nanomaggies": `mag_Vega = 22.5 − 2.5·log10(flux)`. Vega→AB: W1 +2.699, W2 +3.339.
- Fallback for a static image: `https://unwise.me/cutout_fits?version=allwise|neo11&ra=&dec=&size=&bands=12` (tar.gz of full-depth coadds).
- Saturation: W1 saturates around W1 ≈ 8, W2 around W2 ≈ 6.7 (≈). Barnard's Star, R Dra and probably RW Aur are saturated in WISE.
- Catalog with proper motions: CatWISE2020 at IRSA TAP (table `catwise_2020`; inspect schema).
- Model inspiration: WiseView (byw.tools/wiseview) — sliding time window, blink speed, stretch, invert, Gaia overlay, difference imaging,
  shift-and-add, coordinates in URL hash. We mirror its UX vocabulary, then go beyond it.

## 3. Gaia DR3 (ESA — a 2026 Space Apps partner agency → list it as partner data)
- Query via `astroquery.gaia` (ESA archive, `gaiadr3.gaia_source`) or VizieR `I/355/gaiadr3`.
- Columns: source_id, ra, dec, ref_epoch (=2016.0), parallax, pmra (mas/yr, already × cos δ), pmdec, phot_g_mean_mag, bp_rp, ruwe.
- Position at epoch t (years, Julian): `dec_t = dec + pmdec·(t−2016)/3.6e6`, `ra_t = ra + pmra·(t−2016)/(3.6e6·cos(dec))` (degrees).
  Ignore parallax for overlays (sub-pixel except for the nearest stars; Barnard ≈ 0.55", WISE 0855 ≈ 0.44").
  Julian year from MJD: `t = 2000.0 + (mjd − 51544.5)/365.25`.
- Cold brown dwarfs like WISE 0855 are NOT in Gaia (too faint in optical) → use CatWISE / literature as reference.

## 4. The 5 NASA test targets
| id | object | J2000 (deg) ≈ | motion / variability ≈ | expected behaviour & gotchas |
|---|---|---|---|---|
| barnard | Barnard's Star | 269.4521, +4.6934 | μ ≈ 10.4"/yr, mostly north (Gaia pmra ≈ −802, pmdec ≈ +10362 mas/yr) | moved ≈ 4.5' north since 2000 → centre fields at 2018.0; saturated in WISE (centroid on wings; precision of a few arcsec is fine vs 166" track) |
| eps_indi_b | ε Indi Ba/Bb (T1+T6 brown-dwarf binary) | 331.0438, −56.7827 | μ ≈ 4.7"/yr, co-moving with ε Indi A (330.8403, −56.7860), ~400" away | not saturated; best clean validation: B must move exactly like A (Gaia) → "proof they are a bound system" |
| wise0855 | WISE J085510.83−071442.5 (Y dwarf, ≈ 250 K) | 133.795130, −7.245147 | μ ≈ 8.1"/yr mostly west (≈ −8.1"/yr RA, +0.7"/yr Dec), parallax ≈ 0.44" | invisible in D1–D3 and W1-faint; visible in W2 and D5/D6; not in Gaia |
| rw_aur | RW Aurigae (young T Tauri binary) | 76.9564, +30.4014 | irregular dimming/brightening episodes over the 2010s | likely saturated in WISE W1; check SPHEREx OVERFLOW |
| r_dra | R Draconis (Mira variable) | 248.1675, +66.7548 | period ≈ 245 d, large IR amplitude | very bright → saturation likely in both; near the north ecliptic pole → many SPHEREx visits (good time sampling) |
Motion over the full 2010→2026 baseline: Barnard ≈ 166", WISE 0855 ≈ 130", ε Indi B ≈ 75". SPHEREx-only (~1 yr): 1–2 px or less.

## 5. Methods that must be respected (validity)
- **Common grid:** TAN projection centred on the field centre propagated to epoch 2018.0; 2.75"/px (WISE native); SPHEREx is upsampled —
  say so in the UI ("SPHEREx pixels are 6.15"; resampled for comparison").
- **Epoch binning:** WISE = native epochs. SPHEREx = time clusters (gap > 30 days → new epoch); near the poles, optional finer bins (e.g. 14 days).
- **Co-adding SPHEREx:** per detector per epoch, after zodi subtraction and masking, inverse-variance weighted mean. Store the wavelength range covered.
- **LVF trap (variability):** two SPHEREx images of the same star are usually at different wavelengths. Brightness differences between them are
  NOT variability unless compared at the same wavelength. For light curves: build a spectrum per epoch, then interpolate to a fixed wavelength
  (e.g. 3.4 and 4.6 µm to match W1/W2). Co-adds are fine for display/motion, not for photometry.
- **Moving targets:** when extracting a spectrum or photometry of a mover, use its position propagated to each image's MJD, not a fixed position.
- **Cross-instrument display scaling:** subtract each frame's sigma-clipped background; scale frames so the median flux of several bright,
  unsaturated, low-proper-motion Gaia stars matches a reference frame. Units in the viewer are "relative". Never compare raw WISE DN to MJy/sr.
- **Saturation:** detect (WISE: NaN/flat cores or values above a threshold; SPHEREx: OVERFLOW flag) and label it in UI and data. Never present
  saturated photometry as a light curve; if needed use a clearly labelled "relative brightness index" from unsaturated wings.
- **Proper-motion fit:** centroid per epoch (e.g. photutils `centroid_2dg` in a small box around the predicted position) → tangent-plane offsets
  (ξ, η) in arcsec → weighted linear least squares vs time → μ and its error (bootstrap or residual scatter). Report N epochs used.
- **Name resolution:** CDS Sesame `https://cds.unistra.fr/cgi-bin/nph-sesame/-oxp/SNV?{name}` (XML) or astroquery SIMBAD.
  IRSA's own object lookup was partly down on 13 Nov — do not depend on it.
- **Known asteroids** for SPHEREx-only transients: IMCCE SkyBoT cone search (by date and position).

## 6. Unit helpers
- SPHEREx pixel solid angle ≈ (6.15/206265)² sr ≈ 8.9e-10 sr → 1 MJy/sr over one pixel ≈ 8.9e-4 Jy. (A per-pixel solid-angle map exists; ≈ is fine.)
- AB magnitude: `m_AB = −2.5·log10(Fν / 3631 Jy)`.

## 7. Prefetch findings (14 Nov 2026, 00:40–02:10 Baku; full report in the data folder's SUMMARY.md)
- Downloaded with 0 remaining failures: SPHEREx images per target — WISE 0855 258 · Barnard 362 · ε Indi B 461 · R Dra 2,493 · RW Aur 335.
  Cutouts took ~10 s each (not ~30 s); whole SPHEREx set 61.5 min; 884 transient "server busy" errors all recovered on retry.
- **Barnard's Star and R Dra are saturated in essentially every SPHEREx image** (flag set at the star in 359/360 and 2,488/2,488 on-chip
  images; pixel values mostly NaN). RW Aur is partly saturated (flag set, pixel values still present). → For Barnard/R Dra, SPHEREx photometry
  and spectra of the star itself are not usable: say so honestly in the UI; motion can still be shown via WISE frames, and the position of the
  saturated/NaN core (mask centroid) tracks the star. Never plot NaN cores as zero flux.
- **Risk for P1-3 (R Dra light curve, a NASA-listed variability target):** SPHEREx pixels are unusable at the star. Options, in order:
  (a) NEOWISE single-exposure profile-fit photometry (w1mpro/w2mpro fit the unsaturated wings; check its saturation flags and valid range);
  (b) a clearly labelled "relative brightness index" from the wings/halo in unWISE frames; (c) honest fallback: "too bright for these
  detectors" + the literature period. Science decides by M2 (Sat 18:30); if none works, escalate to the captain.
- Neither Barnard nor R Dra is in CatWISE2020; R Dra leaves a ~5′ hole in that catalog. Use Gaia DR3 / SIMBAD for them.
- **CatWISE's proper motion for ε Indi B is wrong** (~0.9″/yr vs true ~4.7″/yr). Use SIMBAD/Gaia values for validation.
  Separation from ε Indi A measured 402″ (expected ~400″) — good co-motion check.
- R Dra alone is 64 % of all SPHEREx images (north ecliptic pole deep field); its D2 and D5 have only 89 images each vs ~580 for other bands.
  → cap/stack per epoch cluster; do not load all 2,493 into the browser.
- ~10 % of cutouts are not 88×88 (clipped at a detector edge, smallest side 38 px). → loaders and reprojection must handle any shape.
- Services were flaky at night: SIMBAD main and CDS Sesame were down (Harvard SIMBAD mirror worked); Gaia async queries failed (sync worked).
  The live API needs fallbacks for name resolution.
