# Apex Dashboard Project Status

## Current Master Path

C:\FalseTech\Projects\Apex-Dashboard

## Do Not Use As Master

C:\Users\andre\Desktop\FalseTech\Apex-Dashboard

## Current Architecture

Streamlit app with modular support files.

## Core Files

- apex_dashboard.py
- apex_config.py
- apex_logging.py
- apex_utils.py
- apex_validation.py
- apex_types.py
- apex_local_importer.py
- pages/08_System_Lab.py

## Verified Working Commands

cd "C:\FalseTech\Projects\Apex-Dashboard"
.\.venv\Scripts\Activate.ps1
python -m py_compile .\apex_local_importer.py .\pages\08_System_Lab.py .\apex_dashboard.py
python -c "from apex_local_importer import collect_local_setup_settings, apply_setup_settings_to_profile, collect_local_network_settings, apply_network_settings_to_profile; print('all importer functions loaded')"
python -m streamlit run .\apex_dashboard.py

## Current Features

- Modular config
- Logging
- Profile validation
- Safe autosave
- Local setup importer
- Local network importer
- System Lab page
- Match monitor
- Ping sampling
- CPU sampling
- PresentMon CSV import
- Storage audit
- Safe trash
- Optional OCR detection
- Tracker integration plan
- Local-first repo path standard

## Current Known Issues

- Desktop copy may be stale.
- Avoid nested repo/submodule confusion.
- PowerShell polling should eventually be replaced or reduced with psutil.
- Match history should eventually be indexed.
- Streamlit background monitoring needs a cleaner long-term strategy.
- Cloudflare/Wrangler .wrangler state files should not be committed.

## Operating Rule

Use C:\FalseTech\Projects\Apex-Dashboard as the master repo on both gaming and dev desktops.
