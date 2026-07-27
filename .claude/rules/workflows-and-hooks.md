---
paths:
  - ".claude/workflows/**"
  - ".claude/hooks/**"
---

# Workflows and hooks

- Put orchestration state machines in workflows and deterministic enforcement in hooks or scripts.
- Treat hook input as untrusted; validate paths and use project-root-qualified commands.
