"""CLI: python -m skylapse_pipeline <inventory|build|build-all|gif|live|resolve>  (run from pipeline/ or with PYTHONPATH=pipeline)."""
from __future__ import annotations

import argparse
import sys

from .config import BUNDLE, DATA, DETECTORS, TARGET_ORDER


def cmd_inventory(a):
    from . import fetch_spherex, fetch_wise
    from .config import TARGETS, load_targets
    from .epochs import assign, cluster_times
    from .export import mjd_to_date

    tg = load_targets()
    print(f"data root: {DATA}")
    for fid in a.fields or TARGET_ORDER:
        t = tg.get(fid, {})
        w = fetch_wise.read_index(fid)
        s = fetch_spherex.read_index(fid)
        print(f"\n== {fid}  centre(2018.0) {t.get('ra_2018')}, {t.get('dec_2018')}")
        for band in (1, 2):
            rows = [r for r in w if r["band"] == band]
            if rows:
                print(f"  WISE W{band}: {len(rows)} epochs  {mjd_to_date(rows[0]['mjdmin'])} .. {mjd_to_date(rows[-1]['mjdmax'])}")
            else:
                print(f"  WISE W{band}: 0 epochs")
        iv = cluster_times([0.5 * (r["t_start"] + r["t_end"]) for r in s], 30.0, TARGETS.get(fid, {}).get("max_bin_days"))
        print(f"  SPHEREx: {len(s)} images, {len(iv)} time bins")
        print("    bin  dates                    " + " ".join(f"{d:>4}" for d in DETECTORS))
        for i, (lo, hi) in enumerate(iv):
            cnt = [sum(1 for r in s if r["band"] == d and assign(0.5 * (r["t_start"] + r["t_end"]), iv) == i) for d in DETECTORS]
            print(f"    t{i:02d}  {mjd_to_date(lo)}..{mjd_to_date(hi)}  " + " ".join(f"{c:>4}" for c in cnt))


def cmd_build(a):
    from .build import build_target

    dets = a.detectors.split(",") if a.detectors else DETECTORS
    for fid in a.field:
        build_target(fid, out_root=a.out, detectors=dets)


def cmd_build_all(a):
    from .build import build_target

    dets = a.detectors.split(",") if a.detectors else DETECTORS
    for fid in TARGET_ORDER:
        build_target(fid, out_root=a.out, detectors=dets)


def cmd_gif(a):
    from .qa import make_gif

    for fid in a.field:
        print(make_gif(fid, a.sequence, root=a.out))


def cmd_live(a):
    from .live import build_live_field

    def cb(state, progress, msg=""):
        print(f"[{state} {progress:.0%}] {msg}", flush=True)

    print(build_live_field(a.ra, a.dec, a.fov, a.out, cb, field_id=a.id))


def cmd_resolve(a):
    from .resolve import resolve

    print(resolve(" ".join(a.query)))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skylapse_pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("inventory")
    p.add_argument("fields", nargs="*")
    p.set_defaults(fn=cmd_inventory)
    p = sub.add_parser("build")
    p.add_argument("--field", action="append", required=True)
    p.add_argument("--detectors", default=None, help="e.g. D6 or D1,D3,D6 (default all)")
    p.add_argument("--out", default=str(BUNDLE))
    p.set_defaults(fn=cmd_build)
    p = sub.add_parser("build-all")
    p.add_argument("--detectors", default=None)
    p.add_argument("--out", default=str(BUNDLE))
    p.set_defaults(fn=cmd_build_all)
    p = sub.add_parser("gif")
    p.add_argument("--field", action="append", required=True)
    p.add_argument("--sequence", default="thermal46")
    p.add_argument("--out", default=str(BUNDLE))
    p.set_defaults(fn=cmd_gif)
    p = sub.add_parser("live")
    p.add_argument("ra", type=float)
    p.add_argument("dec", type=float)
    p.add_argument("--fov", type=float, default=6.0)
    p.add_argument("--id", default=None)
    p.add_argument("--out", default=str(BUNDLE / "_live"))
    p.set_defaults(fn=cmd_live)
    p = sub.add_parser("resolve")
    p.add_argument("query", nargs="+")
    p.set_defaults(fn=cmd_resolve)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
