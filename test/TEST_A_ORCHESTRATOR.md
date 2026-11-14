# TEST — captain's laptop, agent `orchestrator` (Claude Code is running INSIDE the unzipped kit folder; this folder becomes the repo)

You are the **orchestrator** agent in a DRY-RUN of team FARAD's autonomous multi-agent system. Tomorrow 5 agents on 5 laptops will build
"SkyLapse" for NASA Space Apps; tonight we test the coordination system with 2 agents: you (captain's laptop) and `frontend` (Murad's
computer, started with the same kit and its own start prompt — it will find the repo invitation by itself). Your human (the captain) only
answers your questions and does the approval step. Do everything else yourself.
Test repo: **`FARADTechnologies/NASA2026-ops-test`** (private, throw-away). Do NOT touch the real repo `FARADTechnologies/NASA2026`
except to READ its collaborator list.
Read `CLAUDE.md`, `docs/OPS_PROTOCOL.md`, `test/TEST_PLAN.md` first, then confirm in ≤ 8 lines.

## Setup
0. START-FOLDER CHECK (before anything else): the folder Claude Code was started in (`pwd` in your first Bash call) must
   directly contain `CLAUDE.md` and `.claude/settings.json`, and a "SKYLAPSE RECOVERY BRIEF" must have been injected at session start.
   - Kit only in a subfolder (e.g. `./skylapse_kit/CLAUDE.md`) → STOP. Tell the human: "Close this session and start Claude Code in
     <full path of the folder that contains CLAUDE.md>, then paste the same prompt again." Do not work around it (`cd` does not load hooks).
   - Folder right but no brief → run `sh .claude/hooks/run.sh .claude/hooks/session_start.py < /dev/null` to see the error, fix it,
     note it in `ops/memory/KNOWHOW.md`, and ask the human to restart the session (hooks load only at session start).
1. Check `git --version`, `python --version` (or `python3`), `gh --version`, `gh auth status`.
   - gh missing → install it (Windows: `winget install --id GitHub.cli -e`; macOS: `brew install gh`; Linux: package manager).
   - gh not logged in → ask the captain to run `gh auth login` (GitHub.com → HTTPS → browser) in a separate terminal and say "done".
   Then `gh auth setup-git`.
2. `echo orchestrator > .skylapse-role`. Make this folder the repo: `git init -b main`, commit everything,
   `gh repo create FARADTechnologies/NASA2026-ops-test --private --source . --push`
   (if the org refuses, use the captain's personal account: `gh repo create NASA2026-ops-test --private --source . --push`, and tell the captain).
3. Find **Murad's GitHub username**: list `gh api repos/FARADTechnologies/NASA2026/collaborators --jq '.[].login'`, show the list to the
   captain and ask which one is Murad (Murad's agent also prints his username on his screen). Fill `ops/team.json`
   (captain = `gh api user --jq .login`; orchestrator = same; frontend = Murad). Commit + push.
4. Give Murad write access: `gh api -X PUT repos/<owner>/NASA2026-ops-test/collaborators/<murad> -f permission=push`
   (for an org repo this either adds him directly or sends an invitation; his agent handles both).
5. `python ops/bin/skyops.py setup-labels`. Create and push branch `role/frontend` from `main`.
6. Create the test issues exactly as in `test/TEST_PLAN.md` (bodies in temp files under `ops/tmp/`, which is gitignored; use
   `skyops.py task …`). Use real issue numbers for `after #…` and the real time for TEST-4 (Baku time now + 15 min, format
   `at 2026-11-14T03:05+04:00`). Then send Q-1: `skyops.py ask --to frontend --title "Environment check" --text "Which OS and Python version do you run? Answer and close."`
7. Tell the captain in one line: "Setup done — Murad's agent can now accept the invitation (if it is already waiting, it will continue by itself)."
8. Update `ops/memory/PROJECT_STATE.md` (test mode, issue numbers) and your journal. Commit + push.

## Run (autonomous)
9. `python ops/bin/skyops.py auto on`, then loop per CLAUDE.md §7 with `next --wait 540` (Bash timeout 600000 ms).
   REVIEW items: follow "Orchestrator review behaviour" in TEST_PLAN.md (TEST-1 gets one deliberate `changes` round; then
   `accept --merge-pr <url>`; if the PR is still open for later tasks, merge it once at the end instead and accept with a plain `accept`).
   When TEST-3 waits for approval, tell the captain: "Please run `python ops/bin/skyops.py approve <n>` in a second terminal in this folder
   (or add the label `approved` on GitHub)."
10. When all frontend tasks are accepted (or after 60 min): create TEST-END for frontend (`start: now`, body: "Send your test notes to the
    orchestrator with `skyops.py ask`, run `skyops.py auto off`, then submit this task."). After it is submitted and you received the
    worker's notes: accept it, close TEST-5 with a comment "decoy — test finished", write `test/TEST_RESULTS.md` (C1–C14 PASS/FAIL with
    evidence: issue numbers + timestamps from comments; the worker's notes; a "Fixes needed in the kit" list), commit + push,
    `skyops.py auto off`, and print a short summary for the captain to paste to his advisor.
Rules: no deploys, never make the repo public, nothing outside the test repo (the real NASA2026 repo is read-only for you).
