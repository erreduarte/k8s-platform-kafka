from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MONOREPO_ROOT = REPO_ROOT.parent if (REPO_ROOT.parent / "gitops").is_dir() else REPO_ROOT
COMMIT_MESSAGE_PATTERN = re.compile(
    r"^(feat|fix|docs|chore|refactor|test|ci|perf)(\([^)]+\))?: .+"
)


def load_yaml_file(path: Path):
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is not installed. Run `make setup` first.") from exc

    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML ({exc})") from exc


def iter_yaml_files(repo_root: Path = REPO_ROOT) -> list[Path]:
    files: list[Path] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", ".venv", "__pycache__"} for part in path.parts):
            continue
        if path.suffix.lower() in {".yaml", ".yml"}:
            files.append(path)
    return sorted(files)


def validate_yaml(repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    for path in iter_yaml_files(repo_root):
        try:
            load_yaml_file(path)
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append(f"{path.relative_to(repo_root)}: {exc}")
    return errors


def validate_root_app(repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    root_app = repo_root / "bootstrap" / "root-app.yaml"
    if not root_app.exists():
        return ["bootstrap/root-app.yaml: missing required bootstrap manifest"]

    try:
        content = load_yaml_file(root_app) or {}
    except (OSError, RuntimeError, ValueError) as exc:
        return [f"bootstrap/root-app.yaml: {exc}"]

    source_path = (((content.get("spec") or {}).get("source") or {}).get("path"))
    if not isinstance(source_path, str) or not source_path.strip():
        errors.append("bootstrap/root-app.yaml: spec.source.path must be a non-empty string")
        return errors

    target_path = MONOREPO_ROOT / source_path if source_path.startswith("gitops/") else repo_root / source_path
    if not target_path.exists():
        errors.append(
            f"bootstrap/root-app.yaml: spec.source.path points to missing path '{source_path}'"
        )
    return errors


def application_sources(content: dict) -> list[dict]:
    spec = content.get("spec") or {}
    if "source" in spec and "sources" in spec:
        raise ValueError("spec must define either source or sources, not both")

    source = spec.get("source")
    if source is not None:
        if not isinstance(source, dict):
            raise ValueError("spec.source must be a mapping")
        return [source]

    sources = spec.get("sources")
    if not isinstance(sources, list) or not sources or not all(isinstance(item, dict) for item in sources):
        raise ValueError("spec.sources must be a non-empty list of mappings")
    return sources


def resolve_values_path(repo_root: Path, reference: str) -> Path:
    base_root = MONOREPO_ROOT if reference.startswith("gitops/") else repo_root
    path = (base_root / reference).resolve()
    if base_root.resolve() not in path.parents:
        raise ValueError(f"values reference must remain inside the repository: '{reference}'")
    return path


def validate_argocd_applications(repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    applications_dir = repo_root / "applications"

    for path in sorted(applications_dir.glob("*.y*ml")):
        relative_path = path.relative_to(repo_root)
        try:
            content = load_yaml_file(path) or {}
            if not isinstance(content, dict):
                raise ValueError("manifest must be a mapping")
            if content.get("apiVersion") != "argoproj.io/v1alpha1" or content.get("kind") != "Application":
                raise ValueError("manifest must be an argoproj.io/v1alpha1 Application")

            metadata = content.get("metadata") or {}
            spec = content.get("spec") or {}
            destination = spec.get("destination") or {}
            if not isinstance(metadata.get("name"), str) or not metadata["name"].strip():
                raise ValueError("metadata.name must be a non-empty string")
            if not isinstance(destination.get("namespace"), str) or not destination["namespace"].strip():
                raise ValueError("spec.destination.namespace must be a non-empty string")
            if not isinstance(destination.get("server"), str) or not destination["server"].strip():
                raise ValueError("spec.destination.server must be a non-empty string")

            sources = application_sources(content)
            refs = {
                source["ref"]: source
                for source in sources
                if isinstance(source.get("ref"), str) and source["ref"].strip()
            }
            for source in sources:
                helm = source.get("helm") or {}
                if not helm:
                    continue
                if not isinstance(helm, dict):
                    raise ValueError("helm configuration must be a mapping")
                for value_file in helm.get("valueFiles", []):
                    if not isinstance(value_file, str) or not value_file.startswith("$"):
                        continue
                    ref, separator, value_path = value_file[1:].partition("/")
                    if not separator or ref not in refs:
                        raise ValueError(f"value file '{value_file}' references an undefined source ref")
                    resolved_path = resolve_values_path(repo_root, value_path)
                    if not resolved_path.is_file():
                        raise ValueError(f"value file '{value_file}' does not exist")
        except (OSError, RuntimeError, ValueError) as exc:
            errors.append(f"{relative_path}: {exc}")

    return errors


def oci_helm_repositories(repo_root: Path) -> set[str]:
    repositories: set[str] = set()
    for path in iter_yaml_files(repo_root):
        content = load_yaml_file(path) or {}
        if not isinstance(content, dict) or content.get("kind") != "Secret":
            continue
        string_data = content.get("stringData") or {}
        if (
            string_data.get("type") == "helm"
            and string_data.get("enableOCI") == "true"
            and isinstance(string_data.get("url"), str)
        ):
            repositories.add(string_data["url"].rstrip("/"))
    return repositories


def helm_chart_reference(repo_name: str, repo_url: str, chart: str, is_oci: bool) -> str:
    if is_oci:
        return f"oci://{repo_url.removeprefix('oci://').rstrip('/')}/{chart}"
    return f"{repo_name}/{chart}"


def render_argocd_helm_charts(repo_root: Path = REPO_ROOT) -> int:
    errors = validate_argocd_applications(repo_root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    applications_dir = repo_root / "applications"
    oci_repositories = oci_helm_repositories(repo_root)
    for path in sorted(applications_dir.glob("*.y*ml")):
        content = load_yaml_file(path) or {}
        metadata = content["metadata"]
        spec = content["spec"]
        destination = spec["destination"]
        sources = application_sources(content)
        refs = {source["ref"]: source for source in sources if source.get("ref")}

        for index, source in enumerate(sources):
            if "chart" not in source:
                continue
            chart = source["chart"]
            repo_url = source.get("repoURL")
            version = source.get("targetRevision")
            if not all(isinstance(value, str) and value for value in (chart, repo_url, version)):
                print(
                    f"{path.relative_to(repo_root)}: Helm source requires chart, repoURL, and targetRevision",
                    file=sys.stderr,
                )
                return 1

            repo_name = f"argocd-{metadata['name']}-{index}"
            is_oci = repo_url.removeprefix("oci://").rstrip("/") in oci_repositories
            if not is_oci:
                subprocess.run(
                    ["helm", "repo", "add", repo_name, repo_url, "--force-update"],
                    check=True,
                )
            command = [
                "helm",
                "template",
                metadata["name"],
                helm_chart_reference(repo_name, repo_url, chart, is_oci),
                "--version",
                version,
                "--namespace",
                destination["namespace"],
            ]
            helm = source.get("helm") or {}
            for value_file in helm.get("valueFiles", []):
                if value_file.startswith("$"):
                    ref, _, value_path = value_file[1:].partition("/")
                    if ref not in refs:
                        print(
                            f"{path.relative_to(repo_root)}: value file '{value_file}' references an undefined source ref",
                            file=sys.stderr,
                        )
                        return 1
                    command.extend(["--values", str(resolve_values_path(repo_root, value_path))])
                else:
                    command.extend(["--values", value_file])
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL)

    print("Rendered Helm sources from Argo CD Application manifests.")
    return 0


def compile_repo(repo_root: Path = REPO_ROOT) -> int:
    errors = validate_yaml(repo_root)
    errors.extend(validate_root_app(repo_root))
    errors.extend(validate_argocd_applications(repo_root))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print(f"Validated {len(iter_yaml_files(repo_root))} YAML file(s).")
    print("Verified bootstrap/root-app.yaml source path exists.")
    print("Verified Argo CD Application manifests and local $values references.")
    return 0


def validate_commit_message(message: str) -> int:
    if not COMMIT_MESSAGE_PATTERN.fullmatch(message):
        print(
            "ERROR: commit message must follow Conventional Commits format\n"
            f"  Got: {message}",
            file=sys.stderr,
        )
        return 1

    print("Commit message valid")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("compile")
    subparsers.add_parser("argocd-validate")

    validate_commit_msg = subparsers.add_parser("validate-commit-msg")
    validate_commit_msg.add_argument("--msg", required=True)

    args = parser.parse_args()

    if args.command == "compile":
        return compile_repo()
    if args.command == "argocd-validate":
        return render_argocd_helm_charts()
    if args.command == "validate-commit-msg":
        return validate_commit_message(args.msg)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
