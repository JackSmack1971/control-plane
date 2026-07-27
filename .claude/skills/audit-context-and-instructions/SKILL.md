---
description: Audit always-loaded Claude instructions, path-scoped rules, and skill routing for context bloat or conflicts.
disable-model-invocation: true
---

# Audit context and instructions

Do not use to silently rewrite policies or approve changes.

Inputs: instruction paths and observed routing concern.

1. Run `context_budget.py --check`.
2. Identify unconditional rules, duplicate instructions, and procedures misplaced outside skills/workflows.
3. Propose the smallest scoped relocation with fixture coverage.

Output: measured report and advisory recommendations. On a budget failure, report contributors before edits. Validate with the context check and routing fixtures.
