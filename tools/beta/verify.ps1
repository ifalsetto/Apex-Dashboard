# FalseTech Apex Dashboard - Beta Verify
# Validates frontend typecheck/build plus local and Worker API reachability.

[CmdletBinding()]
param(
  [string]$BetaRoot = "C:\FalseTech\Beta\Apex Dashboard",
  [int]$Port = 5173,
  [string]$Player = "NotFalsetto",
  [string]$Platform = "origin",
  [string]$WorkerUrl = "https://falsetech-apex-tracker-proxy.falsetech-andrew.workers.dev"
)

$ErrorActionPreference = "Stop"
$frontend = Join-Path $BetaRoot "FalseTech-Apex-Trial\frontend"

if (-not (Test-Path (Join-Path $frontend "package.json"))) {
  throw "Frontend package.json not found. Run tools/beta/setup.ps1 first. Expected: $frontend"
}

Push-Location $frontend
npm run typecheck
npm run build
Pop-Location

Write-Host ""
Write-Host "Checking Worker health..."
try {
  $health = Invoke-RestMethod -Uri "$WorkerUrl/health" -Method Get
  $health | ConvertTo-Json -Depth 8
} catch {
  Write-Warning "Worker health check failed: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "Checking local dev server if it is running..."
try {
  $local = Invoke-WebRequest -Uri "http://localhost:$Port/" -UseBasicParsing -Method Head
  Write-Host "Local dashboard HTTP status: $($local.StatusCode) $($local.StatusDescription)" -ForegroundColor Green
} catch {
  Write-Warning "Local dashboard is not running on port $Port. Start it with tools/beta/run.ps1."
}

Write-Host ""
Write-Host "Checking API route through local Vite proxy if running..."
try {
  $url = "http://localhost:$Port/api/apex/search?platform=$Platform&query=$([uri]::EscapeDataString($Player))"
  $api = Invoke-RestMethod -Uri $url -Method Get
  $api | ConvertTo-Json -Depth 10
} catch {
  Write-Warning "Local API proxy check failed: $($_.Exception.Message)"
  Write-Warning "If the Worker returns FORBIDDEN, frontend routing is working and Tracker rejected the key/account access."
}
