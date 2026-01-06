param(
  [string]$ApiDir = ".\backend\api"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ApiPath  = Join-Path $RepoRoot $ApiDir

if (-not (Test-Path $ApiPath)) {
  throw "API directory not found: $ApiPath"
}

$Py = Join-Path $ApiPath ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
  throw "Python venv not found at: $Py`nRun .\scripts\run_api.ps1 once to create it."
}

Write-Host "Running Alembic migrations..." -ForegroundColor Yellow
Push-Location $ApiPath

function Test-PyImport {
  param([Parameter(Mandatory=$true)][string]$ImportName)

  $cmdLine = '"' + $Py + '" -c "import ' + $ImportName + '" >nul 2>nul'
  cmd.exe /c $cmdLine | Out-Null
  return ($LASTEXITCODE -eq 0)
}

function Ensure-PipPackage {
  param(
    [Parameter(Mandatory=$true)][string]$ImportName,
    [Parameter(Mandatory=$true)][string]$PipSpec
  )

  if (-not (Test-PyImport -ImportName $ImportName)) {
    Write-Host "Installing $PipSpec into backend/api/.venv..." -ForegroundColor Yellow
    & $Py -m pip install $PipSpec
  } else {
    Write-Host "OK: $ImportName already available" -ForegroundColor DarkGray
  }
}

& $Py -m pip --version | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "pip is not available in the venv: $Py"
}

Ensure-PipPackage -ImportName "alembic" -PipSpec "alembic==1.13.2"
Ensure-PipPackage -ImportName "dotenv"  -PipSpec "python-dotenv==1.0.1"

& $Py -m alembic -c alembic.ini upgrade head
$code = $LASTEXITCODE

Pop-Location

if ($code -ne 0) {
  throw "Alembic migrations failed with exit code $code"
}

Write-Host "Migrations complete." -ForegroundColor Green
