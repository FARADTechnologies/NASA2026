# Technical Readiness / Validity slide — content for Amal (A8, issue #92)
Amal places this in her deck herself. Format required by mentor Tural Salmanov (D-022): existing approaches A / B / C → their gap X → our approach D → working prototype.
Source of truth: `docs/METHODOLOGY.md` (science S8 #90 — **not merged yet at Sun 00:45; re-check wording when it lands**) and `science/QA_FACTS.md`.
Every number is cited in `pitch/FACTS.md` (F-numbers in brackets).

---

## Slide text (short — the slide, not the script)

**Title:** How others do it — and what was missing

| | Existing approach | Its gap |
|---|---|---|
| **A** | **Volunteers blinking WISE images** (NASA Backyard Worlds, WiseView) | WISE only — no SPHEREx colours, no built-in check of the motion |
| **B** | **Motion catalogues** (ESA Gaia DR3, CatWISE2020) | Gaia cannot see the coldest objects (WISE 0855 is not in Gaia); CatWISE lists many false fast movers |
| **C** | **SPHEREx archive tools** (NASA IRSA) | ~1 year of data, 6.15″ pixels → nearby objects move only 1–2 pixels; no time-lapse |

**Gap X:** no public tool joins the 14-year WISE record with SPHEREx's 102 colours in one view — and checks the motion it shows.

**D = SkyLapse:** WISE 2010–2024 + SPHEREx 2025–2026 on one sky grid → a 16-year movie, a measured motion, a spectrum and a plain-language explanation — for any sky position.

**Proof (tested on NASA's 5 targets):**
- Motion vs reference: Barnard's Star **99.8 %**, ε Indi B **99.0 %**, WISE 0855 **99.9 %** [F6]
- R Draconis period **246 d** — known **245.6 d** [F13]
- Blind search: **3 / 3** NASA movers found, **0** false alarms [F15]

**Prototype is live: skylapse.vercel.app**

---

## Speaker notes / 30-second answer to "What is your methodology?"
(72 words — plain English. At a calm 150 words/min ≈ 29 s. Machine estimate: Amal, read it once with a stopwatch and cut the last sentence if over 30 s.)

> "We looked at three existing ways. Volunteers blink old WISE images — but without SPHEREx colours. Catalogues like Gaia measure motion — but miss the coldest objects. NASA's SPHEREx tools have only one year of data, so nearby objects barely move. The gap: nothing joins the long WISE record with SPHEREx's colours and checks the motion. SkyLapse does. Tested on NASA's five targets: 99 to 99.9 percent agreement, and the prototype is live."

Word count: 72 (`wc -w`).

---

## If the jury digs deeper (one line each, all from `science/QA_FACTS.md`)
- **How is motion measured?** Position in every WISE image 2010–2024, straight-line fit, 1000× bootstrap errors (QA_FACTS #1).
- **What does 99 % mean?** 100 % minus the size of the speed-and-direction difference as a % of the true motion (QA_FACTS #6).
- **Why trust the blind search?** It found exactly the 3 known movers and nothing false; CatWISE's 881 raw "fast" entries in these fields had no Gaia confirmation (QA_FACTS #8).
- **Limits we state openly:** WISE parallax is not a result; R Dra's 246 d is "consistent with" the known period (a ~713 d alias fits almost as well); saturated stars use the unsaturated edges of the star.

## References behind A / B / C (for the methodology doc / Q&A, not for the slide)
- A: Kuchner et al. 2017, ApJL 841, L19 (Backyard Worlds: Planet 9); WiseView (byw.tools).
- B: Gaia Collaboration, Vallenari et al. 2023, A&A 674, A1 (Gaia DR3); Marocco et al. 2021, ApJS 253, 8 (CatWISE2020).
- C: NASA/IPAC IRSA SPHEREx archive; SPHEREx mission: Doré et al. 2014, arXiv:1412.4872.
- Data behind the movie: unWISE time-resolved coadds (Meisner, Lang & Schlegel 2018, AJ 156, 69).
