FROM node:20-slim AS frontend-builder

ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build


FROM node:20-slim

WORKDIR /app

ENV PYTHONPATH=/app/src
ENV AI_SCIENTIST_DISABLE_AUTH=0

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -fsSL "https://caddyserver.com/api/download?os=linux&arch=amd64" -o /usr/bin/caddy \
    && chmod +x /usr/bin/caddy

COPY --from=frontend-builder /app/frontend/.next /app/frontend/.next
COPY --from=frontend-builder /app/frontend/node_modules /app/frontend/node_modules
COPY --from=frontend-builder /app/frontend/package.json /app/frontend/package.json
COPY --from=frontend-builder /app/frontend/next.config.mjs /app/frontend/next.config.mjs

COPY pyproject.toml README.md /app/
COPY migrations /app/migrations
COPY alembic.ini /app/alembic.ini
COPY src /app/src
COPY templates /app/templates
RUN pip3 install --no-cache-dir --break-system-packages -e . && pip3 install --break-system-packages cryptography

COPY Caddyfile.prod /app/Caddyfile

EXPOSE 7860

CMD sh -c "\
  cd /app/frontend && node node_modules/.bin/next start -p 3000 2>/tmp/node.log & \
  cd /app && python3 -m uvicorn ai_scientist.main:app --host 0.0.0.0 --port 8000 2>/tmp/python.log & \
  sleep 3 && echo '=== Node log ===' && cat /tmp/node.log && echo '=== Python log ===' && cat /tmp/python.log && \
  echo '=== Starting Caddy ===' && caddy run --config /app/Caddyfile"
