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
from record_event import verify_ledger  # noqa: E402
from transition_run import transition  # noqa: E402


def make_run(name: str):
    run = create_run(ROOT, name, {"summary": "test"}, [".claude/rules/.gitkeep"], "writer-001")
    return run


def remove(run: Path):
    shutil.rmtree(run, ignore_errors=True)


def anchor(run: Path) -> str:
    return json.loads((run / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1])["event_hash"]


def test_legal_lifecycle_requires_external_approval():
    run = make_run("run-lifecycle-001")
    try:
        assert {path.name for path in run.iterdir()} == {"request.json", "baseline.json", "plan.json", "events.jsonl", "proposed.patch", "verification.json", "result.json", "trust-anchor.json"}
        for state in ("CLASSIFIED", "BASELINED", "PLANNED", "PLAN_VALIDATED", "APPLYING", "VERIFYING"):
            transition(ROOT, "run-lifecycle-001", state)
        with pytest.raises(PolicyError, match="approval_id"):
            transition(ROOT, "run-lifecycle-001", "COMMITTED")
        transition(ROOT, "run-lifecycle-001", "COMMITTED", {"approval_id": "review-001"})
        assert verify_ledger(run, "run-lifecycle-001", anchor(run))["events"] == 8
    finally:
        remove(run)


def test_illegal_and_terminal_transitions_are_rejected():
    run = make_run("run-lifecycle-002")
    try:
        with pytest.raises(PolicyError, match="illegal"):
            transition(ROOT, "run-lifecycle-002", "PLANNED")
        transition(ROOT, "run-lifecycle-002", "CANCELLED")
        with pytest.raises(PolicyError, match="illegal"):
            transition(ROOT, "run-lifecycle-002", "FAILED")
    finally:
        remove(run)


def test_failure_can_be_rolled_back():
    run = make_run("run-lifecycle-004")
    try:
        transition(ROOT, "run-lifecycle-004", "FAILED", {"reason": "validation failed"})
        transition(ROOT, "run-lifecycle-004", "ROLLED_BACK")
        assert verify_ledger(run, "run-lifecycle-004", anchor(run))["events"] == 3
    finally:
        remove(run)


def test_duplicate_run_ids_are_rejected():
    run = make_run("run-lifecycle-003")
    try:
        with pytest.raises(PolicyError, match="duplicate"):
            make_run("run-lifecycle-003")
    finally:
        remove(run)
