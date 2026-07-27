<!-- Generated from .claude/control-plane/manifest.yaml; do not edit. -->

# Control-plane policy

- **governed_roots**: `[".claude/agents", ".claude/hooks", ".claude/rules", ".claude/skills", ".claude/workflows", ".claude/control-plane"]`
- **budgets**: `{"maximum_changed_files": 20, "maximum_nested_depth": 2, "maximum_specialists": 5, "maximum_turns": 40, "maximum_writers": 1}`
- **verification**: `{"baseline_comparison_required": true, "deterministic_before_semantic": true, "independent_required": true, "rollback_on_failure": true}`
- **memory_policy**: `{"accepted_sources": ["repository-tracked", "signed-run-record"], "reject_untracked_memory": true}`
- **run_storage**: `{"events_append_only": true, "genesis_previous_hash": "0000000000000000000000000000000000000000000000000000000000000000", "hash_chain_algorithm": "sha256", "run_directory": ".claude/control-plane/state/runs"}`
- **self_improvement**: `{"minimum_days_observed": 14, "minimum_independent_evidence": 2, "minimum_passing_runs": 3}`
