param(
  [int[]]$Ports = @(8000, 3000)
)

$ErrorActionPreference = "SilentlyContinue"

function Stop-Port($port) {
  $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if (-not $conns) {
    Write-Host "No process listening on port $port"
    return
  }

  $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($pid in $pids) {
    Write-Host "Stopping PID $pid on port $port..."
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
  }
}

foreach ($p in $Ports) {
  Stop-Port $p
}

Write-Host "Done."
