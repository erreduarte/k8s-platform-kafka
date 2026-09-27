# project-context.md

> AI context file — read this before changing Terraform in this repository.
> Updated: 2026-08-27

## System purpose

Terraform manages the Proxmox hardware lifecycle for the fra home lab
Kubernetes nodes, Kafka base template, and Kafka broker VMs. It replaces only
the VM-provisioning part of the Ansible component; it must not recreate the running
cluster.

## Bounded contexts

| Context | Responsibility |
|---|---|
| Proxmox infrastructure | K8s and Kafka VM hardware, templates `997` and `999`, Cloud-Init, and data disks |
| Ansible handoff | Guest OS, SSH, inventory groups, Kubernetes requirements, and disk format/mount work |
| GitOps workloads | Argo CD and Kubernetes applications, including Longhorn |

## Architecture

- **Stack:** Terraform 1.15.x with pinned `bpg/proxmox` provider 0.111.1.
- **Execution:** only `controller.example.invalid` and its trusted self-hosted runner may access
	Proxmox. Backend-free checks and same-repository PR plans run before merge.
	Remote verification and manual apply run on this trusted runner.
- **Authentication:** trusted workflows pass Repository Secrets to the provider
	and R2 as environment variables.
- **State:** Cloudflare R2 bucket `example-terraform-state` stores remote state at
	example-infrastructure/terraform.tfstate` and Terraform's native S3 lockfile.
	State credentials and the account-specific R2 endpoint exist only as runner
	environment variables. R2 has no S3 bucket versioning, so keep a separate
	encrypted state backup.
- **Inventory:** Terraform can render a non-sensitive YAML fragment for Ansible
  to use with its hand-maintained role and capability data.

## Key decisions

- VMIDs `141` (`cp01`), `151` (`w01`), `152` (`w02`), and template `999` are
	fixed managed IDs in the R2-backed state.
- Template `997` (`debian13-kafka.template`) is a protected full clone of the
	manually managed Debian template `998`. It has a 20 GiB root disk and a
	Cloud-Init drive. Terraform does not manage `998`.
- The Proxmox LAN is `192.0.2.0/26` and its gateway is `192.0.2.1`. Kafka
	Cloud-Init addresses must use `/26`, not `/24`. A clone of `997` passed with
	`192.0.2.60/26` and DNS `1.1.1.1`.
- Kafka brokers `kafka-1.example.invalid`, `kafka-2.example.invalid`, and `kafka-3.example.invalid` use VMIDs `157`,
	`158`, and `159`, with address suffixes `57`, `58`, and `59`. Each has 2 vCPU,
	2 GiB RAM, a 20 GiB root disk, and a 30 GiB `scsi1` Kafka disk on `local-lvm`.
- Kafka brokers use `virtio-scsi-pci`, while the templates and Kubernetes VMs use
	`virtio-scsi-single`, so the
	guest consistently detects the 20 GiB `scsi0` operating-system disk as
	`/dev/sda` and the 30 GiB `scsi1` data disk as `/dev/sdb`.
- Managed VMs and Longhorn disks use deletion protection. Adoption passed both
	the refresh-only and normal zero-change plan checks.
- Each Longhorn worker has one 100 GiB `local-lvm` disk on `scsi1`. Ansible
	checks, formats, grows, and mounts it at `/var/lib/longhorn`.
- Kubernetes workers `w01` and `w02` use 70 GiB `scsi0` root disks to reduce
	root filesystem `DiskPressure` from containerd and kubelet. Their 100 GiB
	`scsi1` Longhorn disks are separate and unchanged.
- Template `999` is fixed and protected. Its Cloud-Init disk and static
	template IP are separate from the Cloud-Init settings for each node.
- Template `997` passed its `cloud-init` and `qemu-guest-agent` readiness test;
	see `docs/kafka-template.md`. Terraform cannot install guest packages.
- GitHub Actions separates checks, plans, and changes: `Terraform merge test`
	validates PRs without remote access; `verify_terraform_proxmox` plans
	same-repository PRs before merge; and `apply_terraform_proxmox` needs manual
	confirmation from `main` before it can apply.

## What to avoid

- Do not run `apply` until someone has reviewed its plan. Use the manual
	`apply_terraform_proxmox` workflow from `main` with
	`APPLY_TERRAFORM_PROXMOX`; it applies only the plan from that run. Add a
	declarative import mapping before treating an existing resource as managed.
- Do not manage the Proxmox host OS, `vmbr0`, `local-lvm`, DHCP/router,
	Kubernetes resources, Argo CD credentials, or Longhorn Helm resources here.
- Do not put secrets in Git, tfvars, generated inventory, Terraform outputs, or
	plan files.
