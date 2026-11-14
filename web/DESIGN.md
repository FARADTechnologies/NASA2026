# SkyLapse web — design notes (R0, frontend agent, Sat 14:05)
Rule: **works like WiseView, looks like NASA Eyes.** Screenshots in `design-refs/` (wiseview, legacysurvey, nasa_eyes).

## What we take from each reference
| Reference | Function we copy | Look we copy / avoid |
|---|---|---|
| WiseView (byw.tools) | blink interval slider, min/max pixel sliders, stretch linearity, invert, zoom, Gaia overlay, difference imaging, shift-and-add (= our co-add), **whole state in the URL**, epoch date range printed huge above the image, one tick per epoch | avoid its 2018 grey form sidebar and Times font |
| Backyard Worlds (Zooniverse) | "flipbook + mark the mover" framing; plain-language help for non-experts | friendly short labels ("Play the movie", "What am I looking at?") |
| Legacy Surveys Viewer | full-bleed image, translucent floating panels, RA/Dec readout top-left, scale bar, layer/overlay toggle list, "Jump to object" box | panels with soft corners over the image, not boxed forms |
| ESASky / Aladin Lite | live cursor RA/Dec readout, catalog circles, FOV control, search box at top | dark chrome, thin 1px borders |
| NASA Eyes | cinematic black, one big title bottom-left with a small stat line under it ("4,862 solar systems \| 6,470 planets"), hamburger + round icon buttons on the right edge, generous empty space | big sans typography, very little chrome |

## Page layout
- **Home `/`**: full-screen dark hero (blurred sky frame behind), title "SkyLapse", one line "Watch 16 years of the infrared sky and catch what moves.",
  search box (name or RA Dec), five NASA target cards (thumbnail, name, tag "motion"/"variability"), links Discover / About.
- **Viewer `/view`**: top bar (logo, search, share). Left rail (≈260 px): sequence, stretch, min/max, invert, speed, difference, co-add, overlays, FOV.
  Centre: canvas player, big date + instrument + band label above it (WiseView style), RA/Dec cursor readout + scale bar in corners.
  Bottom: timeline 2010 → 2026, one tick per frame, WISE vs SPHEREx colour, 2011–2013 hibernation gap drawn as a hatched gap, play/pause/step.
  Right panel (≈340 px): frame metadata, object card (big agreement %), copilot EN/AZ, spectrum, light curve.
- Laptop 1280 px minimum; projector-readable (body ≥ 15 px, key numbers 28–56 px).

## Palette (one accent)
- background `#05070d` · panel `rgba(14,18,30,0.82)` + border `#1f2740` · text `#e8ecf5` · muted `#8a94ad`
- accent (UI, buttons, current frame) `#4cc9f0` (cyan) · WISE ticks `#f4a259` (amber) · SPHEREx ticks `#4cc9f0` (cyan)
- Gaia circles `#7CFC9A` (green) · target track `#ff5d8f` (pink) · masked tint grey 40% · saturated tint `#ff8c1a` 45%
- status: ok `#5ad17a`, warn `#ffcc4d`, error `#ff6b6b`

## Fonts
- UI: **Inter** (Google Fonts) 400/600/700; numbers/coords: **JetBrains Mono** 500. Fallback system-ui / monospace.

## Motion
- Panels fade/slide 150 ms; no animation on the image itself except the blink. Never block the UI on load: show frames as they arrive.

(Azer owns theme/colours/fonts/spacing — his calls override this file.)
