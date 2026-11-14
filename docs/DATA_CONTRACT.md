# DATA CONTRACT — bundle format (schema_version 1.0)
Owner: orchestrator. Changes only via issue + version bump. Pipeline/science WRITE this; web/api READ this.
Frontend must build against `web/public/bundle/_mock/` (generated mock that follows this file) until real data exists.

## 1. Layout
```
web/public/bundle/
  index.json                      # list of fields
  <field_id>/
    manifest.json                 # everything the viewer needs for this field
    frames/<frame_id>.f32         # raw little-endian Float32Array, row-major, height×width, row 0 = SOUTH edge (FITS order)
    frames/<frame_id>.mask.u8     # optional Uint8Array same size: bit0 = masked/bad, bit1 = saturated
    previews/<frame_id>.png       # optional 8-bit preview (thumbnails, social cards)
    catalogs/gaia.json            # overlay catalog (see §4)
    catalogs/catwise.json
    objects/<object_id>.json      # per-object science products (see §5)
    candidates.json               # auto-discovery output (see §6)
```
Frontend rule: flip vertically when drawing (FITS row 0 is the bottom), and North is up, East is left (standard sky orientation).

## 2. index.json
```json
{
  "schema_version": "1.0",
  "generated_utc": "2026-11-14T12:00:00Z",
  "fields": [
    {"field_id": "wise0855", "title": "WISE 0855−0714", "kind": "nasa_test_target",
     "ra": 133.7951, "dec": -7.2451, "thumb": "wise0855/previews/wise_w2_e00.png", "tags": ["motion", "brown dwarf"]}
  ]
}
```
`kind`: `nasa_test_target` | `showcase` | `live` (live fields come from the API, same format).

## 3. manifest.json
```json
{
  "schema_version": "1.0",
  "field_id": "wise0855",
  "title": "WISE 0855−0714",
  "center": {"ra": 133.79, "dec": -7.245, "epoch": 2018.0},
  "grid": {
    "width": 192, "height": 192, "pixel_scale_arcsec": 2.75,
    "wcs": {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRVAL1": 133.79, "CRVAL2": -7.245,
            "CRPIX1": 96.5, "CRPIX2": 96.5, "CD1_1": -0.000763889, "CD1_2": 0.0, "CD2_1": 0.0, "CD2_2": 0.000763889}
  },
  "frames": [
    {
      "id": "wise_w2_e00",
      "instrument": "WISE",                 // "WISE" | "SPHEREx"
      "band": "W2",                         // "W1" | "W2" | "D1".."D6" | "RGB"
      "lambda_um": [4.6, 4.6],              // [min, max] covered by this frame
      "mjd_start": 55319.36, "mjd_end": 55322.47, "mjd_mid": 55320.9,
      "date": "2010-05-08",                 // from mjd_mid
      "n_inputs": 1,                        // number of images combined
      "file": "frames/wise_w2_e00.f32",
      "mask_file": "frames/wise_w2_e00.mask.u8",   // or null
      "dtype": "float32", "units": "relative",
      "display": {"p01": -3.1, "p50": 0.0, "p99": 210.5, "p999": 900.0},   // percentiles AFTER background subtraction and scaling
      "quality": {"masked_frac": 0.01, "saturated_frac": 0.0, "notes": []},
      "source_files": ["byw.tools epoch 0 band 2"]   // provenance, short
    }
  ],
  "sequences": [
    {"id": "thermal46", "label": "4.6 µm — WISE W2 + SPHEREx D6", "default": true,  "frames": ["wise_w2_e00", "...", "spx_d6_t02"]},
    {"id": "w1d4",      "label": "3.4 µm — WISE W1 + SPHEREx D4", "default": false, "frames": ["..."]},
    {"id": "spherex6",  "label": "SPHEREx only — D1…D6",           "default": false, "frames": ["..."]}
  ],
  "rgb_composites": [
    {"id": "fingerprint_t02", "label": "Spectral fingerprint (D1/D3/D6), 2026", "r": "spx_d6_t02", "g": "spx_d3_t02", "b": "spx_d1_t02"}
  ],
  "objects": ["target"],                   // ids of files in objects/
  "catalogs": {"gaia": "catalogs/gaia.json", "catwise": "catalogs/catwise.json"},
  "candidates": "candidates.json",
  "credits": ["NASA/IPAC IRSA SPHEREx DR1+QR3", "unWISE time-resolved coadds via byw.tools (Backyard Worlds/AMNH)", "ESA Gaia DR3"],
  "build": {"pipeline_version": "0.1.0", "generated_utc": "…", "spherex_releases": ["dr1", "qr3"]}
}
```
Frame id convention: `wise_w{1|2}_e{NN}` and `spx_d{1-6}_t{NN}` (t = SPHEREx time cluster index, 00 = oldest).
`sequences[].frames` are sorted by `mjd_mid`.

