FROM node:20-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

COPY pyproject.toml README.md /app/
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
RUN pip install --no-cache-dir -e .

COPY src /app/src
COPY templates /app/templates

COPY --from=frontend-builder /app/frontend/out /app/frontend/out

RUN chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/admin/live', timeout=3).read()"

CMD sh -c "alembic upgrade head && python -m uvicorn ai_scientist.main:app --host 0.0.0.0 --port ${PORT:-8000}"
