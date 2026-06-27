# FalseTech Apex Dashboard - Beta Run
# Starts the frontend dev server for live beta use while Apex is running.

[CmdletBinding()]
param(
  [string]$BetaRoot = "C:\FalseTech\Beta\Apex Dashboard",
  [int]$Port = 5173,
  [switch]$KillExisting
)

$ErrorActionPreference = "Stop"
$frontend = Join-Path $BetaRoot "FalseTech-Apex-Trial\frontend"

if (-not (Test-Path (Join-Path $frontend "package.json"))) {
  throw "Frontend package.json not found. Run tools/beta/setup.ps1 first. Expected: $frontend"
}

$connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($connections) {
  $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
  if (-not $KillExisting) {
    throw "Port $Port is already in use by PID(s): $($pids -join ', '). Re-run with -KillExisting or close that process."
  }

  foreach ($pid in $pids) {
    Write-Host "Stopping PID $pid on port $Port"
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
  }
}

Push-Location $frontend

if (-not (Test-Path ".\.env.local")) {
  Write-Warning ".env.local is missing. Creating default beta frontend config."
  @"
VITE_AUTH0_DOMAIN=dev-kuqkupxwt56gfcvx.us.auth0.com
VITE_AUTH0_CLIENT_ID=OHH82ZXxE9RvO3WQpSIG0IbDzHgp6Bcr
VITE_AUTH0_REDIRECT_URI=http://localhost:5173/
VITE_AUTH0_LOGOUT_URI=http://localhost:5173/
VITE_API_BASE_URL=https://falsetech-apex-tracker-proxy.falsetech-andrew.workers.dev
"@ | Set-Content .env.local -Encoding utf8
}

Write-Host "Starting Apex Dashboard beta at http://localhost:$Port/" -ForegroundColor Green
Write-Host "Leave this PowerShell window open while playing Apex. Press Ctrl+C to stop."

npm run dev -- --host localhost --port $Port --strictPort

Pop-Location
