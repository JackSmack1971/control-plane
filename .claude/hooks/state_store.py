"""Validated, atomic durable state for hook recovery."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd())).resolve()
STATE = ROOT / ".claude/control-plane/state"
SCHEMA_VERSION = "1.0"


def _schema() -> dict:
    return json.loads(
        (ROOT / ".claude/control-plane/schemas/workflow-state.schema.json").read_text(
            encoding="utf-8"
        )
    )


def _hash(value: dict) -> str:
    payload = dict(value)
    payload.pop("content_hash", None)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _details(value: dict | None) -> dict[str, str]:
    return {str(key)[:64]: str(item)[:500] for key, item in list((value or {}).items())[:20]}


def make(
    workflow_id: str,
    run_id: str,
    lifecycle: str,
    state: str,
    checkpoint: str,
    evidence_paths: list[str],
    details: dict | None = None,
) -> dict:
    value = {
        "schema_version": SCHEMA_VERSION,
        "workflow_id": workflow_id,
        "run_id": run_id,
        "updated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "lifecycle": lifecycle,
        "state": state,
        "recovery": {
            "checkpoint": checkpoint,
            "evidence_paths": evidence_paths,
            "details": _details(details),
        },
    }
    value["content_hash"] = _hash(value)
    Draft202012Validator(_schema(), format_checker=FormatChecker()).validate(value)
    return value


def write(name: str, value: dict) -> None:
    if "/" in name or "\\" in name or not name.endswith(".json"):
        raise ValueError("state name must be a JSON filename")
    if value.get("content_hash") != _hash(value):
        raise ValueError("state content hash mismatch")
    Draft202012Validator(_schema(), format_checker=FormatChecker()).validate(value)
    STATE.mkdir(parents=True, exist_ok=True)
    target = STATE / name
    temporary = target.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)


def read(name: str) -> dict:
    value = json.loads((STATE / name).read_text(encoding="utf-8"))
    if value.get("content_hash") != _hash(value):
        raise ValueError("state content hash mismatch")
    Draft202012Validator(_schema(), format_checker=FormatChecker()).validate(value)
    return value


def append(name: str, value: dict) -> None:
    if "/" in name or "\\" in name or not name.endswith(".jsonl"):
        raise ValueError("state name must be a JSONL filename")
    if value.get("content_hash") != _hash(value):
        raise ValueError("state content hash mismatch")
    Draft202012Validator(_schema(), format_checker=FormatChecker()).validate(value)
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / name).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
