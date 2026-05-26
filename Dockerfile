FROM node:20-slim AS frontend-builder

ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app/src

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=amd64" -o /usr/bin/caddy \
    && chmod +x /usr/bin/caddy

COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

COPY pyproject.toml README.md /app/
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
RUN pip install --no-cache-dir -e .

COPY src /app/src
COPY templates /app/templates

COPY --from=frontend-builder /app/frontend/.next/standalone/ /app/frontend/
COPY --from=frontend-builder /app/frontend/.next/static/ /app/frontend/.next/static/

COPY Caddyfile.prod /app/Caddyfile

RUN chown -R app:app /app

USER app

EXPOSE 8000

CMD sh -c "\
  cd /app/frontend && PORT=3000 node server.js & \
  cd /app && python -m uvicorn ai_scientist.main:app --host 0.0.0.0 --port 8000 & \
  caddy run --config /app/Caddyfile"
