"""Paths and target metadata shared by all science modules."""
from __future__ import annotations

import json
import os
from pathlib import Path

SCIENCE_DIR = Path(__file__).resolve().parent.parent          # <repo>/science
REPO_DIR = SCIENCE_DIR.parent
OUT_DIR = SCIENCE_DIR / "out"
DATA_DIR = Path(os.environ.get("SKYLAPSE_DATA", r"C:\Users\Murad\Downloads\skylapse-data\data"))
RAW = DATA_DIR / "raw"
SLIM = DATA_DIR / "slim"

MOVERS = ["barnard", "eps_indi_b", "wise0855"]
ALL_TARGETS = ["wise0855", "barnard", "eps_indi_b", "rw_aur", "r_dra"]

DISPLAY_NAMES = {
    "wise0855": "WISE 0855\u22120714",
    "barnard": "Barnard's Star",
    "eps_indi_b": "\u03b5 Indi B",
    "rw_aur": "RW Aurigae",
    "r_dra": "R Draconis",
}
KINDS = {
    "wise0855": "brown_dwarf",
    "barnard": "star",
    "eps_indi_b": "brown_dwarf",
    "rw_aur": "young_star",
    "r_dra": "variable_star",
}


def load_targets() -> dict[str, dict]:
    with open(RAW / "targets.json", encoding="utf-8") as f:
        return {t["id"]: t for t in json.load(f)}


def jyear(mjd: float) -> float:
    return 2000.0 + (mjd - 51544.5) / 365.25
