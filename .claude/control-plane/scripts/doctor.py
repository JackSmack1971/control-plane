"""Report whether this checkout can enforce the generated control-plane policy."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / ".claude/hooks"))
from common import repository_root
from state_store import STATE, append, make


def telemetry() -> dict[str, object]:
    samples, denied, false_denials, total = 0, 0, 0, 0.0
    try:
        rows = (STATE / "telemetry.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        rows = []
    for row in rows:
        try:
            details = json.loads(row)["recovery"]["details"]
            if details.get("kind") == "false-denial":
                false_denials += 1
                continue
            total += float(details.get("latency_ms", 0))
            samples += 1
            denied += details.get("diagnostic") != "ALLOW"
        except (KeyError, ValueError, json.JSONDecodeError):
            continue
    return {"samples": samples, "average_latency_ms": round(total / samples, 3) if samples else 0.0, "denials": denied, "false_denials": false_denials}


def diagnose(root: Path) -> dict[str, object]:
    settings = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
    commands = [hook["command"] for entries in settings["hooks"].values() for entry in entries for hook in entry["hooks"]]
    portable = all("powershell" not in command.lower() and "$env:" not in command.lower() for command in commands)
    return {
        "ok": portable and sys.version_info >= (3, 11),
        "platform": platform.system(),
        "python": platform.python_version(),
        "portable_hooks": portable,
        "sandbox_supported": platform.system() in {"Darwin", "Linux"},
        "diagnostics": [] if portable else ["CP401: hook commands use a platform-specific shell invocation"],
        "telemetry": telemetry(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--record-false-denial", metavar="CODE")
    args = parser.parse_args()
    if args.record_false_denial:
        append("telemetry.jsonl", make("control-plane-telemetry", "manual-report", "active", "awaiting-approval", "false denial", [], {"kind": "false-denial", "diagnostic": args.record_false_denial}))
    result = diagnose(repository_root())
    print(json.dumps(result, sort_keys=True) if args.json else "doctor: " + ("PASS" if result["ok"] else "FAIL"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
