# Space Apps project page — SkyLapse (DRAFT v1, Sat 14 Nov ~16:40; final in A6 #27)
Every field in English. `[brackets]` = fill from the deployed site / science/VALIDATION.md before submitting. Test every link in a private window.

## Project Name
SkyLapse

## High-Level Summary (≈ 150 words)
SkyLapse is a free web tool that lets anyone watch 16 years of the infrared sky and catch what moves. NASA's new SPHEREx telescope maps
the whole sky in 102 infrared colours, but its own record is only about a year long, so nearby cold objects move by only a pixel or two.
SkyLapse joins SPHEREx with 14 years of NASA WISE/NEOWISE images at the same 4.6-micron wavelength, places every image on one common sky
grid and plays them as a single movie. Type a star name or coordinates, press play, and nearby brown dwarfs and fast stars visibly crawl
across the screen. Click an object to see its SPHEREx spectrum — its infrared "fingerprint" — and a plain-language explanation in English
or Azerbaijani, written only from our own measurements. We validated SkyLapse on all five NASA test targets: our measured motions agree
with ESA Gaia and the literature to better than 99 percent. It brings the citizen-science blink method to SPHEREx data.

## Link to Demo
`[30-second video URL]` — file ready: `pitch/video/SkyLapse_30s.mp4` (0:31, captions, live-site recording). A human uploads it (YouTube unlisted or Google Drive "anyone with the link") and pastes the link here.

## Link to Final Project
- Live tool: https://skylapse.vercel.app
- Slides: https://docs.google.com/presentation/d/1IdgZwwna3FG_qA31ovPNDHE3TScZNbb8/edit?usp=sharing `[update to final deck link]`
- Code: https://github.com/FARADTechnologies/NASA2026 `[make public Sun ~13:00]`

## Detailed Description
**What it does.** SkyLapse turns two NASA missions into one interactive "time machine" of the infrared sky:
- **16-year movie:** WISE/NEOWISE epochs 2010–2024 plus SPHEREx epochs 2025–2026 of any sky patch, on one grid, with play, step, speed,
  contrast stretch, zoom and a timeline that shows which telescope took each frame.
- **Compare times:** difference images (this frame minus an earlier one) and co-adds over a chosen time range make movers pop out.
- **Overlays:** ESA Gaia DR3 stars moved to each frame's date, CatWISE2020 sources, the target's predicted track, and masks for saturated
  or flagged pixels; a metadata panel shows date, instrument, wavelength and quality for every frame.
- **Spectral fingerprint:** SPHEREx's 102 bands as an RGB composite and as an on-the-fly spectrum, compared with templates
  (e.g. a cold brown dwarf is invisible below 3 µm and bright at 4.6 µm).
- **Validation and automatic search:** positions measured in every epoch give a proper motion, cross-matched with Gaia/CatWISE; objects are
  labelled "known mover", "new candidate" or "artifact". We never call anything a discovery — candidates go to scientists for follow-up.
- **AI explanations** in English and Azerbaijani, generated only from computed facts.
- **Shareable:** the full view state (position, field of view, frame, overlays) lives in the URL.

**How it works.** A Python pipeline (Astropy, astroquery, reproject, photutils) queries NASA IRSA for SPHEREx images by position (no
hard-coded file lists, so new data releases are picked up automatically), subtracts zodiacal light, co-adds per detector and epoch, fetches
time-resolved unWISE coadds for WISE/NEOWISE, reprojects everything onto one TAN grid (2.75″/px) and exports a small static bundle. A React +
TypeScript web app renders the frames on a canvas in the browser. A small FastAPI service resolves names and builds new fields on request.
The five NASA targets are precomputed, so the demo never depends on a live archive.

**Validation.** Barnard's Star, ε Indi B and WISE 0855−0714: measured proper motion vs reference: Barnard 10395 ± 17 vs 10393 mas/yr (99.8 %), ε Indi B 4717 ± 10 vs 4684 (99.0 %), WISE 0855−0714 8157 ± 15 vs 8152 (99.9 %), fitted over up to 46 WISE epochs spanning 14.0 years.
ε Indi B moves together with ε Indi A (~400″ apart), confirming a bound system. RW Aurigae and R Draconis are too bright for normal photometry, so we built a relative brightness index from the unsaturated outer wings of the star: R Draconis pulses with a period of 246 days (known: 246.12 days, AAVSO VSX), and RW Aurigae varies 8× above the noise of a constant comparison star, tracking NEOWISE photometry (r = 0.93/0.98). A blind search that knew nothing about the targets recovered all 3 NASA movers with 0 false candidates in 5 fields.
We flag honestly where a star is too bright: Barnard's Star and R Draconis saturate SPHEREx in nearly every image.

**Benefits.** Makes the newest NASA mission data understandable in one minute, in a browser, at no cost. Gives students and citizen
scientists the same blink method that let NASA's Backyard Worlds volunteers find cold brown dwarfs — now with SPHEREx colours and a
16-year baseline. First users: university students in Azerbaijan and space-agency school lesson programs.

**Goals / what's next.** Weekly updates as SPHEREx releases data (one command per field), automatic candidate lists, more languages,
a classroom program with universities, and a "flag this mover" button for volunteers.

**Tools and languages.** Python 3.11 (Astropy, astroquery, reproject, photutils, NumPy, SciPy), FastAPI, TypeScript, React, Vite,
Canvas 2D, Vercel hosting, GitHub. AI coding assistants (Claude Code) — see "Use of AI".

## Use of AI
We used AI openly. AI coding assistants (Claude Code, Anthropic) helped our team write the data pipeline, web app and documentation;
team members set the concept, checked the science and reviewed every change before it was merged. The plain-language object explanations
(English and Azerbaijani, ≤ 110 words each) are written by Anthropic's Claude Opus 5.5 only from numbers our pipeline computed: the English
texts and one Azerbaijani text in a Claude Code session, the other four Azerbaijani texts through the organizers' Claude API gateway. Every number
in the 10 texts is checked automatically against our computed facts, words like "discovery" are blocked, the team read them, and the site labels
them "AI-generated from our measured facts". All scientific data comes from NASA and ESA, not from AI. No AI-generated images, video or voice are used; our demo video is a plain screen recording of the live site. No AI-generated NASA logos, flags or mission symbols are used.

## NASA Data
- SPHEREx spectral images, Data Release 1 + Quick Release 3 (NASA/JPL-Caltech, via NASA/IPAC IRSA).
- WISE / NEOWISE images — time-resolved unWISE coadds, 2010–2024.
- CatWISE2020 catalogue (via IRSA).

## Space Agency Partner Data
- ESA Gaia Data Release 3 — positions, proper motions and parallaxes for the overlay and for validation.

## References
See `pitch/REFERENCES.md` (data, services, libraries, scientific papers, design inspiration, AI tools). Paste the final list here.
