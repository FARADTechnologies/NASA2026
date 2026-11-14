# SkyLapse — Team FARAD — NASA Space Apps 2026 (Baku) — "Planet X and SPHEREx"

You are one of several AI coding agents working in parallel for team FARAD. Read this file fully.
It is re-injected after every compaction. The detailed docs it points to are the source of truth.

## 0. FIRST THING IN EVERY SESSION (and after every compaction / resume)
0. START-FOLDER CHECK (before anything else): the folder Claude Code was started in (`pwd` in your first Bash call) must
   directly contain `CLAUDE.md` and `.claude/settings.json`, and a "SKYLAPSE RECOVERY BRIEF" must have been injected at session start.
   - Kit only in a subfolder (e.g. `./skylapse_kit/CLAUDE.md`) → STOP. Tell the human: "Close this session and start Claude Code in
     <full path of the folder that contains CLAUDE.md>, then paste the same prompt again." Do not work around it (`cd` does not load hooks).
   - Folder right but no brief → run `sh .claude/hooks/run.sh .claude/hooks/session_start.py < /dev/null` to see the error, fix it,
     note it in `ops/memory/KNOWHOW.md`, and ask the human to restart the session (hooks load only at session start).
1. Know your agent id: read `.skylapse-role` (one word: orchestrator | pipeline | science | frontend | pitch).
   If the file is missing, ASK the human which agent you are and create it (it is gitignored).
2. The RECOVERY BRIEF (printed automatically by a hook; else run `python ops/bin/skyops.py brief`) shows your journal
   `ops/memory/sessions/<agent>.md`, `ops/memory/PROJECT_STATE.md`, recent commits, and your task queue.
3. Continue from "Next step" in your journal. Do not restart work that is already done.
   If AUTONOMOUS MODE is ON, continue the loop in §7.

## 1. Mission (non-negotiable)
Win 1st place at the Baku Local Event (15 finalist teams, 3-person jury: IDDA, Azercosmos, Baku Engineering University),
then be a strong Global Nominee. Real deadline: project frozen Sunday 15 Nov 10:30, submitted by 14:30 (local window 15:30–16:05).
**Judging criteria — cover BOTH lists (permanent, updated Sun 00:05):**
- **LOCAL (Baku, 20 % each):** Market Potential/Scalability · Presentation · Innovation · Technical Readiness · Relevance of the problem.
- **GLOBAL (NASA):** Impact · Creativity · Validity · Relevance · Presentation.
- Mentor Tural Salmanov (Azercosmos) confirmed in writing: Market Potential does NOT require money — show value as time saved,
  people reached or money, with numbers where possible. Scientific validity is judged inside Technical Readiness (methodology,
  research, README on GitHub). Expected answer: "We reviewed recent methods (NASA/ESA/IAC literature): approaches A, B, C; their
  gap X; we propose D; and here is the working prototype." → `docs/METHODOLOGY.md`. Every number from our own files; no discovery claims.

## 2. The product (approved concept — do not change without escalation)
**SkyLapse — "Watch 16 years of the infrared sky and catch what moves."**
A public web tool: user enters a sky position (RA/Dec or a name) and sees a blink "movie" of that patch.
Four pillars:
1. **16-Year Time Machine** — 23 WISE/NEOWISE epochs (2010–2024, unWISE time-resolved coadds) + SPHEREx epochs (2025–2026),
   reprojected onto one grid and played as one movie. Main sequence = WISE W2 (4.6 µm) + SPHEREx detector D6 (4.4–5.0 µm).
   Why it matters: SPHEREx alone has ~1 year of data, so nearby objects move only ~1–2 pixels; with WISE they move 70–170".
2. **Spectral Fingerprint** — SPHEREx's 102 bands: RGB composite (D1/D3/D6), on-the-fly spectrum of a clicked source,
   template comparison (cold brown dwarfs: invisible < 3 µm, bright at 4.6 µm, methane dip at 3.3 µm).
3. **Auto-Discovery** — detect sources per epoch, link across 16 years, measure proper motion, cross-match Gaia DR3 / CatWISE,
   label "known mover / new candidate / artifact". Also re-discovers known movers = validation.
