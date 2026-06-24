$ErrorActionPreference = "Stop"

$RepoPath = "C:\FalseTech\Projects\Apex-Dashboard"
$AppFile = "apex_dashboard.py"

Write-Host ""
Write-Host "FalseTech Apex Dashboard Launcher" -ForegroundColor Cyan
Write-Host "Repo: $RepoPath" -ForegroundColor DarkGray
Write-Host ""

if (!(Test-Path $RepoPath)) {
    Write-Host "ERROR: Repo path not found: $RepoPath" -ForegroundColor Red
    exit 1
}

Set-Location $RepoPath

if (!(Test-Path ".\$AppFile")) {
    Write-Host "ERROR: $AppFile not found in $RepoPath" -ForegroundColor Red
    exit 1
}

if (!(Test-Path ".\.venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

if (Test-Path ".\requirements.txt") {
    Write-Host "Installing repo requirements..." -ForegroundColor Yellow
    pip install -r .\requirements.txt
} else {
    Write-Host "No requirements.txt found. Installing core packages..." -ForegroundColor Yellow
    pip install streamlit pandas psutil
}

Write-Host "Validating app imports..." -ForegroundColor Yellow
python -m py_compile .\apex_local_importer.py .\pages\08_System_Lab.py .\apex_dashboard.py

Write-Host "Validating local importer functions..." -ForegroundColor Yellow
python -c "from apex_local_importer import collect_local_setup_settings, apply_setup_settings_to_profile, collect_local_network_settings, apply_network_settings_to_profile; print('all importer functions loaded')"

Write-Host ""
Write-Host "Starting Apex Dashboard..." -ForegroundColor Green
Write-Host "Local URL: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""

python -m streamlit run .\apex_dashboard.py