# k8s-platform-kafka Kafka and Flink tooling

Python utilities for a homelab Kafka learning environment. The repository contains a Kafka topic administration script, a Binance trade producer, and a PyFlink consumer for the resulting Kafka topic.

## Repository layout

```text
kafka_tools/ Kafka administration, producer, and consumer scripts
scripts/     Local validation and harness utilities
docs/        Architecture and agent-facing documentation
.github/     CI and consumer/producer image publishing workflows
```

## Kafka scripts

| File | Purpose |
|---|---|
| `kafka_tools/admin.py` | Connects with Kafka admin credentials and lists, creates, or deletes topics. |
The BTCUSDT producer image is built from
`kafka_tools/producer/btcusdt@trade/Dockerfile` using `kafka/` as the Docker
build context. Pull requests build the image without publishing it.
| `kafka_tools/consumer/btcusdt@trade/consumer.py` | Consumes the Binance trade topic with PyFlink. |

The consumer image is defined by
docker build -f kafka_tools/producer/btcusdt@trade/Dockerfile -t k8s-platform-kafka-btcusdt-producer kafka
installs Python 3.12.7 and `apache-flink==2.3.0`, adds the Kafka connector and
native S3 filesystem plugin, and copies the consumer job into the Flink image.

## Environment variables

- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_ADMIN_USERNAME` and `KAFKA_ADMIN_PASSWORD` — credentials used by the topic administration script.
- `KAFKA_USERNAME` — username used by the PyFlink consumer.
- `KAFKA_PASSWORD` — password used by the PyFlink consumer.
- `SCHEMA_REGISTRY_URL` — Schema Registry URL used by the Binance producer; defaults to `http://127.0.0.1:8081`.
- `KAFKA_BTCUSDT_TOPIC` — topic consumed by the PyFlink job.
- `R2_ENDPOINT` — required by the consumer; the current image uses the R2 endpoint baked into its Flink configuration.
- `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` — R2 credentials.
- `R2_PREFIX` — object key prefix; defaults to `btcusdt`.
The BTCUSDT consumer image is built from
`kafka_tools/consumer/btcusdt@trade/Dockerfile` using `kafka/` as the Docker
build context. Pull requests build the image without publishing it.
The producer and consumer use `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_USERNAME`, and
`KAFKA_PASSWORD`. The consumer also uses `KAFKA_BTCUSDT_TOPIC`. Set
`KAFKA_BOOTSTRAP_SERVERS` to the comma-separated broker list. Keep all
docker build -f kafka_tools/consumer/btcusdt@trade/Dockerfile -t k8s-platform-kafka-btcusdt-consumer kafka
image starts the producer automatically. The production consumer image does not
install or load `python-dotenv` and must not contain a
`.env` file. The consumer uses one shared R2 credential set for the fixed
`example-flink-data` and `example-flink-checkpoint` buckets.

## Local setup

```powershell
uv sync --locked --all-groups
uv run pre-commit install --hook-type commit-msg
```

Run the local tools with the repository environment, for example:

```powershell
uv run python kafka_tools/admin.py
uv run python kafka_tools/producer/btcusdt@trade/producer.py
```

The scripts and producer support modules perform setup at import time. Run the
entry-point scripts directly rather than importing them from tests or tooling.

## Validation

- `make compile`
- `make lint`
- `make check`
- `make drift`
- `make complexity`

`make check` currently runs the syntax compilation check. There is no automated
unit-test suite yet.

## Pull Requests

Pull Requests targeting `main` are validated by GitHub Actions in the root
workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). The workflow runs
separate build, test, and quality jobs:

- `build` runs `make compile`.
- `test` runs `make check`.
- `quality` runs `make lint`, `make drift`, and `make complexity`.

The workflows do not connect to Kafka or Binance. Pull Requests use the
template in [`.github/pull_request_template.md`](.github/pull_request_template.md)
and must document the checks performed and any post-merge action required.

## Producer image

The BTCUSDT producer image is built from
`kafka_tools/producer/btcusdt@trade/Dockerfile` using the repository root as
the Docker build context. Pull requests build the image without publishing it.
After a successful merge to `main`, GitHub Actions publishes
`ghcr.io/<owner>/<repository>-btcusdt-producer` with the commit SHA and `main`
tags.

Build it locally from the repository root:

```powershell
docker build -f kafka_tools/producer/btcusdt@trade/Dockerfile -t k8s-platform-kafka-btcusdt-producer .
```

The image starts `/app/producer.py` automatically. Provide
`KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_USERNAME`, `KAFKA_PASSWORD`, and
`SCHEMA_REGISTRY_URL` at runtime. The producer validates each Binance trade
record and serializes it through Schema Registry using the local `Trade` Avro
schema.

## Consumer image

The BTCUSDT consumer image is built from
`kafka_tools/consumer/btcusdt@trade/Dockerfile` using the repository root as
the Docker build context. Pull requests build the image without publishing it.
After a successful merge to `main`, GitHub Actions publishes the image to
GHCR with both the commit SHA and the `main` tag. The image name is derived from
the repository name as `ghcr.io/<owner>/<repository>-btcusdt-consumer`.

To build the image locally from the repository root:

```powershell
docker build -f kafka_tools/consumer/btcusdt@trade/Dockerfile -t k8s-platform-kafka-btcusdt-consumer .
```

The Dockerfile does not define an application command. Start the copied job
using the Flink runtime and provide the consumer environment variables at run
time. The consumer reads from the earliest available Kafka offset, remains
active for future records, and writes newline-delimited JSON files to R2
through Flink's native-S3 `FileSink`. Checkpoints run every 10 seconds and are
stored in `example-flink-checkpoint`; they allow completed files and recovery state
to be committed. Because R2 is external to Flink, this is not a formal
end-to-end exactly-once guarantee.
