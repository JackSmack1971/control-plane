from __future__ import annotations
import hashlib, json, subprocess
from datetime import UTC, datetime
from guard_write import ROOT, STATE

def main():
    STATE.mkdir(parents=True, exist_ok=True); revision = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    value = {"anchor_id": "hook-compact", "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"), "lifecycle": "active", "repository_revision": revision, "manifest_hash": hashlib.sha256((ROOT / ".claude/control-plane/manifest.yaml").read_bytes()).hexdigest(), "last_event_hash": "0" * 64}
    value["content_hash"] = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest(); (STATE / "trust-anchor.json").write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
if __name__ == "__main__": main()
