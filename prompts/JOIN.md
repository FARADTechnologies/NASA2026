# JOIN — connect this folder to the team repo (for agents started from the unzipped kit: frontend, pitch, or Kanan's science)
Your agent id is given in the human's prompt. The repo is `FARADTechnologies/NASA2026` (private; everyone is a collaborator).

0. START-FOLDER CHECK (CLAUDE.md §0). Then write your agent id into `.skylapse-role`.
1. Tools: `git --version`, `python --version` (or `python3`), `gh --version`, `gh auth status`.
   - gh missing → install it yourself (Windows: `winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements`;
     macOS: `brew install gh`). If `gh` is still "not found" right after installing, look for gh.exe in `C:\Program Files\GitHub CLI\`,
     `%LOCALAPPDATA%\Microsoft\WinGet\Links\`, `%USERPROFILE%\tools\gh\*\bin\` and prefix PATH in the same command (skyops finds it alone).
   - not logged in → ask your human: "Please open a terminal and run `gh auth login` (GitHub.com → HTTPS → Login with a web browser),
     then tell me done." Then `gh auth setup-git`. Tell your human their login in one line.
2. If this folder is already a git working copy with origin `FARADTechnologies/NASA2026` → go to step 5.
3. Wait for the orchestrator (it may still be setting up — this is normal): every 60 s, up to 45 min, check
   `git ls-remote --heads https://github.com/FARADTechnologies/NASA2026.git role/<agent>` until it prints a line.
   Tell your human once: "Waiting for Murad's orchestrator to finish setup — I will continue by myself."
4. Turn THIS folder into the working copy (do not clone elsewhere — hooks only work in the folder Claude Code started in):
   `git init -b main` · `git remote add origin https://github.com/FARADTechnologies/NASA2026.git` · `git fetch origin` ·
   `git checkout -f -B role/<agent> origin/role/<agent>`. Repo versions overwrite kit files — intended.
5. `python ops/bin/skyops.py brief` must show your agent id. Tell your human: "Joined. Starting my role."
6. Science only (Kanan's computer): Murad's computer has been running science. Before claiming anything run
   `python ops/bin/skyops.py ask --to orchestrator --title "Kanan takes over science" --text "Kanan has arrived; please close Murad's science session after its current step and answer go."`
   and tell Kanan to tell Murad. Wait (`next`) until the orchestrator answers before taking science tasks.
Then continue with the START section of your role prompt.
