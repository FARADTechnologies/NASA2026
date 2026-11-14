#!/usr/bin/env python3
"""SessionStart hook (startup / resume / compact / clear).
Prints a RECOVERY BRIEF to stdout; Claude Code adds it to the agent's context.
Never fails loudly: any error falls back to a minimal reminder and exit code 0.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

source = "startup"
try:
    data = json.load(sys.stdin)
    source = data.get("source", source)
except Exception:
    pass

try:
    sys.path.insert(0, str(ROOT / "ops" / "bin"))
    import skyops  # noqa: E402
    print(skyops.build_brief(source))
    if source == "compact":
        print("\nYou were just COMPACTED. Details may be missing from your memory. Trust the files above over your recollection. "
              "If your journal is stale, rebuild it from git log/diff before continuing.")
except Exception as e:  # minimal fallback
    print("SKYLAPSE: could not build the recovery brief "
          f"({e}). Read CLAUDE.md, .skylapse-role, ops/memory/sessions/<role>.md and ops/memory/PROJECT_STATE.md before acting.")
sys.exit(0)
