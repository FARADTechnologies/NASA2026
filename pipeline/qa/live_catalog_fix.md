# Live star-catalogue fix (T10, #120) — Sun 15 Nov 12:00–12:45 Baku

## Causes
1. ESA Gaia TAP and CDS (tapvizier / vizier.cds) reset the connection, and IRSA TAP answered 502. A failed query was returned as an empty catalogue and cached (`"rows": []`). Result: no Gaia circles and unscaled frames.
2. After the rebuild, Vercel's CDN kept serving the old empty `gaia.json` (`Cache-Control: public, max-age=86400`, `X-Vercel-Cache: HIT`).

## Fixes
- PR #127: the ESA/IRSA TAP query races the VizieR mirrors (CfA → IDIA → CDS); the first answer wins (brightest 2,000 rows). A failure is recorded as `unavailable`, never as empty, and is never cached. Each `catalogs/*.json` has a `status`; the manifest has `build.catalog_status` and `build.fast_movers`. At the end the runner retries a failed catalogue and rescales the frames if Gaia came late. Fast movers: the up-to-3 Gaia DR3 stars with pm > 100 mas/yr become `objects/mover1..3.json`, with a 2010–2026 track predicted from the Gaia proper motion (labelled "predicted, not measured"). `live.needs_rebuild()` lets the API purge and rebuild fields whose catalogue failed.
- PR #129: catalogue file writes are locked (the parallel Gaia/CatWISE threads could overwrite each other).
- Orchestrator: API startup purge + submit() use `needs_rebuild`; live-field JSON is now `no-cache` and binaries `max-age=60`; Vercel CDN purged.

## Tests via https://skylapse.vercel.app/api (8.8′, WISE-only)
| field | wise_ready | done | Gaia (status, overlay rows) | CatWISE | fast movers |
|---|---|---|---|---|---|
| Milky Way 113.7870 −7.2450 | 11.9 s | 16.8 s | ok (VizieR), 1,384 | ok, 1,623 | none: "no fast-moving known star in this field" |
| Luhman 16 162.3058 −53.3177 (fresh) | 11.5 s | 16.4 s | ok (VizieR), 1,595 | ok, 1,585 | 1: Gaia DR3 5353638805629225728, 115 mas/yr |
| High latitude 195.6 +28.6 | 12.2 s | 17.3 s | ok (VizieR), 85 | ok, 899 | none |
| Luhman 16 162.3057 (old cached demo) | 1.7 s (cache) | – | 2,365 (old format, fine) | 0 | not computed (built before this fix) |
Frames are now "scaled on 40 / 39 / 10 Gaia stars" (before the fix: "not enough reference stars; unscaled").
I checked all three in the browser on skylapse.vercel.app: Gaia circles visible, the ring + path on the Luhman-field mover, and the object card says the path is predicted from Gaia DR3.

## Known limits
- Luhman 16 itself is in Gaia DR3 (5353626573555863424, G 16.9) **without** a proper motion (two-parameter solution), so it cannot be a Gaia fast mover.
- CatWISE in the old cached demo fields (Luhman 16 / Teegarden / Kapteyn at the 4-decimal demo coordinates) is still empty, and they have no mover objects. Purging them (SKYLAPSE_STALE_FIELDS) rebuilds them in ~17 s.

## Demo fields rebuilt with T10 + SIMBAD fallback (Sun ~14:05, PR #139)
The orchestrator purged the 3 old demo fields and redeployed; I rebuilt them through skylapse.vercel.app/api/fields one after another and clicked each home-page button in a fresh tab:
| button | done | Gaia / CatWISE overlay | mover with ring + path |
|---|---|---|---|
| Luhman 16 (162.3057 −53.3177) | 17.2 s | 1,595 / 1,584 | **Luhman 16**, 2,790 mas/yr, "track predicted from literature proper motion (SIMBAD)" (+ Gaia star, 115 mas/yr) |
| Teegarden's Star (43.2716 +16.8623) | 16.6 s | 111 / 971 | Gaia DR3 35227046884571776 (= Teegarden's Star), 5,123 mas/yr |
| Kapteyn's Star (77.9651 −45.0470) | 16.7 s | 195 / 1,188 | Gaia DR3 4810594479418041856 (= Kapteyn's Star), 8,644 mas/yr |
Known cosmetic limit: Gaia movers are labelled by their Gaia DR3 id, not their common name.
