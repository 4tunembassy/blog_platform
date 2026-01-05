param(
  [int]$Port = 3000
)

$ErrorActionPreference = "Stop"

Write-Host "Starting Frontend (Next.js) on port $Port..." -ForegroundColor Cyan

$webPath = Resolve-Path ".\frontend\web"
Set-Location $webPath

if (-not (Test-Path ".\package.json")) {
  throw "frontend\web\package.json not found. Run create-next-app properly in frontend\web."
}

# Install deps (safe to re-run)
npm install

# Start dev server
npm run dev -- --port $Port
