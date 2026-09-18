# Tracking and recovering Proxmox VMs

> The original Proxmox VMs were added to Terraform state successfully on
> 2026-08-22. This document explains the accepted state and the rules for later
> changes or state recovery.

## Current status

- The R2 lock and recovery check passed.
- VMIDs `141`, `151`, `152`, and template `999` are in remote Terraform state.
- Adoption passed both the refresh-only and normal zero-change plan checks.
- The configuration keeps declarative import mappings for managed resources.
  They do nothing while the resource is already in state.

## Safety rules

1. Terraform owns VM hardware only after the import is accepted.
2. Ansible still owns guest setup, Kubernetes, and Longhorn disk preparation.
3. This migration must not recreate, replace, or destroy an imported resource.
4. The migration is complete only when refresh-only and normal plans both show
  zero changes.

## Cloudflare R2 backend

The state is always stored at
`example-terraform-state/example-infrastructure/terraform.tfstate`. Terraform creates and
removes its lock file at the same path with the `.tflock` suffix.

The trusted `controller.example.invalid` runner provides these environment variables. Never commit
them or put them in a Terraform backend file:

| Variable | Purpose |
|---|---|
| `AWS_ENDPOINT_URL_S3` | Account-specific R2 endpoint: `https://object-storage.example.invalid` |
| `AWS_ACCESS_KEY_ID` | R2 S3 API access key for state |
| `AWS_SECRET_ACCESS_KEY` | R2 S3 API secret for state |

Trusted GitHub workflows receive these from Repository Secrets. The Proxmox
provider also receives `PROXMOX_VE_ENDPOINT`, `PROXMOX_VE_API_TOKEN`, and
`PROXMOX_VE_INSECURE` from Repository Secrets.

Use a dedicated R2 token with **Object Read & Write** permission only for the
`example-terraform-state` bucket. It must list the state prefix, read and write the
state file, and read, write, and delete its `.tflock` file. Do not reuse the
Proxmox token.

R2 supports the conditional S3 operations Terraform needs for locks, but it has
no S3 bucket versioning. Keep an encrypted copy of each accepted state snapshot
outside the bucket. Never commit the backup.

## Required foundation

- A dedicated least-privilege Proxmox API token. It is available only on
  `controller.example.invalid` and the self-hosted runner as `PROXMOX_VE_API_TOKEN`.
- The token must list managed VMs through the Proxmox cluster-resources API and
  read each VM configuration. Test both with the exact workflow token; a role
  assignment alone does not prove the provider can look up resources.
- A reviewed copy of template source, boot disk, BIOS, machine type, SCSI
  controller, Cloud-Init drive, network bridge, MAC address, guest agent, tags,
  and power state. Terraform owns the non-secret Cloud-Init user, SSH key,
  static IP addresses, and gateway.
- A backup of the Proxmox configuration and remote Terraform state before import.

## Ongoing change workflow

1. Open a pull request from this repository. `Terraform merge test` checks the
  configuration without R2, Proxmox, or secrets. Before merge,
  `verify_terraform_proxmox` runs a plan on the trusted runner. Fork PRs skip
  this job because it has R2 and Proxmox read credentials.
2. Review both checks before merging. If the plan finds changes, run
  `apply_terraform_proxmox` after the merge.
3. From the Actions UI, run
  `apply_terraform_proxmox` on `main` and enter
  `APPLY_TERRAFORM_PROXMOX` as its confirmation input.
4. The apply workflow creates and shows a current plan, then applies the exact
  `tfplan` from that run. It never reuses an old verification plan.

## Adopting another existing VM

1. Capture the live Proxmox configuration and back up remote state on the
   trusted runner.
2. Add the resource with its VMID, `prevent_destroy`, and a declarative
   `import` mapping that uses its Proxmox node and VMID.
3. Run a plan. It must adopt state, not create a VM. Never delete or replace a
   VM to fix an import or configuration mismatch.
4. Run `terraform plan -refresh-only` and resolve every difference.
5. Run a normal plan. Stop unless it is a reviewed zero-change plan.
6. Repeat the normal plan from a clean `controller.example.invalid` checkout, then run two reviewed
   no-op applies in a row.

## Recovery

- Restore state only from a verified backup. Never delete state to fix drift.
- Restore a missing state binding with its existing declarative import mapping.
- A planned VM or Longhorn-disk replacement is a blocking incident and needs
  explicit human review.
- Never use a normal template update to replace an existing Kubernetes node.
