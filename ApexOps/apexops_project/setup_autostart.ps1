# Creates a user logon scheduled task to start ApexOps collector automatically.
# Run in PowerShell (no admin required in most setups).

$taskName = "ApexOpsCollector"
$batPath = Join-Path $PSScriptRoot "run_collector.bat"

if (!(Test-Path $batPath)) {
  Write-Host "Missing: $batPath" -ForegroundColor Red
  exit 1
}

$tr = '"' + $batPath + '"'

schtasks /Create /F /TN $taskName /SC ONLOGON /RL LIMITED /TR $tr | Out-Null
Write-Host "Created scheduled task: $taskName" -ForegroundColor Green
Write-Host "To remove: run remove_autostart.ps1" -ForegroundColor Yellow
