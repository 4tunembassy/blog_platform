Param(
  [string]$ComposeFile = ".\infra\docker\docker-compose.local.yml",
  [string]$PgContainer = $Env:BP_PG_CONTAINER,
  [int]$WaitSeconds = 60
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ComposeFile)) {
  Write-Host "ERROR: Compose file not found: $ComposeFile" -ForegroundColor Red
  Write-Host "Run this from the repo root (blog_platform)." -ForegroundColor Yellow
  exit 1
}

if (-not $PgContainer -or $PgContainer.Trim() -eq "") {
  $PgContainer = "governed_blog_platform-postgres-1"
}

Write-Host "Starting local infra using $ComposeFile ..." -ForegroundColor Cyan
docker compose -f $ComposeFile up -d

Write-Host "Waiting for Postgres ($PgContainer) to be ready..." -ForegroundColor Cyan
$deadline = (Get-Date).AddSeconds($WaitSeconds)

while ((Get-Date) -lt $deadline) {
  try {
    docker exec -i $PgContainer pg_isready -U blog -d blog_platform *> $null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "Postgres is ready." -ForegroundColor Green
      break
    }
  } catch {}
  Start-Sleep -Seconds 2
}

if ((Get-Date) -ge $deadline) {
  Write-Host "ERROR: Timed out waiting for Postgres to be ready." -ForegroundColor Red
  docker compose -f $ComposeFile ps
  exit 1
}

# Seed
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "seed.ps1") -ComposeFile $ComposeFile -PgContainer $PgContainer
