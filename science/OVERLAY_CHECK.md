# Live-field overlay check after T10 (S10, #123)

Deployed API v0.4.0, Sun 15 Nov ~11:30 Baku. Reproduce: `cd science && .venv/Scripts/python.exe -m skylapse_science.overlay_check out/validation/overlay_check.json`.
Method: for each catalog source that should be clearly visible (Gaia 9 < G < 17, CatWISE 9 < W2 < 14, inside the frame, not saturated),
propagate it to the frame's `mjd_mid` exactly as the viewer does, project with the manifest WCS, and measure the real source's centroid
(photutils `centroid_2dg`) in the first (2010) and last (2023–24) W2 frames. 1 px = 2.75″.

| field | live build | frames | catalog rows (Gaia / CatWISE) | overlay offset 2010: median / 90 % (n) | overlay offset 2024: median / 90 % (n) | marked mover | mover track vs real source |
|---|---|---|---|---|---|---|---|
| Luhman 16 (162.3288, −53.3195) | done, 20 s | 50 | 1577 / 1609 | 0.07 / 1.51 px (224) | 0.11 / 1.63 px (189) | **none** | — |
| Teegarden's Star (43.2537, +16.8813) | done, 16 s | 48 | 113 / 969 | 0.06 / 0.14 px (22) | 0.08 / 0.13 px (22) | Gaia DR3 35227046884571776, 5.1″/yr | 0.13 px (2010), 0.08 px (2024) |
| Kapteyn's Star (77.9191, −45.0184) | done, 12 s | 46 | 195 / 1109 | 0.04 / 0.23 px (33) | 0.07 / 0.16 px (31) | Gaia DR3 4810594479418041856, 8.6″/yr | all 23 W2 frames: median 0.13 px, max 0.55 px (saturated star; brightness-weighted centre) |
| fresh coordinate (30.1234, −20.4321) | done, 16 s | 50 | 82 / 903 | 0.10 / 0.25 px (8) | 0.12 / 0.20 px (7) | none (none expected) | — |

**Result:** the Gaia/CatWISE circles land on the stars (median ≤ 0.12 px ≈ 0.3″ in both 2010 and 2024 frames), so the proper-motion
propagation to each frame date is correct; the marked movers follow their stars across 14 years.

**Findings for pipeline / orchestrator**
1. **Luhman 16 (the 3rd-closest system to the Sun) is not marked as a mover.** Gaia DR3 has no source moving > 1″/yr within 60″ of it
   (checked on the VizieR I/355 mirror), and the CatWISE overlay has none near it (it is very bright in W2). Live mode marks only Gaia
   fast movers, so it cannot mark Luhman 16. Do not use Luhman 16 as a live demo of an auto-marked mover; Teegarden's or Kapteyn's Star work.
2. **Catalog cap:** the Luhman 16 field is crowded (VizieR: 2189 Gaia DR3 sources within 4.4′) and the live query returned exactly 2000
   rows (`build.catalog_status`), so some faint stars are missing from the overlay in dense Milky Way fields. Cosmetic, but say "brightest
   2000 stars" if asked.
3. The 90th-percentile offset of 1.5–1.6 px in the Luhman 16 field comes from blended faint stars in that crowded field, not from the
   propagation (the median is 0.07–0.11 px).
