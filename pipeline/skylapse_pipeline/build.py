"""Build one field of the bundle: WISE epochs + SPHEREx co-adds on one grid -> web/public/bundle/<field>/.

FieldBuilder is incremental (used by live.py): add_wise() -> write() -> add_spherex(["D6"]) -> write() -> ...
"""
from __future__ import annotations

import csv
import math
import shutil
import time
from pathlib import Path

import numpy as np

from . import catalogs as cat
from . import fetch_spherex, fetch_wise
from .coadd import coadd_spherex, reproject_wise
from .config import (BUNDLE, CREDITS, DERIVED, DETECTORS, GAP_DAYS, PIPELINE_VERSION, SCHEMA, SPHEREX_RANGE, TARGETS, WISE_LAMBDA,
                     get_logger, load_targets)
from .epochs import assign, cluster_times
from .export import mjd_to_date, update_index, utcnow, write_frame, write_json, write_preview, write_rgb_preview
from .grid import grid_wcs, make_grid
from .resolve import julian_year, propagate
from .scale import display_percentiles, scale_factor, select_ref_stars, subtract_background, aperture_fluxes

log = get_logger("build")
WISE_REF_FOR = {"D1": "W1", "D2": "W1", "D3": "W1", "D4": "W1", "D5": "W2", "D6": "W2"}
PREVIEW_BANDS = {"W2", "D6", "D3", "D1"}


