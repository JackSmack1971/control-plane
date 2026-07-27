---
description: Author a bounded control-plane proposal after a transaction baseline and write set exist.
disable-model-invocation: true
---

# Author governed change

Do not use before a baseline, to alter application source, or to approve the result.

Inputs: approved write set, baseline, and requested outcome.

1. Edit only declared, owned, non-generated paths.
2. Use the smallest durable artifact; put deterministic checks in scripts.
3. Record the actual diff and required evaluation updates.

Output: proposal diff and changed-path list. On scope drift, stop and amend the transaction before continuing. Validate with focused checks and `git diff --check`.
