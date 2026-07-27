"""Advance a run only through its declared lifecycle."""

from __future__ import annotations

import argparse
import json

from common import PolicyError, repository_root
from record_event import NEXT, append_event, read_events, run_path

STATES = ("RECEIVED", "CLASSIFIED", "BASELINED", "PLANNED", "PLAN_VALIDATED", "APPLYING", "VERIFYING", "COMMITTED", "FAILED", "ROLLED_BACK", "CANCELLED")
def current_state(run, run_id: str) -> str:
    events = read_events(run / "events.jsonl")
    if not events:
        raise PolicyError("ledger is empty")
    state = events[-1].get("state")
    if state not in STATES:
        raise PolicyError("ledger has an invalid state")
    return state


def transition(root, run_id: str, target: str, details: dict | None = None) -> dict:
    run = run_path(root, run_id)
    current = current_state(run, run_id)
    if target not in NEXT.get(current, set()):
        raise PolicyError(f"illegal transition: {current} -> {target}")
    if target == "COMMITTED" and not (details or {}).get("approval_id"):
        raise PolicyError("COMMITTED requires externally supplied approval_id evidence")
    return append_event(run, run_id, "state-transition", target, {**(details or {}), "from": current}, expected_state=current)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--to", required=True, choices=STATES)
    parser.add_argument("--details", default="{}", help="JSON object; COMMITTED requires approval_id")
    args = parser.parse_args()
    try:
        details = json.loads(args.details)
        if not isinstance(details, dict):
            raise PolicyError("details must be a JSON object")
        print(json.dumps(transition(repository_root(), args.run_id, args.to, details), sort_keys=True))
    except (OSError, json.JSONDecodeError, PolicyError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
