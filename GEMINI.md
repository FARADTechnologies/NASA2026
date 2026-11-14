# GEMINI.md (for Gemini CLI)
Read `CLAUDE.md` in this folder and follow it exactly — it is the single source of truth for this project.
You do not have Claude Code hooks, so do the memory protocol manually:
1. At the start of every task (and whenever you feel you lost context) run `python ops/bin/skyops.py brief` and read the output.
2. After every meaningful step, update `ops/memory/sessions/<role>.md` (your role is in `.skylapse-role`).
3. Report on your GitHub issue with the REPORT template in `docs/OPS_PROTOCOL.md`.
