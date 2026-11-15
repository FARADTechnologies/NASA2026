# SkyLapse — Story, 7-slide outline, live pitch script (A2, issue #23)
Owner: pitch. Presenter: Amal (English). Numbers in `[brackets]` are placeholders until `science/VALIDATION.md` / the deployed site
deliver them — every number must also be in `pitch/FACTS.md` with its source file.

## 0. Hard constraints (docs/LOCAL_RULES.md)
- **5:00 total for presentation + live demo. Over time = disqualified.** Target **4:40**, leaving 20 s buffer. Then 5:00 Q&A.
- Max **7 slides**, English, shared by link. Slide 1 must show team name, member names, challenge.
- AI use must be shown (slide 7). Any AI image/video carries a watermark. No AI-made NASA logos, flags, mission patches.

## 1. The story in six sentences
- **Problem:** SPHEREx maps the whole sky in 102 infrared colours every six months, but its own record is barely a year long —
  nearby worlds move only a pixel or two, and no one can sift a billion objects alone.
- **Insight:** NASA's WISE watched the same sky for 14 years at the same wavelength, 4.6 microns. Join the two, and you get a
  16-year infrared movie.
- **Solution:** SkyLapse — type any sky position, watch 16 years of the infrared sky, and catch what moves.
- **Proof:** All five NASA test targets work. Our measured speeds for Barnard's Star, Epsilon Indi B and WISE 0855 agree with
  Gaia and the literature to better than 99 percent (99.0–99.9 %, `science/VALIDATION.md`).
