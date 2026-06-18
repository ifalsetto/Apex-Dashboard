# Apex Dashboard (BETA)

Beta release for testing, bug reports, and safe Apex Legends performance review.

This project is for legitimate dashboarding, settings management, performance tracking, public stats lookup, and AI-assisted coaching summaries.

---

## How to run locally

```bash
pip install -r requirements.txt
streamlit run apex_dashboard.py
```

---

## Streamlit pages

This app includes Streamlit pages inside the `pages/` folder.

Current beta page:

```txt
pages/Live_Tracker_AI_Coach.py
```

Streamlit automatically surfaces files inside `pages/` in the app navigation.

---

## Optional secrets / environment variables

Tracker.gg player search and the AI coach are optional.

The app still runs without either key.

### Streamlit secrets

Create:

```txt
.streamlit/secrets.toml
```

Example:

```toml
TRACKER_API_KEY = "your_tracker_api_key"
OPENAI_API_KEY = "your_openai_api_key"
```

### Environment variables

You can also use:

```txt
TRACKER_API_KEY
OPENAI_API_KEY
```

---

## Fallback behavior

- If Tracker.gg is unavailable or the API key is missing/invalid, the live page keeps fallback data visible and logs the error.
- If the OpenAI API is unavailable or the key is missing, the app generates a local coaching fallback report instead of failing.
- Existing autosave, match logging, profile management, and storage audit behavior remain intact.

---

## Safety boundaries

This project does **not** include or support:

- cheats
- macros
- recoil scripts
- process memory reading
- anti-cheat bypasses
- input automation
- credential exposure
- unsafe API key exposure

The dashboard is designed for safe optimization, documentation, review, and learning.

---

## Manual testing checklist

Before reporting a bug, test the following:

- Start the app with `streamlit run apex_dashboard.py`.
- Confirm the main dashboard loads.
- Open the `Live Tracker AI Coach` page.
- Verify the app loads with no API keys configured.
- Verify Tracker search works with a valid Tracker API key.
- Verify Tracker search failure keeps fallback data visible.
- Verify an invalid Tracker API key does not crash the app.
- Verify the AI coach produces a local fallback report without an OpenAI key.
- Verify existing match logs still load.
- Verify no API keys are committed to the repository.

---

## Beta testing: how to report bugs

1. Open the app and reproduce the issue once.
2. Click **Report a bug** in the sidebar, if available.
3. Include:
   - app version shown in the sidebar
   - what you clicked
   - steps to reproduce
   - what you expected
   - what actually happened
   - screenshot, if possible

If the in-app bug report button is unavailable, open a GitHub issue and include the same details.

---

## Recommended issue format

```md
## What I clicked

## What I expected

## What happened

## Steps to reproduce

1.
2.
3.

## Screenshot

## Notes
```

---

## Status

This is a beta dashboard. Expect active changes, bug fixes, and feature updates.
