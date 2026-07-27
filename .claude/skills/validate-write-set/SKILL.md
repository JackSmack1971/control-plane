---
description: Validate a declared control-plane write set before or after a governed change.
disable-model-invocation: true
---

# Validate write set

Do not use to choose scope or authorize a change.

Inputs: baseline revision and declared paths.

1. Run `check_write_set.py` against the declared paths and baseline.
2. Run `check_ownership.py` for the writer and paths.
3. Compare actual governed changes to the declared set.

Output: pass/fail paths and ownership evidence. On a mismatch, stop and reject or roll back. Validation is the two checks plus `git diff --check`.
