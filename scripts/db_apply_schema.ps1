param(
  [string]$DbName = "blog_platform",
  [string]$DbUser = "blog",
  [string]$DbPassword = "blog",
  [string]$DockerPostgresContainer = ""
)

$ErrorActionPreference = "Stop"
$env:PGPASSWORD = $DbPassword

Write-Host "Applying schema to ${DbUser}@docker/${DbName} ..."

$schemaPath = ".\infra\db\schema.sql"

# Auto-detect postgres container if not provided
if (-not $DockerPostgresContainer -or $DockerPostgresContainer.Trim() -eq "") {
  $pg = docker ps --format "{{.Names}} {{.Image}}" | Select-String -Pattern "postgres" | Select-Object -First 1
  if (-not $pg) {
    throw "Could not find a running postgres container. Start docker compose first."
  }
  $DockerPostgresContainer = ($pg.Line.Split(" ")[0]).Trim()
}

Write-Host "Using container: $DockerPostgresContainer"

# PowerShell-safe pipe of SQL into psql inside container
Get-Content $schemaPath -Raw | docker exec -i $DockerPostgresContainer psql -U $DbUser -d $DbName

Write-Host "Schema applied successfully (docker psql)."
