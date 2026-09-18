# Agent instructions

## Project scope

This repository manages the Proxmox infrastructure for the fra home lab. The
R2-backed Terraform state tracks Kubernetes VMIDs `141`, `151`, and `152`; the
templates `997` and `999`; and Kafka broker VMIDs `157`, `158`, and `159`.

Read [project-context.md](./project-context.md) and
[docs/INDEX.md](./docs/INDEX.md) before editing Terraform.

## Safety rules

- Terraform is the only owner of the managed Proxmox VM hardware. A plan that
  replaces or destroys anything is a blocking incident and needs human review.
- Before adopting an existing resource, back up remote state, add a declarative
  import mapping, and require a reviewed zero-change plan after adoption.
- Only the trusted runner receives `AWS_ENDPOINT_URL_S3`, `AWS_ACCESS_KEY_ID`,
  and `AWS_SECRET_ACCESS_KEY` from Repository Secrets.
- Run Proxmox commands only from `controller.example.invalid` or its trusted self-hosted runner.
- Provider credentials are environment variables from Repository Secrets. Never
  commit or expose them in inventory, outputs, or plan files.
- Ansible manages guest OS work, Kubernetes setup, and Longhorn disk setup.
  Argo CD manages Kubernetes workloads.

## Development commands

| Command | Purpose |
|---|---|
| `make setup` | Initialize the configured remote state backend |
| `make compile` | Validate Terraform configuration |
| `make lint` | Check Terraform formatting without changing files |
| `make format` | Format Terraform configuration files |
| `make check` | Run the required local validation gate |

`build`, `unit-tests`, and `integration-tests` do not exist yet. Add them only
when this repository has code and tests that need them. `lint` is intentionally
separate from `check` and commit hooks.

## Agent commit protocol

**Never commit or push directly to `main`.** Start every change in a feature
branch or isolated worktree, push that branch, and open a pull request. Only a
reviewed pull request may merge changes into `main`.

Before every feature-branch commit, agents must run:

1. `make agent-validate MSG="feat(terraform): add network module"`
2. Commit with a Conventional Commit message.
3. `make check` before pushing.

The `commit-msg` hook also checks Conventional Commit messages. Use `feat`,
`fix`, `docs`, `chore`, `refactor`, `test`, `ci`, `perf`, or `style`.

## CI and quality boundaries

- `Terraform merge test` checks pull requests without R2, Proxmox, or secrets.
- `verify_terraform_proxmox` runs before merge for PRs from this repository. It
	shows drift or planned changes but never applies them. Fork PRs are excluded
	because the trusted runner has R2 and Proxmox read credentials.
- `apply_terraform_proxmox` is the only apply path. It runs manually from
	`main` and requires the exact confirmation `APPLY_TERRAFORM_PROXMOX`.
- Verify and apply run only on the trusted runner and use one concurrency group
	so Proxmox operations cannot overlap.
