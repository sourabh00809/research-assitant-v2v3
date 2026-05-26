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
Start-Sleep -Seconds 10
docker compose --env-file .env.production -f $ComposeFile exec backend alembic upgrade head 2>$null
Start-Sleep -Seconds 5
docker compose --env-file .env.production -f $ComposeFile exec backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/admin/ready', timeout=10).read(); print('ready')"
docker compose --env-file .env.production -f $ComposeFile ps
