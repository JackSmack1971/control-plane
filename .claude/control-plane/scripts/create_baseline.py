"""Capture pre-mutation evidence for an explicit governed write set."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from common import PolicyError, rejection, repo_path, repository_root
from inventory import canonical_bytes, check_inventory, sha256
from load_manifest import load_manifest


def _owner(path: str, manifest: dict[str, object]) -> str:
    for entry in manifest["specialist_ownership"]:
        prefix = entry["pattern"].removesuffix("/**")
        if path.startswith(prefix + "/") or path == prefix:
            return entry["specialist"]
    if _companion(path, manifest):
        return "companion"
    raise PolicyError(rejection("CP101", f"no policy owner for path: {path}"))


def _companion(path: str, manifest: dict[str, object]) -> bool:
    policy = manifest["transaction_policy"]
    return path in policy["companion_files"] or any(path == root or path.startswith(root + "/") for root in policy["companion_roots"])


def _generated(path: str, manifest: dict[str, object]) -> bool:
    return any(path == root or path.startswith(root + "/") for root in manifest["generated_file_roots"])


def _record(root: Path, relative: str, manifest: dict[str, object]) -> dict[str, object]:
    path = root / relative
    if path.is_symlink():
        raise PolicyError(f"symlink write target is not allowed: {relative}")
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", "--", relative], text=True, capture_output=True
    ).returncode == 0
    exists = path.exists()
    if exists and not tracked:
        raise PolicyError(f"untracked write target: {relative}")
    if tracked and not exists:
        raise PolicyError(f"deleted tracked write target: {relative}")
    if exists and not path.is_file():
        raise PolicyError(f"write target is not a regular file: {relative}")
    data = path.read_bytes() if exists else b""
    return {"path": relative, "exists": exists, "sha256": sha256(root, relative, data) if exists else None, "mode": format(path.stat().st_mode & 0o777, "03o") if exists else None, "owner": _owner(relative, manifest), "generated": _generated(relative, manifest)}


def build_baseline(root: Path, baseline_id: str, write_set: list[str]) -> dict[str, object]:
    manifest = load_manifest(root)
    inventory_path = root / "INVENTORY.json"
    if not check_inventory(root, inventory_path):
        raise PolicyError(rejection("CP102", "committed inventory is missing or does not match the working tree"))
    if not write_set or len(write_set) > manifest["budgets"]["maximum_changed_files"]:
        raise PolicyError(rejection("CP103", "write set must contain 1 to maximum_changed_files paths"))
    safe = []
    for value in write_set:
        path = repo_path(root, value)
        if any(path == forbidden or path.startswith(forbidden + "/") for forbidden in manifest["forbidden_roots"]):
            raise PolicyError(rejection("CP104", f"forbidden write target: {path}"))
        if not any(path == governed or path.startswith(governed + "/") for governed in manifest["governed_roots"]) and not _companion(path, manifest):
            raise PolicyError(rejection("CP105", f"write target is neither governed nor an allowed companion: {path}"))
        if _generated(path, manifest):
            raise PolicyError(rejection("CP106", f"generated write target: {path}"))
        safe.append(path)
    if len(set(safe)) != len(safe):
        raise PolicyError("write set contains duplicate paths")
    revision = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], text=True, capture_output=True, check=True).stdout.strip()
    manifest_hash = hashlib.sha256(canonical_bytes((root / ".claude/control-plane/manifest.yaml").read_bytes())).hexdigest()
    result = {"baseline_id": baseline_id, "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"), "repository_revision": revision, "manifest_hash": manifest_hash, "lifecycle": "active", "files": [_record(root, path, manifest) for path in sorted(safe)]}
    result["content_hash"] = hashlib.sha256(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-id", required=True)
    parser.add_argument("--write-set", required=True, type=Path, help="JSON array of proposed repository-relative paths")
    parser.add_argument("--output", required=True, help="new path below the declared run directory")
    args = parser.parse_args()
    try:
        root = repository_root()
        write_set = json.loads(args.write_set.read_text(encoding="utf-8"))
        if not isinstance(write_set, list) or not all(isinstance(item, str) for item in write_set):
            raise PolicyError("write set must be a JSON array of strings")
        output_path = repo_path(root, args.output)
        run_root = load_manifest(root)["run_storage"]["run_directory"]
        if not output_path.startswith(run_root + "/"):
            raise PolicyError(f"baseline output must stay under {run_root}")
        output = root / output_path
        candidate = root
        for part in output_path.split("/"):
            candidate /= part
            if candidate.is_symlink():
                raise PolicyError(f"baseline output path contains a symlink: {output_path}")
        if output.exists() or output.is_symlink():
            raise PolicyError(f"baseline output already exists: {output_path}")
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            output.parent.resolve().relative_to(root.resolve())
        except ValueError as error:
            raise PolicyError(f"baseline output escapes repository: {output_path}") from error
        output.write_text(json.dumps(build_baseline(root, args.baseline_id, write_set), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    except (OSError, json.JSONDecodeError, subprocess.CalledProcessError, PolicyError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
