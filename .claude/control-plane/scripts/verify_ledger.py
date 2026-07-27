"""Verify one run's append-only event ledger."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path

from common import PolicyError, repository_root
from load_manifest import load_manifest
from record_event import run_path, verify_ledger


def anchor_signature(anchor: dict, key: str) -> str:
    payload = {key: value for key, value in anchor.items() if key != "signature"}
    return hmac.new(key.encode("utf-8"), json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"), hashlib.sha256).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--anchor-file", required=True, type=Path, help="externally retained, HMAC-authenticated JSON anchor")
    args = parser.parse_args()
    try:
        root = repository_root()
        run = run_path(root, args.run_id)
        anchor = args.anchor_file.resolve()
        run_root = (root / load_manifest(root)["run_storage"]["run_directory"]).resolve()
        if anchor.is_relative_to(run_root):
            raise PolicyError("external anchor must not be stored under mutable run storage")
        value = json.loads(anchor.read_text(encoding="utf-8"))
        key = os.environ.get("CONTROL_PLANE_ANCHOR_KEY")
        if not key or not isinstance(value, dict) or value.get("run_id") != args.run_id or not isinstance(value.get("last_event_hash"), str) or not hmac.compare_digest(value.get("signature", ""), anchor_signature(value, key)):
            raise PolicyError("invalid external trust anchor")
        print(json.dumps(verify_ledger(run, args.run_id, value["last_event_hash"]), sort_keys=True))
    except (OSError, PolicyError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
