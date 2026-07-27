import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / ".claude/control-plane/scripts/check_package.py"


def command(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True)


def test_package_manifest_is_current():
    assert command("--check").returncode == 0


def test_package_check_detects_hash_mismatch_and_stale_artifact():
    assert command("--write").returncode == 0
    target = ROOT / ".claude/control-plane/scripts/common.py"
    original = target.read_text(encoding="utf-8")
    try:
        target.write_text(original + "\n", encoding="utf-8", newline="\n")
        result = command("--check")
        assert result.returncode != 0
        assert "hash mismatch: .claude/control-plane/scripts/common.py" in result.stderr
    finally:
        target.write_text(original, encoding="utf-8", newline="\n")


def test_package_check_detects_deleted_required_artifact():
    assert command("--write").returncode == 0
    target = ROOT / ".claude/rules/.gitkeep"
    original = target.read_bytes()
    try:
        target.unlink()
        result = command("--check")
        assert result.returncode != 0
        assert "missing required artifact: .claude/rules/.gitkeep" in result.stderr
    finally:
        target.write_bytes(original)


def test_package_write_rejects_deleted_tracked_artifact():
    target = ROOT / ".claude/rules/.gitkeep"
    original = target.read_bytes()
    try:
        target.unlink()
        assert command("--write").returncode != 0
    finally:
        target.write_bytes(original)
