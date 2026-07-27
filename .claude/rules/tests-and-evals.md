---
paths:
  - "tests/**/*.py"
  - ".claude/**/evals/**"
---

# Tests and eval fixtures

- Keep fixtures declarative and include positive, negative, and boundary cases for each artifact category.
- Tests must assert routing or deterministic behavior, not merely parse fixture files.
