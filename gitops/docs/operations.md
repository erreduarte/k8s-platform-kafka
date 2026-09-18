> Accurate as of 2026-09-10. Update when the codebase changes significantly.

# Operations

## Repository layout

| Path | Role |
|---|---|
| `bootstrap/` | Cluster bootstrap assets that connect ArgoCD to this repo |
| `applications/<name>.yaml` | Managed Argo CD Application manifest directly discovered by the root application |
| `values/<domain>/` | Helm values matching the application domain |
| `manifests/<domain>/<service>/` | Raw Kubernetes resources for applications that do not require Helm |
| `docs/<domain>/` | Domain-specific runbooks and design notes |

## Expected workflow

1. Keep bootstrap definitions separate from workload definitions.
2. Add each managed Application directly under `applications/` with the deployed service name.
3. Store its Helm values under `values/<domain>/`, or raw resources under `manifests/<domain>/<service>/`, and its runbook under `docs/<domain>/`.
4. Update the repository and domain documentation with the new operational state.
5. Validate YAML and repository path assumptions locally before committing.
6. Run `make argocd-validate` to render every Helm source declared by an Argo CD Application before merging.

## Longhorn rollout

1. Confirm the Ansible component has mounted the dedicated worker disks at `/var/lib/longhorn`.
2. Label `worker-1.example.invalid` and `worker-2.example.invalid` with `node.longhorn.io/create-default-disk=true` before merging the Longhorn Application.
3. Merge `applications/longhorn.yaml`; the root application discovers it and syncs Longhorn to `longhorn-system`.
4. Verify its pods, settings, Longhorn node disks, and the non-default `longhorn` StorageClass. See [storage/longhorn.md](storage/longhorn.md).

## Secret ownership

The Grafana administrator Secret is not stored in this repository. The Ansible component
creates `monitoring/grafana-admin-credentials` using the protected
`GRAFANA_ADMIN_PASSWORD` deployment input. The Secret name and keys must stay
compatible with the Grafana values.

The former External Secrets Operator resources were removed from GitOps.
Configure the Ansible secret input, synchronize this removal, and run Ansible
again so the Secret is applied after ESO has stopped reconciling it. Verify the
Secret and Grafana before approving any further pruning.

## kube-prometheus-stack rollout

1. Confirm the `longhorn` StorageClass exists and is healthy.
2. Merge `applications/kube-prometheus-stack.yaml`; the root Application syncs the stack to `monitoring`.
3. Verify its pods and persistent volume claims, then verify Prometheus targets by port-forwarding its ClusterIP service.
4. Keep host-level exporter ownership in the Ansible component; this Application monitors Kubernetes resources and opt-in `ServiceMonitor`, `PodMonitor`, and `PrometheusRule` resources. See [monitoring/kube-prometheus-stack.md](monitoring/kube-prometheus-stack.md).

## BTCUSDT producer rollout

The `btcusdt-producer` Application deploys the producer image published by the
`k8s-platform-kafka` repository as a raw Kubernetes `Deployment` in the `flink`
namespace. Kafka brokers remain on the external Proxmox VMs.

Before enabling it, confirm that `flink` contains these externally managed
Secrets:

- `ghcr-pull-secret`, containing read access for `ghcr.io`.
- `kafka-flink-credentials`, containing `bootstrapServers`, `username`, and
	`password` keys.

The Deployment intentionally starts with `replicas: 0` so an Argo CD sync does
not begin producing traffic unexpectedly. After the image has been published,
enable it explicitly:

```bash
kubectl -n flink scale deployment btcusdt-producer --replicas=1
kubectl -n flink get deployment btcusdt-producer
kubectl -n flink get pods -l app.kubernetes.io/name=btcusdt-producer
```

Disable it with `--replicas=0`. Because the desired manifest remains at zero,
the scale-up is an operational override and will be reverted by Argo CD on a
sync. For a persistent change, update the manifest and review the producer
image tag deliberately.

## Current gaps

- Coverage thresholds are not configured yet.
- Complexity thresholds are not applicable until the repo contains more imperative source code.

## CI backstop

- GitHub Actions is the authoritative CI backstop for now.
- The workflow keeps build, lint, Argo CD rendering, and test as separate jobs.
- Build maps to `make compile`; Argo CD rendering maps to `make argocd-validate`; test maps to `make unit-tests`.
