---
description: Reject or safely roll back a failed governed control-plane transaction.
disable-model-invocation: true
---

# Roll back failed transaction

Do not use to discard unrelated user work or replace a missing verification.

Inputs: transaction baseline, write set, and failure evidence.

1. Identify only declared paths changed after the baseline.
2. Restore those paths from the recorded baseline using a reviewable patch or VCS operation.
3. Record rejection and rerun deterministic validation.

Output: restored paths and failure record. On uncertain scope, stop for human direction. Validate a clean declared diff and passing fast validation.
