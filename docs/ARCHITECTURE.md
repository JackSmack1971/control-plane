# Architecture

## Scope

The control plane governs Claude Code configuration artifacts under `.claude/`. It does not modify application source and does not implement authorization policy in this bootstrap.

## Transaction boundary

Each future transaction has one primary writer and an explicit write set. It runs deterministic validation before semantic review, then an independent read-only verifier checks the authored result. Failed verification causes rejection or rollback.

Before a write, the writer captures a schema-valid baseline for the declared set and compares it to the committed governed-file inventory. Package integrity verifies that the tracked scaffold matches its SHA-256 manifest.

The control plane can prepare a proposal but cannot approve that proposal in the same run. Human or otherwise independent authorization remains outside the writer's authority.

## Artifact areas

- `agents/`, `rules/`, `skills/`, `workflows/`, and `hooks/` hold Claude Code configuration artifacts.
- `control-plane/schemas/`, `evals/`, and `scripts/` will hold validation inputs and tooling.
- `control-plane/generated/` will hold generated, read-only policy output.
- `control-plane/state/` will hold control-plane state once a governed mechanism exists.

The future manifest policy is the canonical source of truth. Generated policy files are outputs, never hand-edited inputs.
