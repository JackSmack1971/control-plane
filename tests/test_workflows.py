import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / ".claude/hooks"))

from state_store import make, read, write  # noqa: E402


REQUIRED = {
    "version",
    "trigger",
    "prerequisites",
    "state_schema",
    "stages",
    "owning_specialist",
    "permitted_mutations",
    "deterministic_gates",
    "human_approval_gates",
    "interruption_behavior",
    "terminal_conditions",
    "evidence_outputs",
}


def test_workflow_contracts_are_complete_and_self_improvement_is_evidence_gated():
    workflows = {
        path.stem: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in (ROOT / ".claude/workflows").glob("*.yaml")
    }
    assert set(workflows) == {
        "governed-change",
        "independent-verification",
        "rollback",
        "policy-regeneration",
        "control-plane-audit",
        "evidence-based-self-improvement",
    }
    for workflow in workflows.values():
        assert REQUIRED <= workflow.keys()
        assert workflow["version"] == "1.0"
    improvement = workflows["evidence-based-self-improvement"]
    assert "two-independent-evidence-items" in improvement["prerequisites"]
    assert "explicit-approval-before-manifest-change" in improvement["human_approval_gates"]
    assert "session" not in improvement["trigger"]


def test_workflow_contracts_cover_completion_rejection_interruption_resume_and_rollback():
    workflows = {
        path.stem: yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in (ROOT / ".claude/workflows").glob("*.yaml")
    }
    assert "verified" in workflows["governed-change"]["terminal_conditions"]
    assert "failed" in workflows["independent-verification"]["terminal_conditions"]
    assert "rolled-back" in workflows["rollback"]["terminal_conditions"]
    assert "resume" in workflows["governed-change"]["interruption_behavior"]


def test_durable_state_is_versioned_validated_and_atomic(monkeypatch, tmp_path):
    import state_store

    monkeypatch.setattr(state_store, "ROOT", ROOT)
    monkeypatch.setattr(state_store, "STATE", tmp_path)
    value = make(
        "governed-change", "run-001", "active", "planned", "baseline", [".claude/rules/example.md"]
    )
    write("active-transaction.json", value)
    assert read("active-transaction.json") == value
    assert not list(tmp_path.glob("*.tmp"))
    tampered = json.loads((tmp_path / "active-transaction.json").read_text(encoding="utf-8"))
    tampered["state"] = "verified"
    (tmp_path / "active-transaction.json").write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        read("active-transaction.json")


def test_incompatible_state_version_is_rejected_before_resume(monkeypatch, tmp_path):
    import state_store

    monkeypatch.setattr(state_store, "ROOT", ROOT)
    monkeypatch.setattr(state_store, "STATE", tmp_path)
    value = make("governed-change", "run-001", "active", "planned", "baseline", [])
    value["schema_version"] = "2.0"
    value["content_hash"] = state_store._hash(value)
    with pytest.raises(Exception):
        write("recovery.json", value)
