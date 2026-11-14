# PLAN — SkyLapse (scope, milestones, timeline, demo, pitch facts)

## 1. Context that drives every decision
- Baku Local Event final: 15 teams. Jury (none are astronomers):
  Elkhan Shukurov (IDDA – Innovation and Digital Development Agency), Asad Hasanov (Azercosmos), Bunyamin Seyidov (Baku Engineering University).
- Judging Sun 16:05–18:00 → ~7 min per team incl. Q&A. A live demo moment and a one-sentence problem decide a lot.
- Mentors: Tural Salmanov (Azercosmos — idea & pitch), Vugar Aliyev (IDDA — users & scope), Ilkin Aliyev (Azercosmos — satellite tech, architecture).
  We listen and learn; we only change direction through the escalation protocol.
- Local organizers allow AI tools for everything, on condition that the presentation explains how AI was used.
- Real working time ≈ 16–17 h: Sat 11:00–24:00 (minus meals), Sun 07:30–13:30. Venue: Baku Engineering University (Xırdalan).
- Format (LOCAL_RULES): pitch + live demo = 5 min total (overrun = disqualified), Q&A 5 min, max 7 English slides.

### 1b. Judging criteria — we must score on BOTH lists (updated Sun 00:05, permanent)
| LOCAL (Baku, 20 % each) | how we score it | GLOBAL (NASA) |
|---|---|---|
| Market Potential / Scalability | value as **time saved, people reached, cost per user** (money only with stated inputs): live field in seconds vs manual download + alignment; any sky position, free; users = citizen scientists, students/teachers, SRDA 1000+; ~0 cost/user on NASA open data + free hosting | Impact |
| Presentation | 5-min story, live demo, backup video | Presentation |
| Innovation | first public tool joining the 16-yr WISE baseline with SPHEREx spectra | Creativity |
| Technical Readiness (includes scientific validity) | live prototype + `docs/METHODOLOGY.md` (A/B/C → gap X → D) + README + validation 99.0–99.9 %, 3/3 blind recovery, 0 false alarms | Validity |
| Relevance of the problem | NASA challenge; SPHEREx's 1-yr baseline problem; volunteer science precedent | Relevance |
Mentor (Tural Salmanov, in writing): Market Potential needs no money; validity is judged inside Technical Readiness. Expected methodology answer:
"We reviewed recent methods (NASA/ESA/IAC literature): approaches A, B, C; their gap X; we propose D; and here is the working prototype."

## 2. What NASA asks for (challenge "Planet X and SPHEREx") — our checklist
Objective (mandatory): public web tool; user enters RA/Dec; tool shows a series of SPHEREx images of that patch like a little video,
so moving objects are easy to spot. Test on: Barnard's Star, Epsilon Indi B, WISE 0855 (08h55m10.831s −7d14m42.53s), RW Aurigae, R Draconis.
"Potential considerations" (optional, but the jury reads them as a checklist):
| # | Consideration | Our feature | Priority |
|---|---|---|---|
| C1 | Easy to update with new data releases | pipeline queries DR1+QR3 by position, no hardcoded file lists; "rebuild field" command | P0 |
| C2 | Creative display of 102 bands; per-detector co-adds for S/N | D1–D6 co-adds; RGB fingerprint composite | P0 (co-adds) / P1 (RGB) |
| C3 | Spectra on the fly ("extra kudos") | click → spectrum from cached cutouts; template overlay | P1 (target objects P0-ish for demo) |
| C4 | Add / subtract images from different times | difference mode + co-add range mode | P0 |
| C5 | User-selectable field of view | FOV selector (crop/zoom of grid; live fetch size) | P0 |
| C6 | Overlay Gaia / WISE | Gaia DR3 propagated per frame; WISE frames are in the movie itself; CatWISE overlay | P0 (Gaia) |
| C7 | Coordinates in URL (embeddable) | `/view?ra=&dec=&fov=&seq=…` | P0 |
| C8 | Metadata such as contamination flags | per-frame metadata panel + flag-mask overlay | P0 |
| C9 | Use Astropy / Aladin | Astropy everywhere in pipeline; Aladin Lite context map | P0 (astropy) / P1 (Aladin) |

