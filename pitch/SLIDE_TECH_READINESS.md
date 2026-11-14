# Technical Readiness / Validity slide — content for Amal (A8, issue #92, v2 after review)
Amal places this in her deck herself. Format required by mentor Tural Salmanov (D-022): existing approaches A / B / C → their gap X → our approach D → working prototype.
Aligned with `docs/METHODOLOGY.md` (science S8, merged Sun ~01:15) and `science/QA_FACTS.md`. F-numbers point to `pitch/FACTS.md`.

---

## Slide text (short — the slide, not the script)

**Title:** How moving infrared objects are found today — and the gap

| | Existing approach | Its limit |
|---|---|---|
| **A** | **Human blinking** of WISE images — Backyard Worlds: Planet 9, WiseView | WISE only (2 colours), no spectra, motion judged by eye, not measured |
| **B** | **Automated WISE motion catalogues** — CatWISE2020, unTimely | No spectra; motions can fail: CatWISE gives ε Indi B **1.1″/yr** — the true value is **4.7″/yr** [F20] |
| **C** | **NASA SPHEREx + IRSA archive tools** | 102 colours, but only ~1 year of data: nearby objects move just 1–2 of its 6.15″ pixels; no time-lapse |

**Gap X:** no public tool joins WISE's 14-year record (2010–2024) with SPHEREx's 102-band spectra.

**D = SkyLapse:** all WISE epochs + SPHEREx on one sky grid → a 16-year movie, measured motion, spectrum and a plain-language explanation — for any sky position.

**Proof — tested on NASA's 5 targets, checked against ESA Gaia DR3 and the literature:**
- Motion: Barnard's Star **99.8 %**, ε Indi B **99.0 %**, WISE 0855 **99.9 %** [F6]
- R Draconis pulsation period **246 d** — known **245.6 d** [F13]
- Blind search: **3 / 3** NASA movers found, **0** false alarms [F15]

**Prototype is live: skylapse.vercel.app**

---

## Speaker notes / 30-second answer to "What is your methodology?"
(73 words — plain English, ≈ 29 s at a calm 150 words/min. Amal: read it once with a stopwatch; cut the last sentence if over 30 s.)

> "We looked at three ways people find moving objects today. Volunteers blink WISE images — but only by eye, with no spectra. Automated catalogues like CatWISE measure motion — but can be wrong: for one brown dwarf they say a quarter of the true speed. SPHEREx has spectra — but only one year of data. Nobody joins the long WISE record with SPHEREx spectra. SkyLapse does — and our motions match Gaia to 99 percent."

---

## If the jury digs deeper (one line each — all from `science/QA_FACTS.md` / `docs/METHODOLOGY.md`)
- **How is motion measured?** Position in every WISE image 2010–2024, straight-line fit, 1000× bootstrap errors (QA_FACTS #1).
- **What does 99 % mean?** 100 % minus the size of the speed-and-direction difference as a % of the true motion (QA_FACTS #6).
- **Why trust the blind search?** It found exactly the 3 known movers and nothing false; CatWISE's 881 raw "fast" entries in these 5 fields had no Gaia confirmation (QA_FACTS #8).
- **Limits we state openly:** WISE parallax is not a result; R Dra's period is "consistent with" the known one (a ~713 d alias fits almost as well); saturated stars are measured from the unsaturated edges of the star.

## References behind A / B / C (numbers as in docs/METHODOLOGY.md)
- A: Kuchner et al. 2017, ApJL (Backyard Worlds) [1]; Caselden et al. 2018, WiseView, ascl:1806.004 [2]; Meisner, Lang & Schlegel 2018, AJ 156, 69 (time-resolved unWISE) [3].
- B: Marocco et al. 2021, ApJS (CatWISE2020) [4]; Meisner et al. 2023, AJ (unTimely) [5].
- C: Doré et al. 2014, arXiv:1412.4872 (SPHEREx) [6]; Gagné et al. 2026, arXiv:2604.22012 (SPHEREx ultracool-dwarf library) [7].
- Reference values: Gaia DR3 [8]; Kirkpatrick et al. 2021 [9].
