"""Append and inspect tamper-evident run ledger events."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from common import PolicyError, repository_root
from load_manifest import load_manifest

GENESIS = "0" * 64
ID = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
NEXT = {
    "RECEIVED": {"CLASSIFIED", "FAILED", "CANCELLED"}, "CLASSIFIED": {"BASELINED", "FAILED", "CANCELLED"},
    "BASELINED": {"PLANNED", "FAILED", "CANCELLED"}, "PLANNED": {"PLAN_VALIDATED", "FAILED", "CANCELLED"},
    "PLAN_VALIDATED": {"APPLYING", "FAILED", "CANCELLED"}, "APPLYING": {"VERIFYING", "FAILED", "CANCELLED"},
    "VERIFYING": {"COMMITTED", "FAILED", "CANCELLED"}, "FAILED": {"ROLLED_BACK"},
}


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def event_hash(event: dict[str, Any]) -> str:
    value = dict(event)
    value.pop("event_hash", None)
    return hashlib.sha256(canonical(value)).hexdigest()


def _refresh_anchor(run: Path, last_event_hash: str) -> None:
    """Keep the run's anchor bound to the latest append-only ledger event."""
    path = run / "trust-anchor.json"
    anchor = json.loads(path.read_text(encoding="utf-8"))
    anchor["last_event_hash"] = last_event_hash
    payload = dict(anchor)
    payload.pop("content_hash", None)
    anchor["content_hash"] = hashlib.sha256(canonical(payload)).hexdigest()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(anchor, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def run_path(root: Path, run_id: str) -> Path:
    if not ID.fullmatch(run_id):
        raise PolicyError("run id must match the declared identifier format")
    path = root / load_manifest(root)["run_storage"]["run_directory"] / run_id
    if path.is_symlink() or not path.is_dir():
        raise PolicyError(f"run does not exist: {run_id}")
    return path


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise PolicyError(f"missing ledger: {path}")
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise PolicyError("truncated ledger")
    events = []
    for line in data.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise PolicyError("invalid ledger event") from error
        if not isinstance(event, dict):
            raise PolicyError("ledger event must be an object")
        events.append(event)
    return events


def _validate_event(event: dict[str, Any], root: Path) -> None:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
        schema = json.loads((root / ".claude/control-plane/schemas/run-event.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(event)
    except Exception as error:
        raise PolicyError(f"invalid ledger event: {error}") from error


def verify_events(events: list[dict[str, Any]], run_id: str, root: Path) -> dict[str, Any]:
    previous = GENESIS
    event_ids = set()
    for sequence, event in enumerate(events):
        _validate_event(event, root)
        if event.get("event_id") in event_ids:
            raise PolicyError("duplicate event id")
        event_ids.add(event.get("event_id"))
        if event.get("run_id") != run_id or event.get("sequence") != sequence:
            raise PolicyError("ledger sequence or run id mismatch")
        if event.get("previous_hash") != previous or event.get("event_hash") != event_hash(event):
            raise PolicyError("ledger hash chain mismatch")
        if sequence == 0 and (event.get("event_type") != "run-started" or event.get("state") != "RECEIVED"):
            raise PolicyError("ledger genesis event is invalid")
        if sequence and event.get("event_type") == "state-transition":
            prior = events[sequence - 1].get("state")
            if event.get("details", {}).get("from") != prior or event.get("state") not in NEXT.get(prior, set()):
                raise PolicyError("illegal historical lifecycle transition")
        previous = event["event_hash"]
    return {"events": len(events), "last_event_hash": previous}


def verify_ledger(run: Path, run_id: str, expected_last_hash: str) -> dict[str, Any]:
    root = repository_root(run)
    status = verify_events(read_events(run / "events.jsonl"), run_id, root)
    if expected_last_hash != status["last_event_hash"]:
        raise PolicyError("external trust anchor mismatch")
    return status


def append_event(run: Path, run_id: str, event_type: str, state: str, details: dict[str, Any] | None = None, expected_state: str | None = None) -> dict[str, Any]:
    lock = run / ".ledger.lock"
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise PolicyError("ledger is locked by another writer") from error
    try:
        events = read_events(run / "events.jsonl")
        status = verify_events(events, run_id, repository_root(run))
        if expected_state is not None and (not events or events[-1].get("state") != expected_state):
            raise PolicyError("run state changed before transition was recorded")
        if event_type == "run-started":
            if events or state != "RECEIVED":
                raise PolicyError("run-started is only valid as the genesis event")
        elif not events:
            raise PolicyError("only run-started may create the genesis event")
        elif event_type == "evidence-recorded":
            if events[-1].get("lifecycle") == "terminal" or state != events[-1].get("state"):
                raise PolicyError("evidence events cannot change or extend a terminal state")
        elif event_type == "state-transition":
            prior = events[-1].get("state")
            if details is None or details.get("from") != prior or state not in NEXT.get(prior, set()):
                raise PolicyError("illegal lifecycle transition")
            if state == "COMMITTED" and not details.get("approval_id"):
                raise PolicyError("COMMITTED requires externally supplied approval_id evidence")
        else:
            raise PolicyError("unknown event type")
        event = {
            "event_id": f"event-{uuid.uuid4().hex}", "run_id": run_id, "sequence": status["events"],
            "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"), "event_type": event_type,
            "lifecycle": "terminal" if state in {"COMMITTED", "ROLLED_BACK", "CANCELLED"} else "open",
            "state": state, "details": details or {}, "previous_hash": status["last_event_hash"],
        }
        event["event_hash"] = event_hash(event)
        _validate_event(event, repository_root(run))
        descriptor = os.open(run / "events.jsonl", os.O_WRONLY | os.O_APPEND)
        try:
            os.write(descriptor, canonical(event) + b"\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _refresh_anchor(run, event["event_hash"])
        return event
    finally:
        lock.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--event-type", required=True, choices=["evidence-recorded"])
    parser.add_argument("--details", default="{}", help="JSON object")
    args = parser.parse_args()
    try:
        details = json.loads(args.details)
        if not isinstance(details, dict):
            raise PolicyError("details must be a JSON object")
        root = repository_root()
        run = run_path(root, args.run_id)
        events = read_events(run / "events.jsonl")
        if not events:
            raise PolicyError("ledger is empty")
        if events[-1]["lifecycle"] == "terminal":
            raise PolicyError("terminal runs cannot record additional evidence")
        print(json.dumps(append_event(run, args.run_id, args.event_type, events[-1]["state"], details), sort_keys=True))
    except (OSError, json.JSONDecodeError, PolicyError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
