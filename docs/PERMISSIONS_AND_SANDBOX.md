# Permissions and sandbox

`.claude/control-plane/manifest.yaml` is the source of truth. `generate_policy.py` derives `generated/permission-policy.json` and synchronizes its `permissions` value into `.claude/settings.json`; do not maintain path ownership in both places.

Native rules use explicit `defaultMode: default`: unlisted commands, including other network-capable commands, require approval. They deny reads and edits of manifest forbidden roots plus `.git`, `secrets`, and `credentials`; allow the listed inspection, validation, and test commands; request confirmation for governed edits; and deny `WebFetch` plus common command-line fetch clients. Deny rules take precedence over ask and allow rules.

Claude Code's Bash sandbox is supported on macOS, Linux, and WSL2—not native Windows—and only applies to Bash. It does not constrain Claude file tools, hooks, MCP tools, or built-in network tools. This project therefore does not claim an enabled project sandbox protects those surfaces: native permissions cover supported tools, and `guard_write.py` runs for every Bash call as fail-closed defense in depth for shell spelling, traversal, quoting, composition, and declared-write-set checks.

For an OS-enforced Bash sandbox, deploy managed settings on a supported platform with `sandbox.enabled`, filesystem deny lists, and an explicit network domain allowlist. Project settings alone cannot make that a hard policy on native Windows or prevent users from adding broader user-level allowlists; use managed settings for those guarantees.
