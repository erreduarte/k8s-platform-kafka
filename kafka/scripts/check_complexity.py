from __future__ import annotations

from pathlib import Path

from radon.complexity import cc_rank, cc_visit

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "__pycache__"}
ACCEPTED_RANKS = {"A", "B"}


def iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def main() -> int:
    violations: list[str] = []

    for path in iter_python_files(ROOT):
        source = path.read_text(encoding="utf-8")
        for block in cc_visit(source):
            rank = cc_rank(block.complexity)
            if rank not in ACCEPTED_RANKS:
                violations.append(
                    f"{path.relative_to(ROOT)}:{block.lineno} {block.name} -> {rank} ({block.complexity})"
                )

    if violations:
        print("Complexity threshold exceeded:")
        for violation in violations:
            print(violation)
        return 1

    print("Complexity checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
