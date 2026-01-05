$ErrorActionPreference = "Stop"

Write-Host "Starting full local development stack..." -ForegroundColor Green

# 1) Start Docker services
Write-Host "Starting Docker services..." -ForegroundColor Yellow
docker compose -f .\infra\docker\docker-compose.local.yml up -d

# 2) Apply DB schema (safe)
Write-Host "Applying DB schema..." -ForegroundColor Yellow
.\scripts\db_apply_schema.ps1

# 3) Start backend in a NEW PowerShell window
Write-Host "Launching backend window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy", "Bypass",
  "-Command", "cd `"$PWD`"; .\scripts\run_backend.ps1"
)

# 4) Start frontend in a NEW PowerShell window
Write-Host "Launching frontend window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy", "Bypass",
  "-Command", "cd `"$PWD`"; .\scripts\run_frontend.ps1"
)

Write-Host ""
Write-Host "Backend:  http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Tip: Use .\scripts\stop.ps1 to stop both dev servers." -ForegroundColor DarkGray
