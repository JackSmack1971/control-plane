import copy
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / ".claude/control-plane/scripts"
sys.path.insert(0, str(SCRIPTS))

from common import PolicyError, repo_path  # noqa: E402
from load_manifest import load_manifest  # noqa: E402


def test_manifest_loads_and_normalizes_paths():
    manifest = load_manifest(ROOT)
    assert manifest["derived_artifacts"] == [
        ".claude/control-plane/generated/README.md",
        ".claude/control-plane/generated/ownership-map.json",
        ".claude/control-plane/generated/protected-paths.json",
        ".claude/control-plane/generated/agent-capabilities.json",
        ".claude/control-plane/generated/policy-summary.md",
        ".claude/control-plane/generated/ownership-evals.yaml",
    ]


@pytest.mark.parametrize("value", [".", "a/./b", "/etc/passwd", "C:/Windows", "a/../b", "a\\b"])
def test_unsafe_paths_fail(value):
    with pytest.raises(PolicyError):
        repo_path(ROOT, value)


def test_symlink_escape_fails(tmp_path):
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    try:
        (tmp_path / "escape").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows runner")
    with pytest.raises(PolicyError):
        repo_path(tmp_path, "escape/file")


def test_conflicting_ownership_fails(tmp_path):
    control = tmp_path / ".claude/control-plane"
    schemas = control / "schemas"
    schemas.mkdir(parents=True)
    (schemas / "manifest.schema.json").write_text(
        (ROOT / ".claude/control-plane/schemas/manifest.schema.json").read_text(), encoding="utf-8"
    )
    manifest = copy.deepcopy(load_manifest(ROOT))
    manifest["specialist_ownership"].append({"pattern": ".claude/agents/private/**", "specialist": "other"})
    (control / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    with pytest.raises(PolicyError, match="contradictory ownership"):
        load_manifest(tmp_path)


def test_malformed_glob_fails():
    for pattern in (".claude/agents/*.json", ".claude/agents/*"):
        with pytest.raises(PolicyError, match="malformed glob"):
            repo_path(ROOT, pattern, glob=True)
