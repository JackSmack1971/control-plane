from __future__ import annotations
import subprocess
from guard_write import ROOT
from state_store import make, write


def main():
    revision = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    write(
        "recovery.json",
        make("control-plane-recovery", "hook-compact", "active", "awaiting-approval", revision, []),
    )


if __name__ == "__main__":
    main()
