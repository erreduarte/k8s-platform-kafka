# project-context.md

> AI context file — read this before writing any code in this repo.
> Updated: 2026-09-10

## System purpose

This repository stores GitOps configuration for a homelab Kubernetes environment managed through ArgoCD. The current bootstrap flow is centered on a root ArgoCD application that points ArgoCD at the `applications/` directory for managed workloads.

## Bounded contexts

| Context | Responsibility |
|---|---|
| bootstrap | Owns the initial ArgoCD root application definition used to connect the cluster to this repo. |
| applications | Argo CD Application manifests directly discovered by the root app. |
| values | Per-domain Helm values referenced by Argo CD applications. |
| storage | Longhorn distributed block storage; host-level prerequisites remain in the Ansible component. |
| security and secrets | Secret references and security-related notes; secret values are owned by external automation. |
| monitoring | In-cluster Prometheus, Alertmanager, Grafana, and Prometheus Operator configuration. |
| flink | Flink Kubernetes Operator, the managed BTCUSDT PyFlink consumer, and the BTCUSDT producer Deployment. |

## Architecture

- **Pattern:** GitOps repository for ArgoCD with a root-app bootstrap pattern
- **Stack:** YAML manifests; ArgoCD `Application` custom resources
- **Persistence:** Git is the source of truth for desired cluster state
- **Messaging:** Kafka is external to Kubernetes; Kafka UI, monitoring, and the BTCUSDT producer are managed here as supporting workloads.
- **Deployment:** ArgoCD watches this GitHub repository and syncs resources from `applications/` into the cluster; GitHub Actions validates repository manifests on pushes and pull requests

## Key decisions

- **Longhorn storage:** `applications/longhorn.yaml` installs the pinned Longhorn chart with `values/storage/longhorn.yaml`. It uses V1, two replicas, and the dedicated `/var/lib/longhorn` disks on labelled workers.
- **Grafana credentials:** The Ansible component creates `monitoring/grafana-admin-credentials` from a protected deployment input. GitOps keeps only the Secret name reference in Grafana values.
- **Cluster monitoring:** `applications/kube-prometheus-stack.yaml` installs the pinned kube-prometheus-stack chart with Longhorn-backed Prometheus, Alertmanager, and Grafana state. The chart node-exporter is disabled because the Ansible component owns the host exporters.
- **Kafka:** Dedicated VMs run the Kafka broker/controller infrastructure. The Terraform component owns their hardware and the Ansible component owns host/runtime configuration and JMX exporter. This repository deploys Kafka UI and configures Prometheus to scrape broker metrics; no Kafka broker runs in Kubernetes.
- **Flink:** The Flink Kubernetes Operator tracks Apache's `release-1.16.0-rc3` chart from Git because the stable `1.15.0` CRD rejects `v2_3`. It watches the `flink` namespace, where the `btcusdt-consumer` `FlinkDeployment` runs the published Flink 2.3 PyFlink image. Kafka remains external, and the consumer uses Cloudflare R2 for checkpoints and processed data.
- **BTCUSDT producer:** The `btcusdt-producer` Argo CD Application applies a raw Kubernetes `Deployment` in the `flink` namespace. It currently uses `ghcr.io/example-org/k8s-platform-kafka-btcusdt-producer:main`, consumes `flink/kafka-flink-credentials`, and starts with `replicas: 0` until explicitly enabled. Use an immutable image tag or digest before long-lived operation.
- **Repository-first desired state:** Operational changes should be represented as committed manifests rather than ad hoc cluster edits. `[inferred — verify with team]`
- **GitHub Actions as initial CI backstop:** build, lint, Argo CD rendering, and unit-test jobs run in GitHub-hosted CI before expanding to any additional pipeline.

## Integrations

| System | Protocol | Contract location |
|---|---|---|
| ArgoCD | Kubernetes CRD sync from Git | `bootstrap/root-app.yaml` |
| GitHub | Git repository source for manifests | `bootstrap/root-app.yaml` |
| Kubernetes API | ArgoCD destination cluster | `bootstrap/root-app.yaml` |

## Coding conventions

- Keep Argo CD Application manifests directly under `applications/` so their graph nodes are named after the deployed service.
- Applications may reference Helm charts or raw manifests under `manifests/<domain>/<service>/`; document the operational contract for either style.
- Keep bootstrap concerns in `bootstrap/`, Applications in `applications/`, values in `values/<domain>/`, and domain runbooks in `docs/<domain>/`.
- When repo intent is not obvious from the manifests, document it in `docs/` rather than leaving structure implicit.

## What to avoid

- Do not place host-level Longhorn configuration in GitOps; the Ansible component owns disks, packages, services, and mounts.
- Do not commit application secrets or generated Kubernetes Secrets that contain them.
- Do not introduce CI, hook logic, or formatting rules that depend on tools unavailable in a clean developer environment.
- Do not repurpose `bootstrap/root-app.yaml` for workload-specific configuration.
