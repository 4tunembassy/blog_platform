$ErrorActionPreference = "Stop"

Write-Host "Starting Backend API..." -ForegroundColor Cyan

cd "$PSScriptRoot\..\backend\api"

if (-not (Test-Path ".\.venv")) {
    python -m venv .venv
}

.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m uvicorn app.main:app --reload --port 8000
