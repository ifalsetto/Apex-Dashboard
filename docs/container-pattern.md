# FalseTech Container Pattern

This is the first reusable container pattern for FalseTech app stacks. Apex Dashboard is the reference implementation. SimLay, local AI services, and automation workers should reuse the same shape unless they have a clear reason not to.

## Standard service layout

Every FalseTech service should define:

1. `Dockerfile` for the app runtime.
2. `docker-compose.yml` for local-first startup.
3. `.dockerignore` to keep secrets, local exports, caches, and generated data out of builds.
4. `.env.example` for safe optional configuration.
5. A persistent runtime data mount, usually `/data`.
6. A healthcheck that proves the app is actually serving traffic.
7. A README section with build, run, stop, logs, and reset commands.

## Runtime data rule

Do not write durable app state only inside the image layer. Use an environment variable to point state at `/data` inside the container.

For Apex Dashboard:

```env
APEX_DASHBOARD_DATA_DIR=/data
```

This keeps source code and runtime state separate:

- `/app` = code copied into the image.
- `/data` = user-generated snapshots, exports, autosaves, storage maps, scans, and temporary runtime files.

## Compose baseline

The baseline Compose service should include:

```yaml
services:
  app-name:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8501:8501"
    environment:
      APP_DATA_DIR: /data
    volumes:
      - app_data:/data

volumes:
  app_data:
```

Adjust the exposed port for non-Streamlit services.

## Healthcheck rule

Every app needs a container-level healthcheck. For Streamlit services, use:

```bash
http://127.0.0.1:8501/_stcore/health
```

For API workers, expose a lightweight `/health` route. For background-only workers, use a command that checks dependency connectivity and process readiness.

## Secret rule

Secrets must come from environment variables or local-only secret files. Never commit:

- `.env`
- `.env.*`
- `.streamlit/secrets.toml`
- API keys
- machine-specific diagnostics
- personal exports

Commit only `.env.example` with blank values.

## Transfer checklist for SimLay

When moving this pattern to SimLay:

1. Add `SIMLAY_DATA_DIR=/data` support.
2. Move inventory databases, image uploads, valuation reports, and export files under `/data`.
3. Keep source code under `/app`.
4. Add a Compose volume named `simlay_data`.
5. Add healthcheck coverage for the app page or API endpoint.
6. Add a smoke-test GitHub Action that builds the image and verifies health.

## Transfer checklist for local AI services

For local AI stacks:

1. Keep model files outside the image.
2. Mount models under `/models` and runtime state under `/data`.
3. Use GPU-specific Compose overrides only when required.
4. Keep CPU-only Compose as the default fallback where practical.
5. Add explicit resource notes for VRAM/RAM requirements.

## Transfer checklist for automation workers

For automation workers:

1. Use one worker process per service.
2. Mount durable run logs under `/data/logs`.
3. Mount queue state or local SQLite files under `/data`.
4. Add a healthcheck that verifies the worker can read config and reach required local services.
5. Keep job schedules outside the image when schedules change often.
