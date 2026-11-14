# How we used AI — SkyLapse (team FARAD)
Local organizers' rule: AI use is allowed and must be shown. AI-generated images/videos carry a watermark. No AI-generated NASA logos,
flags or mission symbols. This statement is used on slide 7, in the Space Apps "Use of AI" field and on the site's About page.

## Short version (for slide 7 / project page, ≤ 60 words)
We used AI openly. AI coding assistants (Claude Code) helped our team write the data pipeline and web app faster; humans set the
concept, checked the science and reviewed every merge. The plain-language explanations (English and Azerbaijani) are written by an AI
model **only from numbers our pipeline computed**. Any AI-generated image or audio is labelled.

## Details
| Where | AI tool | What it did | Human control |
|---|---|---|---|
| Software development | Claude Code (Anthropic Claude models) as coding agents, one per role (orchestrator, pipeline, science, frontend, pitch) | Wrote and debugged code, ran tests, drafted docs and task issues | Team members assigned tasks, reviewed results, made all concept and scope decisions; every change merged by the orchestrator after review |
| Object explanations ("AI Copilot") | Anthropic Claude — the site labels the texts "AI-generated from our measured facts · model: claude-opus-5-5" (written in a Claude Code session — no API key at the venue, decision D-018; `science/copilot_offline_texts.json`) | Turns computed facts (proper motion, agreement with Gaia, saturation flags, spectrum class) into short EN + AZ text Only computed facts (`copilot_facts.json`) as input; every number is checked automatically against those facts, forbidden words ("discovery", "Planet X") blocked, ≤ 110 words; read by the team; labelled "Written by AI" in the UI (science/QA_FACTS.md #15) |
| Pitch preparation | Claude Code (pitch agent) | Drafted script, Q&A answers, this statement | Amal edited wording; all numbers come from repo files (`pitch/FACTS.md`) |
| Images / video / audio | none — the backup demo video is a plain screen recording of the live site | — | — |

## What AI did NOT do
- It did not produce the scientific data: all images and catalogue values come from NASA (SPHEREx, WISE/NEOWISE, CatWISE) and ESA (Gaia).
- It did not decide whether an object is a candidate: that is done by our measurement code (positions per epoch → straight-line fit → cross-match).
- It did not create logos, flags or mission symbols.

The AI agents' instructions are part of the repository (`CLAUDE.md`, `.claude/`, `ops/`, `prompts/`) on purpose, for transparency.