- **Impact:** Volunteers blinking images have already found brown dwarfs that algorithms missed (NASA's Backyard Worlds). SkyLapse
  brings that to SPHEREx — for anyone, starting with students in Azerbaijan.
- **Future:** SPHEREx sends new data every week; rebuilding a field is one command, and hosting costs almost nothing.

## 2. Seven slides (follows the organizers' recommended order, so the jury can tick it off)
| # | Organizer slot | Title on slide | What is on it (little text, big visual) | Time |
|---|---|---|---|---|
| 1 | Title | **SkyLapse** — *Watch 16 years of the infrared sky and catch what moves.* | Team FARAD · Amal Mirzayev, Hasan Dadashzada, Murad Qaramollayev, Azer Valiyev, Kanan Pashazada · Challenge: "Planet X and SPHEREx" · NASA Space Apps 2026, Baku · one striking frame of the movie | 0:20 |
| 2 | Challenge | **One year is too short** | Left: SPHEREx frame, a star moved 1–2 pixels. Right: "102 colours · whole sky · every 6 months · 1 year of data". One line: "Nearby worlds hide in plain sight." | 0:35 |
| 3 | Solution | **A 16-year infrared time machine** | Timeline bar: WISE/NEOWISE 2010 → 2024 (23 epochs, 4.6 µm) + SPHEREx 2025 → 2026 (4.4–5.0 µm). WISE 0855 moves ≈ 2 arcmin (≈ 130″). | 0:30 |
| 4 | How it works | **Type a position. Watch. Catch.** | 3 screenshots: movie player · spectral fingerprint · AI explanation in AZ/EN. → **switch to LIVE DEMO here (1:30)** | 0:10 + 1:30 demo |
| 5 | Space data | **NASA data, tested on NASA's targets** | Logos as text (no AI logos): NASA SPHEREx · NASA WISE/NEOWISE (unWISE) · CatWISE · ESA Gaia DR3 (partner). Tools: Python, Astropy. Validation table: 3 movers 99.0–99.9 %; R Dra period 246 d vs 246.12 d (AAVSO VSX); RW Aur 7–8× above noise; blind search 3/3 movers, 0 false. | 0:35 |
| 6 | Impact | **Anyone can search the sky** (A10 #94; never "discover") | Backyard Worlds precedent; first users (mentor V. Aliyev, IDDA): **university students** + **space agencies' school lesson programs** as a channel; SRDA community (`[1000+ — confirm]`); free, browser, no install. | 0:30 |
| 7 | Next steps | **What's next + how we used AI** | Weekly SPHEREx updates · auto-candidates for follow-up · more languages. AI box: coding assistants; copilot text only from computed facts; AI media watermarked. Link/QR to the live site. | 0:30 |
Total: 4:40 (3:10 talk + 1:30 demo).

## 3. Live demo (1:30 — inside slide 4; cut from PLAN §5 to fit 5 minutes)
Pre-open the site in a browser tab, on WISE 0855, paused at 2010. Zoom set. No typing during the demo except step 4 (optional).
| t | Action | Say |
|---|---|---|
| 0:00 | Press play on WISE 0855 | "This is one patch of sky, 2010 to 2026. Watch the faint red dot." |
| 0:15 | Let it loop once; point at the track line | "That is WISE 0855 — the coldest brown dwarf we know — about minus twenty degrees Celsius. In 16 years it crossed about two arcminutes. In SPHEREx alone, it barely moves." |
| 0:35 | Toggle Spectral Fingerprint / spectrum panel | "SPHEREx sees 102 colours. This object is invisible at short wavelengths and bright at 4.6 microns — the fingerprint of a very cold brown dwarf." |
| 0:55 | Click Barnard's Star → validation card | "Is the motion real? For Barnard's Star we measure 10.4 arcseconds per year. Gaia says the same: 99.8 percent agreement." |
| 1:15 | Open the AI explanation, Azerbaijani first | "And every object is explained in plain language — in Azerbaijani and English — written only from our own measurements." |
| 1:30 | Back to slides | — |
Fallback: if Wi-Fi or the site fails → play `pitch/video/SkyLapse_demo_backup.mp4` (1:22, same story, captions) from the laptop, no apology longer than one sentence.
Status Sun 00:20: copilot EN/AZ is LIVE (step at 1:15 works); R Dra light curve live (optional swap for the Barnard step if time allows).
Steps cut for time (mention only if asked): live arbitrary coordinates, Discover tab, difference/co-add modes, Gaia overlay.

### Optional live step (only if the 5:00 clock allows — Q&A is the better place)
Pre-warmed live positions (checked Sun ~02:15: each opens in 3–5 s, WISE-only, no target ring → point at the moving star yourself):
- Luhman 16, nearest brown-dwarf pair (6.5 ly), ~40″ west 2010–2024: https://skylapse.vercel.app/view?ra=162.3057&dec=-53.3177&fov=8.8
- Teegarden's Star, red dwarf with planets (12.5 ly), ~70″ south-east: https://skylapse.vercel.app/view?ra=43.2716&dec=16.8623&fov=8.8
- Kapteyn's Star, fast halo star (13 ly), ~2′ south-east, saturated core: https://skylapse.vercel.app/view?ra=77.9651&dec=-45.0470&fov=8.8
Say: "And this works for any position — here is Teegarden's Star, built live." A brand-new typed coordinate takes ~½ min (F17) — don't type one on stage.
(Distances/motions from pipeline/qa/live_api_test.md — pipeline #104.)

## 4. Script (read aloud; short sentences; ≈ 140 words/min)
**Slide 1 — Title (0:20)**
"Good afternoon. We are team FARAD. Our challenge is Planet X and SPHEREx. This is SkyLapse: watch sixteen years of the infrared
sky — and catch what moves."

**Slide 2 — Challenge (0:35)**
"NASA's SPHEREx telescope maps the whole sky in one hundred and two colours of infrared light, every six months. That is amazing data.
But SPHEREx is new. Its record is about one year long. In one year, even a nearby star moves only a pixel or two.
So the closest, coldest worlds hide in plain sight. And no single person can check a billion objects."

**Slide 3 — Solution (0:30)**
"Our insight: NASA already watched this sky before. The WISE mission took pictures of the whole sky for fourteen years, at the same
wavelength — four point six microns. We put WISE and SPHEREx on one grid. Now you get a sixteen-year movie. In sixteen years, nearby
objects move not one pixel, but minutes of arc. You can see them move."

**Slide 4 — How it works (0:10) → DEMO (1:30)**
"You type a position in the sky, or a name. SkyLapse plays the movie. Let me show you — live."
→ demo, see §3.

**Slide 5 — Space data (0:35)**
"Everything runs on open space data. NASA SPHEREx, NASA WISE and NEOWISE, and ESA's Gaia catalogue as partner data.
We tested on all five NASA target objects. For the three moving ones, our measured speeds agree with Gaia and the literature to
better than ninety-nine percent. For the two variable stars: R Draconis pulses every 246 days — the known period is about 246 days. And our blind search found all three NASA movers by itself, with zero false alarms."

**Slide 6 — Impact (0:30)**
"Why does it matter? With NASA's Backyard Worlds project, volunteers blinking sky images found cold brown dwarfs that computers missed.
SkyLapse brings that power to SPHEREx — in a browser, free, for anyone. Our first users: university students in Azerbaijan — and, through space agencies' school lessons, young learners too. We do not claim
discoveries. We help people find candidates for scientists to follow up."

**Slide 7 — Next steps + AI (0:30)**
"SPHEREx sends new data every week. Updating a field is one command, and hosting costs almost nothing. Next: automatic candidate lists,
more languages, and a class program for schools.
We used AI openly: coding assistants helped us build it, and the AI explanations are written only from our own measurements.
SkyLapse — sixteen years of sky, for everyone. Thank you."

Word count of spoken script (without demo) = 350 (counted with `wc -w`) → 2:30 at 140 wpm, 2:55 at a calm 120 wpm;
demo narration = 107 words in 1:30. Estimated total 4:00–4:25 → 15–60 s buffer under the 5:00 hard limit.
**Timing estimate Sun 03:00 (A12):** spoken §4 = 372 words + demo ≈ 110 words → ≈ 3:10 at Amal's measured pace (≈ 152 wpm); + demo clicks with PRE-OPENED tabs ≈ 15 s + slide↔browser switches → **≈ 3:30–3:50**. Real stopwatch run = Amal (her deck/notes may differ). Pre-open WISE 0855, ε Indi B, Barnard (10.9 s cold load!) and R Dra (8.9 s) in tabs before going on stage.
**Timing proof:** Amal read §4 script + §3 demo narration aloud with a stopwatch on Sat 14 Nov ~14:40: **3:00**.
Live clicking/loading will add time → rehearse with the real site (A6) and keep the total ≤ 4:40.

## 5. Rules for the stage
- Years: "16 years" = the movie (2010→2026). Motion was MEASURED over 14 years of WISE (2010–2024). Never mix 130″ (16 yr, literature) with 114″ (14 yr, measured).
- "Bright at 4.6 microns" is true for WISE 0855 only — ε Indi B (T dwarf) peaks near 4 µm and dips at 4.6 µm.
- Full fact sheet with caveats for Q&A: `science/QA_FACTS.md`.
- Never say "we discovered" or "Planet X found". Say "candidates for follow-up".
- If asked "Can it find Planet X?": "No single tool can promise that. SkyLapse helps people find moving candidates in the infrared — where a cold, distant planet would have to be found."
- If time is short: drop the slide 6 Backyard Worlds sentence first, then the slide 3 last sentence.
