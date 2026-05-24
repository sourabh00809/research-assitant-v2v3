FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
RUN npm run build

FROM python:3.11-slim AS backend

WORKDIR /app

ENV PYTHONPATH=/app/src
ENV AI_SCIENTIST_DB_PATH=/app/data/ai_scientist.db
ENV AI_SCIENTIST_STORAGE_DIR=/app/storage

RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY templates /app/templates
COPY frontend /app/frontend
COPY --from=frontend-build /app/frontend/out /app/frontend/out

RUN pip install --no-cache-dir \
    fastapi uvicorn pydantic pypdf jinja2 pyyaml \
    sqlalchemy alembic "psycopg[binary]" redis celery stripe minio docker

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/admin/live', timeout=3).read()"

CMD ["python", "-m", "uvicorn", "ai_scientist.main:app", "--host", "0.0.0.0", "--port", "8000"]
