---
name: docker
description: Used when generating Dockerfiles, docker-compose configurations, or troubleshooting containerized environments.
---

## Boundaries

- Do not run `docker exec` without my explicit approval

## Image Construction

- **Optimization:** Default to multi-stage builds. Order layers strictly from least frequently changed (package managers, dependencies) to most frequently changed (source code) to maximize layer caching.
- **Base Images:** Prefer minimal, secure base images (e.g., `alpine`, `distroless`, or `-slim` variants) unless a full OS environment is explicitly requested.
- **Security:** Never run containerized applications as the `root` user. Always create, configure, and switch to a dedicated non-root user (`USER <username>`) before the final `CMD` or `ENTRYPOINT`.

## Docker Compose

- **IaC:** Always create or use a docker-compose.yml file. Never use `docker run`.
- **Reliability:** Always implement `healthcheck` blocks for foundational services (e.g., databases, message brokers). Use `depends_on` with `condition: service_healthy` to manage startup orchestration.
- **Environment Management:** Do not hardcode environment variables in the `docker-compose.yml`. Expect and use `.env` files or external secret injection.
- **Networking & Storage:** Define explicit named networks and volumes. Avoid relying on default/implicit networks for multi-service stacks. Prefer path-based volumes over using named volumes.

## Operations & Troubleshooting

- **Resource usage:** `docker stats`
- **Logs:** `docker compose logs -f -n 20` or `docker compose logs -f -n 20 | grep -iE "ERROR|WARNING|CRITICAL"`
- **Environment:** `docker inspect <id> --format '{{range .Config.Env}}{{println .}}{{end}}' | cut -d= -f1`. Do not use any command that will print out the environment variable values to my terminal, you are only concerned with the presence or absence of a variable. If you need to verify if a variable is set correctly ask me and I will answer with a yes or no.
- **Networking:** run `docknets` which generates a pretty printed report of subnets to investigate networking issues. You can also utilise `docker network inspect <network_name>`.
