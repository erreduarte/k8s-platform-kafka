# Ansible architecture

This destination configures only Kafka broker VMs and Kubernetes nodes. Every
other resource remains outside this public mirror.

## Inventory model

| Group | Hosts | Responsibility |
| --- | --- | --- |
| `kafka_server` | `kafka-1.example.invalid`, `kafka-2.example.invalid`, `kafka-3.example.invalid` | Kafka KRaft runtime and data disk |
| `k8s` | `control-plane-1.example.invalid`, `worker-1.example.invalid`, `worker-2.example.invalid` | Kubernetes parent group |
| `k8s_control_plane` | `control-plane-1.example.invalid` | Control-plane bootstrap |
| `k8s_worker` | `worker-1.example.invalid`, `worker-2.example.invalid` | Worker join |
| `longhorn_storage` | `worker-1.example.invalid`, `worker-2.example.invalid` | Worker disk preparation |

## Playbook flow

1. Apply `common`, `users`, `shell`, and `firewall` to all six hosts.
2. Prepare Kafka brokers serially with `kafka_server`.
3. Prepare Kubernetes nodes with `k8s_common`.
4. Initialize the control plane, join workers, and run readiness checks.

Only `ansible.posix`, `community.general`, and `kubernetes.core` are declared
as collection dependencies. Terraform owns VM hardware and disks; GitOps owns
Kubernetes workloads.
