"""Load and validate the control-plane manifest without mutating it."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from common import PolicyError, repo_path, repository_root


def _require_modules() -> tuple[Any, Any]:
    try:
        import yaml
        from jsonschema import Draft202012Validator
    except ImportError as error:
        raise PolicyError("PyYAML and jsonschema are required to load the manifest") from error
    return yaml, Draft202012Validator


def _overlap(left: str, right: str) -> bool:
    left_prefix, right_prefix = left.removesuffix("/**"), right.removesuffix("/**")
    return left_prefix == right_prefix or left_prefix.startswith(right_prefix + "/") or right_prefix.startswith(left_prefix + "/")


def load_manifest(root: Path | None = None) -> dict[str, Any]:
    root = root or repository_root()
    yaml, validator_type = _require_modules()
    manifest_path = root / ".claude/control-plane/manifest.yaml"
    schema_path = root / ".claude/control-plane/schemas/manifest.schema.json"
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator_type.check_schema(schema)
        validator_type(schema).validate(manifest)
    except Exception as error:
        if isinstance(error, PolicyError):
            raise
        raise PolicyError(f"invalid manifest or schema: {error}") from error

    for key in ("governed_roots", "forbidden_roots", "generated_file_roots", "derived_artifacts"):
        manifest[key] = [repo_path(root, item) for item in manifest[key]]
    for owner in manifest["specialist_ownership"]:
        owner["pattern"] = repo_path(root, owner["pattern"], glob=True)
    generated_roots = tuple(manifest["generated_file_roots"])
    if any(not any(item.startswith(generated + "/") for generated in generated_roots) for item in manifest["derived_artifacts"]):
        raise PolicyError("derived artifacts must stay under generated roots")
    if any(
        item == generated or item.startswith(generated + "/") or generated.startswith(item + "/")
        for item in manifest["forbidden_roots"]
        for generated in generated_roots
    ):
        raise PolicyError("forbidden and generated roots cannot overlap")
    owners = manifest["specialist_ownership"]
    for index, owner in enumerate(owners):
        for other in owners[index + 1 :]:
            if owner["pattern"] == other["pattern"]:
                raise PolicyError(f"duplicate ownership: {owner['pattern']}")
            if owner["specialist"] != other["specialist"] and _overlap(owner["pattern"], other["pattern"]):
                raise PolicyError(f"contradictory ownership: {owner['pattern']} and {other['pattern']}")
    return manifest
