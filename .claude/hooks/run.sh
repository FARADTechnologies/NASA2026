#!/bin/sh
# Portable Python launcher for Claude Code hooks (Windows Git Bash, macOS, Linux).
# Tries python3, python, py and uses the first one that really runs (skips the Windows Store stub).
for p in python3 python py; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >/dev/null 2>&1; then
    exec "$p" "$@"
  fi
done
echo "SKYLAPSE hook: no working Python 3 found. Install Python 3 and restart Claude Code." >&2
exit 0
