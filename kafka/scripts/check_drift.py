from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    ROOT / "project-context.md",
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "INDEX.md",
    ROOT / ".github" / "copilot-instructions.md",
    ROOT / "AGENTS.md",
    ROOT / "Makefile",
    ROOT / "pyproject.toml",
    ROOT / "uv.lock",
    ROOT / ".pre-commit-config.yaml",
]
LINK_FILES = [
    ROOT / "AGENTS.md",
    ROOT / ".github" / "copilot-instructions.md",
    ROOT / "docs" / "INDEX.md",
]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def validate_required_files() -> list[str]:
    problems: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            problems.append(f"Missing required file: {path.relative_to(ROOT)}")
    return problems


def validate_links() -> list[str]:
    problems: list[str] = []
    for path in LINK_FILES:
        if not path.exists():
            continue

        content = path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK.finditer(content):
            target = match.group(1).split("#", 1)[0]
            if not target or "://" in target:
                continue

            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                problems.append(f"Out-of-repo link in {path.relative_to(ROOT)}: {target}")
                continue

            if not resolved.exists():
                problems.append(f"Broken link in {path.relative_to(ROOT)}: {target}")

    return problems


def main() -> int:
    problems = validate_required_files()
    problems.extend(validate_links())

    if problems:
        for problem in problems:
            print(problem)
        return 1

    print("Harness drift checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
