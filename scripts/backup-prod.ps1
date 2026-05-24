param(
  [string]$OutDir = "backups"
)

$ErrorActionPreference = "Stop"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = Join-Path $OutDir $stamp
New-Item -ItemType Directory -Force -Path $target | Out-Null

docker compose --env-file .env.production -f docker-compose.prod.yml exec -T postgres pg_dump -U ai_scientist ai_scientist | Set-Content -Encoding UTF8 (Join-Path $target "postgres.sql")
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T minio sh -c "tar -C /data -cf - ." > (Join-Path $target "minio.tar")
Compress-Archive -Path $target -DestinationPath "$target.zip" -Force
Write-Host "Backup written to $target.zip"
