import importlib.util
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / ".claude/hooks"))
SPEC = importlib.util.spec_from_file_location("guard_write", ROOT / ".claude/hooks/guard_write.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def policy(tmp_path):
    generated = tmp_path / ".claude/control-plane/generated"
    generated.mkdir(parents=True)
    (generated / "protected-paths.json").write_text(json.dumps({"forbidden_roots": [".git"], "generated_file_roots": [".claude/control-plane/generated"]}))
    (generated / "ownership-map.json").write_text(json.dumps({"ownership": {".claude/hooks/**": "hook-config"}}))


def test_guard_allows_declared_and_denies_protected_unowned_and_recovery(monkeypatch, tmp_path):
    import state_store

    policy(tmp_path); state = tmp_path / ".claude/control-plane/state"; state.mkdir(parents=True)
    monkeypatch.setattr(guard, "ROOT", tmp_path); monkeypatch.setattr(guard, "STATE", state)
    monkeypatch.setattr(state_store, "ROOT", ROOT); monkeypatch.setattr(state_store, "STATE", state)
    state_store.write("recovery.json", state_store.make("governed-change", "run-001", "active", "planned", "baseline", []))
    state_store.write("active-transaction.json", state_store.make("governed-change", "run-001", "active", "planned", "baseline", [".claude/hooks/ok.py"]))
    assert guard.allowed(".claude/hooks/ok.py") == (True, "")
    assert guard.allowed(".claude/hooks/no.py") == (False, "undeclared write path")
    assert guard.allowed(".git/config") == (False, "forbidden write path")
    state_store.write("recovery.json", state_store.make("governed-change", "run-001", "terminal", "rejected", "invalid", []))
    assert guard.allowed(".claude/hooks/ok.py") == (False, "recovery state is incomplete")


def test_shell_read_is_ignored_and_write_without_target_is_denied():
    assert guard.write_paths({"tool_name": "Bash", "tool_input": {"command": "git status"}}) == []
    assert guard.write_paths({"tool_name": "Bash", "tool_input": {"command": "echo x > /tmp/x"}}) == [None]
    assert guard.write_paths({"tool_name": "Bash", "tool_input": {"command": "git config x y"}}) == [None]


def test_guard_denies_unowned_and_symlink_escape(monkeypatch, tmp_path):
    policy(tmp_path); monkeypatch.setattr(guard, "ROOT", tmp_path); monkeypatch.setattr(guard, "STATE", tmp_path / "state")
    assert guard.allowed("README.md") == (False, "unowned write path")
    outside = tmp_path.parent / "outside"; outside.mkdir(exist_ok=True)
    try: (tmp_path / "link").symlink_to(outside, target_is_directory=True)
    except OSError: pytest.skip("symlink creation is not permitted on this host")
    assert guard.rel(str(tmp_path / "link" / "file")) is None


def test_guard_emits_a_denial_for_an_undeclared_write(monkeypatch, tmp_path, capsys):
    policy(tmp_path); state = tmp_path / ".claude/control-plane/state"; state.mkdir(parents=True)
    monkeypatch.setattr(guard, "ROOT", tmp_path); monkeypatch.setattr(guard, "STATE", state)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(tmp_path / ".claude/hooks/no.py")}})))
    assert guard.main() == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_settings_guard_every_bash_command():
    settings = json.loads((ROOT / ".claude/settings.json").read_text())
    bash = next(item for item in settings["hooks"]["PreToolUse"] if item["matcher"] == "Bash")
    assert len(bash["hooks"]) == 1
    assert "if" not in bash["hooks"][0]


def test_mutation_and_failure_hooks_persist_evidence(monkeypatch, tmp_path):
    import record_failure
    import record_mutation

    import state_store

    monkeypatch.setattr(state_store, "ROOT", ROOT); monkeypatch.setattr(state_store, "STATE", tmp_path)
    monkeypatch.setattr(record_mutation, "event", lambda: {"tool_name": "Write", "tool_input": {"file_path": str(ROOT / ".claude/hooks/x.py")}})
    monkeypatch.setattr(record_mutation, "write_paths", lambda _: [".claude/hooks/x.py"])
    record_mutation.main()
    monkeypatch.setattr(record_failure, "event", lambda: {"error": "failed"})
    record_failure.main()
    assert json.loads((tmp_path / "mutations.jsonl").read_text())["recovery"]["evidence_paths"] == [".claude/hooks/x.py"]
    assert json.loads((tmp_path / "failures.jsonl").read_text())["recovery"]["details"]["error"] == "failed"


def test_dirty_state_and_compaction_fail_closed(monkeypatch, tmp_path, capsys):
    import post_compact
    import validate_dirty_state

    monkeypatch.setattr(validate_dirty_state, "ROOT", tmp_path)
    monkeypatch.setattr(validate_dirty_state, "protected", lambda: (set(), set(), {}))
    monkeypatch.setattr(validate_dirty_state, "allowed", lambda _: (False, "undeclared write path"))
    monkeypatch.setattr(validate_dirty_state.subprocess, "run", lambda *_, **__: SimpleNamespace(stdout="?? .claude/hooks/x.py\n"))
    validate_dirty_state.main()
    assert json.loads(capsys.readouterr().out)["decision"] == "block"
    import state_store

    monkeypatch.setattr(state_store, "ROOT", ROOT); monkeypatch.setattr(state_store, "STATE", tmp_path)
    post_compact.main()
    assert state_store.read("recovery.json")["state"] == "rejected"


def test_hooks_do_not_invoke_claude_tools_recursively():
    for name in ("guard_write.py", "record_mutation.py", "record_failure.py", "validate_dirty_state.py"):
        assert "subprocess.run" not in (ROOT / ".claude/hooks" / name).read_text() or name == "validate_dirty_state.py"
