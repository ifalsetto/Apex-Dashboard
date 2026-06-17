 # PR Summary: Refactor Apex Optimizer Dashboard for Stability, Maintainability, and Safer Performance Logging

## Overview

This pull request refactors the Apex Optimizer Dashboard from a mostly monolithic Streamlit application into a more maintainable, modular structure.

The main goal is to preserve the existing dashboard behavior while improving code organization, safety, reliability, validation, and future scalability. The refactor introduces dedicated modules for configuration, logging, utilities, validation, and shared types. It also improves error handling around file operations, Windows monitoring helpers, profile autosave, storage scanning, and performance log generation.

This PR is not intended to redesign the entire UI or change the core product direction. It is focused on making the current app easier to maintain, safer to extend, and more stable during real use.

---

## Primary Goals

1. Split reusable logic out of the main Streamlit app.
2. Centralize configuration and path management.
3. Add safer logging and error handling.
4. Improve profile validation and typed data structure clarity.
5. Preserve public-safe defaults for Apex optimization.
6. Keep storage scanning scoped and user-safe.
7. Maintain backward compatibility with existing saved profiles, snapshots, exports, and autosave behavior.
8. Prepare the app for future AI coach, performance monitoring, and live data features.

---

## Key Changes

## 1. Modularized Core App Structure

The app now imports shared functionality from dedicated modules:

```python
from apex_config import config, Config
from apex_logging import setup_logging
from apex_utils import (...)
from apex_validation import validate_profile_structure, safe_int, safe_float
from apex_types import Profile, MonitorState, PerformanceLog
```

This reduces the amount of utility logic living directly inside `apex_dashboard.py`.

### Benefits

* Easier to debug.
* Easier to test individual helpers.
* Cleaner separation of responsibilities.
* Less risk when adding new dashboard features.
* More readable main app file.

---

## 2. Centralized Configuration

The PR introduces a config-driven structure for paths, app metadata, and storage locations.

Examples of centralized path values include:

```python
BASE_DIR
SNAP_DIR
SCAN_DIR
EXPORT_DIR
PROFILES_DIR
TEMPBIN_DIR
DAILY_TEMP_DIR
TRASHBIN_DIR
STORAGE_DIR
AUTOSAVE_PATH
```

These values now come from `apex_config`.

### Benefits

* Reduces duplicated path logic.
* Makes it easier to change folder structure later.
* Keeps path setup consistent across the app.
* Supports future expansion without hardcoding paths everywhere.

---

## 3. Improved Logging System

The app now initializes logging through:

```python
logger = setup_logging(config.DAILY_TEMP_DIR)
logger.info("Apex Dashboard started")
```

Logging is used throughout the app for safer exception handling.

### Areas improved with logging

* JSON save/load failures.
* PowerShell command failures.
* Ping failures.
* CPU sampling failures.
* OCR failures.
* PresentMon parsing failures.
* Storage scan failures.
* Trash cleanup failures.

### Benefits

* Easier troubleshooting.
* Better visibility into app failures.
* Cleaner debugging for beta testing.
* Less silent failure behavior.

---

## 4. Safer Profile Handling

The app now validates profile structure before loading autosaved data:

```python
loaded = safe_load_json(AUTOSAVE_PATH)
st.session_state.profile = loaded if loaded and validate_profile_structure(loaded) else deep_copy(DEFAULT_PROFILE)
```

### Benefits

* Prevents broken or malformed autosave files from crashing the app.
* Falls back to a known-good default profile.
* Protects user workflow during beta testing.
* Improves resilience after manual edits or corrupted saves.

---

## 5. Typed Data Structures

The refactor adds type imports for core dashboard objects:

```python
from apex_types import Profile, MonitorState, PerformanceLog
```

### Benefits

* Clearer expected shape for profiles.
* Safer future refactoring.
* Better editor support.
* Easier debugging when performance logs grow.
* Better foundation for future tests.

---

## 6. Public-Safe Default Profile Preserved

The dashboard still includes a safe default Apex competitive profile with:

