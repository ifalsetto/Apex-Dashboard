$ErrorActionPreference = "Stop"

$RepoPath = "C:\FalseTech\Projects\Apex-Dashboard"

Write-Host ""
Write-Host "FalseTech Apex - Gaming Desktop Source Push" -ForegroundColor Cyan
Write-Host ""

if (!(Test-Path $RepoPath)) {
    Write-Host "ERROR: Repo path not found: $RepoPath" -ForegroundColor Red
    exit 1
}

Set-Location $RepoPath

if (!(Test-Path ".git")) {
    Write-Host "ERROR: This folder is not a Git repo." -ForegroundColor Red
    exit 1
}

if (!(Test-Path ".\.venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

.\.venv\Scripts\Activate.ps1

Write-Host "Installing/updating dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip

if (Test-Path ".\requirements.txt") {
    pip install -r .\requirements.txt
} else {
    pip install streamlit pandas psutil
}

Write-Host "Validating Python files..." -ForegroundColor Yellow

$FilesToCheck = @(
    ".\apex_dashboard.py",
    ".\apex_local_importer.py",
    ".\pages\08_System_Lab.py"
)

foreach ($file in $FilesToCheck) {
    if (Test-Path $file) {
        python -m py_compile $file
    }
}

Write-Host "Validating local importer functions..." -ForegroundColor Yellow
python -c "from apex_local_importer import collect_local_setup_settings, apply_setup_settings_to_profile, collect_local_network_settings, apply_network_settings_to_profile; print('importer validation passed')"

Write-Host ""
Write-Host "Git status:" -ForegroundColor Cyan
git status --short

$HasChanges = git status --porcelain

if ($HasChanges) {
    Write-Host ""
    Write-Host "Adding and committing changes..." -ForegroundColor Yellow

    git add .

    $CommitMessage = "Sync Apex Dashboard working gaming desktop version"

    git commit -m $CommitMessage

    Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
    git push
} else {
    Write-Host "No local changes to commit." -ForegroundColor Green
    git pull
    git push
}

Write-Host ""
Write-Host "Gaming desktop source is pushed/up to date." -ForegroundColor Green