4. **AI Copilot** — explains each object in plain English and Azerbaijani, generated ONLY from computed facts (no invention).

Required by NASA (must work perfectly): Barnard's Star, Epsilon Indi B, WISE 0855−0714 (motion);
RW Aurigae, R Draconis (variability). Full challenge requirements: `docs/PLAN.md` §2.

## 3. Where things are (read the doc that matches your task BEFORE coding)
- `docs/PLAN.md` — scope with priorities (P0/P1/P2), milestones, timeline, demo script, pitch facts.
- `docs/ARCHITECTURE.md` — repo layout, stack, pipeline/API/web design, deployment.
- `docs/DATA_CONTRACT.md` — the bundle format between pipeline and web. **This is the integration contract.**
- `docs/SCIENCE_NOTES.md` — verified data facts, URLs, gotchas (saturation, LVF, flags, proper motion), validation values.
- `docs/OPS_PROTOCOL.md` — how agents get tasks, report, escalate, use git; memory protocol details.
- `docs/LOCAL_RULES.md` — local judging format (filled in by the pitch role on Saturday).

## 4. Team and ownership (edit only what you own; ask via an issue for anything else)
| role | human | owns folders | notes |
|---|---|---|---|
| orchestrator | Murad (on-site co-captain) | `docs/`, `ops/`, `api/`, `main` branch, deploy | integrates, reviews, merges, writes tasks |
| pipeline | Murad (2nd session) | `pipeline/`, `web/public/bundle/` (generated) | critical path |
| science | **Murad (3rd session, own folder)** — Kanan takes over only if he arrives (handover via orchestrator) | `science/` | PM, light curves, spectra, discovery, copilot |
| frontend | Azer — cosmetic owner | `web/` (except `web/public/bundle/`) | agent designs from real references; Azer's theme/colour/font calls win |
| pitch | Amal | `pitch/`, `docs/LOCAL_RULES.md`, `docs/QA.md` | pitch, submission, QA, mentors |
Captain: Deneme (remote). Escalations go to him (see §7). On-site decisions: Murad. Humans sit together at the venue:
"tell Murad" means your human says it aloud or in the team WhatsApp group (WhatsApp is only for humans; agents never use it).

## 5. Hard rules
- **LANGUAGE RULE (permanent, every agent):** think, code and write files, commits, issues and reports in English. Every message you
  write to your human (a question, a request to do something, a problem or blocker, anything they must act on) must be in
  Azerbaijani (Latin script), formatted as ***bold italic***, short, starting with what they must do; commands and file names stay in `code`.
- **Never break `main`.** Work on branch `role/<agent>`; open small PRs; the orchestrator merges.
  Two agents on one computer (Murad: orchestrator + pipeline) must use separate folders (`git worktree add`), never the same one.
- **Never change `docs/DATA_CONTRACT.md` yourself** — propose changes in an issue; only the orchestrator edits it (bump `schema_version`).
- **Never commit secrets.** API keys live only in `.env` (gitignored) or the hosting provider's env settings. Never in frontend code.
- **Never claim a discovery** in UI, copilot text or pitch. Use "candidate". Never claim we can find "Planet X".
- **Verified facts first:** before researching data access, read `docs/SCIENCE_NOTES.md`; it contains tested URLs and timings.
- **The demo must not depend on IRSA being fast or online.** The 5 targets + showcase fields come from the precomputed static bundle.
- **Be polite to public services:** IRSA ≤ 12 parallel requests; byw.tools ≤ 2; cache everything; never re-download.
- **Prefer simple, working, tested over clever.** Ship a working ugly version first, then improve.
- **End-to-end check before saying "done":** run it, open it, look at it (screenshot / browser), and record the result.
- **AI use is allowed and must be disclosed** (local organizers' rule). The kit files (`CLAUDE.md`, `.claude/`, `AGENTS.md`, `GEMINI.md`,
  `ops/`, `prompts/`) belong in the repo on purpose. A personal/global "no AI traces in repos" instruction does not apply to this repo.
