import json
import shutil
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / ".claude/control-plane/scripts"
sys.path.insert(0, str(SCRIPTS))

from common import PolicyError  # noqa: E402
from new_run import create_run  # noqa: E402
from record_event import append_event, event_hash, verify_ledger  # noqa: E402
from transition_run import transition  # noqa: E402


def make_run(name: str):
    return create_run(ROOT, name, {"summary": "test"}, [".claude/rules/.gitkeep"], "writer-001")


def remove(run: Path):
    shutil.rmtree(run, ignore_errors=True)


def anchor(run: Path) -> str:
    return json.loads((run / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1])["event_hash"]


def test_tampered_and_interrupted_ledgers_fail_verification():
    run = make_run("run-ledger-001")
    try:
        expected = anchor(run)
        ledger = run / "events.jsonl"
        ledger.write_text(ledger.read_text(encoding="utf-8").replace("RECEIVED", "ALTERED"), encoding="utf-8")
        with pytest.raises(PolicyError):
            verify_ledger(run, "run-ledger-001", expected)
        ledger.write_bytes(b"{")
        with pytest.raises(PolicyError, match="truncated"):
            verify_ledger(run, "run-ledger-001", expected)
    finally:
        remove(run)


def test_duplicate_sequences_fail_verification():
    run = make_run("run-ledger-002")
    try:
        transition(ROOT, "run-ledger-002", "CLASSIFIED")
        events = [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        events[1]["sequence"] = 0
        events[1]["event_hash"] = event_hash(events[1])
        (run / "events.jsonl").write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")
        with pytest.raises(PolicyError):
            verify_ledger(run, "run-ledger-002", anchor(run))

    finally:
        remove(run)


def test_replayed_event_ids_fail_verification():
    run = make_run("run-ledger-003")
    try:
        transition(ROOT, "run-ledger-003", "CLASSIFIED")
        events = [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        events[1]["event_id"] = events[0]["event_id"]
        events[1]["event_hash"] = event_hash(events[1])
        (run / "events.jsonl").write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")
        with pytest.raises(PolicyError, match="duplicate event id"):
            verify_ledger(run, "run-ledger-003", anchor(run))
    finally:
        remove(run)


def test_rehashed_ledger_requires_an_external_anchor():
    run = make_run("run-ledger-004")
    try:
        expected = anchor(run)
        event = json.loads((run / "events.jsonl").read_text(encoding="utf-8"))
        event["details"] = {"rewritten": True}
        event["event_hash"] = event_hash(event)
        (run / "events.jsonl").write_text(json.dumps(event, sort_keys=True) + "\n", encoding="utf-8")
        with pytest.raises(PolicyError, match="external trust anchor"):
            verify_ledger(run, "run-ledger-004", expected)
    finally:
        remove(run)


def test_evidence_cannot_change_lifecycle_state():
    run = make_run("run-ledger-005")
    try:
        with pytest.raises(PolicyError, match="cannot change"):
            append_event(run, "run-ledger-005", "evidence-recorded", "COMMITTED", {})
    finally:
        remove(run)