## 4. Catalog overlay files (catalogs/*.json)
```json
{"catalog": "Gaia DR3", "ref_epoch": 2016.0, "columns": ["id","ra","dec","pmra","pmdec","parallax","mag","color"],
 "rows": [["4472832130942575872", 269.45, 4.74, -801.6, 10362.4, 546.9, 8.19, 2.83]]}
```
pmra in mas/yr (already × cos δ). `mag` = G for Gaia, W2 for CatWISE. The frontend propagates positions to each frame's `mjd_mid`.

## 5. objects/<object_id>.json
```json
{
  "id": "target", "name": "WISE 0855−0714", "kind": "brown_dwarf",
  "ra": 133.79, "dec": -7.245, "epoch": 2018.0,
  "motion": {
    "measured": {"pmra": -8120, "pmdec": 690, "pm_total": 8150, "err": 60, "unit": "mas/yr", "n_epochs": 24},
    "reference": {"source": "CatWISE2020", "pmra": -8110, "pmdec": 680, "unit": "mas/yr"},
    "agreement_pct": 99.6,
    "track": [{"mjd": 55320.9, "ra": 133.80, "dec": -7.246, "instrument": "WISE"}]
  },
  "spectrum": {
    "unit_flux": "mJy", "points": [{"lambda_um": 4.62, "flux": 0.41, "err": 0.04, "mjd": 61160.2, "detector": "D6", "flagged": false}],
    "template": {"name": "Y1 (Gagné+2026)", "lambda_um": [], "flux": []},
    "notes": ["Undetected below 3 µm"]
  },
  "lightcurve": {
    "points": [{"mjd": 55320.9, "instrument": "WISE", "band": "W2", "mag": 13.9, "err": 0.05, "saturated": false}],
    "notes": []
  },
  "copilot": {"en": "…", "az": "…", "model": "claude-sonnet-5-5", "facts_hash": "…", "audio_en": null, "audio_az": null},
  "flags": {"saturated_in": [], "warnings": []}
}
```
Any block may be `null` if not computed yet — the frontend must handle nulls gracefully ("not available yet").

## 6. candidates.json
```json
{"method": "16-yr cross-epoch linking, ≥3σ motion", "stats": {"known_movers_in_field": 4, "recovered": 4, "new_candidates": 1},
 "items": [{"id": "c001", "ra": 133.81, "dec": -7.25, "pm_total": 950, "err": 120, "class": "candidate|known|artifact",
            "match": {"gaia": null, "catwise": "J0855…"}, "score": 0.82, "object_file": "objects/c001.json"}]}
```

## 7. Live API (same format)
`GET /api/resolve?q=` → `{"name","ra","dec","source"}`
`POST /api/fields {ra, dec, fov_arcmin}` → `{"field_id", "status_url"}`
`GET /api/fields/{id}/status` → `{"state": "queued|wise_ready|spherex_partial|done|error", "progress": 0.42, "manifest_url": "…"}`
`GET /api/fields/{id}/manifest.json` and frame files under the same path as the static bundle.
`POST /api/copilot {facts}` → `{"en","az"}` (P2; server-side key only).
