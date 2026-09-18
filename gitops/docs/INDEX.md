# Documentation Index

> Navigation map for AI agents and developers.
> Read this to find the right document — then read that document.
> Updated: 2026-09-10

## Core context

| File | What it covers |
|---|---|
| [`project-context.md`](../project-context.md) | System purpose, bounded contexts, integrations, and repo-specific conventions |
| [`README.md`](../README.md) | Short project overview |
| [`AGENTS.md`](../AGENTS.md) | Agent workflow, validation commands, and harness expectations |

## Architecture & design

| File | What it covers |
|---|---|
| [`docs/architecture.md`](./architecture.md) | Root-app GitOps flow, component responsibilities, and current repository state |
| [`docs/storage/longhorn.md`](./storage/longhorn.md) | Longhorn configuration, storage-node prerequisite, and verification runbook |
| [`docs/monitoring/kube-prometheus-stack.md`](./monitoring/kube-prometheus-stack.md) | In-cluster monitoring stack configuration, ownership boundary, and verification runbook |
| [`docs/kafka/kafka-ui.md`](./kafka/kafka-ui.md) | Kafka UI, external broker metrics, and the BTCUSDT producer integration |
| [`docs/kafka/schema-registry.md`](./kafka/schema-registry.md) | Confluent Schema Registry backed by the external Kafka cluster |
| [`docs/flink/operator.md`](./flink/operator.md) | Flink Kubernetes Operator installation, BTCUSDT consumer and producer rollout, boundaries, and verification |

## Operations

| File | What it covers |
|---|---|
| [`docs/operations.md`](./operations.md) | Repository layout, expected authoring workflow, and current operational gaps |