* 240 Hz refresh target.
* 237 FPS cap target.
* HDR / Auto HDR options.
* G-SYNC enabled.
* V-Sync off.
* Reflex + Boost enabled.
* Public-safe hardware metadata.
* Sanitized export settings.
* Default launch options.
* Network note structure.

### Benefits

* Keeps current user experience intact.
* Avoids exposing private machine-specific data.
* Gives users a safe starting profile.
* Preserves Apex-focused optimization workflow.

---

## 7. Improved Helper Functions

Several helper functions are now cleaner and safer, including:

```python
load_index()
save_index()
save_unique_json()
build_launch_string()
bump_updated()
logs_to_csv_bytes()
hdr_method_label()
settings_signature()
```

### Improvements

* Better try/except handling.
* Logging on failure.
* Safer fallback values.
* Better type hints.
* More predictable app behavior.

---

## 8. Safer Windows Helper Behavior

The Windows helper section still supports:

* PowerShell command execution.
* Apex process detection.
* Foreground window detection.
* Apex CPU sampling.
* Ping sampling.

The refactor improves exception handling and logging around these operations.

### Current behavior

* `ps_run()` safely catches timeouts and general exceptions.
* `apex_process_running()` checks for `r5apex` / `r5apex.exe`.
* `get_foreground_window_info()` safely parses window/process data.
* `get_apex_cpu_pct_sample()` returns `0.0` on failure.
* `ping_sample()` returns `(None, None)` on timeout or error.

### Important note

The PR improves safety and error handling, but PowerShell polling and synchronous ping sampling may still need future optimization to reduce blocking behavior during live monitoring.

---

## 9. Match Monitor Improvements

The match monitor keeps the existing heuristic behavior:

* Detect whether Apex is running.
* Detect whether Apex is foreground.
* Track foreground/background streaks.
* Start match tracking after a configured foreground streak.
* End match tracking after Apex closes or background streak threshold is met.
* Sample CPU usage during active monitoring.
* Track CPU average and peak.

### Benefits

* Existing workflow remains intact.
* Safer state initialization.
* Better typed monitor state.
* Improved logging around failures.

---

## 10. Similar Match Comparison Preserved

The PR keeps the existing comparison workflow:

```python
find_similar_entries()
compare_vs_similar()
safe_metric_comparison()
```

The dashboard can still compare a new match against similar prior sessions using:

* settings signature
* HDR mode
* CPU average
* ping
* packet loss
* average FPS
* 1% low FPS

### Future improvement

For very large match histories, this should eventually be optimized with an indexed lookup instead of scanning all logs each time.

---

## 11. Auto Notes System Preserved

The auto notes template remains intact and continues to generate structured match summaries.

The notes include:

* App version.
* Refresh rate.
* FPS cap.
* VRR state.
* V-Sync state.
* Reflex state.
* HDR mode.
* Launch options.
* Match duration.
* CPU average and peak.
* Ping and packet loss.
* FPS metrics.
* Comparison to similar sessions.
* Suggested next steps.

### Benefits

* Keeps the dashboard useful as a learning tool.
* Helps users track what settings worked.
* Supports future AI coaching features.
* Gives match history more context.

---

## 12. Safe Trash System Preserved

The app continues to use a move-first cleanup model.

Instead of deleting files immediately, files are moved into a scoped trash folder first:

```python
safe_move_to_trash()
safe_empty_trash_today()
```

### Safety benefits

* Reduces accidental deletion risk.
* Limits cleanup scope.
* Uses a daily trash folder.
* Checks that deletion stays inside the expected trash path.
* Logs cleanup errors.

---

## 13. Storage Audit Safety Preserved

The storage scan remains scoped to known dashboard folders:

```python
SAFE_SCAN_PRESETS
```

The scan includes:

* Apex Dashboard root folder.
* Profiles.
* Snapshots.
* Scans.
* TempBin.
* Trash bin.

The storage audit counts files, file types, total bytes, newest modified date, oldest modified date, and whether the result was truncated.

### Safety controls

* No file contents are read.
* Scan scope is limited.
* Max file count is enforced.
* Results are written to JSON and CSV.
* Errors are logged instead of crashing the app.

---

## 14. OCR Optional Detection Preserved

