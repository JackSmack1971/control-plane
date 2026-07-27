# Repository Instructions

## Purpose

This repository governs Claude Code configuration artifacts. It may propose configuration changes, never approve its own changes.

## Before editing

1. Start from a clean worktree and inspect the target artifact and its governing instructions.
2. Declare the transaction's explicit write set before mutation.
3. Follow instructions in this order: platform and organization policy, this file, then the nearest nested `AGENTS.md`.

## Required validation

Run deterministic validation first, then obtain an independent read-only review. Reject or roll back a transaction that fails verification. Report files changed, tests run, and unresolved risks.

## Boundaries

- Nested `AGENTS.md` files govern their directory trees.
- Generated files are read-only; regenerate them through their owning process.
- Do not edit application source from control-plane work.
- Do not manually edit generated policy files or bypass the manifest policy once introduced.
- Keep persistent instructions concise and scoped; put multi-step procedures in skills or workflows.
