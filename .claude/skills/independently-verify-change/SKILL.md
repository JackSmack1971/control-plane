---
description: Perform an independent read-only verification of a completed control-plane proposal.
disable-model-invocation: true
---

# Independently verify

Do not use as the transaction writer, to edit, or to authorize/merge.

Inputs: declared write set, baseline, and proposal diff.

1. Establish fresh status and inspect the actual diff.
2. Run deterministic validation before semantic review.
3. Check ownership, generated drift, package/inventory evidence, and fixture coverage.

Output: advisory pass/fail findings, commands, and residual risks. On failure, reject or request rollback. Validate that the verifier identity differs from the writer.
