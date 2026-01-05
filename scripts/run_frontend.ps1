$ErrorActionPreference = "Stop"

Write-Host "Starting Frontend (Next.js)..." -ForegroundColor Cyan

cd "$PSScriptRoot\..\frontend\web"

if (-not (Test-Path "node_modules")) {
    npm install
}

npm run dev
