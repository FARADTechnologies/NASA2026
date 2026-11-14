#!/usr/bin/env python3
"""Stop hook — two jobs:
1. Journal guard: if the agent changed files but its journal (ops/memory/sessions/<agent>.md) is older than 15 min,
   send it back once to update the journal (5-min grace after a block, so it can never loop on this).
2. Autonomous loop: if `.skylapse-auto` exists (and `.skylapse-pause` does not), never let the agent go idle:
   send it back to take the next task (`skyops.py next --wait 540`).
   Safety brake: more than 6 autonomous continuations within 4 minutes → let it stop (something is failing fast).
Claude Code's own 8-in-a-row cap resets on every tool call, so a healthy loop (which always calls `next`) is unaffected.
Output uses the documented JSON form: {"decision": "block", "reason": "..."}.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
FRESH = 15 * 60
GRACE = 5 * 60
MARKER = ROOT / ".claude" / ".stop_block_marker"
CYCLES = ROOT / ".claude" / ".auto_cycles"


def read_role(root):
    """Agent id from .skylapse-role; tolerates UTF-16 (PowerShell `echo x > file`), BOM and CRLF."""
    try:
        raw = (root / ".skylapse-role").read_bytes()
    except Exception:
        return None
    txt = raw.decode("utf-16", "ignore") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", "ignore")
    return txt.replace("\x00", "").strip().lower() or None


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def allow():
    sys.exit(0)


try:
    json.load(sys.stdin)
except Exception:
    pass

agent = read_role(ROOT)
if not agent:
    allow()
journal = ROOT / "ops" / "memory" / "sessions" / f"{agent}.md"
t = time.time()

# 1. journal guard
journal_fresh = journal.exists() and t - journal.stat().st_mtime < FRESH
in_grace = MARKER.exists() and t - MARKER.stat().st_mtime < GRACE
if not journal_fresh and not in_grace:
    try:
        st = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, timeout=8).stdout
    except Exception:
        st = ""
    changed = [l for l in st.splitlines() if l.strip() and "ops/memory/sessions/" not in l
               and ".claude/." not in l and not l.strip().endswith(".log")]
    if changed:
        try:
            MARKER.write_text(str(t), encoding="utf-8")
        except Exception:
            pass
        block(f"Before finishing: update your journal ops/memory/sessions/{agent}.md (Current task, Status, Done with proof, "
              "exact Next step, Files touched, Gotchas). Add durable lessons to ops/memory/KNOWHOW.md.")

# 2. autonomous loop
if (ROOT / ".skylapse-auto").exists() and not (ROOT / ".skylapse-pause").exists():
    recent = []
    try:
        recent = [float(x) for x in CYCLES.read_text().split() if t - float(x) < 240]
    except Exception:
        pass
    if len(recent) >= 6:
        try:
            CYCLES.write_text("")
        except Exception:
            pass
        sys.stderr.write("Autonomous loop braked: too many fast cycles (is gh/network failing?). "
                         "Human: check the last output, then tell the agent 'continue'.\n")
        allow()
    recent.append(t)
    try:
        CYCLES.write_text(" ".join(str(x) for x in recent))
    except Exception:
        pass
    block("AUTONOMOUS MODE is ON — do not go idle. If you are in the middle of a task, continue it. "
          "If you just finished one, make sure you ran `skyops.py submit`. Otherwise run "
          "`python ops/bin/skyops.py next --wait 540` with a Bash timeout of 600000 ms and act on its output "
          "(START → claim and do the task; RESUME → continue; REVIEW → review; NO_TASK → run it again; PAUSED → stop).")
allow()
