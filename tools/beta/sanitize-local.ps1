# FalseTech Apex Dashboard - Local Sanitizer
# Removes generated/cached local artifacts. Preview by default; use -Apply to remove.

[CmdletBinding()]
param(
  [string]$RepoRoot = "C:\FalseTech\Beta\Apex Dashboard",
  [switch]$Apply,
  [switch]$IncludeLocalEnv
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $RepoRoot)) {
  throw "Repo root not found: $RepoRoot"
}

$patterns = @(
  "**/node_modules",
  "**/dist",
  "**/build",
  "**/.vite",
  "**/.vite-temp",
  "**/.wrangler",
  "**/LocalRepairBackup_*",
  "**/*.before-*",
  "**/*.before-*.*",
  "**/*.log"
)

if ($IncludeLocalEnv) {
  $patterns += @("**/.env.local", "**/.env.*.local")
}

$targets = foreach ($pattern in $patterns) {
  Get-ChildItem -Path $RepoRoot -Recurse -Force -ErrorAction SilentlyContinue -Include ($pattern -replace '^\*\*/', '')
}

$targets = $targets | Sort-Object FullName -Unique

if (-not $targets) {
  Write-Host "No local artifacts matched. Repo is already clean." -ForegroundColor Green
  return
}

Write-Host "Matched local artifacts:"
$targets | ForEach-Object { Write-Host "  $($_.FullName)" }

if (-not $Apply) {
  Write-Host ""
  Write-Host "Preview only. Re-run with -Apply to remove these artifacts." -ForegroundColor Yellow
  return
}

foreach ($target in $targets) {
  Remove-Item -Path $target.FullName -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Local artifacts removed." -ForegroundColor Green
