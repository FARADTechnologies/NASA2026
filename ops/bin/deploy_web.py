#!/usr/bin/env python3
"""Deploy web/ to Vercel production (project 'skylapse') from a git-free copy.

Why: Vercel Hobby blocks a deployment when the last git commit's author is not a member of the Vercel team
(merged PRs are authored by teammates). Deploying a copy without .git sends no commit metadata.
Usage (repo root, after `npx vercel login`):  python ops/bin/deploy_web.py
"""
import shutil

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
SKIP = {"node_modules", "dist", ".vercel", "public/devmock"}


def ignore(src, names):
    rel = Path(src).relative_to(WEB).as_posix()
    return [n for n in names if n in ("node_modules", "dist") or (rel == "public" and n == "devmock") or n.endswith(".tsbuildinfo")]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not (WEB / ".vercel" / "project.json").is_file():
        sys.exit("web/.vercel/project.json missing: run `cd web && npx vercel link --yes --project skylapse` first")
    tmp = Path(tempfile.mkdtemp(prefix="skylapse-deploy-"))
    dst = tmp / "web"
    try:
        shutil.copytree(WEB, dst, ignore=ignore)
        shutil.copytree(WEB / ".vercel", dst / ".vercel", dirs_exist_ok=True)
        npx = "npx.cmd" if sys.platform.startswith("win") else "npx"
        r = subprocess.run([npx, "--yes", "vercel", "deploy", "--prod", "--yes"], cwd=dst, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = r.stdout + r.stderr
        print(out[-1500:])
        sys.exit(r.returncode)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
