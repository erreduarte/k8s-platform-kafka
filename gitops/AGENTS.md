# AGENTS.md

## Project context

- [`project-context.md`](./project-context.md) — system purpose, architecture, integrations, and conventions
- [`docs/INDEX.md`](./docs/INDEX.md) — documentation map for deeper context

## Development commands

| Command | What it does |
|---|---|
| `make setup` | Install local validation dependencies and register the commit-msg hook |
| `make compile` | Parse tracked YAML and validate the root ArgoCD source path |
| `make argocd-validate` | Validate Argo CD Application references and render their Helm sources without a cluster |
| `make unit-tests` | Run unit tests for the repository validation helpers |
| `make lint` | Run YAML linting separately from hooks and `make check` |
| `make check` | Required local validation; runs `compile` and `unit-tests` |
| `make format` | Auto-format YAML files for developer convenience |
| `make validate-commit-msg MSG="feat: add app"` | Validate Conventional Commit format without creating a commit |
| `make agent-validate MSG="feat: add app"` | Agent pre-commit gate: validate message format, then run `compile` |

## Agent validation protocol

1. Run `make agent-validate MSG="<type>: <summary>"`.
2. Commit with the same message.
3. Run `make check` before pushing.

## Repo notes

- `bootstrap/root-app.yaml` points ArgoCD at `applications/`, which contains the active Application manifests, including the raw-manifest BTCUSDT producer deployment.
- `applications/` contains Application definitions; some Applications use Helm values under `values/`, while others sync raw resources under `manifests/`.
- `lint` stays separate from hooks and from `make check`.

## CI backstop

- Authoritative backstop: GitHub Actions via `.github/workflows/ci.yml`.
- `build` runs `make compile`, `lint` runs `make lint`, `argocd` renders Application Helm sources, and `test` runs `make unit-tests`.
- Jenkins is not configured for this repository today.

## Active sensors

- Drift: `make compile` parses repo YAML and verifies that `bootstrap/root-app.yaml` still points to an existing repository path.
- Coverage: not configured yet; current unit tests provide a test backstop but no threshold is enforced.
- Complexity: not applicable until the repo contains imperative source code.

## Org-standard commands not yet defined

- `make infra`
- `make run`
- `make build`
- `make integration-tests`
- `make clean`
