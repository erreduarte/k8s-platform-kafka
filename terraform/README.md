# k8s-platform-kafka Terraform

This repository uses Terraform to manage the Proxmox virtual machines for the
`fra` home lab. It manages VM hardware and Cloud-Init settings. It does not set
up the guest operating systems or deploy Kubernetes applications.

## What this repository manages

Every Proxmox resource in this table is already tracked in Terraform state,
which is stored in Cloudflare R2:

| Resource | VMID | Terraform responsibility |
|---|---:|---|
| Ubuntu Cloud-Init template | 999 | Template hardware and template network settings |
| Debian Kafka Cloud-Init template | 997 | Template hardware for Kafka broker clones |
| Kubernetes control plane | 141 | VM hardware, Cloud-Init, and static network settings |
| Kubernetes worker `w01` | 151 | VM hardware, 70 GiB root disk, Cloud-Init, static network, and Longhorn disk |
| Kubernetes worker `w02` | 152 | VM hardware, 70 GiB root disk, Cloud-Init, static network, and Longhorn disk |
| Kafka broker `kafka01` | 157 | VM hardware, Cloud-Init, static network, and 30 GiB data disk |
| Kafka broker `kafka02` | 158 | VM hardware, Cloud-Init, static network, and 30 GiB data disk |
| Kafka broker `kafka03` | 159 | VM hardware, Cloud-Init, static network, and 30 GiB data disk |

All templates and VMs are protected with `prevent_destroy`. Terraform also
ignores the clone source after a VM has been imported. This prevents a config
change from rebuilding a running VM just to record which template created it.

## Ownership boundaries

| System | What it manages |
|---|---|
| Terraform | Proxmox VM hardware, Cloud-Init, static IPs, MAC addresses, and worker data disks |
| [Ansible](https://github.com/erreduarte/k8s-platform-kafka/tree/main/ansible) | Guest OS configuration, users, packages, UFW, Kubernetes bootstrap, and Longhorn disk format/mount |
| Argo CD | Longhorn and other Kubernetes workloads |

Do not use this repository to manage the Proxmox host, `vmbr0`, `local-lvm`,
the router, DHCP, or Kubernetes resources. Those systems are managed elsewhere.

## How changes are applied

Infrastructure changes use three separate workflows:

| Workflow | Trigger | What it does |
|---|---|---|
| `Terraform merge test` | Pull request to `main` | Checks formatting and Terraform syntax. It does not use secrets, Proxmox, or remote state. |
| `verify_terraform_proxmox` | Pull request from this repository to `main` | Runs a read-only plan on the trusted `controller.example.invalid` runner before merge. It never applies changes. Fork PRs do not run it because the runner has R2 and Proxmox read credentials. |
| `apply_terraform_proxmox` | Manual run from `main` | Requires `APPLY_TERRAFORM_PROXMOX`, creates and shows a fresh plan, then applies that exact plan. |

The normal operating sequence is:

1. Create a feature branch or isolated worktree; **never commit or push directly to `main`**.
2. Push the feature branch and open a pull request.
3. Review both the backend-free `Terraform merge test` and the trusted-runner `verify_terraform_proxmox` plan before merging.
4. Merge the reviewed pull request into `main`.
5. If the plan is expected, manually run `apply_terraform_proxmox` from `main`.
6. Enter `APPLY_TERRAFORM_PROXMOX` only after reviewing the displayed plan.

Nothing is applied automatically after a merge. The verify and apply workflows
run only on the trusted self-hosted runner. They share one concurrency lock, so
two Proxmox operations cannot run at the same time.

## Manual validation and debugging

Use these commands only for investigation on `controller.example.invalid` or its trusted runner.
For normal changes, use the GitHub Actions flow above.

First, validate configuration without accessing Proxmox or remote state:

```text
make compile
make lint
make check
```

To inspect the remote backend during diagnosis, run:

```text
make setup
make state-backend-check
```

These commands initialize and read the R2 state. Run them only on `controller.example.invalid` or
its trusted runner, where the required secrets are available. Do not run
`terraform apply` manually. Use `apply_terraform_proxmox` after reviewing a
plan.

The trusted workflows need these Repository Secrets:
`AWS_ENDPOINT_URL_S3`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`PROXMOX_VE_ENDPOINT`, `PROXMOX_VE_API_TOKEN`, and `PROXMOX_VE_INSECURE`.
Never commit their values or copy them into Terraform files.

## Further reading

- [Project context](project-context.md): ownership, constraints, and decisions.
- [Architecture](docs/architecture.md): managed fleet and execution flow.
- [State adoption and recovery](docs/migration-proxmox-k8s-vms.md): safeguards
	for imported resources and state recovery.
- [Documentation index](docs/INDEX.md): navigation for the complete document set.
