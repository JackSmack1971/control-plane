---
description: Start a governed control-plane change. Use before modifying managed Claude configuration artifacts.
disable-model-invocation: true
---

# Start transaction

Do not use for read-only analysis or application code.

Application-development mode does not start a control-plane transaction. Control-plane-maintenance mode starts one command:

`python .claude/control-plane/scripts/new_run.py --run-id <id> --writer-id <id> --summary "<change>" --class <lightweight|standard|sensitive> --path <path> [--path <path>]`

1. Read root and nearest instructions, trust model, manifest, and target artifacts.
2. Require a clean worktree; declare one writer and the explicit write set. Tests, evals, docs, and `README.md` are allowed companion paths.
3. The command captures a schema-valid baseline before mutation.

Output: baseline path, writer, and write set. On any failure, stop before editing. Validate the baseline against its schema.
