from __future__ import annotations
from guard_write import event
from state_store import append, make


def main():
    append(
        "failures.jsonl",
        make(
            "control-plane-recovery",
            "hook-failure",
            "active",
            "awaiting-approval",
            "tool failure",
            [],
            event(),
        ),
    )


if __name__ == "__main__":
    main()