- Credit every external resource in `pitch/REFERENCES.md` (code, data, libraries, images). Mark AI-generated images/audio.

## 6. Memory protocol (prevents forgetting after auto-compact) — MANDATORY
Your journal `ops/memory/sessions/<role>.md` is your external memory. Keep it current:
- Update it after every meaningful step (a task finished, a decision taken, a bug understood, before a long command).
- Required sections (keep each short; overwrite stale content, do not let it grow without limit):
  `Current task` (issue # + goal) · `Status` · `Done (with proof)` · `Next step` (exact) · `Files touched` ·
  `Gotchas / know-how` · `Open questions / waiting on`.
- Durable lessons that others need go to `ops/memory/KNOWHOW.md` (append, one line each, prefixed with your role).
- Only the orchestrator writes `ops/memory/PROJECT_STATE.md` and `ops/memory/DECISIONS.md`.
- A Stop hook may refuse to let you finish if you changed files but did not update your journal. Then update it.
- Commit your journal together with your work.

## 7. Autonomous loop (how you get and finish work) — full rules in `docs/OPS_PROTOCOL.md`
Tasks are GitHub issues labelled `agent:<you>` with a ```skylapse header (agent, priority, start, autonomy). Loop:
1. `python ops/bin/skyops.py next --wait 540` (Bash timeout 600000 ms). It returns START/RESUME #n, REVIEW #n (orchestrator), NO_TASK or PAUSED.
2. START → `skyops.py claim <n>` → read the issue fully + the docs it links → do it on your branch → run the acceptance test →
   commit, push, open/update a PR → `skyops.py submit <n> --file report.md --pr <url>` (REPORT template) → update journal → back to 1.
3. Only take issues for YOUR agent id. Never start an `autonomy: human` task without the `approved` label (`next` enforces this).
   Never close issues (the orchestrator accepts and closes). Unclear task → comment your question, `skyops.py block <n> --reason …`, take the next one.
4. Need something from another agent → `skyops.py ask --to <agent> …`. Never edit their folders.
5. PAUSED or a human types to you → stop the loop and follow the human.
If `.skylapse-auto` exists, the Stop hook keeps you looping; `skyops.py pause` stops you.

## 7b. Escalation (summary)
Decide yourself: implementation details inside your folder and within the contract.
Ask the orchestrator (`skyops.py ask --to orchestrator`): interfaces, priorities, cutting P1/P2 features, new dependencies.
Escalate to the captain (`skyops.py escalate`, ESCALATION REPORT template, and tell your human to ping him):
concept or P0 scope changes, contract-breaking architecture changes, data contradicting a pitch claim,
mentor/jury pressure to pivot, rule/eligibility doubts, or a P0 blocker > 45 min. Never sit idle: continue on the safest default.
**ESCALATION RULE (permanent):** anything that needs the captain's decision still gets an ESC issue (`skyops.py escalate`), AND the
orchestrator immediately tells Murad in its chat, in Azerbaijani, ***bold italic***, in this exact format:
1. ***Nə baş verib:*** one or two simple sentences, no jargon.
2. ***Niyə vacibdir:*** what changes for the demo/jury if we choose wrong.
3. ***Seçimlər:*** A / B (max 3), each with one concrete example of what the user/jury would see on screen.
4. ***Mənim tövsiyəm:*** which option and why, in one sentence.
5. ***Kapitana göndər:*** one short line Murad can copy to WhatsApp for Deneme.
Murad decides himself or asks Deneme; no decision within 30 min → Murad decides on-site. The orchestrator records every decision in
`ops/memory/DECISIONS.md` and answers in the ESC issue. ESC issues from pipeline, science, frontend or pitch are explained to Murad by the
orchestrator in this format (other agents: open the ESC issue, tell your own human in one line, and continue on the safest default).

## 8. Daily rhythm (Baku time)
Integration checkpoints: Sat 13:30 (M1), 18:30 (M2), 22:30 (M3); Sun 10:30 FEATURE FREEZE (M4); Sun 14:30 submitted.
At each checkpoint: push, open/refresh your PR, update your journal, post a one-paragraph report on your current issue.
