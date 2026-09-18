# Architecture

> Accurate as of 2026-09-10. Update when the codebase changes significantly.

## Overview

This repository is a lightweight script-based workflow for interacting with a
homelab Kafka cluster. It administers topics, ingests live Binance trades, and
consumes the resulting topic with PyFlink. Kafka brokers and the Flink runtime
are external to the Python source tree; the consumer can be packaged as a
Docker image for execution with Flink.

## Components

| Component | Responsibility | External dependency |
|---|---|---|
| `kafka_tools/admin.py` | Creates a `KafkaAdminClient`, lists topics, and exposes helper functions to create or delete topics. | Kafka cluster |
| `kafka_tools/producer/btcusdt@trade/producer.py` | Opens a Binance trade WebSocket and forwards raw messages to Kafka. | Binance WebSocket, Kafka cluster |
| `kafka_tools/consumer/btcusdt@trade/consumer.py` | Reads Binance trade messages using PyFlink and uploads JSONL batches to Cloudflare R2. | Flink runtime, Kafka cluster, Cloudflare R2 |
| `kafka_tools/consumer/btcusdt@trade/Dockerfile` | Builds a Flink 2.3.0 image containing the PyFlink job, Kafka connector JARs, and the native S3 filesystem plugin. | Docker, Flink, Java Kafka and S3 connectors |
| `kafka_tools/producer/btcusdt@trade/Dockerfile` | Builds a Python 3.12 image that starts the Binance trade producer. | Docker, Kafka, Binance WebSocket |
| Runtime environment | Supplies Kafka and R2 endpoints and credentials without embedding secrets in the image. | Deployment-managed environment |

## Runtime flow

1. `kafka_tools/producer/btcusdt@trade/producer.py` loads Kafka connection settings from environment variables.
2. The script opens the Binance `btcusdt@trade` WebSocket stream.
3. Each WebSocket message is encoded as UTF-8 and published directly to the `binance-btcusdt-trade` Kafka topic.
4. `kafka_tools/admin.py` uses separate admin credentials to inspect or mutate topic state.
5. `kafka_tools/consumer/btcusdt@trade/consumer.py` reads the configured topic from the earliest available Kafka offset with a PyFlink `KafkaSource`, continues waiting for future records, and writes rolling JSONL objects to R2 through the native S3 `FileSink`.

## Configuration boundaries

- Kafka credentials, R2 credentials, and topic configuration come from environment variables, not tracked source files. The consumer image currently keeps the R2 endpoint in its Flink configuration, although `R2_ENDPOINT` is still validated by the job.
- The production consumer image does not install or load `python-dotenv`; provide all Kafka and R2 settings through the runtime environment.
- The scripts currently perform client initialization at module load time, so importing them has side effects.
- The repository uses `uv` for dependency and environment management. `uv.lock` is committed for reproducible installs.
- GitHub Actions validates Python sources and quality sensors on pull requests and pushes to `main`.
- A separate GitHub Actions workflow builds the consumer image on relevant pull requests and publishes it to GHCR after a successful push to `main`.
- There is no automated unit-test suite; `make check` currently performs compilation.
- The consumer image includes the Flink job but leaves the runtime command to the deployment environment.
- The FileSink writes checkpoint-aware rolling files to
	`s3://example-flink-data/<prefix>`. Checkpoints run every 10 seconds and are
	stored at `s3://example-flink-checkpoint/flink-checkpoints`. One shared R2
	credential set has read/write access to both buckets. Unfinished files are
	rolled back after a restart. R2 is
	external to Flink, so the pipeline does not claim formal end-to-end exactly-once
	delivery.

## Risks and constraints

- Because module import starts work immediately, future tests or tooling should avoid importing these files directly without refactoring.
- The producer forwards raw Binance payloads unchanged, so any downstream schema guarantees must be handled outside this repository.
- The producer and consumer use the shared `KAFKA_USERNAME` and `KAFKA_PASSWORD` credential names; deployment configuration must provide them explicitly.
- This repo is intentionally scoped to local Kafka experimentation; broader orchestration concerns belong in the surrounding homelab repositories.
