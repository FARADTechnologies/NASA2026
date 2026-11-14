# Live mode via the deployed API (T9, #78) — Sun 15 Nov 00:00–00:40 Baku
All jobs were submitted ONE AFTER ANOTHER to `POST https://skylapse.vercel.app/api/fields` with fov 8.8′ (the site default) and timed from submit to `status`. WISE only (D-015).

## API v0.3.0 + PR #100 (final)
| field | RA, Dec | wise_ready | done | frames (W2+W1) | dates |
|---|---|---|---|---|---|
| Galactic plane | 281.5, −2.5 | 11.6 s | 16.2 s | 22 + 22 | 2010-04 → 2024-04 |
| High latitude (NGP area) | 195.5, +28.5 | 10.3 s | 14.8 s | 24 + 24 | 2010-06 → 2024-05 |
| Near a bright star (Vega) | 279.2347, +38.7837 | 10.1 s | 14.7 s | 22 + 22 | 2010-04 → 2024-04 |
| North ecliptic pole | 270.0, +66.5607 | 19.7 s | 33.4 s | 32 + 32 (of ~427 epochs) | 2010-01 → 2024-07 |
(The high-latitude and Vega rows come from v0.3.0, before PR #100; PR #100 touched only epoch selection.)

## Bugs found and fixed
- v0.2 (before PR #87): jobs sat in `wise_ready` for 4–7 min (galactic plane not done after 420 s; Vega done at 416 s) because WISE-only jobs still ran the SPHEREx TAP query, which blocked the one-job queue. Fixed in PR #87.
- v0.3.0 (before PR #100): at the NEP the movie stopped in 2015 (epochs 0–79 of ~427 were fetched), and a single missing epoch (HTTP 500) ended the galactic-plane W1 band after 2 frames. Fixed in PR #100.

## Pre-warmed demo fields (cached: submit → done in 1.1 s; checked in the browser)
| name | RA, Dec (2018.0) | proper motion | what moves |
|---|---|---|---|
| Luhman 16 (nearest brown-dwarf pair, 6.5 ly) | 162.3057, −53.3177 | 2.79″/yr | ~40″ west over 2010–2024; it is not saturated |
| Teegarden's Star (red dwarf with planets, 12.5 ly) | 43.2716, +16.8623 | 5.13″/yr | ~70″ south-east |
| Kapteyn's Star (fast halo star, 13 ly) | 77.9651, −45.0470 | 8.67″/yr | ~2′ south-east; bright and saturated in WISE |
Links: `https://skylapse.vercel.app/view?ra=162.3057&dec=-53.3177&fov=8.8` · `…?ra=43.2716&dec=16.8623&fov=8.8` · `…?ra=77.9651&dec=-45.0470&fov=8.8`
(Use exactly these RA/Dec/fov values: the API caches by RA/Dec rounded to 4 decimals and fov rounded to 0.1. Proper motions are from SIMBAD.)
