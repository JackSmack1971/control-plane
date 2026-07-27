"""Small fail-closed path guard shared by project hooks."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from state_store import append, make, read

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path.cwd())).resolve()
STATE = ROOT / ".claude/control-plane/state"
MUTATING = re.compile(
    r"(?:^|[;&|]\s*|\s)(?:rm|mv|cp|mkdir|touch|tee|sed\s+-i|Set-Content|Add-Content|git\s+(?:apply|clean|checkout|reset|config)|python(?:3)?\b|.*(?:>|>>))(?:\s|$)",
    re.I,
)
READ_ONLY = re.compile(
    r"^\s*(?:git\s+(?:status|diff|log|show|branch)|(?:ls|pwd|rg|grep|Get-Content|type)\b|echo\b(?!.*(?:>|>>)))",
    re.I,
)


def event() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}


def emit(event_name: str, reason: str, *, stop: bool = False) -> None:
    if stop:
        print(json.dumps({"decision": "block", "reason": reason}))
    else:
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": event_name,
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )


def protected() -> tuple[set[str], set[str], dict[str, str]]:
    try:
        policy = json.loads(
            (ROOT / ".claude/control-plane/generated/protected-paths.json").read_text()
        )
        owners = json.loads(
            (ROOT / ".claude/control-plane/generated/ownership-map.json").read_text()
        )["ownership"]
        return set(policy["forbidden_roots"]), set(policy["generated_file_roots"]), owners
    except (OSError, KeyError, json.JSONDecodeError):
        return {".git"}, {".claude/control-plane/generated"}, {}


def safe_bash(command: str) -> bool:
    if re.search(r"[;&|><$`()\r\n]", command):
        return False
    try:
        policy = json.loads(
            (ROOT / ".claude/control-plane/generated/permission-policy.json").read_text()
        )
        allowed = [
            item[5:-2]
            for item in policy["permissions"]["allow"]
            if item.startswith("Bash(") and item.endswith("*)")
        ]
    except (OSError, KeyError, json.JSONDecodeError):
        allowed = []
    return any(command.strip().startswith(item) for item in allowed) or bool(
        READ_ONLY.match(command)
    )


def rel(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return (Path(value).resolve().relative_to(ROOT)).as_posix()
    except ValueError:
        return None


def write_paths(data: dict) -> list[str | None]:
    tool, args = data.get("tool_name"), data.get("tool_input", {})
    if tool in {"Write", "Edit", "NotebookEdit"}:
        return [rel(args.get("file_path"))]
    if tool != "Bash":
        return []
    command = str(args.get("command", ""))
    if safe_bash(command):
        return []
    values = re.findall(
        r"(?:>|>>|\b(?:rm|mv|cp|mkdir|touch|tee)\s+)(?:['\"]([^'\"]+)['\"]|([^\s;&|]+))", command
    )
    return [rel(a or b) for a, b in values] or [None]


def allowed(path: str) -> tuple[bool, str]:
    forbidden, generated, owners = protected()
    if any(path == item or path.startswith(item + "/") for item in forbidden):
        return False, "CP501: forbidden write path"
    if any(path == item or path.startswith(item + "/") for item in generated):
        return False, "CP502: generated write path"
    owner = next(
        (
            name
            for pattern, name in owners.items()
            if path == pattern.removesuffix("/**")
            or pattern.endswith("/**")
            and path.startswith(pattern.removesuffix("/**") + "/")
        ),
        None,
    )
    if owner is None:
        return False, "CP503: unowned write path"
    try:
        recovery = read("recovery.json")
        if recovery["state"] == "rejected":
            return False, "CP504: recovery state is incomplete"
        declared = set(read("active-transaction.json")["recovery"]["evidence_paths"])
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return False, "CP505: no active declared write set"
    return (True, "") if path in declared else (False, "CP506: undeclared write path")


def main() -> int:
    started = time.perf_counter()
    data = event()
    paths = write_paths(data)
    reason = ""
    for path in paths:
        if path is None:
            reason = "CP507: unverifiable shell mutation"
            break
        ok, reason = allowed(path)
        if not ok:
            break
    try:
        append("telemetry.jsonl", make("control-plane-telemetry", "hook-guard", "active", "awaiting-approval", "guard decision", [], {"latency_ms": f"{(time.perf_counter() - started) * 1000:.3f}", "diagnostic": reason or "ALLOW"}))
    except (OSError, ValueError):
        pass
    if reason:
        emit("PreToolUse", reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
