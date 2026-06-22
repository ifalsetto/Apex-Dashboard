# FalseTech Apex Dashboard

This mixed repository contains:

- `FalseTech-Apex-Trial/frontend`: the current Vite + React command center
- `FalseTech-Apex-Trial/backend`: the secure Tracker.gg Worker proxy
- `apex_dashboard.py`: the legacy Streamlit dashboard

The Docker setup runs the React command center and its backend proxy. The Tracker key is injected into the backend container at runtime and is never included in frontend code or the frontend image.

## Docker

Requirements:

- Docker Desktop with the Linux engine running
- Ports `5173` and `8787` available

If a default port is already occupied, override it without changing container networking:

```powershell
$env:APEX_FRONTEND_PORT = "15173"
$env:APEX_BACKEND_PORT = "18787"
docker compose up -d
```

Create a local environment file only if Tracker integration is needed:

```powershell
Copy-Item .env.example .env
```

Leave `TRN_API_KEY` blank to run the dashboard with its existing preview/fallback data. If configured, the key remains server-side.

Build the images:

```powershell
docker compose build
```

Run with Compose:

```powershell
docker compose up -d
```

Open:

- Dashboard: `http://localhost:5173`
- Backend health: `http://127.0.0.1:8787/health`

Run the frontend image directly:

```powershell
docker build -t falsetech/apex-dashboard:local .
docker run --rm -p 5173:5173 falsetech/apex-dashboard:local
```

The direct frontend-only command does not start the backend. Use Compose for working `/api/apex/...` proxy routes.

View logs:

```powershell
docker compose logs --tail=100
docker compose logs -f
```

Rebuild after dependency or source changes:

```powershell
docker compose build --no-cache
docker compose up -d
```

Stop the stack without deleting images or source files:

```powershell
docker compose down
```

Do not add `-v` unless persistent volumes are intentionally disposable.

The backend keeps these server-side routes ready:

- `GET /api/apex/search`
- `GET /api/apex/profile/:platform/:player`
- `GET /api/apex/profile/:platform/:player/sessions`
- `GET /api/apex/profile/:platform/:player/segments/:segmentType`

## Legacy Streamlit Dashboard

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