The OCR feature remains optional and safe-off by default.

The app checks for OCR dependencies:

```python
pytesseract
PIL
mss
```

If dependencies are unavailable, the app reports that instead of failing.

### Benefits

* Optional feature does not break the app.
* Safer dependency handling.
* Maintains future expansion path for screen-based match detection.

---

## 15. PresentMon CSV Import Preserved

The dashboard continues to support optional FPS data import from PresentMon CSV files.

The parser supports:

* `FPS`
* `MsBetweenPresents`

It calculates:

* average FPS
* 1% low FPS
* sample count

### Benefits

* Keeps FPS analysis workflow intact.
* Allows external performance tools to feed the dashboard.
* Provides safer parsing with fallback errors.

---

## 16. Streamlit Session State Stability

The refactor preserves the existing Streamlit state flow:

```python
st.session_state.profile
st.session_state.monitor_state
st.session_state.scan_plan
st.session_state.storage_map
```

### Benefits

* Existing UI flow remains stable.
* Autosave still works.
* Monitor state persists during reruns.
* Storage scan state persists.
* Safe defaults are used when state is missing.

---

## 17. Autosave Behavior Preserved

The app still bumps the profile timestamp and autosaves at the end of the session:

```python
profile = bump_updated(profile)
st.session_state.profile = profile
safe_save_json(AUTOSAVE_PATH, st.session_state.profile)
```

### Benefits

* User changes remain saved.
* Existing autosave workflow is preserved.
* Backward compatibility is maintained.

---

# Files / Areas Impacted

## Main App

* `apex_dashboard.py`

## New / Refactored Support Modules

* `apex_config.py`
* `apex_logging.py`
* `apex_utils.py`
* `apex_validation.py`
* `apex_types.py`

## Runtime Data Areas

* Profiles
* Snapshots
* Scans
* Exports
* TempBin
* Trash Bin
* Storage audit outputs
* Autosave JSON

---

# Technical Impact

## Maintainability

This PR significantly improves maintainability by reducing the amount of repeated helper logic in the main app file.

## Reliability

More operations now fail safely instead of crashing the dashboard.

## Debuggability

Logging makes it easier to understand what failed and where.

## Safety

The refactor keeps destructive operations scoped and avoids unsafe cleanup behavior.

## Extensibility

The new module structure makes it easier to add:

* AI coaching.
* Tracker data integration.
* better performance monitoring.
* additional validation.
* test coverage.
* future frontend/backend separation.

---

# Performance Notes

This PR improves structure and reliability but does not fully eliminate every possible performance issue.

## Improved

* Safer exception handling.
* Better validation.
* Cleaner utility separation.
* More controlled storage scanning.
* Safer CSV and JSON handling paths.

## Still recommended for follow-up

1. Replace PowerShell CPU polling with `psutil`.
2. Add TTL caching for process and foreground checks.
3. Reduce or async-wrap ping sampling.
4. Add cached CSV export generation.
5. Index match logs by settings signature and HDR mode.
6. Add test coverage for large performance logs.
7. Add a Streamlit-safe background monitoring strategy.

---

# Risk Assessment

## Low Risk

* Config centralization.
* Logging setup.
* Utility extraction.
* Type hints.
* Safer validation.
* Storage scan safety improvements.

## Medium Risk

* Moving logic into modules may cause import issues if file paths or module names are wrong.
* Existing saved profiles must match expected structure.
* Streamlit rerun behavior should be tested carefully after modularization.

## High Risk Areas to Watch

* Windows PowerShell helper behavior.
* Match monitor timing.
* Autosave behavior.
* Any path migration from old folder constants to config-driven paths.

---

# Testing Checklist

## App Startup

* [ ] Run `streamlit run apex_dashboard.py`.
* [ ] Confirm dashboard loads without import errors.
* [ ] Confirm app title and version render correctly.
* [ ] Confirm sidebar links render correctly.

## Profile State

* [ ] Confirm autosave profile loads.
* [ ] Confirm invalid autosave falls back to default profile.
* [ ] Confirm profile changes save.
* [ ] Confirm `lastUpdatedISO` updates.

## Snapshots

