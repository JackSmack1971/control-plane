"""Canonical fail-closed deterministic validator for the control plane."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from check_generated_drift import check_generated_drift
from check_ownership import check_ownership
from check_package import check as check_package
from check_write_set import changed_paths, check_write_set
from common import PolicyError, repository_root
from context_budget import BUDGET_BYTES, report as context_report
from inventory import check_inventory
from load_manifest import load_manifest
from record_event import read_events, run_path, verify_events

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"(?i)\b(?:password|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[^\s'\"]{12,}"),
)
REQUIRED_RUN_FILES = {
    "request.json", "baseline.json", "plan.json", "events.jsonl", "proposed.patch", "verification.json", "result.json", "trust-anchor.json",
}
SCHEMA_FILES = {
    "baseline.json": "baseline.schema.json", "plan.json": "change-plan.schema.json",
    "verification.json": "verification.schema.json", "result.json": "result.schema.json", "trust-anchor.json": "trust-anchor.schema.json",
}


@dataclass
class Report:
    mode: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def passed(self, name: str) -> None:
        self.checks.append(name)

    def data(self) -> dict[str, Any]:
        return {"mode": self.mode, "ok": not self.errors, "checks": self.checks, "errors": self.errors, "warnings": self.warnings}


def _within(path: str, roots: list[str]) -> bool:
    return any(path == root or path.startswith(root + "/") for root in roots)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _valid_content_hash(value: dict[str, Any]) -> bool:
    recorded = value.get("content_hash")
    payload = dict(value)
    payload.pop("content_hash", None)
    actual = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return recorded == actual


def _validate_schemas(root: Path, report: Report) -> None:
    schemas = root / ".claude/control-plane/schemas"
    loaded = {}
    for path in sorted(schemas.glob("*.schema.json")):
        try:
            loaded[path.name] = _load_json(path)
            Draft202012Validator.check_schema(loaded[path.name])
        except (OSError, json.JSONDecodeError, Exception) as error:
            report.error(f"invalid schema {path.name}: {error}")
    try:
        manifest = yaml.safe_load((root / ".claude/control-plane/manifest.yaml").read_text(encoding="utf-8"))
        Draft202012Validator(loaded["manifest.schema.json"], format_checker=FormatChecker()).validate(manifest)
        report.passed("manifest schema")
    except (KeyError, OSError, yaml.YAMLError, Exception) as error:
        report.error(f"manifest schema validation failed: {error}")
    for path in sorted((root / ".claude").rglob("*.json")):
        if "runs" in path.parts:
            continue
        try:
            _load_json(path)
        except (OSError, json.JSONDecodeError) as error:
            report.error(f"invalid JSON artifact {path.relative_to(root).as_posix()}: {error}")
    for path in sorted((root / ".claude").rglob("*.yaml")) + sorted((root / ".claude").rglob("*.yml")):
        if "runs" in path.parts:
            continue
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as error:
            report.error(f"invalid YAML artifact {path.relative_to(root).as_posix()}: {error}")
    if not report.errors:
        report.passed("all JSON/YAML artifacts parsed")


def _check_secrets(root: Path, manifest: dict, report: Report) -> None:
    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files"], text=True, capture_output=True, check=True
    ).stdout.splitlines()
    for relative in tracked:
        path = root / relative
        if not _within(relative, manifest["governed_roots"]):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            report.error(f"managed artifact is not UTF-8 text: {relative}")
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                report.error(f"possible secret or credential in managed artifact: {relative}")
                break
    if not any("possible secret" in item for item in report.errors):
        report.passed("managed-artifact secret scan")


def _check_run(root: Path, run_id: str, report: Report) -> None:
    try:
        manifest = load_manifest(root)
        run = run_path(root, run_id)
        actual = {path.name for path in run.iterdir() if not path.name.startswith(".")}
        missing = REQUIRED_RUN_FILES - actual
        if missing:
            report.error(f"run artifacts missing: {sorted(missing)}")
            return
        request = _load_json(run / "request.json")
        if request.get("run_id") != run_id:
            report.error("request run_id does not match transaction")
        patch = run / "proposed.patch"
        if patch.read_bytes():
            result = subprocess.run(["git", "-C", str(root), "apply", "--check", str(patch)], text=True, capture_output=True)
            if result.returncode:
                report.error(f"invalid proposed patch: {result.stderr.strip()}")
        values = {name: _load_json(run / name) for name in SCHEMA_FILES}
        schemas = {name: _load_json(root / ".claude/control-plane/schemas" / schema) for name, schema in SCHEMA_FILES.items()}
        for name, value in values.items():
            if value.get("lifecycle") == "pending":
                report.error(f"required transaction artifact is pending: {name}")
            else:
                Draft202012Validator(schemas[name], format_checker=FormatChecker()).validate(value)
            if value.get("lifecycle") != "pending" and not _valid_content_hash(value):
                report.error(f"{name} content_hash does not match content")
        events = read_events(run / "events.jsonl")
        ledger = verify_events(events, run_id, root)
        plan, baseline, verification = values["plan.json"], values["baseline.json"], values["verification.json"]
        result, anchor = values["result.json"], values["trust-anchor.json"]
        for name, value in values.items():
            if value.get("run_id") not in (None, run_id):
                report.error(f"{name} run_id does not match transaction")
        if plan.get("baseline_id") != baseline.get("baseline_id"):
            report.error("plan baseline_id does not match baseline")
        transaction_class = plan.get("transaction_class")
        classes = manifest["transaction_policy"]["classes"]
        if transaction_class not in classes:
            report.error("CP701: transaction class is not declared by manifest policy")
        elif len(plan["write_set"]) > classes[transaction_class]["maximum_changed_files"]:
            report.error("CP702: transaction write set exceeds its class limit")
        if plan.get("mode") != "control-plane-maintenance":
            report.error("CP703: transaction plan has an invalid maintenance mode")
        if result.get("verification_id") != verification.get("verification_id"):
            report.error("result verification_id does not match verification")
        if anchor.get("repository_revision") != baseline.get("repository_revision") or anchor.get("manifest_hash") != baseline.get("manifest_hash"):
            report.error("trust anchor does not match baseline")
        if anchor.get("last_event_hash") != ledger["last_event_hash"]:
            report.error("trust anchor does not match ledger")
        report.errors.extend(f"write set: {item}" for item in check_write_set(root, plan["write_set"], baseline["repository_revision"]))
        report.errors.extend(f"ownership: {item}" for item in check_ownership(root, plan["write_set"]))
        writer = plan["writer_id"]
        verifier = verification.get("verifier_id")
        if verifier == writer:
            report.error("same-run author and verifier identities must differ")
        if verification.get("operations") != ["read", "validate", "verify"]:
            report.error("verifier is not read-only")
        changed = set(changed_paths(root, baseline["repository_revision"]))
        governed_changed = {path for path in changed if _within(path, manifest["governed_roots"])}
        if governed_changed and not (run / "evaluation.json").is_file():
            report.error("governed behavior changed without required evaluation update")
        report.passed(f"transaction {run_id}")
    except (OSError, json.JSONDecodeError, PolicyError, Exception) as error:
        report.error(f"transaction validation failed: {error}")


def validate(root: Path, mode: str, run_id: str | None = None) -> Report:
    report = Report(mode)
    try:
        manifest = load_manifest(root)
    except PolicyError as error:
        report.error(str(error))
        return report
    _validate_schemas(root, report)
    for name, errors in (("generated-policy drift", check_generated_drift(root)), ("package manifest", check_package(root, root / "PACKAGE_MANIFEST.json"))):
        if errors:
            report.errors.extend(f"{name}: {error}" for error in errors)
        else:
            report.passed(name)
    if not check_inventory(root, root / "INVENTORY.json"):
        report.error("inventory drift")
    else:
        report.passed("inventory")
    context_size, _ = context_report(root)
    if context_size > BUDGET_BYTES:
        report.error(f"always-loaded instruction budget exceeded: {context_size}/{BUDGET_BYTES} bytes")
    else:
        report.passed("always-loaded instruction budget")
    _check_secrets(root, manifest, report)
    if run_id:
        _check_run(root, run_id, report)
    elif mode == "complete":
        report.error("complete mode requires --run-id")
    if mode == "fast":
        report.warning("fast mode does not claim full transaction compliance")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("fast", "complete"), default="fast")
    parser.add_argument("--run-id")
    parser.add_argument("--json", dest="json_path", type=Path, help="write stable JSON report")
    args = parser.parse_args()
    report = validate(repository_root(), args.mode, args.run_id)
    text = f"{args.mode} validation: {'PASS' if not report.errors else 'FAIL'}; {len(report.errors)} error(s), {len(report.warnings)} warning(s)"
    print(text)
    for label, values in (("ERROR", report.errors), ("WARNING", report.warnings)):
        for value in values:
            print(f"{label}: {value}")
    if args.json_path:
        args.json_path.write_text(json.dumps(report.data(), indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
