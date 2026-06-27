## Run with Docker Compose

Use Docker Compose for the cleanest local-first setup.

```bash
cp .env.example .env
docker compose config
docker compose up --build
```

Open the app at:

```text
http://localhost:<port>
```

View logs:

```bash
docker compose logs -f <service-name>
```

Stop the stack:

```bash
docker compose down
```

Reset local container data only when you intentionally want a clean state:

```bash
docker compose down -v
```

## Runtime data

Docker runs store generated runtime state under `/data` inside the container. The Compose file maps `/data` to a named volume so data survives container rebuilds and normal restarts.

## Manual validation

1. `docker compose config` succeeds.
2. `docker compose up --build` starts the stack.
3. The app or API healthcheck passes.
4. The app works with blank optional secrets where fallback behavior is supported.
5. Generated files persist after `docker compose down` followed by `docker compose up`.
6. No secrets, `.env` files, generated exports, logs, local databases, or machine-specific diagnostics are committed.
