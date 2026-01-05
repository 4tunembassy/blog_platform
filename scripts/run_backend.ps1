param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

Write-Host "Starting Backend API on port $Port..." -ForegroundColor Cyan

$apiPath = Resolve-Path ".\backend\api"
Set-Location $apiPath

# Ensure venv exists
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
  throw "Backend venv not found at backend\api\.venv. Create it first."
}

# Activate venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass | Out-Null
. .\.venv\Scripts\Activate.ps1

# Install deps (safe to re-run)
python -m pip install -r requirements.txt

# Start uvicorn
python -m uvicorn app.main:app --reload --port $Port
