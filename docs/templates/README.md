# FalseTech Container Templates

These templates are starting points for reusing the Apex Dashboard Docker pattern across FalseTech stacks.

## Template files

1. `streamlit-dockerfile` — Streamlit dashboard runtime.
2. `fastapi-dockerfile` — FastAPI service runtime.
3. `worker-dockerfile` — background worker runtime.
4. `simlay-compose-starter.yml` — SimLay UI/API/worker/PostgreSQL starter stack.
5. `local-ai-compose-starter.yml` — local AI API and worker starter stack.
6. `automation-worker-compose-starter.yml` — single worker starter stack.
7. `docker-smoke-test.yml` — GitHub Actions smoke-test starter.
8. `env-example-template.env` — safe `.env.example` starter.
9. `dockerignore-template` — runtime/secrets ignore starter.
10. `README-docker-section-template.md` — README Docker section starter.
11. `fastapi-healthcheck.py` — minimal API health route example.
12. `worker-healthcheck.py` — minimal worker healthcheck pattern.

## Copy rule

Copy templates into the target project, rename them to the standard names, then edit service names, ports, healthchecks, and environment variables.

Do not copy secrets, local data, exports, logs, SQLite databases, or model files into Git.
