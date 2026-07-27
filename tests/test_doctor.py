import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / ".claude/control-plane/scripts"))

import doctor  # noqa: E402


def test_doctor_reports_portable_effective_hooks():
    result = doctor.diagnose(ROOT)
    assert result["portable_hooks"]
    assert isinstance(result["sandbox_supported"], bool)
    assert {"samples", "denials", "false_denials"} <= result["telemetry"].keys()


def test_doctor_aggregates_latency_denials_and_false_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(doctor, "STATE", tmp_path)
    (tmp_path / "telemetry.jsonl").write_text(
        '{"recovery":{"details":{"latency_ms":"2.0","diagnostic":"ALLOW"}}}\n'
        '{"recovery":{"details":{"latency_ms":"4.0","diagnostic":"CP501"}}}\n'
        '{"recovery":{"details":{"kind":"false-denial","diagnostic":"CP501"}}}\nnot-json\n',
        encoding="utf-8",
    )
    assert doctor.telemetry() == {"samples": 2, "average_latency_ms": 3.0, "denials": 1, "false_denials": 1}
