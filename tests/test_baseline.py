import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / ".claude/control-plane/scripts"
sys.path.insert(0, str(SCRIPTS))

from common import PolicyError  # noqa: E402
from create_baseline import build_baseline  # noqa: E402


def test_baseline_captures_existing_and_new_governed_paths():
    baseline = build_baseline(ROOT, "base-001", [".claude/rules/.gitkeep", ".claude/rules/new.md"])
    records = {item["path"]: item for item in baseline["files"]}
    assert records[".claude/rules/.gitkeep"]["exists"] is True
    assert records[".claude/rules/new.md"] == {"path": ".claude/rules/new.md", "exists": False, "sha256": None, "mode": None, "owner": "rule-config", "generated": False}
    schema = json.loads((ROOT / ".claude/control-plane/schemas/baseline.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(baseline)


@pytest.mark.parametrize("path", ["src/app.py", ".claude/../secret", "other/file.txt", ".claude/control-plane/generated/README.md"])
def test_baseline_rejects_forbidden_traversal_and_undeclared_paths(path):
    with pytest.raises(PolicyError):
        build_baseline(ROOT, "base-001", [path])


def test_baseline_rejects_untracked_existing_path():
    path = ROOT / ".claude/rules/untracked.md"
    path.write_text("draft", encoding="utf-8")
    try:
        with pytest.raises(PolicyError, match="untracked"):
            build_baseline(ROOT, "base-001", [".claude/rules/untracked.md"])
    finally:
        path.unlink()


def test_baseline_rejects_deleted_tracked_path():
    path = ROOT / ".claude/rules/.gitkeep"
    original = path.read_bytes()
    try:
        path.unlink()
        with pytest.raises(PolicyError, match="inventory"):
            build_baseline(ROOT, "base-001", [".claude/rules/.gitkeep"])
    finally:
        path.write_bytes(original)


def test_baseline_rejects_stale_inventory_and_unsafe_output(tmp_path):
    inventory = ROOT / "INVENTORY.json"
    original = inventory.read_text(encoding="utf-8")
    try:
        inventory.write_text("{}\n", encoding="utf-8")
        with pytest.raises(PolicyError, match="inventory"):
            build_baseline(ROOT, "base-001", [".claude/rules/.gitkeep"])
    finally:
        inventory.write_text(original, encoding="utf-8", newline="\n")


def test_baseline_cli_rejects_unsafe_output_path(tmp_path):
    write_set = tmp_path / "write-set.json"
    write_set.write_text('[".claude/rules/.gitkeep"]', encoding="utf-8")
    command = [
        sys.executable,
        str(SCRIPTS / "create_baseline.py"),
        "--baseline-id",
        "base-001",
        "--write-set",
        str(write_set),
        "--output",
        "README.md",
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    assert result.returncode != 0
    assert "baseline output must stay" in result.stderr


def test_baseline_rejects_symlink_escape(tmp_path):
    outside = tmp_path / "outside.md"
    outside.write_text("outside", encoding="utf-8")
    link = ROOT / ".claude/rules/escape.md"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows runner")
    try:
        with pytest.raises(PolicyError):
            build_baseline(ROOT, "base-001", [".claude/rules/escape.md"])
    finally:
        link.unlink()
