# Claude Code Control Plane

This repository defines a bounded, evidence-gated control plane for shared Claude Code configuration artifacts. It may propose changes to itself, but it never authorizes its own changes.

The initial contract is documentation and directory structure only; no control-plane runtime is implemented.

## Layout

- [Architecture](docs/ARCHITECTURE.md) defines the transaction boundary.
- [Trust model](docs/TRUST_MODEL.md) defines the non-negotiable safeguards.
- [Roadmap](docs/ROADMAP.md) describes the next implementation stages.
- `.claude/` holds managed Claude Code configuration artifacts and control-plane working areas.

## Development commands

Requires Python 3.11+.

```powershell
python -m pip install "pytest>=8" "jsonschema>=4" "PyYAML>=6" "ruff>=0.6"
python -m pytest
python -m ruff check .
```

## Generated policy

`manifest.yaml` is the source for generated policy artifacts. Regenerate and check them with:

```powershell
python .claude/control-plane/scripts/generate_policy.py
python .claude/control-plane/scripts/generate_policy.py --check
```

Generated files are committed with their source and must not be edited by hand.

## Evidence commands

Create or verify the committed governed-file inventory:

```powershell
python .claude/control-plane/scripts/inventory.py
python .claude/control-plane/scripts/inventory.py --check
```

Capture a pre-mutation baseline from an explicit JSON write-set, without changing governed files:

```powershell
python .claude/control-plane/scripts/create_baseline.py --baseline-id base-001 --write-set write-set.json --output .claude/control-plane/state/runs/base-001.json
```

Create or verify the tracked package scaffold manifest:

```powershell
python .claude/control-plane/scripts/check_package.py --write
python .claude/control-plane/scripts/check_package.py --check
```

Before submitting a change, run `git diff --check` and the validation appropriate to the artifact changed.
