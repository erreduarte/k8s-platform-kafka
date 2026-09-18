# AGENTS.md

## Repository identity

This repository is owned and administered by GitHub user `example-org`
(`maintainer@example.invalid`). Use `example-org/k8s-platform-kafka` for repository URLs,
GitHub Actions references, container image names, and GitOps source URLs.

## Project context

- [`project-context.md`](./project-context.md) — read this first: monorepo boundaries, ownership, and domain responsibilities
- [`docs/INDEX.md`](./docs/INDEX.md) — documentation map for deeper context

## Development commands

| Command | What it does |
|---|---|
| `make setup` | Install the root harness dependencies and the Conventional Commit hook |
| `make compile` | Run fast non-mutating validation across Terraform, GitOps, Kafka, and Ansible |
| `make unit-tests` | Run the unit tests currently defined in the monorepo |
| `make argocd-validate` | Render GitOps Helm/Application sources without a cluster |
| `make check` | Run the required local validation gate: `compile` plus existing unit tests |
| `make lint` | Run linting separately from hooks and from `make check` |
| `make drift` | Run the active drift sensors |
| `make complexity` | Run the active complexity sensors |
| `make format` | Run the available formatters in each domain |
| `make validate-commit-msg MSG="feat(platform): add root harness"` | Validate Conventional Commit format |
| `make agent-validate MSG="feat(platform): add root harness"` | Agent pre-commit gate: validate message, then compile |
| `make terraform-check` | Run the Terraform domain validation gate |
| `make gitops-check` | Run the GitOps domain validation gate |
| `make kafka-check` | Run the Kafka domain validation gate |
| `make ansible-check` | Run the Ansible syntax validation gate |

## Agent validation protocol

1. Run `make agent-validate MSG="<type>(platform): <summary>"`.
2. Commit with the same message and include a descriptive body.
3. Run `make check` before pushing.
4. Run `make lint` separately when the touched domain defines it.

## Repo notes

- `terraform/` remains the only owner of managed Proxmox hardware. Root validation uses backend-free Terraform init and never applies infrastructure.
- `ansible/` manages only Kubernetes and Kafka guests in this monorepo. Root validation is syntax-only; do not deploy from validation commands.
- `gitops/` and `kafka/` retain their domain-specific dependency managers, docs, and validation commands.
- Never commit secrets, state files, generated artifacts, virtual environments, dotenv files, or source-repository metadata.

## CI backstop

- Authoritative backstop: GitHub Actions via root `.github/workflows/*.yml`.
- `.github/workflows/ci.yml` is the PR/push backstop. It includes build- and test-equivalent jobs and keeps lint/quality as separate jobs.
- `.github/workflows/verify_terraform_proxmox.yml` runs the trusted read-only Terraform plan for same-repository pull requests.
- `.github/workflows/apply_terraform_proxmox.yml` is the only manual Terraform apply path from `main`.
- `.github/workflows/docker-consumer.yml` and `.github/workflows/docker-producer.yml` preserve the Kafka image build/publish flows.
- Jenkins is not configured for this repository today.

## Active sensors

- Drift: `make drift` delegates to the Kafka harness drift checks.
- Complexity: `make complexity` delegates to the Kafka Radon checks.
- Coverage: not configured repo-wide yet. GitOps has unit tests, but no monorepo coverage threshold is enforced.
- Lint: `make lint` keeps Terraform formatting checks, GitOps YAML linting, and Kafka Ruff checks separate from `make check`.

## Org-standard commands not yet defined

- `make infra`
- `make run`
- `make build`
- `make integration-tests`
- `make clean`
