import copy
import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).parents[1]
SCHEMA_DIR = ROOT / ".claude" / "control-plane" / "schemas"
HASH = "a" * 64
TIMESTAMP = "2026-07-26T12:00:00Z"


def schema(name):
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def validate(name, instance):
    Draft202012Validator.check_schema(schema(name))
    Draft202012Validator(schema(name), format_checker=FormatChecker()).validate(instance)


EXAMPLES = {
    "change-plan.schema.json": {"plan_id": "plan-001", "run_id": "run-001", "created_at": TIMESTAMP, "writer_id": "writer-001", "lifecycle": "draft", "write_set": [".claude/rules/example.md"], "baseline_id": "base-001", "operations": ["propose"], "content_hash": HASH},
    "baseline.schema.json": {"baseline_id": "base-001", "created_at": TIMESTAMP, "repository_revision": "b" * 40, "manifest_hash": HASH, "lifecycle": "active", "content_hash": HASH},
    "run-event.schema.json": {"event_id": "event-001", "run_id": "run-001", "sequence": 0, "occurred_at": TIMESTAMP, "event_type": "run-started", "lifecycle": "open", "previous_hash": "0" * 64, "event_hash": HASH},
    "verification.schema.json": {"verification_id": "verify-001", "run_id": "run-001", "verified_at": TIMESTAMP, "verifier_id": "verifier-001", "lifecycle": "completed", "deterministic_checks": [{"name": "pytest", "command": "pytest", "status": "passed", "output_hash": HASH}], "semantic_findings": [], "content_hash": HASH},
    "result.schema.json": {"result_id": "result-001", "run_id": "run-001", "completed_at": TIMESTAMP, "lifecycle": "terminal", "terminal_result": "verified", "verification_id": "verify-001", "content_hash": HASH},
    "trust-anchor.schema.json": {"anchor_id": "anchor-001", "created_at": TIMESTAMP, "lifecycle": "active", "repository_revision": "b" * 40, "manifest_hash": HASH, "last_event_hash": HASH, "content_hash": HASH},
    "workflow-state.schema.json": {"workflow_id": "flow-001", "run_id": "run-001", "updated_at": TIMESTAMP, "lifecycle": "active", "state": "validating", "content_hash": HASH},
}


def test_all_schemas_pass_meta_validation():
    for path in SCHEMA_DIR.glob("*.schema.json"):
        Draft202012Validator.check_schema(schema(path.name))


def test_manifest_validates_against_its_schema():
    validate("manifest.schema.json", yaml.safe_load((ROOT / ".claude/control-plane/manifest.yaml").read_text()))


@pytest.mark.parametrize("name", EXAMPLES)
def test_valid_examples_pass(name):
    validate(name, EXAMPLES[name])


@pytest.mark.parametrize("name", EXAMPLES)
def test_missing_required_field_fails(name):
    value = copy.deepcopy(EXAMPLES[name])
    value.pop(next(iter(schema(name)["required"])))
    with pytest.raises(ValidationError):
        validate(name, value)


@pytest.mark.parametrize("bad_path", ["/etc/passwd", "C:/Windows/system32", ".claude/../secrets"])
def test_absolute_and_traversal_paths_fail(bad_path):
    value = copy.deepcopy(EXAMPLES["change-plan.schema.json"])
    value["write_set"] = [bad_path]
    with pytest.raises(ValidationError):
        validate("change-plan.schema.json", value)


def test_genesis_event_requires_the_zero_previous_hash():
    value = copy.deepcopy(EXAMPLES["run-event.schema.json"])
    value["previous_hash"] = HASH
    with pytest.raises(ValidationError):
        validate("run-event.schema.json", value)


@pytest.mark.parametrize("name", EXAMPLES)
def test_unknown_lifecycle_states_fail(name):
    value = copy.deepcopy(EXAMPLES[name])
    value["lifecycle"] = "invented"
    with pytest.raises(ValidationError):
        validate(name, value)


@pytest.mark.parametrize("name", EXAMPLES)
def test_malformed_hashes_fail(name):
    value = copy.deepcopy(EXAMPLES[name])
    hash_key = next(key for key in value if key.endswith("hash"))
    value[hash_key] = "not-a-sha256"
    with pytest.raises(ValidationError):
        validate(name, value)


def test_manifest_rejects_unknown_fields():
    value = yaml.safe_load((ROOT / ".claude/control-plane/manifest.yaml").read_text())
    value["implicit_default"] = True
    with pytest.raises(ValidationError):
        validate("manifest.schema.json", value)
