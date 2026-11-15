"""S10 — check that live-field catalog overlays land on real sources (pixel offsets) on the deployed API.

For each test position: create/get the live field, read manifest + catalogs, and in the first and last W2 frames measure the
centroid (photutils centroid_2dg) of every catalog source that should be clearly visible (Gaia G < 17 or CatWISE W2 < 14,
not saturated, inside the frame), with the catalog position propagated to the frame's mjd_mid exactly as the frontend does.
Reports the median and 90th-percentile offset in pixels (2.75"/px), and for the marked mover(s) the offset in both frames.
"""
from __future__ import annotations

import json
import math
import time
import urllib.request

import numpy as np
from astropy.stats import sigma_clipped_stats
from photutils.centroids import centroid_2dg

API = "https://api-production-02611b3c.up.railway.app"


def _get(url, raw=False, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        b = r.read()
    return b if raw else json.loads(b)


def _post(url, body, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def open_field(ra, dec, fov=8.8):
    t0 = time.time()
    r = _post(f"{API}/api/fields", {"ra": ra, "dec": dec, "fov_arcmin": fov})
    su = r["status_url"] if r["status_url"].startswith("http") else API + r["status_url"]
    while time.time() - t0 < 240:
        s = _get(su)
        if s["state"] in ("done", "error"):
            break
        time.sleep(3)
    return r["field_id"], s["state"], time.time() - t0


def world2pix(w, ra, dec):
    """TAN projection with the manifest's CD matrix (same as the frontend's world2pix), 0-based pixels."""
    a0, d0 = math.radians(w["CRVAL1"]), math.radians(w["CRVAL2"])
    a, d = math.radians(ra), math.radians(dec)
    cosc = math.sin(d0) * math.sin(d) + math.cos(d0) * math.cos(d) * math.cos(a - a0)
    xi = math.degrees(math.cos(d) * math.sin(a - a0) / cosc)
    eta = math.degrees((math.cos(d0) * math.sin(d) - math.sin(d0) * math.cos(d) * math.cos(a - a0)) / cosc)
    det = w["CD1_1"] * w["CD2_2"] - w["CD1_2"] * w["CD2_1"]
    x = (w["CD2_2"] * xi - w["CD1_2"] * eta) / det
    y = (-w["CD2_1"] * xi + w["CD1_1"] * eta) / det
    return x + w["CRPIX1"] - 1, y + w["CRPIX2"] - 1


def propagate(row, cols, ref_epoch, mjd):
    r = dict(zip(cols, row))
    t = 2000.0 + (mjd - 51544.5) / 365.25 - ref_epoch
    pmra, pmdec = (r.get("pmra") or 0.0), (r.get("pmdec") or 0.0)
    dec = r["dec"] + pmdec * t / 3.6e6
    ra = r["ra"] + pmra * t / (3.6e6 * math.cos(math.radians(r["dec"])))
    return ra, dec, r


def centroid(img, x, y, half=3):
    ix, iy = int(round(x)), int(round(y))
    if ix - half - 4 < 0 or iy - half - 4 < 0 or ix + half + 4 >= img.shape[1] or iy + half + 4 >= img.shape[0]:
        return None
    big = img[iy - half - 4: iy + half + 5, ix - half - 4: ix + half + 5]
    _, bkg, rms = sigma_clipped_stats(big, sigma=3.0, maxiters=3)
    box = img[iy - half: iy + half + 1, ix - half: ix + half + 1] - bkg
    if not np.isfinite(box).all() or (img[iy - half: iy + half + 1, ix - half: ix + half + 1] == 0).sum() > 2:
        return None
    if box.max() < 8 * rms:
        return None
    try:
        cx, cy = centroid_2dg(box)
    except Exception:
        return None
    return ix - half + cx, iy - half + cy


def check(label, ra, dec):
    fid, state, secs = open_field(ra, dec)
    base = f"{API}/api/fields/{fid}"
    m = _get(f"{base}/manifest.json")
    w, gw, gh = m["grid"]["wcs"], m["grid"]["width"], m["grid"]["height"]
    w2 = sorted([f for f in m["frames"] if f["band"] == "W2"], key=lambda f: f["mjd_mid"])
    out = {"label": label, "field": fid, "state": state, "seconds": round(secs), "frames": len(m["frames"])}
    cats = {}
    for name, path in (m.get("catalogs") or {}).items():
        try:
            cats[name] = _get(f"{base}/{path}")
        except Exception as e:
            cats[name] = None
            out[f"{name}_error"] = str(e)
    out["catalog_rows"] = {k: (len(v["rows"]) if v else None) for k, v in cats.items()}
    for which, fr in (("first", w2[0]), ("last", w2[-1])):
        img = np.frombuffer(_get(f"{base}/{fr['file']}", raw=True), dtype="<f4").reshape(gh, gw).astype(float)
        offs = []
        for name, c in cats.items():
            if not c:
                continue
            cols = c["columns"]
            for row in c["rows"]:
                ra_t, dec_t, r = propagate(row, cols, c["ref_epoch"], fr["mjd_mid"])
                mag = r.get("mag")
                if mag is None or (name == "gaia" and not 9 < mag < 17) or (name == "catwise" and not 9 < mag < 14):
                    continue
                x, y = world2pix(w, ra_t, dec_t)
                if not (8 < x < gw - 8 and 8 < y < gh - 8):
                    continue
                cc = centroid(img, x, y)
                if cc and math.hypot(cc[0] - x, cc[1] - y) < 3:
                    offs.append(math.hypot(cc[0] - x, cc[1] - y))
        out[f"{which}_date"] = fr["date"]
        out[f"{which}_n"] = len(offs)
        out[f"{which}_median_px"] = round(float(np.median(offs)), 2) if offs else None
        out[f"{which}_p90_px"] = round(float(np.percentile(offs, 90)), 2) if offs else None
    # marked movers: candidates.json items / objects
    movers = []
    try:
        cand = _get(f"{base}/{m.get('candidates') or 'candidates.json'}")
        movers = [it for it in cand.get("items", []) if it.get("class") in ("known", "candidate")]
        out["movers_marked"] = len(movers)
    except Exception as e:
        out["movers_error"] = str(e)
    mv = []
    for it in movers[:3]:
        rr = {"id": it.get("id"), "pm": it.get("pm_total")}
        for which, fr in (("first", w2[0]), ("last", w2[-1])):
            img = np.frombuffer(_get(f"{base}/{fr['file']}", raw=True), dtype="<f4").reshape(gh, gw).astype(float)
            t = 2000.0 + (fr["mjd_mid"] - 51544.5) / 365.25 - it.get("epoch", 2018.0)
            dec_t = it["dec"] + (it.get("pmdec") or 0) * t / 3.6e6
            ra_t = it["ra"] + (it.get("pmra") or 0) * t / (3.6e6 * math.cos(math.radians(it["dec"])))
            x, y = world2pix(w, ra_t, dec_t)
            cc = centroid(img, x, y)
            rr[which] = round(math.hypot(cc[0] - x, cc[1] - y), 2) if cc else None
        mv.append(rr)
    out["movers"] = mv
    return out


if __name__ == "__main__":
    import sys
    targets = [("Luhman 16", 162.328814, -53.319466), ("Teegarden's Star", 43.253716, 16.881287),
               ("Kapteyn's Star", 77.919124, -45.018434), ("fresh coordinate", 30.1234, -20.4321)]
    res = [check(*t) for t in targets]
    print(json.dumps(res, indent=1))
    if len(sys.argv) > 1:
        open(sys.argv[1], "w", encoding="utf-8").write(json.dumps(res, indent=1))
