# FalseTech Container Pattern

This is the reusable container pattern for FalseTech app stacks. Apex Dashboard is the reference implementation. SimLay, local AI services, and automation workers should reuse this shape unless they have a clear reason not to.

## 1. Reference implementation status

Apex Dashboard is the baseline implementation.

Current Apex container contract:

1. `Dockerfile` builds the Streamlit runtime image.
2. `docker-compose.yml` starts the local-first app stack.
3. `.dockerignore` keeps secrets, caches, logs, local exports, runtime databases, and generated state out of the build context.
4. `.env.example` exposes safe blank configuration.
5. `/app` contains source code.
6. `/data` contains durable runtime state.
7. A container healthcheck verifies Streamlit is serving traffic.
8. README documents build, run, logs, stop, reset, secrets, and manual validation.

## 2. Standard service layout

Every FalseTech service should define:

1. `Dockerfile` for the service runtime.
2. `docker-compose.yml` for local-first startup.
3. `.dockerignore` to keep secrets, local exports, caches, and generated data out of builds.
4. `.env.example` for safe optional configuration.
5. A persistent runtime data mount, usually `/data`.
6. A healthcheck that proves the service is actually ready.
7. A README section with build, run, stop, logs, reset, and validation commands.
8. A smoke-test workflow that builds the image and checks service health.

## 3. Filesystem contract

Do not write durable app state only inside the image layer. Source code and runtime data must stay separate.

Standard paths:

```text
/app      source code copied into the image
/data     durable app state, exports, uploads, snapshots, reports, local DBs, logs
/models   local AI model files, only for model-serving services
/config   optional mounted config files when config should change without rebuilding
```

Apex Dashboard uses:

```env
APEX_DASHBOARD_DATA_DIR=/data
```

Future services should use equivalent service-specific variables:

```env
SIMLAY_DATA_DIR=/data
FALSETECH_AI_DATA_DIR=/data
FALSETECH_WORKER_DATA_DIR=/data
```

## 4. Compose baseline

The minimum service shape is:

```yaml
services:
  app-name:
    build:
      context: .
      dockerfile: Dockerfile
    image: falsetech/app-name:local
    restart: unless-stopped
    ports:
      - "8501:8501"
    environment:
      APP_DATA_DIR: /data
    volumes:
      - app_data:/data
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5).read()"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

volumes:
  app_data:
```

Adjust the port and healthcheck for non-Streamlit services.

## 5. Healthcheck rules

Every service needs a container-level healthcheck.

| Service type | Healthcheck target |
| --- | --- |
| Streamlit dashboard | `http://127.0.0.1:8501/_stcore/health` |
| FastAPI API | `http://127.0.0.1:8000/health` |
| Database-backed service | API health route that checks DB connectivity |
| Worker service | Command that verifies config, queue access, and required local service reachability |
| Local AI service | `GET /health` or model-server readiness endpoint |

For APIs, add a real route like:

```python
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

## 6. Secret rule

Secrets must come from environment variables or local-only secret files.

Never commit:

1. `.env`
2. `.env.*`
3. `.streamlit/secrets.toml`
4. API keys
5. machine-specific diagnostics
6. personal exports
7. local SQLite databases unless they are sanitized fixtures
8. model weights or paid/private data files

Commit only `.env.example` with blank values.

## 7. SimLay container blueprint

SimLay should become the next stack after Apex.

Recommended services:

```text
simlay-ui       dashboard for inventory review and valuation workflow
simlay-api      FastAPI backend for units, items, comps, reports, and scoring
simlay-db       PostgreSQL durable database
simlay-worker   background processor for image analysis, comp lookup, report generation
```

Recommended Compose starter:

```yaml
services:
  simlay-ui:
    build:
      context: ./ui
      dockerfile: Dockerfile
    image: falsetech/simlay-ui:local
    restart: unless-stopped
    ports:
      - "8502:8501"
    environment:
      SIMLAY_DATA_DIR: /data
      SIMLAY_API_URL: http://simlay-api:8000
    volumes:
      - simlay_data:/data
    depends_on:
      simlay-api:
        condition: service_healthy

  simlay-api:
    build:
      context: ./api
      dockerfile: Dockerfile
    image: falsetech/simlay-api:local
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      SIMLAY_DATA_DIR: /data
      DATABASE_URL: postgresql://simlay:simlay@simlay-db:5432/simlay
    volumes:
      - simlay_data:/data
    depends_on:
      simlay-db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

  simlay-worker:
    build:
      context: ./worker
      dockerfile: Dockerfile
    image: falsetech/simlay-worker:local
    restart: unless-stopped
    environment:
      SIMLAY_DATA_DIR: /data
      DATABASE_URL: postgresql://simlay:simlay@simlay-db:5432/simlay
      SIMLAY_API_URL: http://simlay-api:8000
    volumes:
      - simlay_data:/data
    depends_on:
      simlay-api:
        condition: service_healthy

  simlay-db:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_DB: simlay
      POSTGRES_USER: simlay
      POSTGRES_PASSWORD: simlay
    volumes:
      - simlay_db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U simlay -d simlay"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  simlay_data:
  simlay_db:
