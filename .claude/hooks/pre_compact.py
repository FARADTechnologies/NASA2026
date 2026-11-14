#!/usr/bin/env python3
"""PreCompact hook: snapshot git state into ops/memory/sessions/<role>.log before the context is compacted.
Side effect only; always exits 0 so compaction is never blocked."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
try:
    trigger = json.load(sys.stdin).get("trigger", "?")
except Exception:
    trigger = "?"
def read_role(root):
    """Agent id from .skylapse-role; tolerates UTF-16 (PowerShell `echo x > file`), BOM and CRLF."""
    try:
        raw = (root / ".skylapse-role").read_bytes()
    except Exception:
        return None
    txt = raw.decode("utf-16", "ignore") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig", "ignore")
    return txt.replace("\x00", "").strip().lower() or None


role = read_role(ROOT) or "unknown"


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=8).stdout.strip()
    except Exception:
        return "(git unavailable)"


log = ROOT / "ops" / "memory" / "sessions" / f"{role}.log"
try:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n=== PRE-COMPACT {time.strftime('%Y-%m-%d %H:%M:%S')} trigger={trigger} ===\n")
        f.write("branch: " + git("rev-parse", "--abbrev-ref", "HEAD") + "\n")
        f.write("status:\n" + git("status", "--short") + "\n")
        f.write("last commits:\n" + git("log", "--oneline", "-8") + "\n")
except Exception:
    pass
sys.exit(0)
