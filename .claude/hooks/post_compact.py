from __future__ import annotations
import subprocess

from guard_write import ROOT
from state_store import make, read, write


def main():
    try:
        value = read("recovery.json")
        if (
            value["recovery"]["checkpoint"]
            != subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        ):
            raise ValueError("revision")
    except (KeyError, OSError, ValueError):
        write(
            "recovery.json",
            make(
                "control-plane-recovery",
                "hook-compact",
                "terminal",
                "rejected",
                "invalid recovery checkpoint",
                [],
            ),
        )


if __name__ == "__main__":
    main()
