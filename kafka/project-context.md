# project-context.md

> AI context file — read this before writing any code in this repo.
> Updated: 2026-09-10

## System purpose

This repository contains small Python utilities for a homelab Kafka environment: one script administers topics, one streams Binance trade events into Kafka, and one consumes those events with PyFlink. The primary use is local experimentation and operational learning, with the consumer also packaged as a Flink Docker image.

## Bounded contexts

| Context | Responsibility |
|---|---|
| Kafka administration | Connect to the Kafka cluster with admin credentials, inspect topics, and create or delete topics. |
| Trade event ingestion | Consume live Binance WebSocket trade messages and publish them to a Kafka topic. |
| Trade event consumption | Read the Binance trade topic with PyFlink and batch decoded messages to Cloudflare R2. |
| Local developer setup | Run scripts from a local Python environment and avoid hardcoding credentials. |
| Container images | Build a Flink 2.3.0 consumer image and a Python 3.12 producer image for the Binance trade workflow. |

## Architecture

- **Pattern:** Script-based utilities with module-level setup and direct side effects.
- **Stack:** Python 3.12, `kafka-python`, `websocket-client`, and a Flink 2.3.0/PyFlink consumer image using the native S3 filesystem and `FileSink` for R2. Local utility dependencies remain managed by `uv` and currently pin PyFlink 2.2.1.
- **Persistence:** Consumer records are stored as rolling JSONL objects in Cloudflare R2. Flink checkpoints are stored separately in `example-flink-checkpoint`.
- **Messaging:** External Kafka cluster using `SASL_PLAINTEXT` with `SCRAM-SHA-512`; producer sends trade messages to `binance-btcusdt-trade`.
- **External input:** Binance WebSocket stream at `wss://stream.binance.com:9443/ws/btcusdt@trade`.
- **Consumer deployment:** Docker image based on Flink 2.3.0, built from the repository root with the per-consumer Dockerfile. Kafka and R2 credentials are injected through environment variables; dotenv is not installed in the image. The current R2 endpoint is baked into the image configuration.
- **Producer deployment:** A Python 3.12 image starts the producer script and receives Kafka credentials through environment variables.
- **CI/CD:** GitHub Actions compiles, checks, lints, and measures repository quality; dedicated workflows publish the consumer and producer images to GHCR on pushes to `main`.

## Key decisions

- **Environment-based secrets:** Kafka credentials and R2 credentials are loaded from environment variables. Local tooling may use `.env`, but the production consumer image does not install or load dotenv. The consumer image currently has a fixed R2 endpoint.
- **Direct Kafka publishing:** The producer writes raw WebSocket payloads directly into Kafka rather than normalizing them first, which keeps the ingestion path simple.
- **Single-purpose scripts:** Admin and producer responsibilities are split into separate files instead of a larger application structure.
- **Dedicated images:** The Flink consumer has its own Dockerfile and Kafka connector JARs; the producer has a separate lightweight Python image and workflow.
- **R2 FileSink:** The consumer reads Kafka from the earliest available offset, writes newline-delimited JSON files through Flink's native S3 `FileSink`, and enables 10-second checkpoints. Delivery remains at least once because R2 is external to Flink.

## Integrations

| System | Protocol | Contract location |
|---|---|---|
| Kafka cluster | Kafka wire protocol over SASL/PLAINTEXT | Environment variables in local runtime configuration |
| Cloudflare R2 | S3-compatible HTTPS API | R2 environment variables in runtime configuration |
| Binance market stream | WebSocket | In-code stream URL in `kafka_tools/producer/btcusdt@trade/producer.py` |
| Flink runtime | Flink/PyFlink | `kafka_tools/consumer/btcusdt@trade/consumer.py` and its Dockerfile |

## Coding conventions

- Keep secrets in environment variables only; do not commit `.env` content, copy it into the production image, or embed credentials in code.
- Prefer small, script-oriented changes over speculative framework setup unless the repo is intentionally being promoted into an application.
- Treat this repository as part of the broader homelab Kafka learning environment; avoid Kubernetes-specific Kafka changes here unless the repo purpose explicitly expands.
- Do not assume the consumer Docker image starts the job automatically; the producer image intentionally starts `/app/producer.py`.

## What to avoid

- Do not add TLS, SASL variants, schema tooling, or Kubernetes deployment logic unless the repo scope changes.
- Do not assume the Kafka scripts are safe to import without side effects; current modules connect or start work at import time.
- Do not widen the repo into a general Kafka platform project without first defining packaging, tests, and CI expectations.
