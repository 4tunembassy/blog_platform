param(
  [string]$DbName = "blog_platform",
  [string]$DbUser = "blog",
  [string]$DbPassword = "blog",
  [string]$DockerPostgresContainer = $Env:BP_PG_CONTAINER
)

$ErrorActionPreference = "Stop"
$env:PGPASSWORD = $DbPassword

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$schemaPath = Join-Path $RepoRoot "infra\db\schema.sql"

if (-not (Test-Path $schemaPath)) {
  throw "Schema file not found: $schemaPath"
}

Write-Host "Applying schema to ${DbUser}@docker/${DbName} ..." -ForegroundColor Yellow

if (-not $DockerPostgresContainer -or $DockerPostgresContainer.Trim() -eq "") {
  $preferred = "governed_blog_platform-postgres-1"
  $names = docker ps --format "{{.Names}}"
  if ($names -contains $preferred) {
    $DockerPostgresContainer = $preferred
  } else {
    $pg = docker ps --format "{{.Names}} {{.Image}}" | Select-String -Pattern "postgres|pgvector" | Select-Object -First 1
    if (-not $pg) {
      throw "Could not find a running postgres container. Start docker compose first."
    }
    $DockerPostgresContainer = ($pg.Line.Split(" ")[0]).Trim()
  }
}

Write-Host "Using container: $DockerPostgresContainer" -ForegroundColor Cyan
Write-Host "Schema path: $schemaPath" -ForegroundColor DarkGray

(Get-Content -Raw -Path $schemaPath) | docker exec -i $DockerPostgresContainer psql -U $DbUser -d $DbName -v ON_ERROR_STOP=1

Write-Host "Schema applied successfully (docker psql)." -ForegroundColor Green
