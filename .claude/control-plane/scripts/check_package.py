"""Create and check the tracked control-plane package manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from common import PolicyError, repository_root
from inventory import canonical_bytes, sha256
from load_manifest import load_manifest

MANIFEST_NAME = "PACKAGE_MANIFEST.json"
EXCLUDED = {MANIFEST_NAME, "INVENTORY.json"}


def _tracked(root: Path) -> list[str]:
    result = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], text=False, capture_output=True, check=True)
    return sorted(path.decode("utf-8") for path in result.stdout.split(b"\0") if path)


def _eligible(root: Path) -> list[str]:
    manifest = load_manifest(root)
    run_root = manifest["run_storage"]["run_directory"]
    return [path for path in _tracked(root) if path not in EXCLUDED and not (path == run_root or path.startswith(run_root + "/"))]


def build_manifest(root: Path, *, allow_missing: bool = False) -> dict[str, object]:
    run_root = load_manifest(root)["run_storage"]["run_directory"]
    required = {}
    for relative in _eligible(root):
        path = root / relative
        if not path.exists() and not path.is_symlink():
            if allow_missing:
                continue
            raise PolicyError(f"tracked package path is missing: {relative}")
        if path.is_symlink():
            data = path.readlink().as_posix().encode("utf-8")
        elif path.is_file():
            data = path.read_bytes()
        else:
            raise PolicyError(f"tracked package path is not a file: {relative}")
        required[relative] = sha256(root, relative, data) if path.is_file() else hashlib.sha256(canonical_bytes(data, text=False)).hexdigest()
    return {"schema_version": "1.0", "excluded": sorted(EXCLUDED | {run_root}), "required": required}


def render(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def check(root: Path, path: Path) -> list[str]:
    if not path.is_file():
        return [f"missing manifest: {path.name}"]
    try:
        expected = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"invalid manifest: {error}"]
    actual = build_manifest(root, allow_missing=True)
    errors = []
    expected_required = expected.get("required", {})
    actual_required = actual["required"]
    for item in sorted(set(expected_required) - set(actual_required)):
        errors.append(f"missing required artifact: {item}")
    for item in sorted(set(actual_required) - set(expected_required)):
        errors.append(f"unexpected stale artifact: {item}")
    for item in sorted(set(expected_required) & set(actual_required)):
        if expected_required[item] != actual_required[item]:
            errors.append(f"hash mismatch: {item}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write PACKAGE_MANIFEST.json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        root = repository_root()
        path = root / MANIFEST_NAME
        if args.write:
            path.write_text(render(build_manifest(root)), encoding="utf-8", newline="\n")
        if args.check or not args.write:
            errors = check(root, path)
            if errors:
                raise PolicyError("package integrity failed: " + "; ".join(errors))
    except (OSError, subprocess.CalledProcessError, PolicyError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
