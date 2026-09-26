# AGENTS.md

## Project context

- [`project-context.md`](./project-context.md) — read this first: system purpose, boundaries, integrations, and constraints
- [`docs/INDEX.md`](./docs/INDEX.md) — map of all documentation

## Development commands

| Command | What it does |
|---|---|
| `make setup` | Install runtime and developer dependencies, then install the Conventional Commit hook |
| `make compile` | Syntax-compile repository Python files without triggering network side effects |
| `make lint` | Run Ruff checks separately from hooks and from `make check` |
| `make check` | Required local validation; currently runs `compile` because no automated unit tests are defined |
| `make format` | Auto-format Python files with Ruff |
| `make drift` | Verify required harness files exist and documentation links still resolve |
| `make complexity` | Run Radon cyclomatic complexity checks on repository Python sources |
| `make validate-commit-msg MSG="feat: add topic helper"` | Validate Conventional Commit format |
| `make agent-validate MSG="feat: add topic helper"` | Agent pre-commit gate: validate message format, then compile |

## Agent validation protocol

1. Run `make agent-validate MSG="<type>: <summary>"`.
2. Commit with the same message and include a descriptive body.
3. Run `make check` before pushing.

## Repo notes

- `kafka_tools/admin.py` and `kafka_tools/producer/btcusdt@trade/producer.py` execute work at module import time; avoid importing them from tests or tooling that expects side-effect-free modules.
- `kafka_tools/consumer/btcusdt@trade/consumer.py` is a PyFlink job. Its Docker image is built from `kafka_tools/consumer/btcusdt@trade/Dockerfile` with the repository root as the build context.
- The consumer image uses Flink 2.3.0, Python 3.12.7, and the Kafka connector JARs tracked under `kafka_tools/jars/`. Local development dependencies still pin `apache-flink==2.2.1`.
- The admin script uses `KAFKA_ADMIN_USERNAME` and `KAFKA_ADMIN_PASSWORD`; the producer and consumer use `KAFKA_USERNAME` and `KAFKA_PASSWORD`. The consumer also requires `KAFKA_BTCUSDT_TOPIC`.
- Secrets live in local environment variables loaded from `.env`; never commit that file.
- This repository is part of a homelab Kafka learning environment and is intentionally lightweight; avoid adding Kubernetes deployment or broader cluster orchestration concerns here.

## Current runtime notes

- The consumer image uses the Flink 2.3.0 base image, Python 3.12.7, and the Kafka connector JARs tracked under `kafka_tools/jars/`.
- The producer image starts automatically and uses `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_USERNAME`, and `KAFKA_PASSWORD`; the consumer also uses `KAFKA_BTCUSDT_TOPIC`.

## CI backstop

- Authoritative backstop: GitHub Actions via `.github/workflows/ci.yml`.
- `.github/workflows/docker-consumer.yml` builds the BTCUSDT consumer image on pull requests and publishes it to GHCR after a successful push to `main`; `.github/workflows/docker-producer.yml` does the same for the producer image.
- `build` runs `make compile`, `test` runs `make check`, and `quality` runs `make lint`, `make drift`, and `make complexity`.
- Jenkins is not configured for this repository today.
- Pull Requests use `.github/pull_request_template.md` and must include validation evidence and post-merge instructions.

## Active sensors

- Drift: `make drift` verifies required harness files exist and that documentation links resolve.
- Complexity: `make complexity` fails if any repository Python file exceeds Radon grade B.
- Coverage: not configured yet because the repository has no automated tests. Add tests before choosing a coverage threshold.

## Org-standard commands not yet defined

- `make infra`
- `make run`
- `make build`
- `make unit-tests`
- `make integration-tests`
- `make clean`
