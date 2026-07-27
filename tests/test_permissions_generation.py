import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / ".claude/control-plane/scripts"
sys.path.insert(0, str(SCRIPTS))

from common import PolicyError  # noqa: E402
from generate_policy import generate, permission_policy, render  # noqa: E402
from load_manifest import load_manifest  # noqa: E402


def test_permission_fixtures_cover_allow_ask_and_deny():
    policy = permission_policy(load_manifest(ROOT))["permissions"]
    fixtures = json.loads((ROOT / "tests/fixtures/permission-outcomes.json").read_text())["fixtures"]
    for fixture in fixtures:
        assert any(_matches(rule, fixture["tool"], fixture["input"]) for rule in policy[fixture["outcome"]])


def _matches(rule, tool, value):
    if not rule.startswith(f"{tool}("):
        return False
    pattern = rule[len(tool) + 1 : -1]
    return value.startswith(pattern.rstrip("*")) if pattern.endswith("*") else value == pattern


def test_generated_settings_match_the_permission_artifact_and_are_deterministic():
    manifest = load_manifest(ROOT)
    assert render(manifest)["permission-policy.json"] == render(manifest)["permission-policy.json"]
    settings = json.loads((ROOT / ".claude/settings.json").read_text())
    assert settings["permissions"] == permission_policy(manifest)["permissions"]
    assert generate(ROOT, check=True)


def test_generation_check_detects_settings_drift(tmp_path):
    shutil.copytree(ROOT / ".claude/control-plane", tmp_path / ".claude/control-plane")
    shutil.copy(ROOT / ".claude/settings.json", tmp_path / ".claude/settings.json")
    settings = tmp_path / ".claude/settings.json"
    settings.write_text("{}\n", encoding="utf-8")
    with pytest.raises(PolicyError, match="settings.json"):
        generate(tmp_path, check=True)


def test_shell_compositions_fail_closed_for_protected_paths(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("guard_write", ROOT / ".claude/hooks/guard_write.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    generated = tmp_path / ".claude/control-plane/generated"
    generated.mkdir(parents=True)
    (generated / "protected-paths.json").write_text(json.dumps({"forbidden_roots": [".git"], "generated_file_roots": []}))
    (generated / "ownership-map.json").write_text(json.dumps({"ownership": {}}))
    monkeypatch.setattr(guard, "ROOT", tmp_path)
    monkeypatch.setattr(guard, "STATE", tmp_path / "state")
    for command in ("rm './.git/config'", "rm ../.git/config", "cd .git; rm config", "echo x > .git/config", "powershell Remove-Item .git/config", "git status $(rm .git/config)", "python -m pytest `rm .git/config`"):
        for path in guard.write_paths({"tool_name": "Bash", "tool_input": {"command": command}}):
            assert path is None or guard.allowed(path)[0] is False


def test_guard_allows_generated_validator_commands():
    spec = importlib.util.spec_from_file_location("guard_write", ROOT / ".claude/hooks/guard_write.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    assert guard.write_paths({"tool_name": "Bash", "tool_input": {"command": "python -m pytest tests/test_permissions_generation.py"}}) == []
