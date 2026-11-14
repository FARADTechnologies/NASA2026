#!/usr/bin/env python3
"""Merge science outputs into the static bundle (DECISIONS D-009 / D-017).

science/out/<field>/objects/<id>.json  → web/public/bundle/<field>/objects/<id>.json  (block-level merge: science's non-null
                                          top-level blocks win; pipeline-only keys are kept)
science/out/<field>/candidates.json    → web/public/bundle/<field>/candidates.json
manifest.objects is extended with every merged id. Run from the repo root, then `python ops/bin/validate_bundle.py`.
Usage: python ops/bin/merge_science.py [--field wise0855] [--dry-run]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCI = ROOT / "science" / "out"
BUNDLE = ROOT / "web" / "public" / "bundle"


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def dump(p: Path, obj, dry: bool):
    if not dry:
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def merge_field(field: str, dry: bool) -> list[str]:
    fdir, sdir = BUNDLE / field, SCI / field
    log = []
    if not (fdir / "manifest.json").is_file() or not sdir.is_dir():
        return log
    man = load(fdir / "manifest.json")
    ids = list(man.get("objects") or [])
    for src in sorted((sdir / "objects").glob("*.json")) if (sdir / "objects").is_dir() else []:
        sci = load(src)
        oid = sci.get("id") or src.stem
        dst = fdir / "objects" / f"{oid}.json"
        base = load(dst) if dst.is_file() else {}
        merged = dict(base)
        for k, v in sci.items():
            if v is not None or k not in merged:
                merged[k] = v
        merged["id"] = oid
        (fdir / "objects").mkdir(exist_ok=True)
        dump(dst, merged, dry)
        if oid not in ids:
            ids.append(oid)
        blocks = [k for k in ("motion", "spectrum", "lightcurve", "copilot") if sci.get(k) is not None]
        log.append(f"{field}/objects/{oid}.json ← science blocks {blocks}")
    cand = sdir / "candidates.json"
    if cand.is_file():
        dump(fdir / "candidates.json", load(cand), dry)
        man["candidates"] = "candidates.json"
        log.append(f"{field}/candidates.json ← science")
    if ids != (man.get("objects") or []) or cand.is_file():
        man["objects"] = ids
        dump(fdir / "manifest.json", man, dry)
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--field")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    fields = [a.field] if a.field else [d.name for d in sorted(BUNDLE.iterdir()) if d.is_dir() and not d.name.startswith("_")]
    lines = []
    for f in fields:
        lines += merge_field(f, a.dry_run)
    print("\n".join(lines) or "nothing to merge")


if __name__ == "__main__":
    main()
