# Container PR Checklist

Use this checklist before opening or merging a containerization PR.

## Required files

1. `Dockerfile`
2. `docker-compose.yml`
3. `.dockerignore`
4. `.env.example`
5. README Docker section
6. healthcheck route or healthcheck command
7. smoke-test workflow

## Required behavior

1. `docker compose config` succeeds.
2. `docker compose build` succeeds.
3. `docker compose up -d` starts services.
4. Healthcheck passes.
5. App works without optional secrets when fallback behavior is supported.
6. Runtime state persists after `docker compose down` and `docker compose up`.
7. Destructive reset is documented as `docker compose down -v`.
8. No secrets or generated runtime state are committed.

## Review focus

1. `/app` is source code only.
2. `/data` is durable runtime data.
3. `.env.example` contains blank safe keys only.
4. Healthcheck proves real service readiness.
5. README gives copy/paste commands.
