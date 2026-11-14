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
from pydantic import BaseModel, Field

from . import copilot, live
from . import resolve as resolver

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get("SKYLAPSE_CACHE", str(ROOT / "cache"))).resolve()
FIELDS = CACHE / "fields"
FIELD_ID = re.compile(r"^[A-Za-z0-9_.+-]{1,80}$")

app = FastAPI(title="SkyLapse API", version="0.3.0")
origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])
resolver.init_cache(CACHE / "resolve.json")
live.init(FIELDS)

MEDIA = {".json": "application/json", ".f32": "application/octet-stream", ".u8": "application/octet-stream",
         ".png": "image/png", ".mp3": "audio/mpeg"}


@app.get("/api/health")
def health():
    return {"ok": True, "version": app.version, "copilot": copilot.configured(), "fields_cached": len(list(FIELDS.glob("*/manifest.json"))) if FIELDS.exists() else 0}


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


class CopilotRequest(BaseModel):
    facts: dict


@app.post("/api/copilot")
def api_copilot(req: CopilotRequest):
    """Optional live copilot (P2-1). Always answers; on any problem returns {fallback: true, message}."""
    code, body = copilot.generate(req.facts)
    return JSONResponse(body, status_code=code)


class FieldRequest(BaseModel):
    ra: float = Field(..., ge=0, lt=360)
    dec: float = Field(..., ge=-90, le=90)
    fov_arcmin: float | None = Field(None, gt=0, le=60)


@app.post("/api/fields")
def create_field(req: FieldRequest):
    """Start (or reuse) a live WISE-only field build. Contract §7."""
    try:
        return live.submit(req.ra, req.dec, req.fov_arcmin)
    except RuntimeError:
        return JSONResponse({"error": "The live builder is busy. Please try again in a minute."}, status_code=503)


@app.get("/api/fields/{field_id}/status")
def field_status(field_id: str):
    _field_dir(field_id)
    st = live.read_status(field_id)
    if st is None:
        if (FIELDS / field_id / "manifest.json").is_file():
            return {"state": "done", "progress": 1.0, "manifest_url": f"/api/fields/{field_id}/manifest.json"}
        raise HTTPException(404, "unknown field")
    return JSONResponse(st, headers={"Cache-Control": "no-cache"})


@app.get("/api/fields/{field_id}/{path:path}")
def field_file(field_id: str, path: str):
    d = _field_dir(field_id).resolve()
    f = (d / path).resolve()
    if not str(f).startswith(str(d) + os.sep) or not f.is_file():
        raise HTTPException(404, "not found")
    headers = {"Cache-Control": "no-cache" if f.name in ("manifest.json", "status.json") else "public, max-age=86400"}
    return FileResponse(f, media_type=MEDIA.get(f.suffix, "application/octet-stream"), headers=headers)
