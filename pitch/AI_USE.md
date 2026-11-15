# How we used AI — SkyLapse (team FARAD)
Local organizers' rule: AI use is allowed and must be shown. AI-generated images/videos carry a watermark. No AI-generated NASA logos,
flags or mission symbols. This statement is used on slide 7, in the Space Apps "Use of AI" field and on the site's About page.

## Short version (for slide 7 / project page, ≤ 60 words)
We used AI openly. AI coding assistants (Claude Code) helped our team write the data pipeline and web app faster; humans set the
concept, checked the science and reviewed every merge. The plain-language explanations (English and Azerbaijani) are written by Anthropic's Claude Opus 5.5
**only from numbers our pipeline computed** (English in a Claude Code session; most Azerbaijani texts via the organizers' Claude API). Any AI-generated image or audio is labelled.

## Details
| Where | AI tool | What it did | Human control |
|---|---|---|---|
| Software development | Claude Code (Anthropic Claude models) as coding agents, one per role (orchestrator, pipeline, science, frontend, pitch) | Wrote and debugged code, ran tests, drafted docs and task issues | Team members assigned tasks, reviewed results, made all concept and scope decisions; every change merged by the orchestrator after review |
| Object explanations ("AI Copilot") | Anthropic **Claude Opus 5.5** (`claude-opus-5-5`). **English** texts (all 5 targets) and the **Azerbaijani** text for ε Indi B were written in a Claude Code session from our facts (D-018); the other 4 **Azerbaijani** texts were generated through the **organizers' Claude API gateway** (S7). Source per language: `objects/target.json` → `copilot.served_by`. | Turns computed facts (proper motion, agreement with Gaia, saturation flags, spectrum class) into short EN + AZ text (≤ 110 words) | Only computed facts (`copilot_facts.json`) as input; every number checked automatically against those facts; "discovery" and "Planet X" blocked; read by the team; labelled "AI-generated from our measured facts · model: claude-opus-5-5" on the site (science/QA_FACTS.md #15) |
| Pitch preparation | Claude Code (pitch agent) | Drafted script, Q&A answers, this statement | Amal edited wording; all numbers come from repo files (`pitch/FACTS.md`) |
| Images / video / audio | none — the backup demo video is a plain screen recording of the live site | — | — |

## What AI did NOT do
- It did not produce the scientific data: all images and catalogue values come from NASA (SPHEREx, WISE/NEOWISE, CatWISE) and ESA (Gaia).
- It did not decide whether an object is a candidate: that is done by our measurement code (positions per epoch → straight-line fit → cross-match).
- It did not create logos, flags or mission symbols.

The AI agents' instructions are part of the repository (`CLAUDE.md`, `.claude/`, `ops/`, `prompts/`) on purpose, for transparency.
