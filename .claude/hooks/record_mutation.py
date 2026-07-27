from __future__ import annotations
from guard_write import event, write_paths
from state_store import append, make


def main():
    paths = [path for path in write_paths(event()) if path]
    if paths:
        append(
            "mutations.jsonl",
            make(
                "control-plane-recovery",
                "hook-mutation",
                "active",
                "awaiting-approval",
                "mutation recorded",
                paths,
            ),
        )


if __name__ == "__main__":
    main()
