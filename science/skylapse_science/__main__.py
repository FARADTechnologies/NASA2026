"""CLI: python -m skylapse_science <cmd> [--field <id>]   (run from the science/ folder or with science/ on PYTHONPATH)."""
from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog="skylapse_science")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="S1: proper-motion validation for barnard, eps_indi_b, wise0855")
    v.add_argument("--field", action="append", help="limit to one field (repeatable)")
    sp = sub.add_parser("spectra", help="S2: SPHEREx spectra (spectrum block + PNG)")
    sp.add_argument("--field", action="append", help="limit to one field (repeatable)")
    sub.add_parser("spectra-calib", help="S2: check the SPHEREx flux scale against CatWISE W1/W2 for isolated stars")
    lc = sub.add_parser("lightcurves", help="S3: saturation-aware light curves for R Dra and RW Aur")
    lc.add_argument("--field", action="append", help="limit to one field (repeatable)")
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        from . import validate
        validate.run(a.field)
    elif a.cmd == "spectra":
        from . import spectra
        spectra.run(a.field)
    elif a.cmd == "spectra-calib":
        from . import spectra
        spectra.calibration_check()
    elif a.cmd == "lightcurves":
        from . import photometry
        photometry.run(a.field)
    return 0


if __name__ == "__main__":
    sys.exit(main())
