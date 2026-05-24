param(
  [string]$ComposeFile = "docker-compose.prod.yml"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env.production")) {
  throw "Create .env.production from .env.production.example before deploying."
}

docker compose --env-file .env.production -f $ComposeFile pull
docker compose --env-file .env.production -f $ComposeFile build
docker compose --env-file .env.production -f $ComposeFile up -d
docker compose --env-file .env.production -f $ComposeFile exec backend alembic upgrade head
docker compose --env-file .env.production -f $ComposeFile exec backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/admin/ready', timeout=5).read(); print('ready')"
docker compose --env-file .env.production -f $ComposeFile ps
