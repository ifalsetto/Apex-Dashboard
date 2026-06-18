# Apex Dashboard (BETA)

Beta release for testing and bug reports.

## How to run locally

```bash
pip install -r requirements.txt
streamlit run apex_dashboard.py
```

## New beta page

This branch adds a Streamlit page at:

```txt
pages/Live_Tracker_AI_Coach.py
```

Streamlit automatically surfaces files inside `pages/` in the app navigation.

## Optional secrets / environment variables

Tracker.gg player search and the AI coach are optional. The app still runs without either key.

### Streamlit secrets

Create `.streamlit/secrets.toml`:

```toml
TRACKER_API_KEY = "your_tracker_api_key"
OPENAI_API_KEY = "your_openai_api_key"
```

### Or environment variables

- `TRACKER_API_KEY`
- `OPENAI_API_KEY`

## Fallback behavior

- If Tracker.gg is unavailable or the API key is missing/invalid, the live page keeps fallback data visible and logs the error.
- If the OpenAI API is unavailable or the key is missing, the app generates a local coaching fallback report instead of failing.
- Existing autosave, match logging, and storage audit behavior stay intact.

## Safety boundaries

This project is for legitimate dashboarding, settings management, performance review, and public stats lookup only.

It does **not** include:

- cheats
- macros
- recoil scripts
- process memory reading
- anti-cheat bypasses
- input automation
- credential exposure

## Manual testing checklist

- Start the app with `streamlit run apex_dashboard.py`.
- Open the `Live Tracker AI Coach` page.
- Verify the app still loads with no API keys configured.
- Verify Tracker search works with a valid API key.
- Verify Tracker search failure keeps fallback data visible.
- Verify invalid Tracker API key does not crash the app.
- Verify the AI coach produces a local fallback report without an OpenAI key.
- Verify existing match logs still load.
- Verify no API key is committed to the repository.

## Report a bug

Open a GitHub issue and include:

- what you clicked
- what you expected
- what happened
- screenshot if possible
