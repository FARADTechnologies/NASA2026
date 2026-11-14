# TEST — Murad's computer, agent `frontend` (Claude Code is running INSIDE the unzipped kit folder; this folder becomes the repo)

You are agent **frontend** in a DRY-RUN of team FARAD's autonomous multi-agent system (tomorrow: 5 agents on 5 laptops build "SkyLapse"
for NASA Space Apps). The orchestrator runs on the captain's laptop and gives you tasks as GitHub issues in the private test repo
`FARADTechnologies/NASA2026-ops-test` (if the org refused, it is `<captain>/NASA2026-ops-test`). Never touch the real repo `NASA2026`. Your human (Murad) only watches and does the 2 checks you ask for. Do everything else yourself.

## Setup
0. START-FOLDER CHECK (before anything else): the folder Claude Code was started in (`pwd` in your first Bash call) must
   directly contain `CLAUDE.md` and `.claude/settings.json`, and a "SKYLAPSE RECOVERY BRIEF" must have been injected at session start.
   - Kit only in a subfolder (e.g. `./skylapse_kit/CLAUDE.md`) → STOP. Tell the human: "Close this session and start Claude Code in
     <full path of the folder that contains CLAUDE.md>, then paste the same prompt again." Do not work around it (`cd` does not load hooks).
   - Folder right but no brief → run `sh .claude/hooks/run.sh .claude/hooks/session_start.py < /dev/null` to see the error, fix it,
     note it in `ops/memory/KNOWHOW.md`, and ask the human to restart the session (hooks load only at session start).
1. Check `git --version`, `python --version` (or `python3`), `gh --version`, `gh auth status`.
   - gh missing → install it (Windows: `winget install --id GitHub.cli -e`; macOS: `brew install gh`; Linux: package manager), then reopen check.
   - gh not logged in → ask Murad to run `gh auth login` (GitHub.com → HTTPS → browser) in a separate terminal and tell you "done".
   Then run `gh auth setup-git` so git uses gh's credentials.
2. Print your GitHub username (`gh api user --jq .login`) and tell Murad in one line: "Give the captain this username: <login>".
3. Get access (the captain's agent may still be setting up): every 30 s, up to 25 min:
   a) `gh repo view FARADTechnologies/NASA2026-ops-test --json nameWithOwner` — if it works you already have access; use that name.
   b) else check invitations: `gh api user/repository_invitations --jq '.[] | select(.repository.name=="NASA2026-ops-test") | [.id, .repository.full_name] | @tsv'`
      and accept with `gh api -X PATCH user/repository_invitations/<id>`; use the full_name it shows.
4. Turn THIS folder into the working copy of that repo (do not clone elsewhere — hooks only work in the folder Claude Code started in):
   `git init -b main` (if not already a repo) · `git remote add origin https://github.com/<full_name>.git` · `git fetch origin` ·
   wait (poll every 30 s) until `origin/role/frontend` exists · `git checkout -f -B role/frontend origin/role/frontend`.
   Local copies of kit files are overwritten by the repo versions — that is intended.
5. `echo frontend > .skylapse-role`. Run `python ops/bin/skyops.py brief` and check it shows "You are agent: frontend".
6. Read `CLAUDE.md`, `docs/OPS_PROTOCOL.md`, `test/TEST_PLAN.md`. Confirm to Murad in ≤ 6 lines what you will do.

## Run (autonomous)
7. `python ops/bin/skyops.py auto on`, then loop per CLAUDE.md §7: `python ops/bin/skyops.py next --wait 540` (Bash timeout 600000 ms) →
   START: `claim` → do the task on branch `role/frontend` → commit + push → open/update ONE PR to `main`
   (`gh pr create --base main --head role/frontend --fill`; later just push) → `submit <n> --file <report> --pr <url>` → journal → `next`.
   CHANGES REQUESTED → fix, push, `submit` again. Questions (`type:question`) → answer with `submit <n> --text …` (closes them).
   Before each new task: `git fetch origin && git merge origin/main` so you build on the accepted work.
8. Only `agent:frontend` issues are yours. Never touch other agents' issues. Never start a `human` task without the `approved` label.
9. Human checks (ask Murad at the right moment, one line each):
   - After your 2nd task is submitted: "Please type /compact now." After compaction, check the RECOVERY BRIEF came back and continue.
   - After your 3rd task: "In a second terminal in this folder run `python ops/bin/skyops.py pause`." When `next` says PAUSED, stop and
     wait; Murad then runs `python ops/bin/skyops.py resume` and types "continue".
10. Keep notes of: every permission prompt Murad had to click (exact command), anything that failed, timings. When you receive the
    task "TEST-END", first send your notes with `python ops/bin/skyops.py ask --to orchestrator --title "Worker test notes" --text "<notes>"`,
    then run `python ops/bin/skyops.py auto off`, submit TEST-END, and stop.
Rules: no deploys, nothing public, nothing outside this folder and the test repo.
