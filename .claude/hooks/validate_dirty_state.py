from __future__ import annotations
import subprocess
from guard_write import ROOT, allowed, emit
from state_store import read


def main():
    try:
        transaction = read("active-transaction.json")
    except (OSError, ValueError, KeyError):
        return
    if transaction.get("lifecycle") != "active":
        return
    declared = set(transaction.get("recovery", {}).get("evidence_paths", []))
    changed = subprocess.run(
        ["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True
    ).stdout.splitlines()
    changed = [line[3:].replace("\\", "/") for line in changed if len(line) > 3]
    bad = [path for path in changed if path in declared and not allowed(path)[0]]
    if bad:
        emit("Stop", "CP601: dirty active transaction paths: " + ", ".join(sorted(set(bad))), stop=True)


if __name__ == "__main__":
    main()
