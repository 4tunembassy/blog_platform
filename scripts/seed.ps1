Param(
  [string]$ComposeFile = ".\infra\docker\docker-compose.local.yml",
  [string]$PgContainer = $Env:BP_PG_CONTAINER
)

$ErrorActionPreference = "Stop"

if (-not $PgContainer -or $PgContainer.Trim() -eq "") {
  $PgContainer = "governed_blog_platform-postgres-1"
}

$seedSqlPath = Join-Path $PSScriptRoot "..\infra\db\seed.sql"
$seedSqlPath = (Resolve-Path $seedSqlPath).Path

Write-Host "Seeding default tenant using container: $PgContainer" -ForegroundColor Cyan

# Verify container exists
$names = docker ps --format "{{.Names}}"
if ($names -notcontains $PgContainer) {
  Write-Host "ERROR: Postgres container not running: $PgContainer" -ForegroundColor Red
  Write-Host "Tip: run .\scripts\bootstrap_db.ps1 first." -ForegroundColor Yellow
  exit 1
}

# PowerShell-safe way to feed SQL into psql inside the container:
# - Read file as one string
# - Pipe it to docker exec -i ... psql ...
$sql = Get-Content -Raw -Path $seedSqlPath
$sql | docker exec -i $PgContainer psql -U blog -d blog_platform -v ON_ERROR_STOP=1

Write-Host "Seed completed." -ForegroundColor Green

# Show tenants
docker exec -i $PgContainer psql -U blog -d blog_platform -c "SELECT id, name, slug, created_at FROM tenants ORDER BY created_at DESC;"
