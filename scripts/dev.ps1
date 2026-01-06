$ErrorActionPreference = "Stop"

Write-Host "Starting full local development stack..." -ForegroundColor Green

# Resolve repo root regardless of where PowerShell is launched from
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

# 1) Start Docker services + seed default tenant
Write-Host "Bootstrapping Docker services + seeding default tenant..." -ForegroundColor Yellow
$bootstrap = Join-Path $RepoRoot "scripts\bootstrap_db.ps1"
if (-not (Test-Path $bootstrap)) { throw "Missing script: $bootstrap" }
powershell -NoProfile -ExecutionPolicy Bypass -File $bootstrap

# 2) Apply DB schema (optional; keep if you maintain infra/db/schema.sql)
$dbApply = Join-Path $RepoRoot "scripts\db_apply_schema.ps1"
if (Test-Path $dbApply) {
  Write-Host "Applying DB schema..." -ForegroundColor Yellow
  powershell -NoProfile -ExecutionPolicy Bypass -File $dbApply
} else {
  Write-Host "Skipping DB schema apply (scripts\db_apply_schema.ps1 not found)..." -ForegroundColor DarkGray
}

# 3) Start backend in a NEW PowerShell window (support run_api.ps1 OR run_backend.ps1)
$runApi = Join-Path $RepoRoot "scripts\run_api.ps1"
$runBackend = Join-Path $RepoRoot "scripts\run_backend.ps1"
$backendScript = $null
if (Test-Path $runApi) { $backendScript = $runApi }
elseif (Test-Path $runBackend) { $backendScript = $runBackend }
else { throw "Missing backend runner. Expected scripts\run_api.ps1 or scripts\run_backend.ps1" }

Write-Host "Launching backend window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-Command", "cd `"$RepoRoot`"; & `"$backendScript`""
)

# 4) Start frontend in a NEW PowerShell window
$runFrontend = Join-Path $RepoRoot "scripts\run_frontend.ps1"
if (-not (Test-Path $runFrontend)) { throw "Missing frontend runner: $runFrontend" }

Write-Host "Launching frontend window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-Command", "cd `"$RepoRoot`"; & `"$runFrontend`""
)

Write-Host ""
Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Smoke test: powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1" -ForegroundColor DarkGray
Write-Host "Stop:       .\scripts\stop.ps1 (or .\scripts\stop.ps1 -StopDocker)" -ForegroundColor DarkGray
