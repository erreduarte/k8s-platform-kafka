# Kafka UI and broker metrics

## Scope

Kafka runs on three dedicated Proxmox VMs outside Kubernetes. This repository
runs Kafka UI, Prometheus monitoring integration, and the BTCUSDT producer in
Kubernetes; it does not deploy Kafka brokers, Schema Registry, or Kafka Connect.

The producer is documented in [flink/operator.md](../flink/operator.md). It is
a raw Kubernetes Deployment in the `flink` namespace, owned by GitOps, while
its image is built and published by the `k8s-platform-kafka` repository.

## Kafka UI

`applications/kafka-ui.yaml` deploys Kafka UI to the `kafka-ui` namespace as a
single internal `ClusterIP` service. It connects directly to the three external
brokers using SASL_PLAINTEXT with SCRAM-SHA-512 on port `9092`.

The control-plane Ansible role publishes the internal service to the LAN at
`http://control-plane-1.example.invalid:8081`. Open that address and select the `fra` cluster.

The Kafka UI Secret is deliberately not stored in Git. Before deploying the
Ansible Kafka and control-plane roles, configure the `KAFKA_ADMIN_PASSWORD`
GitHub Actions secret for this repository. It must contain at least 32 letters,
digits, periods, underscores, or hyphens. The control-plane role creates the
`kafka-ui-credentials` Secret from that value after Argo CD has created the
`kafka-ui` namespace.

## Metrics

The Ansible component runs Prometheus JMX exporter alongside Kafka on each broker and
exposes metrics on TCP `9404`. `applications/kafka-monitoring.yaml` applies a
`ScrapeConfig` in the `monitoring` namespace with static targets for the three
broker IPs. Target relabeling adds a stable `host` label mapping the broker
addresses to `kafka01`, `kafka02`, and `kafka03`; the original `instance` label
remains the target address. The kube-prometheus-stack configuration selects
`ScrapeConfig` resources without requiring Helm labels.

Verify target health through Prometheus:

```bash
kubectl -n monitoring port-forward service/kube-prometheus-stack-prometheus 9090:9090
```

Open `http://localhost:9090/targets` and confirm the `kafka-brokers` target is
up.
