# k8s-platform-kafka project context

The canonical GitHub owner is `example-org` (`maintainer@example.invalid`). Repository
URLs, GitHub Actions integrations, container image references, and GitOps source
URLs must use `example-org/k8s-platform-kafka`.

This monorepo consolidates the four homelab source repositories without
changing their ownership boundaries. Terraform provisions Proxmox hardware;
the destination Ansible tree configures only Kubernetes and Kafka guests;
GitOps declares Kubernetes workloads; and Kafka contains the learning-
environment utilities and images.

## Layout

| Path | Responsibility |
| --- | --- |
| `terraform/` | Proxmox state-backed VM and template configuration |
| `ansible/` | Inventory, baseline roles, Kafka, and Kubernetes guest configuration only |
| `gitops/` | Argo CD bootstrap, applications, values, and manifests |
| `kafka/` | Kafka admin/producer utilities and Flink consumer image |
| `docs/` | Monorepo migration and cross-domain navigation |

Terraform remains the only owner of managed VM hardware. Ansible owns guest OS
work. GitOps owns Kubernetes workloads. Kafka brokers remain external VMs.
Secrets stay in environment variables or deployment-time inputs and are not
migrated into Git. Non-Kubernetes and non-Kafka Ansible resources remain
exclusively outside this public repository; they are not represented
in `ansible/` here.
