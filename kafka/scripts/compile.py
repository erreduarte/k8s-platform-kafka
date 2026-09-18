from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "__pycache__"}


def iter_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def main() -> int:
    python_files = iter_python_files(ROOT)
    if not python_files:
        print("No Python files found to compile.")
        return 1

    for path in python_files:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            print(f"Compile failed: {path.relative_to(ROOT)}")
            print(exc.msg)
            return 1

    print(f"Compiled {len(python_files)} Python file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
