---
paths:
  - ".claude/control-plane/scripts/**/*.py"
---

# Control-plane Python

- Keep commands deterministic, fail closed, and independent of application source.
- Reuse `common.py` and preserve UTF-8/newline handling.
- Add a focused pytest when logic branches; run Ruff and the focused test.
