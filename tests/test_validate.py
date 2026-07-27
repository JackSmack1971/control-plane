import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / ".claude/control-plane/scripts"))

from validate import Report, SECRET_PATTERNS, _valid_content_hash, validate  # noqa: E402


def test_secret_patterns_detect_conservative_credentials():
    assert any(pattern.search("api_key=123456789012") for pattern in SECRET_PATTERNS)
    assert any(pattern.search("ghp_abcdefghijklmnopqrstuvwxyz123456") for pattern in SECRET_PATTERNS)


def test_fast_report_does_not_claim_complete_compliance():
    report = validate(ROOT, "fast")
    assert isinstance(report, Report)
    assert "fast mode does not claim full transaction compliance" in report.warnings


def test_complete_mode_fails_closed_without_a_transaction():
    report = validate(ROOT, "complete")
    assert "complete mode requires --run-id" in report.errors


def test_content_hash_must_bind_the_artifact_content():
    value = {"name": "café"}
    import hashlib
    import json

    value["content_hash"] = hashlib.sha256(
        json.dumps({"name": "café"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert _valid_content_hash(value)
    value["name"] = "tampered"
    assert not _valid_content_hash(value)
