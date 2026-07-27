---
description: Start a governed control-plane change. Use before modifying managed Claude configuration artifacts.
disable-model-invocation: true
---

# Start transaction

Do not use for read-only analysis or application code.

Inputs: requested change and candidate paths.

1. Read root and nearest instructions, trust model, manifest, and target artifacts.
2. Require a clean worktree; declare one writer and the explicit write set.
3. Capture a schema-valid baseline with `create_baseline.py` before mutation.

Output: baseline path, writer, and write set. On any failure, stop before editing. Validate the baseline against its schema.
