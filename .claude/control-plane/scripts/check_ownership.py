"""Check that governed paths have their manifest-declared specialist owner."""

from __future__ import annotations

import argparse

from common import PolicyError, repo_path, repository_root
from load_manifest import load_manifest


def owner_for(path: str, manifest: dict) -> str | None:
    for entry in manifest["specialist_ownership"]:
        prefix = entry["pattern"].removesuffix("/**")
        if path == prefix or path.startswith(prefix + "/"):
            return entry["specialist"]
    return None


def check_ownership(root, paths: list[str], specialist: str | None = None) -> list[str]:
    manifest = load_manifest(root)
    errors = []
    for value in paths:
        path = repo_path(root, value)
        owner = owner_for(path, manifest)
        if owner is None:
            errors.append(f"no specialist owner: {path}")
        elif specialist and owner != specialist:
            errors.append(f"specialist {specialist!r} does not own {path} (owner: {owner})")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--specialist")
    args = parser.parse_args()
    try:
        errors = check_ownership(repository_root(), args.path, args.specialist)
    except PolicyError as error:
        parser.error(str(error))
    if errors:
        parser.error("; ".join(errors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
