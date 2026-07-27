import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / ".claude/control-plane/scripts"))

from check_ownership import check_ownership, owner_for  # noqa: E402
from load_manifest import load_manifest  # noqa: E402


def test_ownership_maps_governed_paths_and_rejects_unowned_paths():
    manifest = load_manifest(ROOT)
    assert owner_for(".claude/control-plane/scripts/validate.py", manifest) == "control-plane"
    assert check_ownership(ROOT, ["tests/test_validate.py"]) == ["no specialist owner: tests/test_validate.py"]


def test_specialist_must_match_manifest_owner():
    errors = check_ownership(ROOT, [".claude/control-plane/scripts/validate.py"], "rule-config")
    assert errors == ["specialist 'rule-config' does not own .claude/control-plane/scripts/validate.py (owner: control-plane)"]
