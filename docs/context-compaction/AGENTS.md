# Context Compaction Research

## Purpose

Research, methodology, validation, and operating guidance for Claude Code context compaction. This area informs project decisions but does not itself enforce them.

## Entry Points

- `LLM Context Compaction Methodology.md` — analytical model and proposed protocol.
- `Claude Code CLI Compaction Playbook.md` — operational guidance.
- `Claude Code Compaction Validation Report.md` — empirical findings.
- `Expert Signals in Claude Code CLI Context Compaction.md` — external expert signals.

## Contracts & Invariants

- Label modeled, provisional, and empirically verified claims distinctly.
- Preserve exact CLI versions, commands, diagnostics, dates, and test conditions with results.
- Verify version-sensitive CLI behavior against current official documentation before operational use.
- The validation report is duplicated byte-for-byte under `../validation-and-hardening/`; keep both copies synchronized if either is intentionally revised.
- Promote only durable, project-scoped conclusions into root control-plane policy.

## Anti-patterns

- Do not turn a benchmark assumption into a platform guarantee.
- Do not recommend user-global or host-level configuration for this project.
