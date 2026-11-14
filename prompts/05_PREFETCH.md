# SkyLapse — DATA PREFETCH TASK (run tonight, before the hackathon)

## Who you are helping and why
You are helping team FARAD at the NASA Space Apps Challenge 2026 (Baku Local Event), challenge "Planet X and SPHEREx".
The servers we depend on are SLOW (one SPHEREx cutout takes ~30 s). Tomorrow the team must build, not wait.

**Your ONLY job in this task:** download, organize and sanity-check the raw data for the 5 required test targets.
Do NOT build the web app. Do NOT reproject, co-add or analyze beyond the QA checks listed below.

## Facts already verified on 13–14 Nov 2026 (trust these; do not spend time re-researching them)
1. SPHEREx Data Release 1 (DR1) + Quick Release 3 (QR3) are queryable together through the IRSA TAP service
   (tables `spherex.artifact` and `spherex.plane`). DR1 and QR3 supersede QR2; do not use QR2.
2. This query works (it takes ~35 s per position):
   ```sql
   SELECT a.uri, p.energy_bandpassname AS band, p.time_bounds_lower AS t_start, p.planeid
   FROM spherex.artifact a JOIN spherex.plane p ON a.planeid = p.planeid
   WHERE 1 = CONTAINS(POINT('ICRS', {ra}, {dec}), p.poly)
   ORDER BY p.time_bounds_lower
   ```
   Before the first real query, run `SELECT TOP 1 * FROM spherex.plane` and `SELECT TOP 1 * FROM spherex.artifact`,
   save the column names to `data/raw/spherex/_schema.txt`, and add any useful extra columns
   (e.g. time_bounds_upper, obs_id, release/collection) to the query.
   Use `astroquery.ipac.irsa.Irsa.query_tap(...)` or plain HTTP `https://irsa.ipac.caltech.edu/TAP/sync?FORMAT=csv&QUERY=...`.
3. Cutout URL pattern (size is in DEGREES):
   `https://irsa.ipac.caltech.edu/{uri}?center={ra},{dec}d&size={size_deg}`
   It returns a multi-extension FITS: PRIMARY, IMAGE (MJy/sr, zodiacal light NOT subtracted), FLAGS, VARIANCE,
   ZODI, EPSF, WCS-WAVE. One cutout ≈ 30 s and ≈ 4 MB (the EPSF extension is most of the size).
   Transient download failures are normal → retries are mandatory.
4. Example: WISE 0855 has 258 SPHEREx images (D1:36, D2:48, D3:45, D4:36, D5:48, D6:45) in 3 time clusters:
   MJD 60800–60802 (May 2025), 60980–61022 (Nov–Dec 2025), 61151–61174 (Apr–May 2026).
5. WISE/NEOWISE time-resolved unWISE coadds (2010–2024), one FITS per epoch:
   `http://byw.tools/cutout?ra={ra}&dec={dec}&size={pixels}&band={1|2}&epoch={n}`
   Returns float32 FITS with a TAN WCS and MJDMIN/MJDMAX header keywords, in < 1 s. Epochs run 0..~22
   (varies by position); requests past the last epoch return HTTP 500. Pixel scale 2.75".
   This is a public service run by Backyard Worlds / AMNH: be polite — max 2 concurrent requests,
   ~0.3 s pause between requests, never download the same file twice.

## Targets (the 5 objects NASA requires us to test on)
Resolve each name with SIMBAD (`astroquery.simbad`) or CDS Sesame. Compare with the fallback; if they differ
by > 30", log it in the summary and use the resolver value.

| id | resolver name | fallback ICRS J2000 (deg) | note |
|---|---|---|---|
| wise0855 | WISE J085510.83-071442.5 | 133.795130, -7.245147 | coordinates given by NASA in the challenge |
| barnard | Barnard's star | 269.4521, +4.6934 | proper motion ≈ 10.4"/yr toward north |
| eps_indi_b | eps Ind B (try "eps Ind Ba" if needed) | 331.0438, -56.7827 | must be ≈ 400" from eps Ind A (330.8403, -56.7860) |
| rw_aur | RW Aur | 76.9564, +30.4014 | young variable star |
| r_dra | R Dra | 248.1675, +66.7548 | Mira variable, near the north ecliptic pole |

