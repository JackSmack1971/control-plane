import json
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
AGENTS = ROOT / ".claude/agents"
CAPABILITIES = ROOT / ".claude/control-plane/generated/agent-capabilities.json"
FIXTURES = (
    ROOT / ".claude/skills/evals/routing.yaml",
    ROOT / ".claude/rules/evals/routing.yaml",
    ROOT / ".claude/workflows/evals/routing.yaml",
)
WRITERS = {"skills-specialist", "rules-specialist", "workflow-specialist"}
READ_ONLY = {"control-plane-auditor", "control-plane-verifier"}
ROUTES = {
    "skill": "skills-specialist",
    "rule": "rules-specialist",
    "workflow": "workflow-specialist",
    "audit": "control-plane-auditor",
    "verification": "control-plane-verifier",
}


def frontmatter(path):
    _, value, _ = path.read_text(encoding="utf-8").split("---", 2)
    return yaml.safe_load(value)


def tools(metadata, field):
    if isinstance(metadata[field], list):
        return set(metadata[field])
    return {item.strip() for item in str(metadata[field]).split(",")}


def in_owned_path(path, owned_paths):
    return any(path == pattern.removesuffix("/**") or path.startswith(pattern.removesuffix("/**") + "/") for pattern in owned_paths)


def route(fixture, profiles):
    if fixture["kind"] in {"application", "ambiguous"}:
        return "none"
    agent = fixture.get("candidate", ROUTES[fixture["kind"]])
    if fixture.get("write_requested") and agent in READ_ONLY:
        return "reject-write"
    if any(not in_owned_path(path, profiles[agent]) for path in fixture.get("target_paths", [])):
        return "reject-outside-ownership"
    return agent


def test_agent_capabilities_match_constrained_agent_definitions():
    profiles = {item["name"]: item["owned_paths"] for item in json.loads(CAPABILITIES.read_text(encoding="utf-8"))["agents"]}
    assert set(profiles) == WRITERS | READ_ONLY
    for name, paths in profiles.items():
        metadata = frontmatter(AGENTS / f"{name}.md")
        assert metadata["name"] == name
        assert metadata["maxTurns"] <= 40
        assert "Agent" in tools(metadata, "disallowedTools")
        assert "mcp__*" in tools(metadata, "disallowedTools")
        assert all(path in (AGENTS / f"{name}.md").read_text(encoding="utf-8") for path in paths)
        if name in WRITERS:
            assert {"Edit", "Write"} <= tools(metadata, "tools")
            assert metadata["permissionMode"] == "default"
        else:
            assert not paths
            assert {"Edit", "Write"} <= tools(metadata, "disallowedTools")
            assert metadata["permissionMode"] == "plan"
            assert "Bash" not in tools(metadata, "tools")
            assert any(value.startswith("Bash(") for value in tools(metadata, "tools"))


def test_routing_fixtures_cover_required_boundaries():
    fixtures = [item for path in FIXTURES for item in yaml.safe_load(path.read_text(encoding="utf-8"))["fixtures"]]
    profiles = {item["name"]: item["owned_paths"] for item in json.loads(CAPABILITIES.read_text(encoding="utf-8"))["agents"]}
    routed = {item["expected_agent"] for item in fixtures}
    assert WRITERS | READ_ONLY | {"none"} <= routed
    for fixture in fixtures:
        expected = fixture.get("expected_result", fixture["expected_agent"])
        assert route(fixture, profiles) == expected
