"""Compare changed governed files with a transaction's declared write set."""

from __future__ import annotations

import argparse
import json
import subprocess

from common import PolicyError, rejection, repo_path, repository_root
from load_manifest import load_manifest


def _within(path: str, roots: list[str]) -> bool:
    return any(path == root or path.startswith(root + "/") for root in roots)


def _managed(path: str, manifest: dict) -> bool:
    policy = manifest["transaction_policy"]
    return _within(path, manifest["governed_roots"]) or path in policy["companion_files"] or _within(path, policy["companion_roots"])


def changed_paths(root, revision: str) -> list[str]:
    command = ["git", "-C", str(root), "diff", "--name-only", "--diff-filter=ACDMRTUXB", revision, "--"]
    tracked = subprocess.run(command, text=True, capture_output=True, check=True).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"], text=True, capture_output=True, check=True
    ).stdout.splitlines()
    return sorted(set(tracked + untracked))


def check_write_set(root, declared: list[str], revision: str) -> list[str]:
    manifest = load_manifest(root)
    if not declared:
        return [rejection("CP201", "declared write set is empty")]
    if len(declared) > manifest["budgets"]["maximum_changed_files"]:
        return [rejection("CP202", "declared write set exceeds changed-file budget")]
    try:
        declared = [repo_path(root, path) for path in declared]
    except PolicyError as error:
        return [str(error)]
    if len(declared) != len(set(declared)):
        return [rejection("CP203", "declared write set contains duplicate paths")]
    changed = [
        path
        for path in changed_paths(root, revision)
        if _managed(path, manifest)
        and not _within(path, manifest["generated_file_roots"])
    ]
    errors = []
    if len(changed) > manifest["budgets"]["maximum_changed_files"]:
        errors.append(rejection("CP204", "changed-file budget exceeded"))
    for path in changed:
        if _within(path, manifest["forbidden_roots"]):
            errors.append(rejection("CP205", f"forbidden changed path: {path}"))
        if path not in declared:
            errors.append(rejection("CP206", f"changed path is outside declared write set: {path}"))
    for path in declared:
        if path not in changed:
            errors.append(rejection("CP207", f"declared path was not changed: {path}"))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-set", required=True, help="JSON array of repository-relative paths")
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    try:
        declared = json.loads(args.write_set)
        if not isinstance(declared, list) or not all(isinstance(path, str) for path in declared):
            raise PolicyError("write set must be a JSON array of strings")
        errors = check_write_set(repository_root(), declared, args.revision)
    except (json.JSONDecodeError, subprocess.CalledProcessError, PolicyError) as error:
        parser.error(str(error))
    if errors:
        parser.error("; ".join(errors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
