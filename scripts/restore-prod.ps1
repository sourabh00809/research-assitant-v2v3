param(
  [Parameter(Mandatory = $true)]
  [string]$BackupZip
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BackupZip)) {
  throw "Backup archive not found: $BackupZip"
}

$tempDir = Join-Path $env:TEMP "restore-redis"
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
Expand-Archive -Path $BackupZip -DestinationPath $tempDir -Force
$dumpFile = Get-ChildItem -Path $tempDir -Recurse -Filter "dump.rdb" | Select-Object -First 1
if (-not $dumpFile) {
  Remove-Item -Recurse -Force $tempDir
  throw "No dump.rdb found in $BackupZip"
}

$container = docker compose --env-file .env.production -f docker-compose.prod.yml ps -q redis
if (-not $container) {
  throw "Redis container not running"
}

docker cp $dumpFile.FullName "${container}:/tmp/dump.rdb"
docker compose --env-file .env.production -f docker-compose.prod.yml exec -T redis sh -c "cp /tmp/dump.rdb /data/dump.rdb && redis-cli SHUTDOWN SAVE"
docker compose --env-file .env.production -f docker-compose.prod.yml up -d redis
Start-Sleep -Seconds 3
docker compose --env-file .env.production -f docker-compose.prod.yml up -d backend worker scheduler

Remove-Item -Recurse -Force $tempDir
Write-Host "Restored from $BackupZip"