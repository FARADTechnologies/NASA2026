# KNOW-HOW — one line per lesson, prefixed with your role. Append only. Newest at the bottom.
[seed] IRSA SPHEREx TAP query by position takes ~35 s; cutout ~30 s and ~4 MB each; no CORS → backend only.
[seed] Cutout URL: https://irsa.ipac.caltech.edu/{uri}?center={ra},{dec}d&size={deg}; ~5% transient failures → retry with backoff.
[seed] byw.tools/cutout?ra=&dec=&size=&band=&epoch= returns unWISE epoch FITS in <1 s; HTTP 500 = past last epoch; max 2 concurrent.
[seed] SPHEREx IMAGE is NOT zodi-subtracted: always IMAGE − ZODI. Do not mask the SOURCE flag. OVERFLOW = saturation.
[seed] Read flag bit names from the image header; never hardcode bit numbers.
[seed] Barnard's Star has moved ~4.5' since J2000: centre fields at the position propagated to 2018.0.
[seed] LVF: same star in two SPHEREx images is usually at two different wavelengths → not variability.
[seed] WISE 0855 is not in Gaia; use CatWISE2020 / literature for its reference proper motion.
[pipeline] System Python 3.14 has no astropy: pipeline uses repo-local `.venv` (gitignored); run `cd pipeline && ../.venv/Scripts/python.exe -m skylapse_pipeline …`.
[pipeline] Venue network: `git push` of an 11 MB bundle gave HTTP 408; `git -c http.postBuffer=524288000 push` works better. GitHub API had TLS timeouts at 14:20.
[pipeline] SPHEREx IMAGE header WCS has SIP; use WCS(IMAGE header).all_world2pix. Wavelength: WCS(hdr, fobj=hdul, key="W") with .sip=None.
[pipeline] Bundle frames: NaN pixels are written as 0 with mask bit0 set; mask_file is null when a frame has no masked/saturated pixel.
