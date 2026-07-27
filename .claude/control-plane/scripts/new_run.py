"""Create a governed transaction run without authorizing it."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from common import PolicyError, repository_root
from create_baseline import build_baseline
from load_manifest import load_manifest
from record_event import GENESIS, append_event

ID = re.compile(r"^[a-z][a-z0-9-]{2,63}$")


def _write_new(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            if isinstance(value, str):
                handle.write(value)
            else:
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _hashed(value: dict[str, Any]) -> dict[str, Any]:
    value["content_hash"] = hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return value


def create_run(root: Path, run_id: str, request: dict[str, Any], write_set: list[str], writer_id: str, transaction_class: str = "standard", mode: str = "control-plane-maintenance") -> Path:
    if not ID.fullmatch(run_id) or not ID.fullmatch(writer_id):
        raise PolicyError("run and writer ids must match the declared identifier format")
    manifest = load_manifest(root)
    if mode != "control-plane-maintenance":
        raise PolicyError("CP304: application-development does not start a control-plane transaction")
    classes = manifest["transaction_policy"]["classes"]
    if transaction_class not in classes:
        raise PolicyError(f"CP301: unknown transaction class: {transaction_class}")
    if len(write_set) > classes[transaction_class]["maximum_changed_files"]:
        raise PolicyError(f"CP302: {transaction_class} transaction exceeds its changed-file limit")
    run = root / manifest["run_storage"]["run_directory"] / run_id
    if run.exists() or run.is_symlink():
        raise PolicyError(f"duplicate run id: {run_id}")
    run.mkdir(parents=True)
    try:
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        _write_new(run / "request.json", {"run_id": run_id, "received_at": now, "request": request})
        suffix = hashlib.sha256(run_id.encode()).hexdigest()[:16]
        baseline_id, plan_id, anchor_id = (f"baseline-{suffix}", f"plan-{suffix}", f"anchor-{suffix}")
        baseline = build_baseline(root, baseline_id, write_set)
        _write_new(run / "baseline.json", baseline)
        plan = _hashed({"plan_id": plan_id, "run_id": run_id, "created_at": now, "writer_id": writer_id, "lifecycle": "draft", "mode": mode, "transaction_class": transaction_class, "write_set": write_set, "baseline_id": baseline_id, "operations": ["propose", "validate", "verify"]})
        _write_new(run / "plan.json", plan)
        _write_new(run / "events.jsonl", "")
        _write_new(run / "proposed.patch", "")
        _write_new(run / "verification.json", {"lifecycle": "pending"})
        _write_new(run / "result.json", {"lifecycle": "pending"})
        _write_new(run / "trust-anchor.json", _hashed({"anchor_id": anchor_id, "created_at": now, "lifecycle": "active", "repository_revision": baseline["repository_revision"], "manifest_hash": baseline["manifest_hash"], "last_event_hash": GENESIS}))
        append_event(run, run_id, "run-started", "RECEIVED", {"writer_id": writer_id})
    except Exception:
        for child in run.iterdir():
            child.unlink()
        run.rmdir()
        raise
    return run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--request", type=Path, help="optional JSON request object")
    parser.add_argument("--summary", help="one-line request summary; use with --path")
    parser.add_argument("--write-set", type=Path, help="JSON write-set file")
    parser.add_argument("--path", action="append", help="one declared path; repeat instead of --write-set")
    parser.add_argument("--writer-id", required=True)
    parser.add_argument("--class", dest="transaction_class", choices=("lightweight", "standard", "sensitive"), default="standard")
    parser.add_argument("--mode", choices=("application-development", "control-plane-maintenance"), default="control-plane-maintenance")
    args = parser.parse_args()
    try:
        root = repository_root()
        if args.mode == "application-development":
            raise PolicyError("CP304: application-development does not start a control-plane transaction")
        if subprocess.run(["git", "-C", str(root), "status", "--porcelain"], text=True, capture_output=True, check=True).stdout:
            raise PolicyError("CP305: control-plane transaction requires a clean worktree")
        request = json.loads(args.request.read_text(encoding="utf-8")) if args.request else {"summary": args.summary}
        write_set = json.loads(args.write_set.read_text(encoding="utf-8")) if args.write_set else (args.path or [])
        if not isinstance(request, dict) or not isinstance(write_set, list) or not all(isinstance(path, str) for path in write_set):
            raise PolicyError("request must be an object and write set must be an array of strings")
        if not request.get("summary"):
            raise PolicyError("CP303: provide --summary or --request")
        print(create_run(root, args.run_id, request, write_set, args.writer_id, args.transaction_class, args.mode))
    except (OSError, json.JSONDecodeError, PolicyError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
