"""CLI: python -m skylapse_science <cmd> [--field <id>]   (run from the science/ folder or with science/ on PYTHONPATH)."""
from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="skylapse_science")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="S1: proper-motion validation for barnard, eps_indi_b, wise0855")
    v.add_argument("--field", action="append", help="limit to one field (repeatable)")
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        from . import validate
        validate.run(a.field)
    return 0


if __name__ == "__main__":
    sys.exit(main())
