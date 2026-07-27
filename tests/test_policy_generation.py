import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / ".claude/control-plane/scripts/generate_policy.py"
GENERATED = ROOT / ".claude/control-plane/generated"
ARTIFACT = "ownership-map.json"


def command(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True)


def hashes():
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in GENERATED.glob("*.*") if path.name != ".gitkeep"}


def test_generation_is_deterministic_and_check_passes():
    assert command().returncode == 0
    first = hashes()
    assert command().returncode == 0
    assert hashes() == first
    assert command("--check").returncode == 0


def test_check_detects_manual_modification_and_stdout():
    assert command().returncode == 0
    path = GENERATED / ARTIFACT
    original = path.read_text(encoding="utf-8")
    try:
        path.write_text(original + "manual edit\n", encoding="utf-8")
        result = command("--check")
        assert result.returncode != 0
        assert ARTIFACT in result.stderr
    finally:
        path.write_text(original, encoding="utf-8")
    result = command("--stdout", ARTIFACT)
    assert result.returncode == 0
    assert result.stdout == original


def test_unknown_stdout_artifact_fails():
    assert command("--stdout", "unknown.json").returncode != 0
