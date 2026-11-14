# OPS DRY-RUN — test the autonomous agent system before the hackathon (≈ 45–60 min)
Repo: `FARADTechnologies/NASA2026-ops-test` (private, throw-away). The real repo `FARADTechnologies/NASA2026` is NOT touched tonight. Two agents:
- **Captain's laptop → agent `orchestrator`** (start prompt `test/START_A_DENEME.md` → follows `test/TEST_A_ORCHESTRATOR.md`)
- **Murad's computer → agent `frontend`** (start prompt `test/START_B_MURAD.md` → follows `test/TEST_B_WORKER.md`)
Both humans only: unzip the kit, start Claude Code inside the unzipped folder, paste the start prompt. Each unzipped folder becomes the repo working copy.
The "product" is deliberately tiny; we are testing the SYSTEM, not the code.
Run 1 (14 Nov 02:37–03:14): 10 PASS · 2 PARTIAL · 1 FAIL · 1 NOT TESTED — root cause: Claude Code started in the outer folder of a
nested zip, so hooks/allowlist never loaded. Fixed (flat zip + start-folder check + skyops fixes). Re-test hooks with `test/SMOKE_HOOKS.md`.

## Test issues the orchestrator creates (exact content)
Use `python ops/bin/skyops.py task --agent <a> --title "<title>" --body-file <file> --prio <p> --start "<s>" --autonomy <x>`.
| id | agent | prio | start | autonomy | title | body (task template, short) |
|---|---|---|---|---|---|---|
| TEST-1 | frontend | P0 | now | auto | TEST-1 — targets.json | Create `web/test/targets.json`: array of the 5 NASA targets from docs/SCIENCE_NOTES.md §4 with `id`, `name`, `ra`, `dec`. Acceptance: valid JSON with 5 entries; PR from `role/frontend`. |
| TEST-2 | frontend | P0 | after #<TEST-1> | auto | TEST-2 — index.html | Create `web/test/index.html` that fetches `targets.json` and lists name + coordinates in a table. Acceptance: code reads the JSON (no hardcoded list); PR. |
| TEST-3 | frontend | P1 | now | **human** | TEST-3 — footer (needs approval) | Add a footer "SkyLapse ops test — team FARAD" to index.html. Must NOT start before a human adds the label `approved`. |
| TEST-4 | frontend | P1 | at <bootstrap time + 15 min> | auto | TEST-4 — scheduled README | Create `web/test/README.md` (3 lines: what the page is). Must not start before the scheduled time. |
| TEST-5 | science | P0 | now | auto | TEST-5 — decoy for another agent | Anything. The frontend agent must IGNORE this issue. |
| TEST-6 | frontend | P1 | after #<TEST-2> | auto | TEST-6 — escalation drill | Pretend validation disagrees with the reference by 15 %. Open a real escalation with `skyops.py escalate` using the ESCALATION REPORT template (clearly marked "DRILL"), then submit TEST-6 with the ESC issue number. |
| TEST-END | frontend | P0 | now (created at the end) | auto | TEST-END — finish | Send test notes to the orchestrator with `skyops.py ask`, run `skyops.py auto off`, submit. |
| Q-1 | — | — | — | — | (via `skyops.py ask --to frontend`) | "Which OS and Python version are you running? Answer and close." |

## Orchestrator review behaviour (deliberate, to test every path)
- TEST-1 first submission → `changes` ("add a field `kind` to each target: motion or variability"). Second submission → `accept --merge-pr`.
- TEST-2, TEST-3, TEST-4, TEST-6 → check, then `accept --merge-pr` (TEST-6 has no PR: plain accept).
- TEST-5 stays open (nobody may touch it). Close it at the end with a comment "decoy — test finished".

## Pass criteria (the orchestrator fills `test/TEST_RESULTS.md`; humans confirm)
| # | Criterion | How we see it |
|---|---|---|
| C1 | RECOVERY BRIEF appears at session start on BOTH machines | screen |
| C2 | After `/compact` on Murad's agent, the brief re-appears and the agent continues correctly | Murad types `/compact` once mid-test |
| C3 | Worker takes only `agent:frontend` issues; TEST-5 untouched | TEST-5 has no claim comment |
| C4 | TEST-2 starts only after TEST-1 is closed (dependency gate) | claim time of TEST-2 > close time of TEST-1 |
| C5 | Changes-requested loop works (TEST-1 fixed and resubmitted without a human typing) | issue history |
| C6 | TEST-3 starts only after a human adds `approved` | claim time > approval time |
| C7 | TEST-4 starts only after its scheduled time | claim time ≥ schedule |
| C8 | Escalation drill creates an `ESC:` issue assigned to the captain; captain gets a GitHub notification | captain's phone |
| C9 | Question Q-1 answered and closed by the worker | issue closed |
| C10 | Agents keep looping without anyone typing (Stop hook + `next --wait`) | ≥ 2 tasks done back-to-back with no human input |
| C11 | `pause` stops the worker; `resume` + "continue" restarts it | Murad runs it in a second terminal |
| C12 | Journals updated (`ops/memory/sessions/*.md`), orchestrator updated PROJECT_STATE.md | files on main |
| C13 | PRs merged by `accept --merge-pr`; `main` contains targets.json, index.html, footer, README | GitHub |
| C14 | Permissions: the worker did not need a human click for routine git/gh/python commands (note any prompts that appeared) | screen |
Anything that fails → write it in TEST_RESULTS.md with the exact error and a proposed fix to the kit.