* [ ] Save a snapshot.
* [ ] Confirm duplicate detection still works.
* [ ] Confirm snapshot file name uses safe slug output.
* [ ] Confirm index JSON updates.

## Match Monitor

* [ ] Start monitor with Apex closed.
* [ ] Start monitor with Apex running.
* [ ] Confirm foreground detection works.
* [ ] Confirm match start detection still works.
* [ ] Confirm match end detection still works.
* [ ] Confirm CPU sample list is populated.
* [ ] Confirm CPU average and peak are calculated.

## Network / Ping

* [ ] Confirm ping sampling returns values when network is available.
* [ ] Confirm timeout returns safe `None` values.
* [ ] Confirm ping failure does not crash the app.

## Match History

* [ ] Confirm match logs display.
* [ ] Confirm CSV export works.
* [ ] Confirm comparison to similar sessions still works.
* [ ] Confirm auto notes are generated.

## Storage Audit

* [ ] Confirm safe scan presets point to dashboard folders.
* [ ] Confirm scan does not read file contents.
* [ ] Confirm scan truncates at max file count.
* [ ] Confirm JSON and CSV outputs are written.

## Trash System

* [ ] Move file to trash.
* [ ] Confirm file goes to today’s trash folder.
* [ ] Empty today’s trash.
* [ ] Confirm deletion is scoped to trash folder only.

## OCR Optional

* [ ] Confirm app handles missing OCR dependencies.
* [ ] Confirm OCR demo does not crash if unavailable.
* [ ] Confirm OCR errors are logged safely.

## PresentMon Import

* [ ] Upload valid PresentMon CSV.
* [ ] Confirm average FPS calculates.
* [ ] Confirm 1% low calculates.
* [ ] Confirm invalid CSV returns safe error.

---

# Security / Safety Notes

This PR does not introduce unsafe Apex behavior.

The app should continue to avoid:

* cheats
* macros
* recoil scripts
* memory reading
* injection
* anti-cheat bypasses
* credential exposure
* frontend API key exposure
* aggressive Windows service disabling

The dashboard remains focused on legitimate performance tracking, profile management, safe storage auditing, and settings documentation.

---

# Backward Compatibility

This refactor is designed to preserve backward compatibility with existing:

* profiles
* autosave data
* snapshots
* exported logs
* storage audit outputs
* match logs
* launch option structure
* network notes
* privacy settings

Any incompatible saved profile should be handled through validation and fallback to the default profile.

---

# Known Limitations

1. The uploaded refactor appears to show the major structure and helper logic, but the full UI tabs may still need final integration testing.
2. PowerShell-based monitoring may still be heavier than ideal.
3. Match comparison still uses list scanning unless a separate indexing patch is added.
4. CSV export may still need Streamlit caching.
5. Ping sampling may still need a non-blocking implementation.
6. More automated tests should be added.

---

# Recommended Follow-Up PRs

## Follow-Up PR 1: Performance Monitor Optimization

* Replace PowerShell CPU checks with `psutil`.
* Add TTL cache for monitor helper calls.
* Reduce blocking ping behavior.
* Add non-blocking monitor sampling.

## Follow-Up PR 2: Match History Scaling

* Index logs by settings signature and HDR mode.
* Cache CSV export.
* Add pagination or filtering for large histories.

## Follow-Up PR 3: Test Coverage

* Add unit tests for utilities.
* Add validation tests.
* Add PresentMon parser tests.
* Add storage audit tests.
* Add profile hash / duplicate detection tests.

## Follow-Up PR 4: AI Coach Integration

* Add OpenAI-powered coaching as an optional feature.
* Keep API key server-side / secrets-only.
* Use saved profile and latest match logs as context.
* Save generated reports locally.

---

# Reviewer Notes

Please focus review on:

1. Import/module correctness.
2. Streamlit session state behavior.
3. Autosave compatibility.
4. Folder/path compatibility.
5. Safe handling of malformed saved profiles.
6. Match monitor behavior.
7. Storage scan scope.
8. Whether any previous UI behavior was accidentally dropped.

This refactor should be treated as an architecture and stability PR, not a visual redesign.
