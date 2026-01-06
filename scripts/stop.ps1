param(
  [int[]]$Ports = @(8000, 3000),
  [switch]$StopDocker,
  [string]$ComposeFile = ".\infra\docker\docker-compose.local.yml"
)

$ErrorActionPreference = "SilentlyContinue"

function Stop-PortListener {
  param([int]$Port)

  $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if (-not $conns) {
    Write-Host "No process listening on port $Port"
    return
  }

  $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique

  foreach ($pid in $pids) {
    if (-not $pid -or $pid -eq 0) { continue }

    try {
      $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
      $name = if ($proc) { $proc.ProcessName } else { "Unknown" }

      Write-Host "Stopping PID $pid ($name) on port $Port..."
      Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    } catch {}
  }
}

Write-Host "Stopping dev servers..." -ForegroundColor Yellow
foreach ($p in $Ports) {
  Stop-PortListener -Port $p
}

if ($StopDocker) {
  try {
    $RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
    $ComposePath = Join-Path $RepoRoot $ComposeFile

    if (Test-Path $ComposePath) {
      Write-Host "Stopping Docker services via compose..." -ForegroundColor Yellow
      docker compose -f $ComposePath down
    } else {
      Write-Host "Compose file not found: $ComposePath" -ForegroundColor DarkGray
    }
  } catch {}
}

Write-Host "Done." -ForegroundColor Green
