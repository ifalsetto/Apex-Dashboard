# ApexOps (Free) – FPS/Frametime + Settings Snapshot Dashboard

Goal:
- Automatically log frame capture results (CapFrameX) **together with** the Apex config + your sync-chain profile.
- Compare runs over time and “lock in” the best settings.

What it does (free):
- Watches `Documents\CapFrameX\Captures` for new captures.
- On each new capture it:
  - Extracts frametime metrics (Avg FPS, 1% low, 0.1% low, stutter%, etc.)
  - Snapshots Apex config files (`videoconfig.txt`, `settings.cfg` if present)
  - Logs current Windows display mode (resolution + refresh Hz)
  - Logs GPU driver version (if query works)
  - Stores everything in a local SQLite DB
- Provides a local dashboard (Streamlit) to filter/compare sessions.

## Install (Windows)

### 1) Put this folder here
Recommended:
`C:\FalseTech\1-Apex\ApexOps\`

### 2) Create a Python virtual environment
Open PowerShell in the ApexOps folder:

```powershell
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3) Run the collector (the "bot")
```powershell
.\.venv\Scripts\python -m apexops.collector
```
Leave it running while you play / test.

### 4) Run the dashboard
In a second PowerShell window:

```powershell
.\.venv\Scripts\streamlit run apexops\dashboard.py
```

Dashboard opens at:
`http://localhost:8501`

## CapFrameX setup
- Captures must land in: `Documents\CapFrameX\Captures` (default).
- If you use a different location, change it in `config.yaml`.

## Notes / limitations
- NVCP settings are not reliably readable without extra tooling. ApexOps logs:
  - Your **declared** NVCP settings from `config.yaml`
  - The **actual** Windows resolution/refresh Hz (to catch a 225Hz ceiling)
  - The **actual** Apex config values from files
- Apex match stats (kills/damage) are not available via an official free local API.
  - Use the dashboard “Match Log” page to quickly enter them manually.

## Files
- `config.yaml`: your live profile settings + paths
- `apexops.db`: local database (safe to back up)
