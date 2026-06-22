# Backup and Reset Runbook

Use this before destructive Docker cleanup.

## Inspect running stack

```bash
docker compose ps
docker compose logs -f
```

## List local volumes

```bash
docker volume ls
```

## Stop without deleting data

```bash
docker compose down
```

## Destructive reset

This deletes named volumes for the current Compose project.

```bash
docker compose down -v
```

Only run destructive reset when you intentionally want to remove local runtime data.

## Pattern rule

1. Generated state belongs in `/data`.
2. Docker named volumes preserve `/data` across normal container rebuilds.
3. `docker compose down` preserves named volumes.
4. `docker compose down -v` deletes named volumes.