## 3. Scope (IDs are used in issues and commits)
### P0 — must work at M2 (Sat 18:30). Without these we cannot win.
- P0-1 Bundle for the 5 targets: WISE W1/W2 epochs + SPHEREx D1–D6 per epoch, on one common grid (pipeline).
- P0-2 Viewer: blink player, timeline with dates and instrument badges, play/pause/step, speed, stretch (linear/asinh/log + percentiles), invert, zoom (frontend).
- P0-3 Search by name or RA/Dec + URL state + share link (frontend + api resolve).
- P0-4 Difference mode (frame − reference frame) and co-add mode over a selected time range (frontend).
- P0-5 Gaia DR3 overlay with positions propagated to each frame's date; target track line (frontend, data from pipeline).
- P0-6 Frame metadata panel + flags/saturation mask overlay (frontend + pipeline).
- P0-7 Arbitrary coordinates work live: WISE frames fast; SPHEREx frames progressively (queued job with progress); graceful fallback text (api + pipeline + frontend).
- P0-8 Public deployment (web + bundle; API) with a stable URL (orchestrator).
- P0-9 Proper-motion validation table for Barnard's Star, Eps Indi B, WISE 0855: measured vs reference (science).
- P0-10 Pitch: 7-slide deck, live demo script, 30-s video, project page text in English, AI-use explanation (pitch).
### P1 — Sat 22:30 target, Sun 10:30 at the latest. These make us win, not just pass.
- P1-1 Spectrum panel: spectrum of the target objects (precomputed) and of any clicked source in cached fields; template comparison.
- P1-2 Spectral fingerprint RGB composite (D1/D3/D6) toggle.
- P1-3 Light curves for R Dra and RW Aur: WISE W1/W2 + SPHEREx synthesized W-band points, saturation-aware.
- P1-4 AI Copilot texts (EN + AZ) for the 5 targets + all candidates, precomputed into the bundle.
- P1-5 Discover page: auto-detected movers/variables per field, labelled known / candidate / artifact, with recall stats.
- P1-6 About / Method page: how it works, validation results, data credits, AI disclosure.
- P1-7 Aladin Lite context map (SPHEREx HiPS or 2MASS/unWISE) to pick a field.
### P2 — only if all P0+P1 are done and stable
- P2-1 Live copilot endpoint (server-side key). P2-2 ElevenLabs narration ("Listen" button) for the 5 targets.
- P2-3 Citizen "flag this mover" with persistence. P2-4 Extra showcase fields (e.g. a field near the north ecliptic pole).
- P2-5 Parallax in the motion fit. P2-6 Additional partner-agency data, only if it adds real value.
### Explicitly OUT
Finding Planet X; training a deep-learning model from scratch; mobile app; user accounts; anything needing IRSA live during the pitch.

## 4. Milestones (Baku time) and definition of done
| Milestone | Time | Done means |
|---|---|---|
| M0 Kickoff | Sat 11:00 | repo + docs + ops live; every agent has role file and an assigned issue; data zip available |
| M1 Walking skeleton | Sat 13:30 | deployed URL shows the WISE 0855 movie (WISE W2 epochs + SPHEREx D6) from a real bundle, play/pause works |
| M2 Core complete | Sat 18:30 | all P0-1…P0-6 for all 5 targets on the deployed URL; P0-7 at least WISE-live; vertical slice tested by pitch role |
| M3 Winning layer | Sat 22:30 | P0-9 table done; P1-1, P1-3, P1-4 for the 5 targets; demo script rehearsed once on the real site |
| Night | Sat 22:30–24:00 | deploy, record rough demo video; people go home before transport stops; remote work allowed |
| M4 Feature freeze | Sun 10:30 | only bug fixes after this; P1-5/P1-6 if ready; final deploy tagged `v1.0` |
| Submit | Sun 14:30 | Space Apps project page complete and submitted; all links tested in a private window |

## 5. Demo script (≈ 90 s, live, on the deployed site; video backup ready)
1. Home → click "WISE 0855". The 16-year movie plays: 2010 → 2026, a faint red dot crawls ~2 arcminutes. Timeline shows WISE then SPHEREx.
2. Toggle Spectral Fingerprint / detector: invisible at 1 µm, bright at 4.6 µm → spectrum panel: "consistent with the coldest known brown dwarf (~250 K)".
3. Barnard's Star → validation card: measured speed vs Gaia, % agreement. "Tested on all five NASA targets."
4. Discover tab → a candidate list; open one; the AI copilot explains it in Azerbaijani, then English.
5. Paste any coordinates → WISE frames appear in seconds, SPHEREx frames stream in. Share link.
Rule: every number shown in the demo comes from our own pipeline output, never typed by hand.

## 6. Pitch facts (use these exact framings; keep numbers sourced from `bundle/`)
- Problem (one sentence): "SPHEREx maps the whole sky in 102 colours every six months, but its own record is barely a year long —
  nearby worlds move only a pixel or two, and no one can sift a billion objects alone."
- Insight: WISE watched the same sky for 14 years at the same wavelength (4.6 µm). Joining both gives a 16-year infrared movie.
- Proof: all 5 NASA test targets pass; measured proper motions agree with Gaia / literature (exact % from P0-9).
- Impact: NASA's challenge text says most known comets and brown dwarfs were found by volunteers blinking images (Backyard Worlds).
  SkyLapse brings that to SPHEREx for everyone, starting with Azerbaijan's students and SRDA, the country's 1000+ member robotics/AI community.
- Scalability: new SPHEREx data arrives weekly; a field rebuild is one command; static-first design costs ~nothing to host.
- AI use (required by local organizers): explain clearly — coding assistants, copilot text generation from computed facts only, any AI audio/images marked.
- Never say: "we discovered", "Planet X". Say: "candidates for follow-up".
