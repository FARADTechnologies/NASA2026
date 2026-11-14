#!/usr/bin/env python3
"""Validate a SkyLapse bundle against docs/DATA_CONTRACT.md (schema 1.0). Stdlib only (numpy optional for data checks).

Usage:
  python ops/bin/validate_bundle.py                       # = web/public/bundle (every bundle root inside, e.g. _mock/)
  python ops/bin/validate_bundle.py web/public/bundle     # a bundle root (has index.json) — also recurses into sub-roots
  python ops/bin/validate_bundle.py web/public/bundle/wise0855   # one field folder (has manifest.json)
Options: --quiet (only PASS/FAIL lines)  --max-mb 80 (total size limit per root)
Prints PASS/FAIL per field (+ WARN lines) and exits 1 if anything FAILs. Every merge that touches the bundle must PASS.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:  # data checks are skipped without numpy
    np = None

SCHEMA = "1.0"
KINDS = {"nasa_test_target", "showcase", "live"}
INSTRUMENTS = {"WISE", "SPHEREx"}
BANDS = {"W1", "W2", "D1", "D2", "D3", "D4", "D5", "D6", "RGB"}
ID_RE = re.compile(r"^(wise_w[12]_e\d{2,3}|spx_d[1-6]_t\d{2,3})$")
WCS_KEYS = ["CTYPE1", "CTYPE2", "CRVAL1", "CRVAL2", "CRPIX1", "CRPIX2", "CD1_1", "CD1_2", "CD2_1", "CD2_2"]
CLASSES = {"candidate", "known", "artifact"}
MJD0 = dt.date(1858, 11, 17)


class Report:
    def __init__(self, name):
        self.name, self.errors, self.warnings = name, [], []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def need(self, obj, keys, where):
        ok = True
        for k in keys:
            if not isinstance(obj, dict) or k not in obj:
                self.err(f"{where}: missing key '{k}'")
                ok = False
        return ok


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def load_json(path: Path, rep: Report, where: str):
    if not path.is_file():
        rep.err(f"{where}: file missing ({path})")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        rep.err(f"{where}: invalid JSON ({e})")
        return None


# ----------------------------------------------------------------------------- field
def check_frame(fr, fdir: Path, w: int, h: int, rep: Report, data_checks: bool):
    fid = fr.get("id", "?")
    where = f"frame {fid}"
    rep.need(fr, ["id", "instrument", "band", "lambda_um", "mjd_start", "mjd_end", "mjd_mid", "date", "n_inputs", "file",
                  "mask_file", "dtype", "units", "display", "quality", "source_files"], where)
    if not ID_RE.match(str(fid)):
        rep.warn(f"{where}: id does not follow convention wise_w{{1|2}}_eNN / spx_d{{1-6}}_tNN")
    if fr.get("instrument") not in INSTRUMENTS:
        rep.err(f"{where}: instrument '{fr.get('instrument')}' not in {sorted(INSTRUMENTS)}")
    if fr.get("band") not in BANDS:
        rep.err(f"{where}: band '{fr.get('band')}' not in {sorted(BANDS)}")
    lam = fr.get("lambda_um")
    if not (isinstance(lam, list) and len(lam) == 2 and all(num(v) for v in lam) and lam[0] <= lam[1]):
        rep.err(f"{where}: lambda_um must be [min, max] numbers")
    m0, m1, mm = fr.get("mjd_start"), fr.get("mjd_end"), fr.get("mjd_mid")
    if not all(num(v) for v in (m0, m1, mm)):
        rep.err(f"{where}: mjd_start/mjd_end/mjd_mid must be numbers")
    else:
        if not (m0 <= mm <= m1):
            rep.err(f"{where}: need mjd_start <= mjd_mid <= mjd_end")
        try:
            d = dt.date.fromisoformat(str(fr.get("date")))
            if abs((d - MJD0).days - mm) > 1.5:
                rep.err(f"{where}: date {d} does not match mjd_mid {mm}")
        except ValueError:
            rep.err(f"{where}: date '{fr.get('date')}' is not YYYY-MM-DD")
    if not (isinstance(fr.get("n_inputs"), int) and fr["n_inputs"] >= 1):
        rep.err(f"{where}: n_inputs must be an integer >= 1")
    if fr.get("dtype") != "float32":
        rep.err(f"{where}: dtype must be 'float32'")
    disp = fr.get("display") or {}
    keys = ["p01", "p50", "p99", "p999"]
    if rep.need(disp, keys, where + " display"):
        vals = [disp[k] for k in keys]
        if not all(num(v) for v in vals):
            rep.err(f"{where}: display percentiles must be finite numbers (got {vals})")
        elif not (vals[0] <= vals[1] <= vals[2] <= vals[3]):
            rep.err(f"{where}: display percentiles not ordered p01<=p50<=p99<=p999 ({vals})")
        elif vals[3] - vals[0] <= 0:
            rep.warn(f"{where}: display range is zero")
    q = fr.get("quality") or {}
    if rep.need(q, ["masked_frac", "saturated_frac", "notes"], where + " quality"):
        for k in ("masked_frac", "saturated_frac"):
            if not (num(q[k]) and 0 <= q[k] <= 1):
                rep.err(f"{where}: quality.{k} must be within 0..1")
        if not isinstance(q["notes"], list):
            rep.err(f"{where}: quality.notes must be a list")
    if not isinstance(fr.get("source_files"), list):
        rep.err(f"{where}: source_files must be a list")
    # files
    fpath = fdir / str(fr.get("file", ""))
    if not fpath.is_file():
        rep.err(f"{where}: file missing {fr.get('file')}")
    else:
        size = fpath.stat().st_size
        if size != w * h * 4:
            rep.err(f"{where}: {fr.get('file')} is {size} bytes, expected w*h*4 = {w * h * 4}")
        elif data_checks and np is not None:
            a = np.fromfile(fpath, dtype="<f4")
            fin = np.isfinite(a)
            if not fin.any():
                rep.err(f"{where}: frame is all NaN/inf")
            elif np.all(a[fin] == 0):
                rep.err(f"{where}: frame is all zero")
            nan_frac = 1 - fin.mean()
            if nan_frac > 0.5:
                rep.warn(f"{where}: {nan_frac:.0%} of pixels are NaN")
    mf = fr.get("mask_file")
    if mf is not None:
        mpath = fdir / str(mf)
        if not mpath.is_file():
            rep.err(f"{where}: mask_file missing {mf}")
        elif mpath.stat().st_size != w * h:
            rep.err(f"{where}: {mf} is {mpath.stat().st_size} bytes, expected w*h = {w * h}")


def check_catalog(path: Path, rep: Report, name: str):
    cat = load_json(path, rep, f"catalog {name}")
    if cat is None:
        return
    if not rep.need(cat, ["catalog", "ref_epoch", "columns", "rows"], f"catalog {name}"):
        return
    cols = cat["columns"]
    for c in ("id", "ra", "dec", "pmra", "pmdec", "mag"):
        if c not in cols:
            rep.err(f"catalog {name}: column '{c}' missing")
    if not num(cat["ref_epoch"]):
        rep.err(f"catalog {name}: ref_epoch must be a number (Julian year)")
    bad = [i for i, r in enumerate(cat["rows"]) if not isinstance(r, list) or len(r) != len(cols)]
    if bad:
        rep.err(f"catalog {name}: {len(bad)} rows do not match the column count (first: row {bad[0]})")
    if not cat["rows"]:
        rep.warn(f"catalog {name}: no rows")
    else:
        ira, idec = cols.index("ra") if "ra" in cols else None, cols.index("dec") if "dec" in cols else None
        if ira is not None and idec is not None:
            nonnum = sum(1 for r in cat["rows"] if isinstance(r, list) and len(r) == len(cols)
                         and not (num(r[ira]) and num(r[idec])))
            if nonnum:
                rep.err(f"catalog {name}: {nonnum} rows with non-numeric ra/dec")


def check_object(path: Path, rep: Report, oid: str):
    o = load_json(path, rep, f"object {oid}")
    if o is None:
        return
    where = f"object {oid}"
    rep.need(o, ["id", "name", "kind", "ra", "dec", "epoch", "motion", "spectrum", "lightcurve", "copilot", "flags"], where)
    if o.get("id") != oid:
        rep.err(f"{where}: id '{o.get('id')}' does not match file name")
    m = o.get("motion")
    if m is not None:
        rep.need(m, ["measured", "reference", "agreement_pct", "track"], where + " motion")
        if isinstance(m.get("measured"), dict):
            rep.need(m["measured"], ["pmra", "pmdec", "pm_total", "err", "unit", "n_epochs"], where + " motion.measured")
        tr = m.get("track") or []
        if not isinstance(tr, list):
            rep.err(f"{where}: motion.track must be a list")
        else:
            for i, p in enumerate(tr[:5000]):
                if not (isinstance(p, dict) and all(num(p.get(k)) for k in ("mjd", "ra", "dec"))):
                    rep.err(f"{where}: motion.track[{i}] needs numeric mjd/ra/dec")
                    break
            mj = [p.get("mjd") for p in tr if isinstance(p, dict)]
            if all(num(x) for x in mj) and mj != sorted(mj):
                rep.warn(f"{where}: motion.track is not sorted by mjd")
    s = o.get("spectrum")
    if s is not None:
        rep.need(s, ["unit_flux", "points"], where + " spectrum")
        for i, p in enumerate(s.get("points") or []):
            if not (isinstance(p, dict) and num(p.get("lambda_um"))):
                rep.err(f"{where}: spectrum.points[{i}] needs numeric lambda_um")
                break
            if p.get("flux") is not None and not num(p.get("flux")):
                rep.err(f"{where}: spectrum.points[{i}] flux must be a number or null (never NaN)")
                break
        t = s.get("template")
        if isinstance(t, dict) and len(t.get("lambda_um") or []) != len(t.get("flux") or []):
            rep.err(f"{where}: spectrum.template lambda_um and flux lengths differ")
    lc = o.get("lightcurve")
    if lc is not None:
        rep.need(lc, ["points"], where + " lightcurve")
        for i, p in enumerate(lc.get("points") or []):
            if not (isinstance(p, dict) and num(p.get("mjd")) and "saturated" in p):
                rep.err(f"{where}: lightcurve.points[{i}] needs numeric mjd and a 'saturated' flag")
                break
            if p.get("mag") is not None and not num(p.get("mag")):
                rep.err(f"{where}: lightcurve.points[{i}] mag must be a number or null (never NaN)")
                break
    c = o.get("copilot")
    if c is not None:
        rep.need(c, ["en", "az", "model", "facts_hash"], where + " copilot")
        txt = f"{c.get('en', '')} {c.get('az', '')}".lower()
        if "planet x" in txt or "we discovered" in txt:
            rep.err(f"{where}: copilot text claims a discovery / Planet X (forbidden, CLAUDE.md §5)")


def check_field(fdir: Path, rep: Report, data_checks=True, index_entry=None):
    man = load_json(fdir / "manifest.json", rep, "manifest.json")
    if man is None:
        return
    rep.need(man, ["schema_version", "field_id", "title", "center", "grid", "frames", "sequences", "rgb_composites",
                   "objects", "catalogs", "candidates", "credits", "build"], "manifest")
    if man.get("schema_version") != SCHEMA:
        rep.err(f"manifest: schema_version '{man.get('schema_version')}' != '{SCHEMA}'")
    if man.get("field_id") != fdir.name:
        rep.err(f"manifest: field_id '{man.get('field_id')}' does not match folder name '{fdir.name}'")
    c = man.get("center") or {}
    if rep.need(c, ["ra", "dec", "epoch"], "manifest center") and not all(num(c[k]) for k in ("ra", "dec", "epoch")):
        rep.err("manifest center: ra/dec/epoch must be numbers")
    g = man.get("grid") or {}
    w = h = 0
    if rep.need(g, ["width", "height", "pixel_scale_arcsec", "wcs"], "manifest grid"):
        w, h = g["width"], g["height"]
        if not (isinstance(w, int) and isinstance(h, int) and w > 0 and h > 0):
            rep.err("grid: width/height must be positive integers")
            w = h = 0
        rep.need(g["wcs"], WCS_KEYS, "grid wcs")
    frames = man.get("frames") or []
    if not frames:
        rep.err("manifest: no frames")
    ids = [f.get("id") for f in frames if isinstance(f, dict)]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        rep.err(f"manifest: duplicate frame ids {sorted(dup)[:5]}")
    by_id = {f.get("id"): f for f in frames if isinstance(f, dict)}
    for fr in frames:
        check_frame(fr, fdir, w, h, rep, data_checks)
    seqs = man.get("sequences") or []
    if not seqs:
        rep.err("manifest: no sequences")
    defaults = [s for s in seqs if s.get("default")]
    if len(defaults) != 1:
        rep.err(f"manifest: exactly one default sequence required (found {len(defaults)})")
    for s in seqs:
        rep.need(s, ["id", "label", "default", "frames"], f"sequence {s.get('id')}")
        missing = [f for f in s.get("frames", []) if f not in by_id]
        if missing:
            rep.err(f"sequence {s.get('id')}: unknown frame ids {missing[:5]}")
            continue
        mj = [by_id[f]["mjd_mid"] for f in s.get("frames", []) if num(by_id[f].get("mjd_mid"))]
        if mj != sorted(mj):
            rep.err(f"sequence {s.get('id')}: frames not sorted by mjd_mid")
        if not s.get("frames"):
            rep.err(f"sequence {s.get('id')}: empty")
    for r in man.get("rgb_composites") or []:
        rep.need(r, ["id", "label", "r", "g", "b"], f"rgb {r.get('id')}")
        for ch in ("r", "g", "b"):
            if r.get(ch) not in by_id:
                rep.err(f"rgb {r.get('id')}: channel {ch} -> unknown frame '{r.get(ch)}'")
    cats = man.get("catalogs") or {}
    for name, rel in cats.items():
        if rel is not None:
            check_catalog(fdir / rel, rep, name)
    if "gaia" not in cats:
        rep.warn("manifest: no gaia catalog (P0-5 overlay needs it)")
    for oid in man.get("objects") or []:
        check_object(fdir / "objects" / f"{oid}.json", rep, oid)
    cand = man.get("candidates")
    if cand is not None:
        cj = load_json(fdir / cand, rep, "candidates")
        if cj is not None and rep.need(cj, ["method", "stats", "items"], "candidates"):
            for it in cj["items"]:
                rep.need(it, ["id", "ra", "dec", "pm_total", "class", "match", "score", "object_file"], f"candidate {it.get('id')}")
                if it.get("class") not in CLASSES:
                    rep.err(f"candidate {it.get('id')}: class '{it.get('class')}' not in {sorted(CLASSES)}")
                of = it.get("object_file")
                if of is not None and not (fdir / of).is_file():
                    rep.err(f"candidate {it.get('id')}: object_file {of} missing")
    if index_entry is not None:
        th = index_entry.get("thumb")
        if th and not (fdir.parent / th).is_file():
            rep.err(f"index thumb '{th}' missing")
    rep.info = f"{len(frames)} frames, {len(seqs)} sequences, grid {w}x{h}"


# ----------------------------------------------------------------------------- roots
def dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def validate_root(root: Path, args, results):
    idx_rep = Report(f"{root.as_posix()}/index.json")
    idx = load_json(root / "index.json", idx_rep, "index.json")
    listed = {}
    if idx is not None and idx_rep.need(idx, ["schema_version", "generated_utc", "fields"], "index"):
        if idx.get("schema_version") != SCHEMA:
            idx_rep.err(f"index: schema_version '{idx.get('schema_version')}' != '{SCHEMA}'")
        for f in idx["fields"]:
            idx_rep.need(f, ["field_id", "title", "kind", "ra", "dec", "thumb", "tags"], f"index field {f.get('field_id')}")
            if f.get("kind") not in KINDS:
                idx_rep.err(f"index field {f.get('field_id')}: kind '{f.get('kind')}' not in {sorted(KINDS)}")
            if not (root / str(f.get("field_id")) / "manifest.json").is_file():
                idx_rep.err(f"index field {f.get('field_id')}: folder/manifest missing")
            listed[f.get("field_id")] = f
    size_mb = dir_size(root) / 1e6
    if size_mb > args.max_mb and root.name != "_mock":
        idx_rep.err(f"bundle size {size_mb:.1f} MB > {args.max_mb} MB")
    idx_rep.info = f"{len(listed)} fields listed, {size_mb:.1f} MB total"
    results.append(idx_rep)
    for sub in sorted(p for p in root.iterdir() if p.is_dir()):
        if (sub / "manifest.json").is_file():
            rep = Report(sub.as_posix())
            check_field(sub, rep, not args.no_data, listed.get(sub.name))
            if sub.name not in listed:
                rep.warn("field folder is not listed in index.json")
            results.append(rep)
        elif (sub / "index.json").is_file():
            validate_root(sub, args, results)


def main():
    ap = argparse.ArgumentParser(description="Validate a SkyLapse bundle against DATA_CONTRACT 1.0")
    ap.add_argument("path", nargs="?", default=str(Path(__file__).resolve().parents[2] / "web" / "public" / "bundle"))
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--no-data", action="store_true", help="skip reading frame pixels")
    ap.add_argument("--max-mb", type=float, default=80.0)
    args = ap.parse_args()
    p = Path(args.path)
    results = []
    if (p / "manifest.json").is_file():
        rep = Report(p.as_posix())
        check_field(p, rep, not args.no_data)
        results.append(rep)
    elif (p / "index.json").is_file() or p.is_dir():
        if not (p / "index.json").is_file():
            subs = [s for s in p.iterdir() if s.is_dir() and (s / "index.json").is_file()]
            if not subs:
                print(f"FAIL {p}: no index.json or manifest.json found")
                sys.exit(1)
            for s in subs:
                validate_root(s, args, results)
            print(f"WARN {p}: no top-level index.json (no real fields yet)")
        else:
            validate_root(p, args, results)
    else:
        print(f"FAIL {p}: path not found")
        sys.exit(1)
    failed = 0
    for r in results:
        status = "FAIL" if r.errors else "PASS"
        failed += bool(r.errors)
        print(f"{status} {r.name}  ({getattr(r, 'info', '')})")
        if not args.quiet:
            for e in r.errors[:40]:
                print(f"   ERROR {e}")
            if len(r.errors) > 40:
                print(f"   … +{len(r.errors) - 40} more errors")
            for w in r.warnings[:15]:
                print(f"   WARN  {w}")
            if len(r.warnings) > 15:
                print(f"   … +{len(r.warnings) - 15} more warnings")
    print(f"\n{'FAIL' if failed else 'PASS'}: {len(results) - failed}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
