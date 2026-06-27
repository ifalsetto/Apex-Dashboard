# FalseTech Apex Dashboard - Beta Setup
# Creates a clean beta checkout, installs dependencies, writes public frontend config, and validates the app.

[CmdletBinding()]
param(
  [string]$RepoUrl = "https://github.com/ifalsetto/Apex-Dashboard.git",
  [string]$BetaRoot = "C:\FalseTech\Beta\Apex Dashboard",
  [string]$ApiBaseUrl = "https://falsetech-apex-tracker-proxy.falsetech-andrew.workers.dev",
  [string]$Auth0Domain = "dev-kuqkupxwt56gfcvx.us.auth0.com",
  [string]$Auth0ClientId = "OHH82ZXxE9RvO3WQpSIG0IbDzHgp6Bcr",
  [switch]$Fresh
)

$ErrorActionPreference = "Stop"

function Require-Command {
  param([Parameter(Mandatory = $true)][string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command '$Name' was not found in PATH. Install it, reopen PowerShell, and retry."
  }
}

Require-Command git
Require-Command node
Require-Command npm

if ($Fresh -and (Test-Path $BetaRoot)) {
  $archive = "$BetaRoot.archive.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
  Write-Host "Archiving existing beta folder to: $archive"
  Rename-Item -Path $BetaRoot -NewName (Split-Path $archive -Leaf)
}

if (-not (Test-Path $BetaRoot)) {
  New-Item -ItemType Directory -Force (Split-Path $BetaRoot -Parent) | Out-Null
  git clone $RepoUrl $BetaRoot
} else {
  Write-Host "Using existing beta checkout: $BetaRoot"
  Push-Location $BetaRoot
  git fetch origin
  git switch main
  git pull --ff-only origin main
  Pop-Location
}

$frontend = Join-Path $BetaRoot "FalseTech-Apex-Trial\frontend"
if (-not (Test-Path (Join-Path $frontend "package.json"))) {
  throw "Frontend package.json not found at $frontend"
}

Push-Location $frontend

$envText = @"
VITE_AUTH0_DOMAIN=$Auth0Domain
VITE_AUTH0_CLIENT_ID=$Auth0ClientId
VITE_AUTH0_REDIRECT_URI=http://localhost:5173/
VITE_AUTH0_LOGOUT_URI=http://localhost:5173/
VITE_API_BASE_URL=$ApiBaseUrl
"@

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $frontend ".env.local"), $envText, $utf8NoBom)

Remove-Item -Recurse -Force ".\node_modules\.vite" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".\node_modules\.vite-temp" -ErrorAction SilentlyContinue

if (Test-Path ".\package-lock.json") {
  npm ci
} else {
  npm install
}

npm run typecheck
npm run build

Pop-Location

Write-Host ""
Write-Host "Beta setup complete." -ForegroundColor Green
Write-Host "Run:"
Write-Host "  cd '$frontend'"
Write-Host "  npm run dev"
Write-Host "Open: http://localhost:5173/"
