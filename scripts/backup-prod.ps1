param(
  [string]$OutDir = "backups"
)

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $OutDir $stamp
New-Item -ItemType Directory -Force -Path $target | Out-Null

$container = docker compose --env-file .env.production -f docker-compose.prod.yml ps -q redis
if (-not $container) {
  throw "Redis container not running"
}

docker compose --env-file .env.production -f docker-compose.prod.yml exec -T redis redis-cli --rdb /tmp/dump.rdb
docker cp "${container}:/tmp/dump.rdb" (Join-Path $target "dump.rdb")
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T redis rm /tmp/dump.rdb

Compress-Archive -Path $target -DestinationPath "$target.zip" -Force
Remove-Item -Recurse -Force $target
Write-Host "Backup written to $target.zip"