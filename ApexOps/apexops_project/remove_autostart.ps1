# Removes the ApexOps collector auto-start scheduled task.

$taskName = "ApexOpsCollector"
schtasks /Delete /F /TN $taskName | Out-Null
Write-Host "Removed scheduled task: $taskName" -ForegroundColor Green
