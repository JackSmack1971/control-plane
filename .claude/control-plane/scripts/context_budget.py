"""Report always-loaded instruction size and fail above a 6 KB project budget.

Six KB retains the repository's universal invariants while forcing topic guidance
into path-scoped rules or on-demand skills instead of startup context.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from common import repository_root

BUDGET_BYTES = 6_000


def is_path_scoped(rule: Path) -> bool:
    text = rule.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return False
    _, frontmatter, _ = text.split("---", 2)
    return bool(yaml.safe_load(frontmatter).get("paths"))


def always_loaded(root: Path) -> list[Path]:
    paths = [root / "AGENTS.md", root / ".claude/AGENTS.md"]
    for rule in sorted((root / ".claude/rules").rglob("*.md")):
        if not is_path_scoped(rule):
            paths.append(rule)
    return paths


def report(root: Path) -> tuple[int, list[str]]:
    paths = always_loaded(root)
    return sum(path.stat().st_size for path in paths), [path.relative_to(root).as_posix() for path in paths]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    size, paths = report(repository_root())
    print(f"always-loaded instructions: {size}/{BUDGET_BYTES} bytes")
    for path in paths:
        print(path)
    return int(args.check and size > BUDGET_BYTES)


if __name__ == "__main__":
    raise SystemExit(main())