class FieldBuilder:
    def __init__(self, field_id: str, ra: float, dec: float, title: str, kind: str = "nasa_test_target", tags=None,
                 out_root: Path = BUNDLE, n_px: int = 192, max_bin_days: float | None = None, target: dict | None = None):
        self.field_id, self.title, self.kind, self.tags = field_id, title, kind, list(tags or [])
        self.ra, self.dec = ra, dec
        self.out_root = Path(out_root)
        self.fdir = self.out_root / field_id
        self.grid = make_grid(ra, dec, n_px)
        self.wcs = grid_wcs(self.grid)
        self.shape = (n_px, n_px)
        self.max_bin_days = max_bin_days
        self.target = target  # targets.json row (NASA targets) or None
        self.frames: dict[str, dict] = {}
        self.arrays: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self.refs: dict[str, dict] = {}  # band -> {"fid", "flux"}
        self.ref_xy = (np.array([]), np.array([]))
        self.gaia_rows: list[dict] = []
        self.catwise_rows: list[dict] = []
        self.spx_rows: list[dict] = []
        self.intervals: list[tuple[float, float]] = []
        self.per_image: list[dict] = []
        self.releases: set[str] = set()
        self.objects: list[str] = []
        self.skipped: list[dict] = []
        self.fdir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ inputs
    def load_catalogs(self, online: bool = False, parts=("gaia", "catwise"), timeout: float = 60):
        r = self.grid["width"] * self.grid["pixel_scale_arcsec"] / 3600 * 0.75
        kw = dict(ra=self.ra, dec=self.dec, radius_deg=r, timeout=timeout) if online else {}
        if "gaia" in parts:
            self.gaia_rows = cat.load_gaia(self.field_id, **kw)
        if "catwise" in parts:
            self.catwise_rows = cat.load_catwise(self.field_id, **kw)
        if "gaia" in parts:
            self.ref_xy = select_ref_stars(self.gaia_rows, self.wcs, self.shape)
        log.info("%s: Gaia %d rows, CatWISE %d rows, %d reference stars", self.field_id, len(self.gaia_rows), len(self.catwise_rows),
                 len(self.ref_xy[0]))
        self._write_catalogs(parts)

    def _in_field(self, ra, dec, margin_px=20):
        from .grid import world_to_grid

        x, y = world_to_grid(self.wcs, ra, dec)
        n = self.grid["width"]
        return (x > -margin_px) & (x < n + margin_px) & (y > -margin_px) & (y < n + margin_px)

    def _write_catalogs(self, parts=("gaia", "catwise")):
        for name, rows, fn, rak, deck in (("gaia", self.gaia_rows, cat.gaia_json, "ra", "dec"),
                                         ("catwise", self.catwise_rows, cat.catwise_json, "ra", "dec")):
            if name not in parts and (self.fdir / "catalogs" / f"{name}.json").is_file():
                continue
            js = fn(rows)
            if js["rows"]:
                ra = np.array([r[1] for r in js["rows"]])
                dec = np.array([r[2] for r in js["rows"]])
                keep = self._in_field(ra, dec)
                js["rows"] = [r for r, k in zip(js["rows"], keep) if k]
            write_json(self.fdir / "catalogs" / f"{name}.json", js)

    # ------------------------------------------------------------------ frames
    def _store(self, fid: str, meta: dict, data: np.ndarray, mask: np.ndarray, notes: list[str], derived_fits: bool = True):
        data = data.astype(np.float32)
        valid = np.isfinite(data) & (mask & 1 == 0)
        meta["display"] = display_percentiles(data, mask)
        if 1 - valid.mean() > 0.05:
            notes = notes + [f"{(1 - valid.mean()):.0%} of the field masked or not covered"
                             + (" (cutouts clipped at a detector edge)" if meta["instrument"] == "SPHEREx" else "")]
        meta["quality"] = {"masked_frac": round(float(1 - valid.mean()), 4),
                           "saturated_frac": round(float(((mask & 2) != 0).mean()), 5), "notes": notes}
        rel, mrel = write_frame(self.fdir, fid, data, mask)
        meta["file"], meta["mask_file"] = rel, mrel
        meta["dtype"], meta["units"] = "float32", "relative"
        if meta["band"] in PREVIEW_BANDS:
            write_preview(self.fdir, fid, data, meta["display"])
        self.frames[fid] = meta
        self.arrays[fid] = (data, mask)
        if derived_fits:
            self._write_derived_fits(fid, data, mask, meta)

    def _write_derived_fits(self, fid, data, mask, meta):
        from astropy.io import fits

        d = DERIVED / self.field_id / "frames"
        d.mkdir(parents=True, exist_ok=True)
        hdr = self.wcs.to_header()
        for k in ("instrument", "band", "mjd_start", "mjd_end", "mjd_mid", "n_inputs"):
            hdr[k[:8].upper()] = meta[k]
        hdr["LAM_MIN"], hdr["LAM_MAX"] = meta["lambda_um"]
        hdr["SCALE"] = meta.get("_scale", 1.0)
        hdr["BKG"] = meta.get("_bkg", 0.0)
        fits.HDUList([fits.PrimaryHDU(data, hdr), fits.ImageHDU(mask, name="MASK")]).writeto(d / f"{fid}.fits", overwrite=True)

    def add_wise(self, rows: list[dict] | None = None, progress=None):
        rows = rows if rows is not None else fetch_wise.read_index(self.field_id)
        if not rows:
            log.warning("%s: no WISE epochs", self.field_id)
            return
        raw = {}
        for r in rows:
            band = f"W{r['band']}"
            fid = f"wise_w{r['band']}_e{r['epoch']:02d}"
            try:
                fr = reproject_wise(r["path"], r["band"], self.wcs, self.shape)
            except Exception as e:  # noqa: BLE001
                log.warning("%s %s: %s", self.field_id, fid, e)
                continue
            cover = float(np.isfinite(fr["data"]).mean())
            if cover < 0.5:
                log.info("%s %s: skipped, only %.0f%% of the grid covered", self.field_id, fid, cover * 100)
                self.skipped.append({"id": fid, "reason": f"unWISE epoch covers {cover:.0%} of the field"})
                continue
            data, bkg, _ = subtract_background(fr["data"])
            raw[fid] = (band, r, fr, data, bkg)
        # reference frame per band: the epoch closest to 2018.0
        for band in ("W1", "W2"):
            cands = [(abs(julian_year(v[2]["mjd_mid"]) - 2018.0), fid) for fid, v in raw.items() if v[0] == band]
            if cands:
                fid = min(cands)[1]
                self.refs[band] = {"fid": fid, "flux": aperture_fluxes(raw[fid][3], raw[fid][2]["mask"], *self.ref_xy)}
        for fid, (band, r, fr, data, bkg) in sorted(raw.items(), key=lambda kv: kv[1][2]["mjd_mid"]):
            notes = []
            ref = self.refs.get(band)
            k, n = scale_factor(data, fr["mask"], ref["flux"], *self.ref_xy) if ref else (None, 0)
            if fid == (ref or {}).get("fid"):
                k, notes = 1.0, [f"reference frame for {band} scaling"]
            elif k is None:
                k = 1.0
                notes.append("not enough reference stars; unscaled")
            else:
                notes.append(f"scaled on {n} Gaia stars")
            if (fr["mask"] & 2).any():
                notes.append("saturated pixels present")
            meta = {"id": fid, "instrument": "WISE", "band": band, "lambda_um": list(WISE_LAMBDA[band]),
                    "mjd_start": round(fr["mjd_start"], 5), "mjd_end": round(fr["mjd_end"], 5), "mjd_mid": round(fr["mjd_mid"], 5),
                    "date": mjd_to_date(fr["mjd_mid"]), "n_inputs": 1,
                    "source_files": [f"byw.tools unWISE epoch {r['epoch']} band {r['band']}"], "_scale": k, "_bkg": bkg}
            self._store(fid, meta, data * k, fr["mask"], notes)
        if progress:
            progress("wise", len(raw))

    def set_spherex_index(self, rows: list[dict]):
        """All SPHEREx rows in the archive for this field (downloaded or not): fixes the time-cluster indices."""
        self.spx_rows = rows
        self.intervals = cluster_times([0.5 * (r["t_start"] + r["t_end"]) for r in rows], GAP_DAYS, self.max_bin_days)

    def add_spherex(self, detectors=DETECTORS, progress=None):
        if not self.spx_rows:
            self.set_spherex_index(fetch_spherex.read_index(self.field_id))
        for det in detectors:
            for ti, (a, b) in enumerate(self.intervals):
                rows = [r for r in self.spx_rows if r["band"] == det and r["path"].is_file()
                        and assign(0.5 * (r["t_start"] + r["t_end"]), self.intervals) == ti]
                if not rows:
                    continue
                fid = f"spx_{det.lower()}_t{ti:02d}"
                t0 = time.time()
                co = coadd_spherex(rows, self.wcs, self.shape, log)
                if co is None:
                    continue
                data, bkg, _ = subtract_background(co["data"])
                notes = [f"co-add of {co['n_inputs']} images (inverse-variance)", "SPHEREx 6.15\"/px resampled to 2.75\"/px"]
                ref = self.refs.get(WISE_REF_FOR[det])
                k, n = scale_factor(data, co["mask"], ref["flux"], *self.ref_xy) if ref else (None, 0)
                if k is None:
                    k = self._fallback_scale(data, WISE_REF_FOR[det])
                    notes.append("too few reference stars; scaled by bright-pixel percentile")
                else:
                    notes.append(f"scaled to {WISE_REF_FOR[det]} on {n} Gaia stars")
                if (co["mask"] & 2).any():
                    notes.append("saturated pixels (OVERFLOW) present")
                lam = co["lam"] or SPHEREX_RANGE[det]
                meta = {"id": fid, "instrument": "SPHEREx", "band": det, "lambda_um": [round(lam[0], 4), round(lam[1], 4)],
                        "mjd_start": round(co["mjd_start"], 5), "mjd_end": round(co["mjd_end"], 5), "mjd_mid": round(co["mjd_mid"], 5),
                        "date": mjd_to_date(co["mjd_mid"]), "n_inputs": co["n_inputs"],
                        "source_files": [f"IRSA SPHEREx {'+'.join(co['releases'])} L2 cutouts x{co['n_inputs']}"], "_scale": k, "_bkg": bkg}
                self.releases.update(co["releases"])
                self._store(fid, meta, data * k, co["mask"], notes)
                for r in rows:
                    self.per_image.append(dict(field=self.field_id, detector=det, cluster=ti, frame_id=fid, filename=r["filename"],
                                               path=str(r["path"]), t_start=r["t_start"], t_end=r["t_end"],
                                               mjd_mid=round(0.5 * (r["t_start"] + r["t_end"]), 6), release=r["release"]))
                log.info("%s %s: %d inputs, scale %.4g, %.1fs", self.field_id, fid, co["n_inputs"], k, time.time() - t0)
                if progress:
                    progress(fid, co["n_inputs"])

    def _fallback_scale(self, data, band):
        ref = self.refs.get(band)
        if not ref:
            return 1.0
        rd = self.arrays[ref["fid"]][0]
        a = np.nanpercentile(rd, 99.5)
        b = np.nanpercentile(data, 99.5)
        return float(a / b) if b > 0 and a > 0 else 1.0

    # ------------------------------------------------------------------ manifest
    def sequences(self):
        fr = self.frames
        srt = lambda ids: sorted(ids, key=lambda i: (fr[i]["mjd_mid"], i))  # noqa: E731
        seqs = []
        t46 = srt([i for i in fr if fr[i]["band"] in ("W2", "D6")])
        if t46:
            seqs.append({"id": "thermal46", "label": "4.6 µm — WISE W2 + SPHEREx D6", "default": True, "frames": t46})
        w1 = srt([i for i in fr if fr[i]["band"] in ("W1", "D4")])
        if w1:
            seqs.append({"id": "w1d4", "label": "3.4 µm — WISE W1 + SPHEREx D4", "default": not t46, "frames": w1})
        spx = srt([i for i in fr if fr[i]["instrument"] == "SPHEREx"])
        if spx:
            seqs.append({"id": "spherex6", "label": "SPHEREx only — D1…D6", "default": not (t46 or w1), "frames": spx})
        return seqs

    def rgb_composites(self, write_previews=True):
        out = []
        for ti, (a, b) in enumerate(self.intervals):
            ids = [f"spx_d{d}_t{ti:02d}" for d in (6, 3, 1)]
            if all(i in self.frames for i in ids):
                year = mjd_to_date(self.frames[ids[0]]["mjd_mid"])[:7]
                cid = f"fingerprint_t{ti:02d}"
                out.append({"id": cid, "label": f"Spectral fingerprint (D1/D3/D6), {year}", "r": ids[0], "g": ids[1], "b": ids[2]})
                if write_previews:
                    write_rgb_preview(self.fdir, cid, [self.arrays[i][0] for i in ids], [self.frames[i]["display"] for i in ids])
        return out

    def write_target_object(self):
        t = self.target
        if not t:
            return
        info = TARGETS.get(self.field_id, {})
        sat_frames = [f for f in self.frames if self._target_saturated(f)]
        for f in sat_frames:
            self.frames[f]["quality"]["notes"].append("target saturated")
        sat_in = sorted({self.frames[f]["band"] for f in sat_frames})
        obj = {"id": "target", "name": info.get("title", self.title), "kind": info.get("obj_kind", "star"),
               "ra": t["ra_2018"], "dec": t["dec_2018"], "epoch": 2018.0,
               "motion": {"measured": None,
                          "reference": {"source": f"SIMBAD ({t.get('pm_bibcode')})", "pmra": t["pmra_masyr"], "pmdec": t["pmdec_masyr"],
                                        "unit": "mas/yr"},
                          "agreement_pct": None, "track": []},
               "spectrum": None, "lightcurve": None, "copilot": None,
               "flags": {"saturated_in": sat_in, "warnings": (["target saturated in some frames"] if sat_in else [])},
               "simbad_id": t.get("simbad_main_id"), "sp_type": t.get("sp_type"), "parallax_mas": t.get("parallax_mas")}
        p = self.fdir / "objects" / "target.json"
        if p.is_file():  # never overwrite science products
            if "target" not in self.objects:
                self.objects.append("target")
            return
        write_json(p, obj, indent=1)
        self.objects.append("target")

    def _target_saturated(self, fid) -> bool:
        t = self.target
        fr = self.frames[fid]
        ra, dec = propagate(t["ra_2018"], t["dec_2018"], t["pmra_masyr"] or 0, t["pmdec_masyr"] or 0, 2018.0, julian_year(fr["mjd_mid"]))
        from .grid import world_to_grid

        x, y = world_to_grid(self.wcs, ra, dec)
        xi, yi = int(round(float(x[0]))), int(round(float(y[0])))
        m = self.arrays[fid][1]
        if not (0 <= xi < m.shape[1] and 0 <= yi < m.shape[0]):
            return False
        return bool((m[max(yi - 1, 0):yi + 2, max(xi - 1, 0):xi + 2] & 2).any())

    def write(self, status: str = "done", rgb=True):
        frames = [{k: v for k, v in self.frames[i].items() if not k.startswith("_")}
                  for i in sorted(self.frames, key=lambda i: (self.frames[i]["mjd_mid"], i))]
        objs = sorted({p.stem for p in (self.fdir / "objects").glob("*.json")}) if (self.fdir / "objects").is_dir() else []
        cand = "candidates.json" if (self.fdir / "candidates.json").is_file() else None
        man = {"schema_version": SCHEMA, "field_id": self.field_id, "title": self.title,
               "center": {"ra": round(self.ra, 7), "dec": round(self.dec, 7), "epoch": 2018.0}, "grid": self.grid,
               "frames": frames, "sequences": self.sequences(), "rgb_composites": self.rgb_composites(rgb) if rgb else [],
               "objects": objs, "catalogs": {"gaia": "catalogs/gaia.json", "catwise": "catalogs/catwise.json"}, "candidates": cand,
               "credits": CREDITS,
               "build": {"pipeline_version": PIPELINE_VERSION, "generated_utc": utcnow(), "spherex_releases": sorted(self.releases),
                         "status": status, "grid_note": "SPHEREx pixels are 6.15\"; resampled to 2.75\"/px for comparison",
                         "skipped_frames": self.skipped,
                         "spherex_epochs": [[round(a, 3), round(b, 3)] for a, b in self.intervals],
                         "wise_source": "byw.tools time-resolved unWISE (neo7-style epochs)",
                         "scaling": "per-frame sigma-clipped background subtracted; scaled to the WISE epoch nearest 2018.0 "
                                    "on bright unsaturated low-PM Gaia stars (D1-D4 -> W1, D5-D6 -> W2)"}}
        write_json(self.fdir / "manifest.json", man)
        thumb = f"{self.field_id}/previews/wise_w2_e00.png"
        if not (self.out_root / thumb).is_file():
            pv = sorted((self.fdir / "previews").glob("*.png"))
            thumb = f"{self.field_id}/previews/{pv[0].name}" if pv else thumb
        update_index(self.out_root, {"field_id": self.field_id, "title": self.title, "kind": self.kind, "ra": round(self.ra, 6),
                                     "dec": round(self.dec, 6), "thumb": thumb, "tags": self.tags})
        return man

    def write_science_csv(self):
        if not self.per_image:
            return None
        d = DERIVED / self.field_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / "spherex_images.csv"
        rows = sorted(self.per_image, key=lambda r: (r["mjd_mid"], r["detector"]))
        with p.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        return p


def build_target(field_id: str, out_root: Path = BUNDLE, detectors=DETECTORS, clean: bool = True) -> dict:
    t0 = time.time()
    tg = load_targets()[field_id]
    info = TARGETS[field_id]
    fdir = Path(out_root) / field_id
    if clean and fdir.exists():
        keep = {}
        for sub in ("objects", "candidates.json"):
            p = fdir / sub
            if p.exists():
                keep[sub] = p
        for item in fdir.iterdir():
            if item.name in keep:
                continue
            shutil.rmtree(item) if item.is_dir() else item.unlink()
    b = FieldBuilder(field_id, tg["ra_2018"], tg["dec_2018"], info["title"], "nasa_test_target", info["tags"], out_root,
                     max_bin_days=info.get("max_bin_days"), target=tg)
    b.load_catalogs()
    b.add_wise()
    b.set_spherex_index(fetch_spherex.read_index(field_id))
    b.add_spherex(detectors)
    b.write_target_object()
    man = b.write()
    csvp = b.write_science_csv()
    log.info("%s: %d frames in %.0fs; science csv %s", field_id, len(man["frames"]), time.time() - t0, csvp)
    return man
