"""Generate deterministic control-plane policy projections from manifest.yaml."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from common import PolicyError, repository_root
from load_manifest import load_manifest

HEADER = "Generated from .claude/control-plane/manifest.yaml; do not edit."


def _json(value: object) -> str:
    return json.dumps({"_generated": HEADER, **value}, indent=2, sort_keys=True) + "\n"


def _yaml(value: object) -> str:
    return f"# {HEADER}\n" + yaml.safe_dump(value, sort_keys=True, allow_unicode=True)


def permission_policy(manifest: dict) -> dict:
    roots = [*manifest["permission_policy"]["protected_roots"], *manifest["forbidden_roots"]]
    protected = sorted(set(roots))
    policy = manifest["permission_policy"]
    ask_paths = [f"Edit(./{entry})" if entry.endswith(".json") else f"Edit(./{entry}/**)" for entry in manifest["governed_roots"]]
    return {
        "permissions": {
            "defaultMode": "default",
            "allow": [*(f"Bash({command}*)" for command in policy["read_only_commands"]), *(f"Bash({command}*)" for command in policy["validator_commands"])],
            "ask": ask_paths,
            "deny": [*(f"{tool}(./{entry}/**)" for entry in protected for tool in ("Read", "Edit")), "WebFetch", *(f"Bash({command}*)" for command in policy["network_commands"])],
        },
        "sandbox": {
            "supported_platforms": ["macOS", "Linux", "WSL2"],
            "limitation": "Project settings cannot sandbox native Windows or non-Bash tools, hooks, or MCP servers.",
        },
    }


def _settings(value: dict, policy: dict) -> str:
    settings = json.loads(value)
    settings["permissions"] = policy["permissions"]
    return json.dumps(settings, indent=2, sort_keys=True) + "\n"


def render(manifest: dict) -> dict[str, str]:
    ownership = {item["pattern"]: item["specialist"] for item in manifest["specialist_ownership"]}
    permissions = permission_policy(manifest)
    outputs = {
        "README.md": "<!-- " + HEADER + " -->\n\n# Generated policy\n\nThese files are derived from `../manifest.yaml`. Run:\n\n```powershell\npython .claude/control-plane/scripts/generate_policy.py\npython .claude/control-plane/scripts/generate_policy.py --check\n```\n",
        "ownership-map.json": _json({"ownership": ownership}),
        "protected-paths.json": _json({"forbidden_roots": manifest["forbidden_roots"], "generated_file_roots": manifest["generated_file_roots"]}),
        "agent-capabilities.json": _json({"agents": manifest["agent_profiles"], "operations": manifest["operations"], "verifier_restrictions": manifest["verifier_restrictions"]}),
        "policy-summary.md": "<!-- " + HEADER + " -->\n\n# Control-plane policy\n\n" + "\n".join(f"- **{key}**: `{json.dumps(manifest[key], sort_keys=True)}`" for key in ("governed_roots", "budgets", "verification", "memory_policy", "run_storage", "self_improvement")) + "\n",
        "ownership-evals.yaml": _yaml({"ownership_evaluations": [{"pattern": pattern, "specialist": specialist} for pattern, specialist in ownership.items()]}),
        "permission-policy.json": _json(permissions),
    }
    expected = {Path(path).name for path in manifest["derived_artifacts"]}
    if expected != outputs.keys():
        raise PolicyError("manifest must declare exactly the supported generated artifacts")
    return outputs


def generate(root: Path, *, check: bool = False, stdout: str | None = None) -> bool:
    manifest = load_manifest(root)
    outputs = render(manifest)
    paths = {Path(path).name: root / path for path in manifest["derived_artifacts"]}
    settings_path = root / ".claude/settings.json"
    settings = _settings(settings_path.read_text(encoding="utf-8"), permission_policy(manifest))
    if stdout:
        if stdout not in outputs:
            raise PolicyError(f"unknown generated artifact: {stdout}")
        print(outputs[stdout], end="")
        return True
    drift = [name for name, path in paths.items() if not path.is_file() or path.read_text(encoding="utf-8") != outputs[name]]
    if not settings_path.is_file() or settings_path.read_text(encoding="utf-8") != settings:
        drift.append("settings.json")
    if check:
        if drift:
            raise PolicyError("generated policy drift: " + ", ".join(drift))
        return True
    for name, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(outputs[name], encoding="utf-8", newline="\n")
    settings_path.write_text(settings, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--stdout", metavar="ARTIFACT")
    args = parser.parse_args()
    try:
        generate(repository_root(), check=args.check, stdout=args.stdout)
    except PolicyError as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
