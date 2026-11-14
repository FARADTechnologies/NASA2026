# SkyLapse API (FastAPI) — contract: `docs/DATA_CONTRACT.md` §7
```
pip install -r api/requirements.txt
uvicorn skylapse_api.main:app --app-dir api --host 0.0.0.0 --port 8000
```
- `GET /api/health`
- `GET /api/resolve?q=` → `{"name","ra","dec","source"}` (+ `"field"` for the 5 NASA targets → open the precomputed bundle field).
  Order: coordinates (degrees or sexagesimal) → local NASA-target table → CDS Sesame (+ CfA/IDIA mirrors) → SIMBAD TAP mirrors. Cached in `cache/resolve.json`.
- `GET /api/fields/{id}/status` and `GET /api/fields/{id}/<file>` serve `cache/fields/<id>/` (same layout as the static bundle).
- `POST /api/fields {ra, dec, fov_arcmin}` → `{field_id, status_url, cached}`: WISE-only live build (pipeline `live.py`, `detectors=[]`), one job at a time, cached on disk. `wise_ready` ≈ 90 s, `done` ≈ 4 min. 503 when the queue is full.
Env: `SKYLAPSE_CACHE` (default `<repo>/cache`), `CORS_ORIGINS` (default `*`), `RESOLVE_TIMEOUT_S` (default 8).
