"""Check generated policy files against the manifest source of truth."""

from __future__ import annotations

import argparse

from common import PolicyError, repository_root
from generate_policy import generate


def check_generated_drift(root) -> list[str]:
    try:
        generate(root, check=True)
    except PolicyError as error:
        return [str(error)]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    errors = check_generated_drift(repository_root())
    if errors:
        parser.error("; ".join(errors))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
