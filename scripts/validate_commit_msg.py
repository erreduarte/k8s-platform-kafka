from __future__ import annotations

import re
import sys

ALLOWED_TYPES = ("feat", "fix", "docs", "chore", "refactor", "test", "ci", "perf", "style")
COMMIT_PATTERN = re.compile(rf"^({'|'.join(ALLOWED_TYPES)})(\([^)]+\))?: .+")


def is_valid(message: str) -> bool:
    return bool(COMMIT_PATTERN.fullmatch(message.strip()))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print('Usage: python scripts/validate_commit_msg.py "feat(platform): add root harness"')
        return 2

    message = argv[1].strip()
    if not is_valid(message):
        print("ERROR: commit message must follow Conventional Commits format")
        print("Allowed types: " + ", ".join(ALLOWED_TYPES))
        print(f"Got: {message}")
        return 1

    print("Commit message valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
