# Proxmox and guest architecture

> Accurate as of 2026-09-01. Update this document when ownership changes.

Terraform manages the Proxmox hardware for the home lab. Ansible configures the
guest operating systems. Argo CD deploys software into Kubernetes. Each layer
has a separate job so that one tool does not overwrite another tool's work.

```
Terraform
├── Templates: Ubuntu 999 and Debian Kafka 997
├── Proxmox K8s VMs and Kafka broker VMs
├── CPU, memory, disks, boot devices, and VM power state
└── Cloud-Init users, SSH keys, and static network settings
    ↓
Ansible
├── Guest OS, users, packages, UFW, and /etc/hosts
├── Kubernetes host preparation and kubeadm setup
└── Longhorn disk checks, formatting, and mount at /var/lib/longhorn
    ↓
Argo CD
└── Longhorn and other Kubernetes workloads
```

## Managed machines

| Node or template | VMID | vCPU | Memory | IPv4 | Root disk | Extra disk |
|---|---:|---:|---:|---|---|---|
| `debian13-kafka.template` | 997 | 2 | 2048 MiB | — | 20 GiB `scsi0` | — |
| `ubuntu-server-template` | 999 | 2 | 2048 MiB | — | 50 GiB `scsi0` | — |
| `control-plane-1.example.invalid` | 141 | 2 | 5120 MiB | `192.0.2.41/26` | 50 GiB `scsi0` | — |
| `worker-1.example.invalid` | 151 | 4 | 5120 MiB | `192.0.2.51/26` | 70 GiB `scsi0` | 100 GiB `local-lvm`, `scsi1` |
| `worker-2.example.invalid` | 152 | 4 | 5120 MiB | `192.0.2.52/26` | 70 GiB `scsi0` | 100 GiB `local-lvm`, `scsi1` |
| `kafka-1.example.invalid` | 157 | 2 | 2048 MiB | `192.0.2.57/26` | 20 GiB `scsi0` | 30 GiB `local-lvm`, `scsi1` |
| `kafka-2.example.invalid` | 158 | 2 | 2048 MiB | `192.0.2.58/26` | 20 GiB `scsi0` | 30 GiB `local-lvm`, `scsi1` |
| `kafka-3.example.invalid` | 159 | 2 | 2048 MiB | `192.0.2.59/26` | 20 GiB `scsi0` | 30 GiB `local-lvm`, `scsi1` |

The gateway is `192.0.2.1` and the LAN uses `192.0.2.0/26`. Templates and
managed VMs are protected from deletion. Template `999` is used for Kubernetes
VMs. Template `997` is a protected clone of manual Debian template `998` and is
used for Kafka brokers. Terraform does not manage `998`.

The Kubernetes workers use 70 GiB root disks on `scsi0` to provide additional
space for the root filesystem and reduce the risk of `DiskPressure` from
containerd and kubelet. Their separate 100 GiB `scsi1` disks remain dedicated
to Longhorn and are unchanged.

Kafka brokers use the shared `virtio-scsi-pci` controller. This keeps the Linux
guest device order stable: the 20 GiB operating-system disk at `scsi0` is
`/dev/sda`, and the 30 GiB Kafka disk at `scsi1` is `/dev/sdb`.

## Outside Terraform

Terraform does not manage:

- the Proxmox host OS or API endpoint;
- bridge `vmbr0` or `local-lvm` storage;
- router DHCP reservations or the physical network;
- the Ansible service-user bootstrap or other guest configuration.

Before importing an existing VM, record its live settings. Include template
source, boot disk, BIOS, machine type, SCSI controller, Cloud-Init drive,
network bridge, MAC address, guest agent, tags, and power state. Terraform must
describe confirmed live settings, not provider defaults.

## Change flow

```
Pull request from this repository
├── Terraform merge test: formatting and configuration checks
└── verify_terraform_proxmox: read-only plan on trusted runner
                         ↓ reviewed merge to main
              manual apply_terraform_proxmox confirmation
                         ↓
              trusted-runner fresh plan and apply
```

`verify_terraform_proxmox` never applies changes. It runs only for pull requests
from this repository because the trusted runner has R2 and Proxmox read
credentials. Fork pull requests do not receive those credentials.

The manual apply workflow runs only from `main`, requires the exact value
`APPLY_TERRAFORM_PROXMOX`, creates a fresh plan, shows it, and applies that plan.
The verify and apply workflows share one concurrency group, so Proxmox operations
cannot overlap.
