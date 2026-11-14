# Jury Q&A — prepared answers (A5, issue #26)
Q&A is 5 minutes. Answer in 2 sentences, then stop. Numbers in `[brackets]` wait for `science/VALIDATION.md` / the deployed site.
Jury: IDDA (digital innovation), Azercosmos (space agency / satellite operator), Baku Engineering University. None are astronomers.
Who answers: Amal by default; Murad for deep technical questions (pipeline, data, validation).

## A. The idea
1. **What problem do you solve, in one sentence?**
   SPHEREx has only about one year of data, so nearby moving objects shift by only a pixel or two and are almost impossible to see.
   We join it with 14 years of NASA WISE images so anyone can watch 16 years of the infrared sky and see what moves.
2. **How is this different from NASA's own IRSA tools?**
   IRSA is an excellent archive: it gives you files, one mission at a time, for experts. SkyLapse turns two missions into one movie
   on one grid, with motion, spectrum and a plain-language explanation — no software install, no FITS knowledge.
3. **How is this different from WiseView / Backyard Worlds?**
   WiseView blinks WISE images only and inspired our controls. We add SPHEREx's 102 colours, so you can not only see an object move
   but also check its infrared "fingerprint" in the same tool.
4. **Can it find Planet X?**
   No tool can promise that, and we do not claim it. SkyLapse helps people find moving candidates in the infrared, which is exactly
   where a cold, distant planet would have to be found — and every candidate goes to scientists for follow-up.
5. **Why infrared?**
   Cold objects like brown dwarfs, and any distant planet, give off almost no visible light but glow in the infrared. WISE 0855 is
   invisible to normal telescopes and bright at 4.6 microns.

## B. Validity — "how do you know it's right?"
6. **How do you know the motion is real and not noise?**
   We measure the object's position in every epoch over 16 years and fit a straight line; a real object moves steadily, noise does not.
   For Barnard's Star, Epsilon Indi B and WISE 0855 our speeds agree with Gaia and the literature to better than 99 % (99.0–99.9 %); ε Indi B also moves with its companion ε Indi A to 99.3 %.
7. **How did you validate the tool?**
   On the five objects NASA itself chose for this challenge. The three movers are compared with published proper motions; for
   Epsilon Indi B we also check it moves together with its companion star Epsilon Indi A, about 400 arcseconds away.
8. **What about saturated (too bright) stars?**
   Barnard's Star and R Draconis are so bright that SPHEREx saturates on them in almost every image. We detect that, label it in the
   tool, and never show saturated pixels as real brightness — honesty is part of validity.
9. **The two telescopes have different pixel sizes and units. Isn't joining them wrong?**
   We put every image on one common sky grid with Astropy and show brightness as relative, not absolute. The tool says clearly that
   SPHEREx pixels (6.15″) are resampled to WISE's 2.75″ grid for comparison.
10. **SPHEREx sees different colours in different images. Can that fake a brightness change?**
    Yes — that is a known trap, so we only compare brightness at the same wavelength. Co-added images are used for display and
    motion, not for measuring brightness.
11. **How does the AI explanation avoid making things up?**
    The AI only receives numbers our pipeline computed (speed, distance, temperature class, flags) and is told to use nothing else.
    It explains, it does not invent; every text is precomputed and checked.
12. **What is a "candidate" vs a "discovery"?**
    A candidate is something that moves or changes in our data and is not yet in known catalogues. Only follow-up by professional
    astronomers can turn it into a discovery — we never call anything a discovery.

## C. Users and impact
13. **Who will use it?**
    Students, teachers and amateur astronomers first — starting in Azerbaijan with university students and the SRDA community
    `[1000+ — confirm]` — and citizen scientists worldwide. Scientists can use it as a quick-look tool before downloading data.
14. **Why would a student care?**
    It turns real NASA data into something you can watch and understand in one minute, in Azerbaijani or English. It is a door into
    space science that needs only a browser.
15. **What is the impact for Azerbaijan?**
    It gives our students hands-on experience with the newest NASA mission data, at zero cost. It can be used in university labs and
    school astronomy clubs, and it shows that Azerbaijani teams can build tools for global science.
16. **Has citizen science really found anything?**
    Yes. Volunteers in NASA's Backyard Worlds project, blinking WISE images, have found cold brown dwarfs that automated searches had
    missed. SkyLapse gives that method SPHEREx's colours and a longer time baseline.

## D. Technology, cost, future
17. **How does it work technically?**
    A Python pipeline (Astropy) downloads SPHEREx and WISE cutouts from NASA archives, puts them on one grid and saves a small static
    bundle. A React web app plays it in the browser; new positions are processed on a small server.
18. **What does it cost to run?**
    Almost nothing: the showcase data is static files on free hosting, and new fields are cached after the first request. The only
    real cost is a small server for live fields.
19. **How do you handle new SPHEREx data?**
    SPHEREx releases new data every week. Our pipeline queries by position, with no hard-coded file lists, so rebuilding a field
    with the newest data is one command.
20. **What if NASA's servers are slow or down?**
    The demo and the five NASA targets come from our precomputed bundle, so they never depend on a live server. Live fields show
    progress and a clear message if the archive is slow.
21. **What's next after the hackathon?**
    Automatic candidate lists for the whole sky, more languages, and a classroom program with universities in Azerbaijan. Long term,
    a "flag this mover" button so volunteers' findings reach scientists.
22. **Can Azercosmos or others reuse it?**
    Yes — it is open source under the Apache 2.0 licence, and the same "time machine" idea works for any series of satellite images
    of the same place over years.

## E. Team and AI
23. **How did you use AI?**
    We used AI coding assistants (Claude Code) to build the pipeline and web app faster, and an AI model to write the plain-language
    explanations — but only from numbers our code computed. Every AI image or audio is marked; details are in our AI-use statement.
24. **What did you build yourselves in 36 hours?**
    The full pipeline that joins two NASA missions on one grid, the web viewer, the motion measurement and validation, and the
    explanations. The data is NASA's and ESA's; the tool, the method and the validation are ours.
25. **What was the hardest part?**
    Making two very different telescopes agree: different pixel sizes, colours and units, plus saturated bright stars. We solved it
    with a common grid, relative brightness and honest saturation flags.

## Rules
- Never "we discovered", never "Planet X found". Use "candidate for follow-up".
- If you don't know: "Good question — we haven't measured that yet; here is what we do know: …". Never invent a number.
