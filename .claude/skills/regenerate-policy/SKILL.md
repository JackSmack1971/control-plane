---
description: Regenerate and verify control-plane policy derived from manifest.yaml.
disable-model-invocation: true
---

# Regenerate policy

Do not use to manually edit `.claude/control-plane/generated/` or alter unrelated configuration.

Inputs: changed manifest or generator.

1. Run `python .claude/control-plane/scripts/generate_policy.py`.
2. Inspect only generated outputs implied by the source change.
3. Run the generator again with `--check`.

Output: regenerated paths and drift result. On generation failure, leave generated files untouched and report it. Validation is `generate_policy.py --check`.
