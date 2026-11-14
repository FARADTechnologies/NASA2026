# SMOKE TEST — hooks, Stop-hook loop, allowlist, compaction (one machine, ≈ 10 min)
Re-tests C1, C2, C10, C14 from `test/TEST_PLAN.md` after run 1 failed them (hooks never loaded because of a nested folder).
Uses the existing test repo `FARADTechnologies/NASA2026-ops-test` only as a GitHub target for `gh`; nothing is pushed, no issues are created.
Run it in Claude Code's DEFAULT permission mode (not "bypass permissions"), so C14 is meaningful.

1. **C1 — start folder + brief.** Do step 0 of CLAUDE.md (START-FOLDER CHECK). Record: does `pwd` contain `CLAUDE.md` and
   `.claude/settings.json`? Did a "SKYLAPSE RECOVERY BRIEF" arrive at session start (quote its first line)? If not, follow step 0 and stop.
2. Setup (no checkout, so the new kit files stay as they are): `echo orchestrator > .skylapse-role` ·
   `git init -b main` · `git remote add origin https://github.com/FARADTechnologies/NASA2026-ops-test.git` (if `gh` says it cannot access it,
   use `<captain-login>/NASA2026-ops-test`). Check `python ops/bin/skyops.py whoami` → orchestrator.
3. **C14 — allowlist.** Run, one by one: `git status`, `gh auth status`, `python ops/bin/skyops.py status`, `python ops/bin/skyops.py inbox`,
   `python ops/bin/skyops.py next --wait 0`. Ask the human afterwards: "Did you have to approve any of these? Which?" Record the answer.
4. **C10 — Stop-hook loop.** Run `python ops/bin/skyops.py auto on`, then END YOUR TURN with one line "ending turn to test the Stop hook".
   Expected: the Stop hook blocks you (a journal-guard message may come first: then update `ops/memory/sessions/orchestrator.md` and end
   the turn again). When the "AUTONOMOUS MODE is ON" block arrives, record it, but run `python ops/bin/skyops.py next --wait 20` instead of 540.
   After it prints NO_TASK, end your turn once more → a second block should arrive. Then run `python ops/bin/skyops.py pause` and end your turn:
   this time the hook must let you stop (PAUSED). Record what happened at each step.
5. **C2 — compaction.** Ask the human: "Please type /compact now, then type: continue smoke test". After compaction, check that a new
   RECOVERY BRIEF with "You were just COMPACTED" arrived, and that `ops/memory/sessions/orchestrator.log` got a PreCompact snapshot line.
6. Clean up: `python ops/bin/skyops.py resume`, `python ops/bin/skyops.py auto off`. Do not push anything.
7. Print this table for the captain:
   | check | result | evidence |
   |---|---|---|
   | C1 brief at start | PASS/FAIL | … |
   | C10 Stop hook blocks + pause releases | PASS/FAIL | … |
   | C2 brief after /compact + PreCompact log | PASS/FAIL | … |
   | C14 no prompts for routine commands | PASS/FAIL (list prompts) | … |
   plus any error text you saw and the fix you propose.
