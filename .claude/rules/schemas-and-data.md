---
paths:
  - ".claude/control-plane/schemas/**/*.json"
  - ".claude/**/*.yaml"
  - ".claude/**/*.yml"
  - "INVENTORY.json"
  - "PACKAGE_MANIFEST.json"
---

# Schemas and deterministic data

- Keep JSON and YAML deterministic: stable ordering, explicit schema versions, and newline-terminated UTF-8.
- Validate schema changes with the owning deterministic script; do not hand-edit derived policy.