```

Recommended SimLay `.env.example`:

```env
SIMLAY_DATA_DIR=/data
DATABASE_URL=postgresql://simlay:simlay@simlay-db:5432/simlay
OPENAI_API_KEY=
EBAY_APP_ID=
EBAY_CERT_ID=
EBAY_DEV_ID=
FACEBOOK_ACCESS_TOKEN=
```

SimLay migration checklist:

1. Add `SIMLAY_DATA_DIR=/data` support.
2. Move inventory databases, image uploads, valuation reports, exports, scan results, and generated listing drafts under `/data`.
3. Keep source code under `/app` inside each image.
4. Add a Compose volume named `simlay_data`.
5. Add a database volume named `simlay_db` if PostgreSQL is used.
6. Add `/health` to the API.
7. Add smoke-test workflow coverage for `docker compose config`, image build, service startup, and API health.
8. Document run, logs, stop, reset, and backup commands in README.

## 8. Local AI services blueprint

Local AI services should not bake model files into application images.

Recommended layout:

```text
local-ai-api       model gateway or inference API
local-ai-vector    vector database, optional
local-ai-worker    embedding / analysis / report job worker
/models            mounted model files
/data              runtime state and generated outputs
```

Recommended Compose shape:

```yaml
services:
  local-ai-api:
    build:
      context: ./ai-api
      dockerfile: Dockerfile
    image: falsetech/local-ai-api:local
    restart: unless-stopped
    ports:
      - "8010:8000"
    environment:
      FALSETECH_AI_DATA_DIR: /data
      FALSETECH_MODEL_DIR: /models
    volumes:
      - local_ai_data:/data
      - ./models:/models:ro
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s

  local-ai-worker:
    build:
      context: ./ai-worker
      dockerfile: Dockerfile
    image: falsetech/local-ai-worker:local
    restart: unless-stopped
    environment:
      FALSETECH_AI_DATA_DIR: /data
      FALSETECH_AI_API_URL: http://local-ai-api:8000
    volumes:
      - local_ai_data:/data
    depends_on:
      local-ai-api:
        condition: service_healthy

volumes:
  local_ai_data:
```

Local AI checklist:

1. Keep model files outside images.
2. Mount models under `/models`.
3. Mount generated outputs, logs, vector indexes, and cache state under `/data`.
4. Use GPU-specific Compose overrides only when needed.
5. Keep CPU-only Compose as the default fallback when practical.
6. Document VRAM/RAM requirements clearly.
7. Add a healthcheck that confirms the service can load config and answer a lightweight request.

## 9. Automation worker blueprint

Automation workers should be separate services instead of hidden background loops inside dashboards.

Recommended layout:

```text
worker-name/
  Dockerfile
  requirements.txt
  worker.py
  README.md
```

Recommended Compose shape:

```yaml
services:
  resale-scan-worker:
    build:
      context: ./workers/resale-scan
      dockerfile: Dockerfile
    image: falsetech/resale-scan-worker:local
    restart: unless-stopped
    environment:
      FALSETECH_WORKER_DATA_DIR: /data
      WORKER_CONFIG_PATH: /config/worker.env
    volumes:
      - worker_data:/data
      - ./config:/config:ro
    healthcheck:
      test: ["CMD", "python", "worker.py", "--healthcheck"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s

volumes:
  worker_data:
```

Worker checklist:

1. Use one worker process per service.
2. Store durable run logs under `/data/logs`.
3. Store queue state or local SQLite files under `/data`.
4. Keep job schedules outside the image when schedules change often.
5. Add `--healthcheck` or equivalent lightweight readiness command.
6. Do not bake credentials, schedules, or personal target lists into the image.
7. Add log commands to README.

## 10. GitHub Actions smoke-test baseline

Each containerized app should have a workflow with this minimum shape:

```yaml
name: Docker Smoke Test

on:
  pull_request:
  push:
    branches: [main]

jobs:
  docker-smoke-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate Compose config
        run: docker compose config
      - name: Build images
        run: docker compose build
      - name: Start stack
        run: docker compose up -d
      - name: Check running containers
        run: docker compose ps
      - name: Stop stack
        if: always()
        run: docker compose down -v
```

For a dashboard or API, add a curl or Python healthcheck step after startup.

## 11. README acceptance checklist

Every FalseTech container README should include:

1. Prerequisites.
2. `.env.example` copy command.
3. Build/start command.
4. Local URL.
5. Logs command.
6. Stop command.
7. Reset command.
8. Runtime data explanation.
9. Secrets warning.
10. Manual validation checklist.
11. Troubleshooting notes.

Minimum commands:

```bash
cp .env.example .env
docker compose config
docker compose up --build
docker compose logs -f <service-name>
docker compose down
docker compose down -v
```

## 12. Backup and reset rules

Use named volumes for durable app data. Before destructive resets, export or back up important data.

Inspection commands:

```bash
docker volume ls
docker compose ps
docker compose logs -f
```

Destructive reset:

```bash
docker compose down -v
```

Only use `down -v` when intentionally deleting local container state.

## 13. Transfer decision rule

A FalseTech app is ready to reuse this pattern when all of these are true:

1. It runs with `docker compose up --build`.
2. It serves a dashboard, API, or worker healthcheck successfully.
3. It stores durable data under `/data`, not inside `/app`.
4. It has a safe `.env.example`.
5. It ignores local secrets and runtime state in `.dockerignore`.
6. It documents setup and validation in README.
7. CI can build the image and verify health.

If any item is missing, treat the app as not container-ready yet.
