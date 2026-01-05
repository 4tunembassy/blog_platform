$ErrorActionPreference = "Stop"

Write-Host "Starting full local development stack..." -ForegroundColor Green

# 1. Start Docker services
Write-Host "Starting Docker services..." -ForegroundColor Yellow
docker compose -f "$PSScriptRoot\..\infra\docker\docker-compose.local.yml" up -d

Start-Sleep -Seconds 3

# 2. Start Backend API in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$PSScriptRoot\run_api.ps1"

# 3. Start Frontend in new window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "$PSScriptRoot\run_frontend.ps1"

Write-Host "All services started." -ForegroundColor Green
Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
