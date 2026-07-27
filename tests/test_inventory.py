import hashlib
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / ".claude/control-plane/scripts"
sys.path.insert(0, str(SCRIPTS))

from inventory import build_inventory, canonical_bytes  # noqa: E402


def test_canonical_bytes_normalizes_checkout_line_endings_and_preserves_unicode():
    value = "café-雪\n".encode()
    assert canonical_bytes(value.replace(b"\n", b"\r\n")) == value
    assert hashlib.sha256(canonical_bytes(value)).hexdigest() == hashlib.sha256(value).hexdigest()
    assert canonical_bytes(b"A\r\nB", text=False) != canonical_bytes(b"A\nB", text=False)


def test_inventory_is_stable_and_excludes_generated_and_untracked_files():
    first = build_inventory(ROOT)
    assert first == build_inventory(ROOT)
    paths = [item["path"] for item in first["files"]]
    assert paths == sorted(paths)
    assert ".claude/control-plane/generated/README.md" not in paths
    assert ".claude/control-plane/scripts/common.py" in paths


def test_inventory_includes_empty_tracked_files():
    expected = hashlib.sha256(b"").hexdigest()
    assert canonical_bytes(b"") == b""
    assert hashlib.sha256(canonical_bytes(b"")).hexdigest() == expected


def test_inventory_check_detects_stale_committed_inventory():
    command = [sys.executable, str(SCRIPTS / "inventory.py")]
    assert subprocess.run([*command, "--check"], cwd=ROOT, text=True, capture_output=True).returncode == 0
    inventory = ROOT / "INVENTORY.json"
    original = inventory.read_text(encoding="utf-8")
    try:
        inventory.write_text("{}\n", encoding="utf-8")
        assert subprocess.run([*command, "--check"], cwd=ROOT, text=True, capture_output=True).returncode != 0
    finally:
        inventory.write_text(original, encoding="utf-8", newline="\n")
