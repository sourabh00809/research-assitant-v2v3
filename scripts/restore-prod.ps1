param(
  [Parameter(Mandatory = $true)]
  [string]$BackupDir
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $BackupDir "postgres.sql"))) {
  throw "Missing postgres.sql in $BackupDir"
}
if (-not (Test-Path (Join-Path $BackupDir "minio.tar"))) {
  throw "Missing minio.tar in $BackupDir"
}

docker compose --env-file .env.production -f docker-compose.prod.yml exec -T postgres psql -U ai_scientist -d ai_scientist -c "drop schema public cascade; create schema public; create extension if not exists vector;"
Get-Content -Raw (Join-Path $BackupDir "postgres.sql") | docker compose --env-file .env.production -f docker-compose.prod.yml exec -T postgres psql -U ai_scientist -d ai_scientist
Get-Content -Raw (Join-Path $BackupDir "minio.tar") | docker compose --env-file .env.production -f docker-compose.prod.yml exec -T minio sh -c "tar -C /data -xf -"
docker compose --env-file .env.production -f docker-compose.prod.yml restart backend worker scheduler
