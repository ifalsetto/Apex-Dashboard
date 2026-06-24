# Tracker.gg setup

## Purpose

This module adds Streamlit-native Apex player lookup using the Tracker.gg API.

## Required configuration

Set one of the following.

### `.streamlit/secrets.toml`

```toml
TRACKER_API_KEY = "your_tracker_api_key"
```

### Environment variable

```bash
set TRACKER_API_KEY=your_tracker_api_key
```

## Supported platforms

- `pc`
- `psn`
- `xbl`

## Fallback behavior

If the API key is missing, invalid, or the request fails:

- the app logs the error
- the UI keeps fallback data visible
- the app does not crash

## Safety note

This integration only requests public Tracker.gg profile data. It does not read game memory, inject code, automate input, or bypass anti-cheat systems.
