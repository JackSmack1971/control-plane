"""Cancel a nonterminal governed transaction."""

from __future__ import annotations

import argparse

from common import PolicyError, repository_root
from transition_run import transition


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        transition(repository_root(), args.run_id, "CANCELLED", {"reason": "cancelled by operator"})
    except (OSError, PolicyError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
