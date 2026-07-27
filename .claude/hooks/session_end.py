from __future__ import annotations
from guard_write import event
from state_store import make, write


def main():
    write(
        "interruption.json",
        make(
            "control-plane-recovery",
            "hook-session",
            "active",
            "awaiting-approval",
            "session interrupted",
            [],
            event(),
        ),
    )


if __name__ == "__main__":
    main()
