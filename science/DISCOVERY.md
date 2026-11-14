# SkyLapse — auto-discovery of moving sources (S4, P1-5)

Reproduce: `cd science && .venv/Scripts/python.exe -m skylapse_science discover --field barnard --field eps_indi_b --field wise0855 --field rw_aur --field r_dra`
(~1 min). Output: `science/out/<field>/candidates.json` (contract §6 + additive keys).

## Result (blind search, no prior knowledge of the target)
| field | sources (2010 / 2023-24) | trial pairings | verified tracks | known movers | recovered (measured μ vs catalogue) | new candidates |
|---|---|---|---|---|---|---|
| Barnard's Star | 206 / 190 | 30 | 2 | 1 | **1** (10405 ± 74 vs 10393 mas/yr) | 0 |
| ε Indi B | 52 / 45 | 1 | 1 | 1 | **1** (4713 ± 2 vs 4684 mas/yr) | 0 |
| WISE 0855−0714 | 129 / 106 | 24 | 1 | 1 | **1** (8155 ± 15 vs 8152 mas/yr) | 0 |
| RW Aur (control) | 190 / 180 | 7 | 0 | 0 | — | 0 |
| R Dra (control) | 27 / 22 | 7 | 1 (not significant) | 0 | — | 0 |

**Recall 3 / 3 known movers, 0 false candidates in 5 fields.** (The second Barnard track and the R Dra track are stationary
stars whose motion is below 3σ / 150 mas/yr and are dropped.)

## Method
1. All unWISE W2 epochs of a field share one pixel grid. Detect sources (DAOStarFinder, 5σ) in the first-year (2010) and
   last-year (2023–24) median stacks and in the first and last single epochs (fast movers smear in a stack).
   Saturated stars (zero hole) become one detection at the S1 wing-fit centre.
2. Early/late detections within 1 px are stationary. Every other early×late pair 1.2–70 px apart with similar flux is a trial
   track; each is checked in **every** epoch (centroid within 1.5 px of the straight-line prediction, S/N > 4) and kept if seen
   in ≥ 60 % of the epochs (one-to-one, best first).
3. Proper motion of each kept track with the S1 fit (position + motion + parallax, bootstrap errors). Mover = ≥ 3σ and
   ≥ 150 mas/yr (≥ 2" over 14 years, above the systematic floor).
4. Classes: **known** = the NASA target or a Gaia DR3 / CatWISE2020 source at the same place moving the same way (30 % or 3σ);
   **artifact** = near a saturated star, near the frame edge, poor track fit, or a catalogued star that does not move like
   this; otherwise **candidate** (unconfirmed, needs follow-up — never a "discovery").

## Recall definition (and why CatWISE needs cleaning)
Known movers = Gaia DR3 sources with μ > 300 mas/yr and G < 19, plus CatWISE2020 sources with μ > 300 mas/yr that pass reliability
cuts: μ > 5σ, W2 < 15.5, single component (nb = 1), no artifact flag, consistent static vs motion photometry
(|w2mpro − w2mpro_pm| < 0.5), parallax not negative at > 3σ, and not inside the 60" halo of a star that saturates (G < 9 or
W2 < 8). The raw CatWISE list contains 881 entries above 300 mas/yr in these five frames (Barnard 356, RW Aur 206, WISE 0855 220,
ε Indi B 92, R Dra 7) and **none of them has a Gaia counterpart moving the same way**; the ones we inspected by hand were halo
ghosts of saturated stars, diffraction-spike detections, or duplicates of the fast mover itself. Counts per field are stored in
`candidates.json → stats`.

## Limits
Small fields (11.7′ cutouts) hold few real fast movers, so recall rests on 3 objects. Sensitivity: W2 S/N ≥ 5 in a one-year
stack and ≥ 150 mas/yr. SPHEREx D6 is not used for detection (6.15" pixels, 1-year baseline add no leverage here).
