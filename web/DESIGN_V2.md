# SkyLapse web — design v2 (Sun 12:15, frontend agent; Azer owns cosmetics)
Goal: a calm scientific product. Whitespace, alignment and hierarchy instead of glows, gradients and pills.
References were captured with headless Chromium and studied (not copied): NASA Eyes, Stellarium Web, Our World in Data, Linear, Vercel
(ESASky refused the connection today; its layout was studied in R0).

## What we take from each
| Reference | Taken |
|---|---|
| NASA Eyes | the sky image is the hero; big quiet title + one small stat line; almost no chrome around the canvas |
| Stellarium Web | date/time as a confident mono readout; one row of icon controls under the sky; search in the header |
| ESASky | instrument layers have one fixed colour each, used in toggles, overlays and legends |
| Our World in Data | light theme: warm paper background, ink text, thin grid lines, direct labels, source/method line under every chart |
| Linear / Vercel | ink-on-paper primary buttons (no neon), 1 px hairlines instead of boxes, sentence-case labels, 4/8 spacing, small radii |

## Tokens (CSS variables in `src/styles.css`, `html[data-theme]`)
- **Light**: bg `#FAF7F2` · surface `#FFFFFF` · surface-2 `#F2EEE6` · line `#E3DDD2` · ink `#1B1F2A` · muted `#5F6776`
- **Dark**: bg `#0E131C` · surface `#151B26` · surface-2 `#1C2331` · line `#283142` · ink `#E7EAF0` · muted `#98A2B3`
- **Canvas** (both themes): `#05070B` — star images never sit on a light background.
- **Meaning colours** (same hue in both themes, tuned for contrast; also used on the canvas, timeline, badges, charts, legends):
  WISE amber `#C06A10` / `#F0A040` · SPHEREx teal `#0F7F95` / `#3CC0D6` · Gaia green `#2A8554` / `#5CC98A` · target rose `#C2255C` / `#FF6B9A`
  · ok `#1F7446` / `#5AD17A` · warn `#8A6100` / `#F2C94C` · AI label violet-grey `#6B5CA5` / `#B7A6F5` (label only, never decoration)
  · contrast checked (WCAG): all text colours ≥ 4.5:1 on the page background in both themes, instrument marks ≥ 3:1 (projector-safe)
- **Interactive**: primary button = ink on paper (inverted per theme); focus ring `#2F6FEB`; links underlined ink. No accent gradients.
- **Type**: IBM Plex Sans 400/500/600 (UI) + IBM Plex Mono 400/500 (dates, numbers, coordinates). Scale 12 · 13 · 14.5 (body) · 16 · 20 · 28 · 40 · 56.
  Labels are sentence case, 12.5 px, medium, muted — no tracked ALL-CAPS headings.
- **Spacing**: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 72. **Radii**: 6 (controls) · 10 (cards, canvas). 
- **Shadows**: light theme only `0 1px 2px rgba(27,31,42,.06), 0 6px 20px rgba(27,31,42,.06)`; dark theme uses hairlines.
- **Icons**: Lucide only (lucide-react), 16–18 px, 1.75 stroke. No emoji.

## Layout
- **Header** (56 px): wordmark · `#ask-skylapse-slot` (mount point for `components/AskSkyLapse.tsx`, built by the orchestrator) · search · Discover · About · theme toggle.
- **Home**: left-aligned column (max 1120): one sentence (56 px, "16 years" in mono), one supporting line, search, "How it works" line;
  the 5 NASA target cards (real thumbnails on canvas colour, name, plain-text tags, mono coordinates); 3 "Try a live field" rows; credits.
- **Viewer**: the movie is the hero — one compact line above it (mono date 40 px · instrument dot + band · frame n/N), canvas fills the
  remaining height, then transport (icon buttons, speed) and the timeline (one tick per frame, instrument colours, hatched WISE gap).
  Left rail 248 px: What to watch · Compare times · Brightness · Zoom · Show on the image, then one **Advanced** drawer (contrast, co-add, more overlays).
  Right rail 360 px: This frame · object card (agreement % 40 px mono) · AI copilot (always with its AI label) · spectrum · light curve · discovery.
  First-visit hint = one slim dismissible line under the header row, not a box over the movie.
- **Phone (< 800 px)**: single column; image, transport, timeline first; controls in a full-screen "Controls" sheet.
- **Theme**: follows `prefers-color-scheme`, toggle in the header, choice stored in `localStorage["skylapse.theme"]` (try/catch), set before first paint.

## Avoided on purpose
Purple/blue gradients, glowing buttons, glassmorphism, emoji, centred marketing hero, pill clouds, card-in-card borders, decorative glows.

## Later (not now)
Subtle animated starfield / slowly drifting galaxies behind the home page (reduced-motion aware); real per-target hero thumbnails as a short loop.
