# k8s-platform-kafka GitOps

This directory defines the applications that run in the homelab Kubernetes
cluster. Argo CD reads these files and applies the declared configuration to
the cluster.

Use this repository to change Kubernetes application configuration. Do not use
it to manage virtual machines, operating systems, or secrets themselves.

## What this repository manages

| Area | What it provides |
| --- | --- |
| Storage | Longhorn storage for applications that need persistent data. |
| Secrets | References to secrets created outside GitOps, including the Ansible-managed Grafana credentials. |
| Monitoring | Prometheus, Alertmanager, Grafana, and their Kubernetes integration. |
| Application delivery | Argo CD Applications, Helm values, and raw Kubernetes manifests for managed services. |
| Kafka workloads | Kafka UI, broker monitoring, and the BTCUSDT producer Deployment; Kafka brokers remain on Proxmox VMs. |

Kafka runs on dedicated Proxmox virtual machines, not in Kubernetes. Its VM
hardware is managed in this repository's `terraform/` component and its operating system setup is
managed in the Ansible component. Kubernetes will provide supporting services such as
observability, secret delivery, Kafka UI, and the BTCUSDT producer workload.

## How configuration is organized

- `bootstrap/` contains the root Argo CD application. It tells Argo CD to load
	the application manifests under `gitops/applications/` in this monorepo.
- `applications/` contains one Argo CD Application manifest per managed
	service.
- `values/` contains Helm values grouped by area, including storage, Flink,
  and monitoring.
- `manifests/` contains raw Kubernetes resources used by Applications that do
	not require a Helm chart.
- `docs/` contains architecture notes and operating runbooks for each area.

When adding a service, add its Argo CD Application under `applications/`, use a
Helm source with matching values or a raw manifest directory under `manifests/`,
and document operational requirements under `docs/`.

## Common changes

| If you need to… | Start with… |
| --- | --- |
| Change Longhorn settings | [docs/storage/longhorn.md](docs/storage/longhorn.md) and `values/storage/longhorn.yaml`. |
| Change secret ownership | [docs/operations.md](docs/operations.md) and the owning repository's runbook. |
| Change Prometheus, Alertmanager, or Grafana | [docs/monitoring/kube-prometheus-stack.md](docs/monitoring/kube-prometheus-stack.md) and `values/monitoring/`. |
| Add or change an application | The matching manifest in `applications/` and its referenced values or manifest directory. |

Never commit secret values, tokens, unseal shares, or Kubernetes Secrets that
contain sensitive values. Keep credentials outside Git and refer to them only
by name in manifests.

## Validate changes locally

Install the local tools once:

```bash
make setup
```

Before opening a pull request, run:

```bash
make compile
make lint
make check
```

- `make compile` checks that the YAML files and Argo CD references are valid.
- `make lint` checks YAML style.
- `make check` runs the required compile and unit-test checks.

GitHub Actions runs the same validation for pushes and pull requests.

## Commit messages

Use Conventional Commits. Examples:

- `feat: add application manifest`
- `fix: correct root app path`
- `chore: update repository checks`
