# FalseTech Container Next Steps

Use this checklist after Apex Dashboard is running cleanly with Docker.

## 1. Apex verification

Run:

```bash
cp .env.example .env
docker compose config
docker compose up --build
```

Open:

```text
http://localhost:8501
```

Validate:

1. Main dashboard loads.
2. Live Tracker AI Coach page opens.
3. App runs without API keys.
4. Optional API keys work when present.
5. Exports and generated files persist after:

```bash
docker compose down
docker compose up
```

6. Full reset only happens when intentionally running:

```bash
docker compose down -v
```

## 2. SimLay first container section

Start with the API and data contract before building extra services.

Target first PR for SimLay:

1. Add `SIMLAY_DATA_DIR=/data` support.
2. Add a FastAPI `/health` route.
3. Add `Dockerfile` for the API.
4. Add `docker-compose.yml` with API and PostgreSQL.
5. Add `.dockerignore` and `.env.example`.
6. Add README Docker section.
7. Add GitHub Actions smoke test.

Acceptance:

```bash
docker compose config
docker compose up --build
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

## 3. Local AI services second section

Do not put models inside images.

First target:

1. Add local AI API container.
2. Mount `./models:/models:ro`.
3. Mount named volume to `/data`.
4. Expose `/health`.
5. Document CPU fallback and GPU override separately.

## 4. Automation worker third section

Workers should not live inside dashboard apps.

First target:

1. One worker per service.
2. Logs under `/data/logs`.
3. Queue or SQLite state under `/data`.
4. `python worker.py --healthcheck` readiness command.
5. Config mounted from `/config`, not baked into the image.

## 5. Stop condition

A stack is not ready until it has:

1. Dockerfile.
2. Compose file.
3. `.dockerignore`.
4. `.env.example`.
5. Persistent `/data` storage.
6. Healthcheck.
7. README runbook.
8. Smoke test.
