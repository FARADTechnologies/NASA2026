# References and credits — SkyLapse (team FARAD)
Every external resource used in the project. Add new ones as soon as they are used (all roles: tell pitch via `skyops.py ask`).

## NASA data
- **SPHEREx** (NASA/JPL-Caltech) spectral images, Data Release 1 + Quick Release 3, via NASA/IPAC Infrared Science Archive (IRSA):
  TAP `https://irsa.ipac.caltech.edu/TAP`, image cutout service; SPHEREx all-sky HiPS cube `https://irsa.ipac.caltech.edu/data/hips/SPHEREx/spherex_allsky_cube`.
- **WISE / NEOWISE** (NASA/JPL-Caltech, UCLA) — time-resolved **unWISE** coadds (Meisner, Lang, Schlafly & Schlegel), served via
  `byw.tools` (WiseView cutout service) and `unwise.me`.
- **CatWISE2020** catalogue (Marocco et al. 2021, ApJS 253, 8), via IRSA.
- NASA Space Apps Challenge 2026, challenge "Planet X and SPHEREx" — target list and challenge text.

## Space agency partner data
- **ESA Gaia DR3** (Gaia Collaboration, Vallenari et al. 2023, A&A 674, A1), via the ESA Gaia archive / astroquery.

## Other astronomical services
- CDS **SIMBAD** and **Sesame** name resolver (Université de Strasbourg / CNRS) — object names and reference proper motions.
- IMCCE **SkyBoT** — known asteroids (if used for candidate vetting) `[confirm]`.
- **Aladin Lite** (CDS) — sky context map `[if shipped, P1-7]`.

## Software and libraries
- Python 3.11; **Astropy** (Astropy Collaboration 2013, 2018, 2022); astroquery; reproject; photutils; NumPy; SciPy; requests.
- FastAPI (API).
- Web: React 18, TypeScript, Vite; Canvas 2D. Fonts: Inter, JetBrains Mono (Google Fonts, OFL).
- Hosting: Vercel (web, free tier), Railway (API, trial credits) — ops/memory/PROJECT_STATE.md, D-015.

## Design inspiration (no code copied)
- **WiseView** (byw.tools, Caselden et al.) — blink-viewer controls and URL-state ideas.
- NASA's Eyes; Legacy Survey viewer — visual references only.

## Scientific references used for validation
- Barnard's Star, ε Indi A/B proper motions: Gaia DR3 / SIMBAD.
- WISE 0855−0714: Luhman 2014 (ApJL 786, L18), first identification; reference proper motion from Kirkpatrick et al. 2021, ApJS 253, 7 (science/VALIDATION.md).
- Backyard Worlds: Planet 9 citizen-science project (Kuchner et al. 2017, ApJL 841, L19).

## AI tools (see pitch/AI_USE.md)
- Claude Code / Anthropic Claude models — coding agents and copilot text generation.
- AI-generated media: none (videos are plain screen recordings of the live site). Any future AI image/audio is watermarked and listed here.
