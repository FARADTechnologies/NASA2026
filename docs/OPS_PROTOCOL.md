# OPS PROTOCOL — autonomous agents on a GitHub-Issues task bus

## 1. Idea
Every laptop runs one Claude Code agent with a fixed **agent id** (`.skylapse-role`): orchestrator, pipeline, science, frontend, pitch.
GitHub Issues are the shared task board. The orchestrator writes tasks; each agent polls for issues addressed to its id, decides from
the issue header whether it may start, does the work, reports, and immediately takes the next task — without a human copy-pasting.
Humans supervise: they watch their agent's screen, can interrupt at any time (Esc), approve sensitive tasks, and pause/resume.

## 2. Issue format (machine-readable)
Title: `[<agent>][<P0|P1|P2>][<auto|human>] <task id> — <short goal>` e.g. `[frontend][P0][auto] F2 — Controls + URL state`
Body starts with the header block (the `task` command adds it automatically):
````
```skylapse
agent: frontend
priority: P0
start: after #12 #14
autonomy: auto
milestone: M2
```
````
- `agent` — the only agent allowed to take it.
- `start` — `now` | `after #N #M` (all listed issues must be CLOSED) | `at 2026-11-14T13:30+04:00` (not before that time).
- `autonomy` — `auto` (start without asking) | `human` (start only after a human adds the label `approved`; use for deploys,
  making the repo public, spending money, deleting things, contacting people, anything irreversible).
Then the task body (template in §4). Labels mirror the header: `agent:<id>`, `prio:Px`, `type:task|bug|question|checkpoint`, `needs-human`.

## 3. Lifecycle (labels)
open → **claimed** (`status:in-progress`, claim comment) → **submitted** (`status:review`, REPORT comment) →
orchestrator **accepts** (merges PR, closes issue → dependants unlock) or **requests changes** (`status:changes-requested` → the agent picks it again first).
`status:blocked` = waiting on an answer (the agent moves on to other work). Questions (`type:question`) are closed by the answering agent.

## 4. Task template (orchestrator)
```
## Goal            one sentence, user-visible outcome
## Context         why it matters for the project; links to docs sections
## Inputs          files, contract sections, data paths
## Requirements    numbered, testable
## Out of scope
## Acceptance test exact steps (≤ 2 min) + required proof (screenshot / command output / URL)
## Report back     REPORT template
```
Rules: one outcome per task; ≤ ~2 h; always an acceptance test; never give two agents the same files; chain with `start: after #n`.
Checkpoints are scheduled tasks for the orchestrator itself: `[orchestrator][P0][auto] CHECKPOINT M1` with `start: at 2026-11-14T13:30+04:00`.

## 5. Report template (agents, via `skyops.py submit`)
```
Status: done | partial
Works (proof): commands run, numbers, screenshot/URL
Not done / known issues:
Changed files · PR:
Contract impact: none | proposal in #
Next suggestion:
```

## 6. Commands (`python ops/bin/skyops.py …`)
Agents: `next --wait 540` · `claim N` · `submit N --file r.md --pr URL` · `block N --reason …` · `ask --to <agent> --title … --text …` · `escalate --title … --body-file …`
Orchestrator: `setup-labels` · `task --agent A --title … --body-file f.md --prio P0 --start "after #3" --autonomy auto --milestone M2` ·
`accept N --merge-pr URL` · `changes N --text …`
Humans: `status` · `inbox` · `approve N` · `auto on|off` · `pause` · `resume` · `watch`
(`next` blocks up to 9 minutes polling every 45 s, so an idle agent costs about one short turn per 9 minutes.)

## 7. Autonomy switches (local files, gitignored)
- `.skylapse-auto` (via `skyops.py auto on`): the Stop hook never lets the agent go idle — it sends it back to `next`.
- `.skylapse-pause` (via `skyops.py pause`): the agent stops after its current step; `next` answers PAUSED. `resume` + tell it "continue".
- Safety brake: > 6 auto-continuations within 4 minutes (something fails fast) → the hook lets the agent stop; a human checks.
- Humans can always press Esc and talk to their agent; a human instruction overrides the loop.

## 8. Escalation
Levels: L0 agent decides · L1 orchestrator decides · L2 Murad (on-site human) · L3 captain Deneme (remote; consults Claude).
L3 triggers: concept or P0 scope change; contract-breaking change; data contradicting a pitch claim (e.g. validation off by > 10 %);
mentor/jury pressure to pivot; rule/eligibility doubt; P0 blocker > 45 min; deployment down within 3 h of judging.
`skyops.py escalate` creates `ESC: …` labelled `type:escalation` + `agent:captain`, assigned to the captain. The human sends one WhatsApp line:
"ESC #<n>: <one sentence>". The captain answers in the issue. Meanwhile the agent continues on the safest default.
```
ESCALATION REPORT — <time> — from <agent> via <human>
1. Situation in one sentence
2. Current state (what works, deployed URL, milestone status)
3. Problem + evidence (logs, numbers, screenshots)
4. Options A/B/C: what it means, time cost, risk, effect on the 5 judging criteria
5. Recommendation and why
6. Decision needed by <time>. Meanwhile we continue with <safe default>
```

## 9. Git
Branch per agent `role/<agent>`; orchestrator integrates on `main`. Commit small with the task id (`[F2] url state`). Pull `main` hourly.
PR per task; the orchestrator merges with `accept --merge-pr`. Never force-push. Never commit `data/`, `.env`, local flags.
Two agents on one machine → separate folders: `git worktree add ../skylapse-pipeline role/pipeline`, each with its own `.skylapse-role`.

## 10. Memory protocol (survives auto-compaction)
- Project-root `CLAUDE.md` is re-injected after compaction.
- SessionStart hook prints the RECOVERY BRIEF (agent id, journal, project state, know-how, commits, queue, autonomy status).
- Stop hook: if files changed but the journal is > 15 min old → update it first (once; 5-min grace).
- PreCompact hook: snapshot of git state into `ops/memory/sessions/<agent>.log`.
Files: `ops/memory/sessions/<agent>.md` (journal, only that agent writes; keep < ~120 lines) · `PROJECT_STATE.md` and `DECISIONS.md`
(orchestrator only) · `KNOWHOW.md` (everyone appends one-line lessons, prefixed with the agent id).
Codex/Gemini users have no hooks: their AGENTS.md/GEMINI.md tells them to run `skyops.py brief` and update the journal manually.

## 11. Checkpoint ritual (13:30, 18:30, 22:30, Sun 10:30)
Orchestrator (scheduled CHECKPOINT task): merge ready PRs, deploy, smoke-test the 5 targets on the deployed URL, update PROJECT_STATE.md,
post a CHECKPOINT comment (P0/P1 table, URL, risks, next tasks) and give Murad a WhatsApp summary; cut scope per PLAN rules if behind.
