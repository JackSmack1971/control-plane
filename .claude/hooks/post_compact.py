from __future__ import annotations
import hashlib, json, subprocess
from guard_write import ROOT, STATE

def main():
    try:
        value = json.loads((STATE / "trust-anchor.json").read_text())
        digest = value.pop("content_hash")
        if digest != hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest(): raise ValueError("trust anchor hash")
        if value["manifest_hash"] != hashlib.sha256((ROOT / ".claude/control-plane/manifest.yaml").read_bytes()).hexdigest(): raise ValueError("manifest")
        if value["repository_revision"] != subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip(): raise ValueError("revision")
        from jsonschema import Draft202012Validator
        Draft202012Validator(json.loads((ROOT / ".claude/control-plane/schemas/trust-anchor.schema.json").read_text())).validate({**value, "content_hash": digest})
    except (KeyError, OSError, ValueError, json.JSONDecodeError):
        STATE.mkdir(parents=True, exist_ok=True); (STATE / "recovery-blocked").write_text("invalid trust anchor\n", encoding="utf-8")
    else: (STATE / "recovery-blocked").unlink(missing_ok=True)
if __name__ == "__main__": main()
