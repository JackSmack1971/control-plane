# Claude Code Control Plane

This repository maintains Claude Code configuration. Application development stays in application-development mode; control-plane-maintenance uses a bounded transaction and never self-approves.

The repository includes deterministic policy generation, transaction evidence, validation, and compatibility diagnostics.

## Layout

- [Architecture](docs/ARCHITECTURE.md) defines the transaction boundary.
- [Trust model](docs/TRUST_MODEL.md) defines the non-negotiable safeguards.
- [Roadmap](docs/ROADMAP.md) describes the next implementation stages.
- `.claude/` holds managed Claude Code configuration artifacts and control-plane working areas.

## Start here

Requires Python 3.11+.

```sh
python -m pip install "pytest>=8" "jsonschema>=4" "PyYAML>=6" "ruff>=0.6"
python -m pytest
python -m ruff check .
```

For a configuration change, start one transaction (choose `lightweight`, `standard`, or `sensitive`):

```sh
python .claude/control-plane/scripts/new_run.py --run-id change-001 --writer-id writer-001 --summary "Describe the change" --class standard --path .claude/rules/example.md
```

Run `python .claude/control-plane/scripts/doctor.py --json` before onboarding to see effective hook portability and platform support.

## Generated policy

`manifest.yaml` is the source for generated policy artifacts. Regenerate and check them with:

```sh
python .claude/control-plane/scripts/generate_policy.py
python .claude/control-plane/scripts/generate_policy.py --check
```

Generated files are committed with their source and must not be edited by hand.

## Evidence commands

Create or verify the committed governed-file inventory:

```sh
python .claude/control-plane/scripts/inventory.py
python .claude/control-plane/scripts/inventory.py --check
```

Capture a pre-mutation baseline from an explicit JSON write-set, without changing governed files:

```sh
python .claude/control-plane/scripts/create_baseline.py --baseline-id base-001 --write-set write-set.json --output .claude/control-plane/state/runs/base-001.json
```

Create or verify the tracked package scaffold manifest:

```powershell
python .claude/control-plane/scripts/check_package.py --write
python .claude/control-plane/scripts/check_package.py --check
```

Before submitting a change, run `git diff --check` and the validation appropriate to the artifact changed.
