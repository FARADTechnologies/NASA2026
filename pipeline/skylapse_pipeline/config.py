"""Paths, constants and the 5 NASA test targets.

Data root: env var SKYLAPSE_DATA (folder that contains raw/ and slim/), else <repo>/data, else the prefetch folder
C:/Users/Murad/Downloads/skylapse-data/data if it exists. Derived products and logs always go to <repo>/data/.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

PIPELINE_VERSION = "0.2.0"
SCHEMA = "1.0"

REPO = Path(__file__).resolve().parents[2]
LOCAL_DATA = REPO / "data"
_PREFETCH = Path(r"C:/Users/Murad/Downloads/skylapse-data/data")


def _data_root() -> Path:
    env = os.environ.get("SKYLAPSE_DATA")
    if env:
        return Path(env)
    if (LOCAL_DATA / "raw" / "targets.json").is_file():
        return LOCAL_DATA
    if (_PREFETCH / "raw" / "targets.json").is_file():
        return _PREFETCH
    return LOCAL_DATA


DATA = _data_root()
RAW = DATA / "raw"
SLIM = DATA / "slim"
WISE_DIR = RAW / "wise"
SPHEREX_SLIM = SLIM / "spherex"
CATALOG_DIR = RAW / "catalogs"
TARGETS_JSON = RAW / "targets.json"

DERIVED = LOCAL_DATA / "derived"
QA_DIR = LOCAL_DATA / "qa"
LOG_DIR = LOCAL_DATA / "logs"
CACHE = LOCAL_DATA / "cache"  # live fetches land here (same layout as raw/ + slim/)
BUNDLE = REPO / "web" / "public" / "bundle"

# Grid (docs/SCIENCE_NOTES.md §5)
GRID_N = 192
PIX_ARCSEC = 2.75
CENTER_EPOCH = 2018.0

# SPHEREx epoch clustering
GAP_DAYS = 30.0

WISE_LAMBDA = {"W1": (3.4, 3.4), "W2": (4.6, 4.6)}
SPHEREX_RANGE = {"D1": (0.75, 1.11), "D2": (1.10, 1.64), "D3": (1.63, 2.42),
                 "D4": (2.40, 3.82), "D5": (3.81, 4.42), "D6": (4.41, 5.00)}
DETECTORS = ["D1", "D2", "D3", "D4", "D5", "D6"]

# Per-target settings. title/kind/tags for index.json; max_bin_days splits long SPHEREx clusters (R Dra NEP).
TARGETS = {
    "wise0855": dict(title="WISE 0855−0714", obj_kind="brown_dwarf", tags=["motion", "brown dwarf", "coldest known"]),
    "barnard": dict(title="Barnard's Star", obj_kind="star", tags=["motion", "red dwarf", "fastest star"]),
    "eps_indi_b": dict(title="Epsilon Indi B", obj_kind="brown_dwarf", tags=["motion", "brown dwarf", "binary"]),
    "r_dra": dict(title="R Draconis", obj_kind="variable_star", tags=["variability", "Mira variable"], max_bin_days=60.0),
    "rw_aur": dict(title="RW Aurigae", obj_kind="variable_star", tags=["variability", "young star"]),
}
TARGET_ORDER = list(TARGETS)

CREDITS = [
    "NASA/IPAC IRSA SPHEREx DR1+QR3",
    "unWISE time-resolved coadds via byw.tools (Backyard Worlds/AMNH)",
    "NASA WISE/NEOWISE",
    "ESA Gaia DR3",
    "CatWISE2020 (IRSA)",
    "SIMBAD (CDS)",
]


def load_targets() -> dict:
    """targets.json from the prefetch (resolved positions, PM, 2018.0 centres) keyed by id."""
    rows = json.loads(TARGETS_JSON.read_text(encoding="utf-8"))
    return {r["id"]: r for r in rows}


def get_logger(name: str) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger(f"skylapse.{name}")
    if log.handlers:
        return log
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%H:%M:%S")
    fh = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    log.addHandler(fh)
    log.addHandler(sh)
    log.propagate = False
    return log
