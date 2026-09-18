# Monorepo migration manifest

Date: 2026-09-11

## Source mapping

| Source repository | Monorepo path | Policy |
| --- | --- | --- |
| `k8s-platform-kafka` | `terraform/` | Public Terraform, docs, validation, and CI configuration. |
| `k8s-platform-kafka` | `gitops/` | Public GitOps manifests, values, scripts, tests, and docs. |
| `k8s-platform-kafka` | `kafka/` | Public Kafka/Flink source, packaging, tests/scripts, and docs. |
| `k8s-platform-kafka` | `ansible/` | Public Kubernetes and Kafka guest configuration. |

## Ansible inclusions

Hosts: `kafka-1.example.invalid`, `kafka-2.example.invalid`, `kafka-3.example.invalid`, `control-plane-1.example.invalid`,
`worker-1.example.invalid`, and `worker-2.example.invalid`.

Roles: `common`, `firewall`, `k8s_common`, `k8s_control_plane`, `k8s_worker`,
`kafka_server`, `users`, and `shell` because they are invoked for the retained
Kubernetes and Kafka hosts.

## Exclusions

- All `.git` directories, worktrees, virtual environments, caches, and local dotenv files.
- Terraform `.terraform/` and `artifacts/` generated/state-adjacent content.
- Secrets, private keys, generated credentials, and generated deployment artifacts.
- `controller.example.invalid`, `hypervisor.example.invalid`, `ai.example.invalid`, AI, monitoring, NAS, controller,
  router-exporter, and every other non-Kubernetes/non-Kafka resource remain
outside this public mirror and are excluded from `ansible/`.
- Source-repository-only metadata was not carried over as a repository boundary.

The source repositories were not modified. The GitOps root application path and
repository URL were adapted for the monorepo; the URL must be confirmed before
production bootstrap. The strict Ansible scope above is an ownership boundary,
not an invitation to migrate additional infrastructure later.
