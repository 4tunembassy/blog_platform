param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [string]$TenantSlug = "default"
)

$ErrorActionPreference = "Stop"

$headers = @{ "X-Tenant-Slug" = $TenantSlug }

Write-Host "Smoke test against $BaseUrl (tenant=$TenantSlug)" -ForegroundColor Cyan

# Health
$health = Invoke-RestMethod -Uri "$BaseUrl/healthz"
if ($health.status -ne "ok") { throw "Health check failed: $($health | ConvertTo-Json -Compress)" }
Write-Host "✓ healthz ok" -ForegroundColor Green

# Create
$createBody = '{"title":"Smoke Test","risk_tier":1}'
$item = Invoke-RestMethod -Method Post -Uri "$BaseUrl/content" -Headers $headers -ContentType "application/json" -Body $createBody
if (-not $item.id) { throw "Create failed: $($item | ConvertTo-Json -Compress)" }
Write-Host "✓ created content: $($item.id) state=$($item.state)" -ForegroundColor Green

# Transition
$transitionBody = '{"to_state":"CLASSIFIED","reason":"Smoke transition","actor_type":"system"}'
$updated = Invoke-RestMethod -Method Post -Uri "$BaseUrl/content/$($item.id)/transition" -Headers $headers -ContentType "application/json" -Body $transitionBody
Write-Host "✓ transitioned: state=$($updated.state)" -ForegroundColor Green

# Events
$events = Invoke-RestMethod -Uri "$BaseUrl/content/$($item.id)/events" -Headers $headers
$eventTypes = @($events | ForEach-Object { $_.event_type })
Write-Host "✓ events: $($eventTypes -join ', ')" -ForegroundColor Green

Write-Host ""
Write-Host "SMOKE TEST PASSED" -ForegroundColor Green
