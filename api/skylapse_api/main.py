"""SkyLapse API (FastAPI). Contract: docs/DATA_CONTRACT.md §7.

Run locally:  uvicorn skylapse_api.main:app --app-dir api --port 8000
Env:
  SKYLAPSE_CACHE   cache dir (default <repo>/cache)  → live fields in <cache>/fields/<id>/ (same layout as the static bundle)
  CORS_ORIGINS     comma list of allowed origins (default "*"; no credentials are used)
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from . import resolve as resolver

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get("SKYLAPSE_CACHE", str(ROOT / "cache"))).resolve()
FIELDS = CACHE / "fields"
FIELD_ID = re.compile(r"^[A-Za-z0-9_.+-]{1,80}$")

app = FastAPI(title="SkyLapse API", version="0.1.0")
origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])
resolver.init_cache(CACHE / "resolve.json")

MEDIA = {".json": "application/json", ".f32": "application/octet-stream", ".u8": "application/octet-stream",
         ".png": "image/png", ".mp3": "audio/mpeg"}


@app.get("/api/health")
def health():
    return {"ok": True, "version": app.version, "fields_cached": len(list(FIELDS.glob("*/manifest.json"))) if FIELDS.exists() else 0}


@app.get("/api/resolve")
def api_resolve(q: str = Query(..., min_length=1, max_length=200)):
    hit = resolver.resolve(q)
    if not hit:
        return JSONResponse({"error": f"Could not resolve '{q}'. Try RA Dec in degrees, e.g. '133.795 -7.245'."}, status_code=404)
    return hit


def _field_dir(field_id: str) -> Path:
    if not FIELD_ID.match(field_id):
        raise HTTPException(400, "bad field id")
    return FIELDS / field_id


@app.get("/api/fields/{field_id}/status")
def field_status(field_id: str):
    """Static-only fallback until O2 adds live jobs: a cached field is `done`, anything else is unknown."""
    d = _field_dir(field_id)
    st = d / "status.json"
    if st.is_file():
        return FileResponse(st, media_type="application/json")
    if (d / "manifest.json").is_file():
        return {"state": "done", "progress": 1.0, "manifest_url": f"/api/fields/{field_id}/manifest.json"}
    raise HTTPException(404, "unknown field")


@app.get("/api/fields/{field_id}/{path:path}")
def field_file(field_id: str, path: str):
    d = _field_dir(field_id).resolve()
    f = (d / path).resolve()
    if not str(f).startswith(str(d) + os.sep) or not f.is_file():
        raise HTTPException(404, "not found")
    headers = {"Cache-Control": "no-cache" if f.name in ("manifest.json", "status.json") else "public, max-age=86400"}
    return FileResponse(f, media_type=MEDIA.get(f.suffix, "application/octet-stream"), headers=headers)
