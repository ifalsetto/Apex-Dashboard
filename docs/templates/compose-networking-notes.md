# Compose Networking Notes

Docker Compose creates an internal network for services in the same stack.

Use service names as hostnames inside Compose:

```text
http://simlay-api:8000
postgresql://simlay:simlay@simlay-db:5432/simlay
http://local-ai-api:8000
```

Use localhost only from the host machine:

```text
http://localhost:8501
http://localhost:8000
http://localhost:8010
```

Rule:

1. Inside containers, call other services by Compose service name.
2. From Windows/browser/host, call published ports on localhost.
3. Do not use `127.0.0.1` inside one container to reach another container.
4. Healthchecks that check the same container can use `127.0.0.1`.
