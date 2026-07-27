from __future__ import annotations
from guard_write import event
from state_store import append, make


def main():
    data = event()
    append(
        "instructions.jsonl",
        make(
            "control-plane-recovery",
            "hook-instructions",
            "active",
            "awaiting-approval",
            "instruction loaded",
            [],
            {"path": data.get("file_path"), "reason": data.get("load_reason")},
        ),
    )


if __name__ == "__main__":
    main()
