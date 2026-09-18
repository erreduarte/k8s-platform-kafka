# k8s-platform-kafka

`k8s-platform-kafka` is a small, end-to-end Data Platform and Platform
Engineering project. It demonstrates how to provision a homelab platform,
run Kubernetes workloads, stream event data through Kafka, process it with
Flink, and make the whole system observable and repeatable.

The example data flow uses live [BTCUSDT trade events](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/ws-streams/~?lang=python). A producer publishes
events to Kafka, a Flink job consumes them and writes newline-delimited files
to S3-compatible object storage, and Prometheus monitors the platform and
Kafka brokers. The goal is not to provide a production exchange or trading
system; it is to show clear platform boundaries, infrastructure automation,
deployment workflows, and operational thinking.

## What this repository does

This is a monorepo containing the infrastructure and application delivery
needed for the complete demonstration:

| Directory | Role in the solution |
|---|---|
| `terraform/` | Defines the Proxmox virtual machines and templates. |
| `ansible/` | Configures the guest operating systems, Kubernetes hosts, Kafka hosts, and supporting services. |
| `gitops/` | Defines the Kubernetes desired state consumed by Argo CD. |
| `kafka/` | Contains Kafka administration tools, the BTCUSDT producer, and the PyFlink consumer image. |
| `docs/` | Provides cross-domain documentation and project boundaries. |

The repository is the source of truth for infrastructure and deployment
configuration. Kafka brokers run on dedicated virtual machines outside
Kubernetes. Kubernetes runs the supporting platform services and workloads,
including Kafka UI, monitoring, the producer, and the Flink operator and job.

## Main technologies

| Technology | Purpose |
|---|---|
| Terraform | Creates and manages the virtual machine infrastructure. |
| Ansible | Configures operating systems and installs platform services on hosts. |
| Kubernetes | Runs the application and platform workloads. |
| Argo CD | Continuously applies the GitOps configuration from this repository. |
| Apache Kafka | Provides the durable event stream between the producer and consumer. |
| Apache Flink | Consumes Kafka events, checkpoints processing state, and writes output files. |
| Prometheus and Grafana | Collect and visualize application, broker, and Kubernetes metrics. |
| Kafka UI | Provides a visual way to inspect Kafka clusters and topics. |
| GitHub Actions | Compiles, tests, lint-checks, and builds the producer and consumer images. |

## Architecture and data flow

The control plane is GitOps-driven: Argo CD reads the Kubernetes manifests and
Helm values in `gitops/` and reconciles them with the cluster. Runtime data
flows separately from the configuration repository.

```text
HOMELAB
  |
  +-- k8s-platform-kafka public monorepo
          |
          +-- Repository domains
          |   +-- terraform/  -> Proxmox VM definitions
          |   +-- ansible/    -> host and guest configuration
          |   +-- gitops/     -> Argo CD Applications and Kubernetes manifests
          |   `-- kafka/      -> admin tools, producer, and PyFlink consumer
          |
          +-- Proxmox: virtual machine infrastructure
          |   |
          |   +-- Kafka VMs (external to Kubernetes)
          |   |   +-- kafka01: Kafka broker/controller + JMX scraper (:9404)
          |   |   +-- kafka02: Kafka broker/controller + JMX scraper (:9404)
          |   |   `-- kafka03: Kafka broker/controller + JMX scraper (:9404)
          |   |
          |   `-- Kubernetes VMs
          |       +-- cp01: control plane
          |       +-- w01: worker + dedicated 100 GiB Longhorn disk
          |       `-- w02: worker + dedicated 100 GiB Longhorn disk
          |
          +-- Ansible: server and guest configuration
          |   +-- Kafka server roles: Kafka 4.3.1, KRaft, data disks, JMX exporter
          |   `-- Kubernetes node roles: container runtime, Cilium, and Longhorn disks
          |
          +-- Argo CD: Kubernetes desired state from gitops/
          |   |
          |   +-- Longhorn: V1 storage, 2 replicas, 100 GiB dedicated per worker
          |   +-- Monitoring: Prometheus, Alertmanager, Grafana, and ScrapeConfigs
          |   +-- Kafka UI: broker and topic operations
          |   +-- Schema Registry: 1 replica and the _schemas topic
          |   `-- flink namespace
          |       +-- Flink Kubernetes Operator
          |       +-- FlinkDeployment: btcusdt-consumer
          |       `-- BTCUSDT producer Deployment: replicas 0 by default
          |
          `-- Runtime data flow
                  Binance BTCUSDT WebSocket
                          |
                          v
                  BTCUSDT producer Deployment
                  (enabled explicitly to control free-tier usage)
                          |
                          v
                  Kafka topic: binance-btcusdt-trade
                          |
                          v
                  Flink 2.3 PyFlink consumer
                          |\
                          | +--> Cloudflare R2: rolling JSONL FileSink output
                          `----> R2 checkpoint storage: recovery state every 10 seconds

                  Kafka UI and Schema Registry --connect to--> Kafka cluster
                  Prometheus --scrapes--> Kubernetes and Kafka JMX exporter metrics
                  Grafana --visualizes--> Prometheus metrics
