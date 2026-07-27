import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / ".claude/control-plane/scripts"))

import check_write_set  # noqa: E402


def test_write_set_rejects_governed_change_not_declared(monkeypatch):
    monkeypatch.setattr(check_write_set, "changed_paths", lambda root, revision: [".claude/control-plane/scripts/validate.py"])
    errors = check_write_set.check_write_set(ROOT, [".claude/control-plane/scripts/check_write_set.py"], "HEAD")
    assert errors == [
        "CP206: changed path is outside declared write set: .claude/control-plane/scripts/validate.py",
        "CP207: declared path was not changed: .claude/control-plane/scripts/check_write_set.py",
    ]


def test_write_set_enforces_changed_file_budget(monkeypatch):
    paths = [f".claude/control-plane/scripts/file-{number}.py" for number in range(21)]
    monkeypatch.setattr(check_write_set, "changed_paths", lambda root, revision: paths)
    errors = check_write_set.check_write_set(ROOT, paths, "HEAD")
    assert "CP202: declared write set exceeds changed-file budget" in errors


def test_write_set_rejects_unused_declared_authority(monkeypatch):
    monkeypatch.setattr(check_write_set, "changed_paths", lambda root, revision: [])
    errors = check_write_set.check_write_set(ROOT, [".claude/control-plane/scripts/validate.py"], "HEAD")
    assert errors == ["CP207: declared path was not changed: .claude/control-plane/scripts/validate.py"]


def test_write_set_excludes_regenerated_policy_from_declared_authority(monkeypatch):
    monkeypatch.setattr(check_write_set, "changed_paths", lambda root, revision: [".claude/control-plane/generated/agent-capabilities.json"])
    assert check_write_set.check_write_set(ROOT, [".claude/control-plane/scripts/validate.py"], "HEAD") == [
        "CP207: declared path was not changed: .claude/control-plane/scripts/validate.py"
    ]