**Field center rule (important):** high-proper-motion stars have moved a lot since J2000 (Barnard's star is
≈ 4.5' north of its J2000 position today). For every target, take the proper motion from SIMBAD/Gaia and
propagate the position to epoch **2018.0** (the middle of the 2010–2026 window). Use that as the field center
for ALL downloads. Store both the J2000 and the 2018.0 positions.

**Field sizes:** SPHEREx `size=0.15` deg (≈ 88 px at 6.15"/px). WISE `size=256` px (≈ 11.7').

## Steps
0. Setup: Python 3.11+, a virtual environment, `pip install astropy astroquery numpy requests tqdm`.
   Work inside a folder named `skylapse-data/`. Log everything to `data/logs/`.
1. **Resolve targets** → write `data/raw/targets.json` with: id, resolver name, ra/dec J2000, pmra/pmdec,
   center ra/dec at 2018.0, which resolver was used.
2. **Catalogs** (cone radius 0.12 deg around each 2018.0 center), save as CSV per target in `data/raw/catalogs/`:
   - Gaia DR3 via `astroquery.gaia` (ESA archive): source_id, ra, dec, ref_epoch, parallax, pmra, pmdec,
     phot_g_mean_mag, bp_rp, ruwe.
   - CatWISE2020 via IRSA TAP (table name is probably `catwise_2020`; inspect the schema first):
     name, ra, dec, pmra, pmdec, w1mpro, w2mpro and their errors.
3. **WISE epochs**: for band 1 and 2, request epoch = 0, 1, 2, … until 2 consecutive failures or epoch > 40.
   Save `data/raw/wise/<target>/w{band}_e{NN}.fits` and an `index.csv` (epoch, band, MJDMIN, MJDMAX, file).
4. **SPHEREx**:
   - Run the TAP query per target and save `data/raw/spherex/<target>/index.csv` (all columns).
   - Download every cutout with a thread pool of 10 workers, timeout 300 s, 4 retries with backoff
     (5, 15, 45, 90 s). Make it resumable: skip files that already exist AND open correctly with astropy.
   - Order of work: targets wise0855 → barnard → eps_indi_b → r_dra → rw_aur; inside each target download
     bands D6, D5, D3 first, then D1, D2, D4. This way partial results are already useful.
   - Save raw files to `data/raw/spherex/<target>/<band>/<original_filename>`.
   - Write failures to `data/raw/spherex/<target>/failures.csv` and retry them in a second pass at the end.
   - Make a SLIM copy of every cutout WITHOUT the EPSF extension (keep PRIMARY, IMAGE, FLAGS, VARIANCE, ZODI,
     WCS-WAVE, all headers unchanged) in `data/slim/spherex/<target>/<band>/`. The team will use the slim copies.
5. **QA report** → `data/SUMMARY.md`, per target:
   - resolved coordinates and 2018.0 center; number of Gaia and CatWISE sources;
   - WISE epochs per band with first/last date;
   - SPHEREx images per band and per time cluster (group by gaps > 30 days), failures left, disk size.
   - Sanity check on one cutout per band: IMAGE shape; the FLAGS bit names (they are written as header
     keywords — list them all); the central wavelength at the target pixel, computed exactly as in the IRSA
     tutorial: `WCS(header, fobj=hdul, key="W")` with `.sip = None`, then `pixel_to_world(x, y)`.
6. **Package**: zip `data/slim` + `data/raw/wise` + `data/raw/catalogs` + `targets.json` + `SUMMARY.md`
   into `skylapse_data_v1.zip`. Report its size. (A human will upload it to the shared Google Drive.)
7. **Report back** with this format:
   ```
   PREFETCH REPORT
   - Finished: yes/no (what is missing)
   - Per target: WISE epochs (W1/W2), SPHEREx images per band, failures
   - Zip: path + size
   - Anything surprising (e.g. a target with very few SPHEREx images, saturation, resolver mismatch)
   ```

## Rules
- IRSA: never more than 12 parallel requests. byw.tools: never more than 2.
- Never delete raw data. Never overwrite a valid file.
- If after 20 minutes the SPHEREx success rate is below 50 %, stop and report (probably server throttling).
- Expected total time: about 1.5–2.5 hours. Keep the machine awake and on power.

## Optional speed experiment (only if SPHEREx downloads are very slow; never block the main task)
SPHEREx data is also on AWS S3: bucket `nasa-irsa-spherex`, region us-east-1, anonymous access, prefixes `dr1/` and `qr3/`
(prepend the prefix to the IRSA browsable directory path). Try on 3 files:
`fits.open(s3_uri, use_fsspec=True, fsspec_kwargs={"anon": True})`, read the header, then read only the needed pixels with `.section[...]`
(requires `s3fs`). If this is at least 5× faster than the cutout service, use it for the remaining files and write the
same slim MEF structure. Report the timing comparison either way.