```

Configuration entry points for the diagram:

- [Proxmox VM definitions](terraform/k8s_vms.tf) and [Kafka VM definitions](terraform/kafka_vms.tf)
- [Ansible Kafka server role](ansible/roles/kafka_server/README.md) and [Ansible architecture](ansible/docs/architecture.md)
- [Argo CD Applications](gitops/applications/) and [Longhorn values](gitops/values/storage/longhorn.yaml)
- [Kafka broker scrape configuration](gitops/manifests/monitoring/kafka/scrape-config.yaml), [Kafka exporter scrape configuration](gitops/manifests/monitoring/kafka/exporter-scrape-config.yaml), and [Kafka monitoring Application](gitops/applications/kafka-monitoring.yaml)
- [Schema Registry Application](gitops/applications/schema-registry.yaml), [Flink Application](gitops/applications/flink-operator.yaml), and [FlinkDeployment](gitops/manifests/flink/btcusdt-consumer.yaml)
- [Kafka UI manifest](gitops/manifests/kafka/kafka-ui/kafka-ui.yaml), [producer manifest](gitops/manifests/kafka/btcusdt-producer/producer.yaml), and [Kafka/Flink code](kafka/)

### How the pieces interact

1. Terraform creates the virtual machines used by the platform.
2. Ansible prepares those machines and installs the Kubernetes and Kafka host
	services.
3. Argo CD watches `gitops/applications/` and deploys the declared Kubernetes
	applications, including monitoring, Kafka UI, the producer, and Flink.
4. The producer receives trade events and publishes them to a Kafka topic.
5. The Flink job reads that topic, periodically checkpoints its state, and
	writes processed records to object storage.
6. Prometheus scrapes Kubernetes and Kafka metrics; Grafana provides dashboards,
	while Kafka UI provides operational visibility into Kafka.

The BTCUSDT producer is disabled by default (`replicas: 0`). This keeps the
platform lightweight and avoids consuming the monthly Cloudflare R2 Free Tier
allowance unnecessarily. The project intentionally uses free or free-tier
services, so workloads that generate continuous data can be enabled explicitly
when needed.

Credentials and other sensitive values are supplied at deployment or runtime
through environment variables, Kubernetes Secrets, and protected CI inputs.
They are intentionally not stored in this repository.

## Future plans

The next data-platform direction is to evolve the Cloudflare R2 buckets into a
data catalog based on Apache Iceberg. This would add table metadata, schema
evolution, and more practical analytical access while keeping object storage as
the durable data layer.

## Agent-ready project

This repository is agent-ready: the context files required by AI coding agents
are versioned alongside the implementation. Files such as `AGENTS.md`,
`project-context.md`, and the documentation indexes describe ownership,
architecture, conventions, and validation commands. They must be updated when
the project context, architecture, or runtime behavior changes so that both
humans and agents can work from the same current information.

## Validation and CI

The root harness provides cross-domain checks:

```text
make setup       Install validation dependencies and the commit hook
make compile     Run fast, non-mutating compilation and configuration checks
make check       Run the required compile and unit-test gate
make lint        Run repository linters
make drift       Check harness files and documentation links
make complexity  Check Python code complexity
```

GitHub Actions runs the validation backstop and builds the producer and
consumer container images. More detailed commands and operational notes are
available in the domain README files and [the documentation index](docs/INDEX.md).
