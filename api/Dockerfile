# SkyLapse API image (Railway). Build context = repo root.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 SKYLAPSE_CACHE=/data/cache
COPY api/requirements.txt api/requirements.txt
RUN pip install -r api/requirements.txt
# pipeline deps are added here once the live runner (pipeline T5) is wired in (O2)
COPY api api
COPY pipeline pipeline
CMD ["sh", "-c", "uvicorn skylapse_api.main:app --app-dir api --host 0.0.0.0 --port ${PORT:-8000}"]
