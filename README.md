# Apex Dashboard (BETA)

Streamlit Apex Dashboard for legitimate Apex Legends settings management, performance review, public stats lookup, match logging, and AI-assisted coaching.

## Status

Beta release for testing and bug reports.

## Run with Docker Compose

Use this path for the cleanest local-first setup.

```bash
cp .env.example .env
# Optional: edit .env and add TRACKER_API_KEY / OPENAI_API_KEY

docker compose up --build
```

Open the app at:

```txt
http://localhost:8501
```

Stop the app:

```bash
docker compose down
```

View logs:

```bash
docker compose logs -f apex-dashboard
```

Reset local container data only when you intentionally want a clean state:

```bash
docker compose down -v
```

## Run with Docker only

```bash
docker build -t apex-dashboard:local .
docker run --rm -p 8501:8501 \
  -e APEX_DASHBOARD_DATA_DIR=/data \
  -v apex_dashboard_data:/data \
  apex-dashboard:local
```

## Run locally without Docker

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run apex_dashboard.py
```

## Runtime data

By default, local non-Docker runs store app data beside the source files for backward compatibility.

Docker runs set:

```env
APEX_DASHBOARD_DATA_DIR=/data
```

That keeps generated runtime state in the Compose volume instead of inside the image. The persistent data includes snapshots, scans, exports, profiles, temp files, trash-bin files, storage maps, `profile_index.json`, and `profile_autosave.json`.

## Optional secrets / environment variables

Tracker.gg player search and the AI coach are optional. The app still runs without either key.

### Docker / environment variables

Copy `.env.example` to `.env` and fill only the keys you use:

```env
TRACKER_API_KEY=
OPENAI_API_KEY=
```

### Streamlit secrets

For non-Docker Streamlit usage, create `.streamlit/secrets.toml`:

```toml
TRACKER_API_KEY = "your_tracker_api_key"
OPENAI_API_KEY = "your_openai_api_key"
```

Never commit `.env` or `.streamlit/secrets.toml`.

## Pages

The app includes the Streamlit page:

```txt
pages/Live_Tracker_AI_Coach.py
```

Streamlit automatically surfaces files inside `pages/` in the app navigation.

## Fallback behavior

- If Tracker.gg is unavailable or the API key is missing/invalid, the live page keeps fallback data visible and logs the error.
- If the OpenAI API is unavailable or the key is missing, the app generates a local coaching fallback report instead of failing.
- Existing autosave, match logging, and storage audit behavior stay intact.

## Docker validation

This repo includes a Docker smoke-test workflow that:

1. Validates the Compose config.
2. Builds the Docker image.
3. Starts the Streamlit container.
4. Checks Streamlit health at `/_stcore/health`.

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

- Start the app with `docker compose up --build`.
- Open `http://localhost:8501`.
- Verify the main dashboard loads with no API keys configured.
- Open the `Live Tracker AI Coach` page.
- Verify the app still loads with no API keys configured.
- Verify Tracker search works with a valid API key.
- Verify Tracker search failure keeps fallback data visible.
- Verify invalid Tracker API key does not crash the app.
- Verify the AI coach produces a local fallback report without an OpenAI key.
- Verify existing match logs still load.
- Verify generated snapshots/exports persist after `docker compose down` and a second `docker compose up`.
- Verify no API key is committed to the repository.

## Reusable FalseTech container pattern

See [`docs/container-pattern.md`](docs/container-pattern.md) for the repeatable pattern to reuse across SimLay, local AI services, and automation workers.

## Report a bug

Open a GitHub issue and include:

- what you clicked
- what you expected
- what happened
- screenshot if possible
