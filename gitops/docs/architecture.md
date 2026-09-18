> Accurate as of 2026-09-10. Update when the codebase changes significantly.

# Architecture

## Purpose

This repository defines desired Kubernetes state for a homelab environment through ArgoCD-managed GitOps.

## Components

| Component | Responsibility |
|---|---|
| `bootstrap/root-app.yaml` | Bootstraps ArgoCD with a root `Application` that watches this repository. |
| `applications/<name>.yaml` | Application definitions discovered directly by the root application. |
| `values/<domain>/` | Domain-specific Helm values referenced by applications. |
| `docs/<domain>/` | Domain-specific architecture and operation documentation. |
| `applications/longhorn.yaml` | Argo CD Application for Longhorn. |
| `values/storage/longhorn.yaml` | Longhorn V1 configuration for the dedicated storage worker disks. |
| `applications/kube-prometheus-stack.yaml` | Argo CD Application for the in-cluster monitoring stack. |
| `values/monitoring/kube-prometheus-stack.yaml` | Prometheus, Alertmanager, and Grafana persistence and discovery configuration. |
| `applications/flink-operator.yaml` | Argo CD Application for the Flink Kubernetes Operator. |
| `values/flink/operator.yaml` | Flink Operator namespace, resource, and baseline configuration. |
| `applications/btcusdt-producer.yaml` | Argo CD Application for the raw BTCUSDT producer manifests. |
| `manifests/kafka/btcusdt-producer/producer.yaml` | Kubernetes Deployment for the containerized producer in the `flink` namespace. |
| `applications/kafka-ui.yaml` | Argo CD Application for Kafka UI and its raw resources. |
| `manifests/kafka/kafka-ui/` | Raw Kubernetes resources for Kafka UI. |
| `applications/schema-registry.yaml` | Argo CD Application for the external-Kafka-backed Schema Registry chart. |
| `charts/schema-registry/` | Helm chart for the in-cluster Schema Registry Deployment and Service. |
| `values/kafka/schema-registry.yaml` | Schema Registry image, external Kafka, SASL, and resource values. |
| `applications/kafka-monitoring.yaml` | Argo CD Application for broker metrics scraping. |
| `manifests/monitoring/kafka/` | Raw monitoring resources for the external Kafka brokers. |

## Control flow

1. ArgoCD applies `bootstrap/root-app.yaml` to register the root application.
2. The root application discovers each Application manifest directly under `applications/`.
3. An Application can resolve an external Helm chart and values from this repository.
4. ArgoCD syncs each Application into its target namespace according to repo state.
5. Raw-manifest Applications use a directory under `manifests/` instead of a Helm chart.

## Current state

- The bootstrap manifest exists and is valid YAML.
- Longhorn deploys to `longhorn-system`.
- Longhorn uses the official chart at version `1.12.1`, V1 data engine, and two replicas.
- Default Longhorn disks are created only on explicitly labelled storage workers.
- The Ansible component owns the `monitoring/grafana-admin-credentials` Secret; its value is supplied through protected deployment input.
- kube-prometheus-stack deploys to `monitoring` with persistent Prometheus, Alertmanager, and Grafana instances.
- The Flink Kubernetes Operator deploys to `flink-operator` and watches Flink resources in the dedicated `flink` namespace. Kafka remains external to Kubernetes.
- The `btcusdt-producer` Application deploys a raw Kubernetes Deployment to `flink` using the published producer image. It starts with zero replicas and uses the externally managed `kafka-flink-credentials` and `ghcr-pull-secret` Secrets.
- Schema Registry deploys to `schema-registry` from the local Helm chart, uses `confluentinc/cp-schema-registry:8.1.1`, and connects directly to the external Kafka brokers through SASL/SCRAM. Its `schema-registry-kafka-credentials` Secret is external to Git and must contain the Kafka JAAS configuration.
- Its node-exporter DaemonSet and kube-proxy scrape are disabled because Ansible owns the host exporter and Cilium replaces kube-proxy.
- GitHub Actions validates build, lint, Argo CD rendering, and unit-test jobs.

## Operational implications

- Repo structure matters: the `spec.source.path` in `bootstrap/root-app.yaml` must continue to resolve to a real directory.
- Applications are placed directly under `applications/`; domain grouping remains in `values/<domain>/` and `docs/<domain>/`.
