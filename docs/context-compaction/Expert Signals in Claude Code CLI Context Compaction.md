# Expert Signals in Claude Code CLI Context Compaction

## Executive summary

The biggest gap between an expert and an intermediate Claude Code CLI practitioner is not “knowing more commands.” It is having the correct mental model of compaction. Experts treat compaction as a **lossy state transition** over a finite attention budget, not as a neutral space-saving cleanup. That leads them to engineer for **state survivability**, **reload semantics**, **output containment**, and **observability** before they tune thresholds or buy more context. Intermediates more often focus on the visible symptom—high token usage or a near-full context bar—and underweight the deeper question: *which exact facts, constraints, paths, commands, and decisions must still be available after the history is summarized?* Claude Code’s own docs explicitly frame context as a finite resource with diminishing returns, document that compaction summarizes history, and spell out that only some mechanisms reliably survive and reload after compaction. citeturn28view2turn20view1turn18view0turn15view0

In practice, experts notice four things early. First, **startup context tax** matters: before you type anything, Claude Code may already have loaded CLAUDE.md, auto memory, MCP tool names, and skill descriptions, so a session can begin materially “fuller” than it looks from the user’s intent alone. Second, **survival is asymmetric**: project-root CLAUDE.md and auto memory are re-injected after compaction, but nested CLAUDE.md files and path-scoped rules are not automatically restored until matching files are read again. Third, **large reads and tool outputs are not just cost problems; they are compaction-shape problems** that determine what gets preserved or discarded. Fourth, **instrumentation beats intuition**: `/context`, hooks, status lines, `/doctor`, and version-aware troubleshooting consistently outperform guesswork. citeturn18view0turn3view0turn25view1turn18view1turn5view2turn30view0turn30view1

The single most costly reasoning error is to assume that “because the information existed in the session, compaction will preserve it in a form that remains decision-useful.” That is not merely an operational mistake; it is a reasoning error about lossy abstraction. In information-theoretic terms, post-processing cannot increase information, and in statistical terms, a summary is only safe if it preserves a **task-sufficient state** for the future decisions that matter. Claude’s platform docs also warn that compaction is less ideal for tasks requiring precise recall of earlier details, which is exactly where this mistaken mental model breaks. citeturn29search0turn15view0turn16view0

## Scope and assumptions

Because you specified that platform and model versions are unspecified, I am making the following assumptions for this report.

| Item             | Assumption                                                                                                                          | Why it matters                                                                                                                                                                                                                                                                   |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Language         | en-US English                                                                                                                       | Requested by the user.                                                                                                                                                                                                                                                           |
| Runtime surface  | **Claude Code CLI**, with CLI docs treated as the primary operational source                                                        | The behavior of compaction, memory loading, hooks, sessions, and slash commands is CLI-specific. citeturn20view0turn20view1                                                                                                                                                  |
| Version baseline | Current Claude Code documentation and changelog state as of **July 25, 2026**, calling out version-specific behavior where relevant | Several compaction behaviors changed across 2025–2026 releases, including `/compact` failure modes, `/context` reporting, automatic thresholds, tool-result persistence, and post-compaction naming/branching behavior. citeturn22search6turn30view0turn30view1turn30view2 |
| Provider         | Default/direct Anthropic behavior unless otherwise noted                                                                            | Provider and deployment affect 1M context availability, compaction thresholds, and certain context-window rules. citeturn18view2turn13view0                                                                                                                                  |
| Model family     | A recent Claude Code-capable model, not pinned to one version by the user                                                           | Extended thinking, 1M context, compaction thresholds, and cost profiles differ across Sonnet, Opus, and Fable generations. citeturn18view2turn13view1                                                                                                                        |
| Research scope   | Primary sources first; community and academic sources used to explain failure patterns and formalize the reasoning                  | This matches your requested source hierarchy. citeturn15view0turn28view2turn14search2turn23search20                                                                                                                                                                        |

A practical implication of those assumptions is that **folk wisdom can be stale**. An expert tracks what the docs and changelog currently say, rather than assuming the behavior they saw six months ago is still the behavior they have now. For compaction work, that is not optional. Recent release notes include fixes for auto-compact triggering, `/compact` failing when already over limit, stale `/context` pre-compact reporting, compact-boundary handling, and token-usage reductions from read-tool deduplication and persistence of large tool results to disk. citeturn12view0turn12view1turn30view0turn30view1

## What experts notice, weigh, and question

The following flow is the right mental model for CLI compaction behavior.

```mermaid
flowchart LR
    A[Session starts] --> B[Preloaded context<br/>system prompt, root CLAUDE.md,<br/>auto memory, MCP tool names, skills]
    B --> C[Work loop<br/>reads, edits, tool outputs,<br/>hooks, thinking, subagents]
    C --> D{Near compaction threshold?}
    D -- No --> C
    D -- Yes --> E[/compact or auto-compact]
    E --> F[Conversation summarized]
    F --> G[Automatically reloaded<br/>system prompt, project-root CLAUDE.md,<br/>auto memory, unscoped rules]
    F --> H[Not automatically reloaded<br/>nested CLAUDE.md, path-scoped rules<br/>until matching file is read again]
    G --> I[Task continues]
    H --> I
```

This is not just conceptual. Claude Code’s docs explicitly describe what loads before you type, what fills context during the session, and what survives or does not survive compaction. They also document that subagents keep large reads in a separate context window and that `/compact` can be directed with a focus. citeturn18view0turn20view0turn25view2

### Expert versus intermediate focus areas

| Focus area                  | What an expert notices, weighs, or asks                                                                                                                                                                                                                                                                                                                                                  | What an intermediate practitioner typically focuses on                                               |
| --------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Context model               | “Is this token pressure actually the problem, or is the real problem that the current state is no longer **decision-sufficient**?” Experts treat context as the model’s working state, not as a chat transcript. Anthropic’s context-engineering guidance frames context as a finite resource whose utility must be optimized, not merely expanded. citeturn28view2turn28view3       | “The context bar is high; I should compact or switch to a larger model.”                             |
| Startup tax                 | “What loaded before I even started?” Experts check the invisible preload: CLAUDE.md, auto memory, MCP tool names, skill descriptions, and any extra system prompt material. citeturn18view0turn19search11                                                                                                                                                                            | “Most of my tokens must be coming from the files I just opened.”                                     |
| Survivability semantics     | “Which facts survive compaction deterministically, which reload from disk, and which disappear unless I explicitly reload them?” Project-root CLAUDE.md and auto memory are re-injected; nested CLAUDE.md and path-scoped rules are not automatically restored until a matching file is read again. citeturn3view0turn18view0                                                        | “CLAUDE.md is memory, so after compact Claude should still know the same rules.”                     |
| Placement of instructions   | “Should this live in project-root CLAUDE.md, a nested CLAUDE.md, a scoped rule, a skill, a hook, or a file-backed task tracker?” Experts choose the mechanism based on survival and scope, not just convenience. Claude Code explicitly recommends hooks for deterministic lifecycle actions and skills for on-demand specialized instructions. citeturn3view0turn5view1turn18view3 | “I’ll just tell Claude in the chat” or “I’ll put everything in one big CLAUDE.md.”                   |
| Manual compaction quality   | “What future queries must the summary answer?” Experts use `/compact <instructions>` and can also add compact instructions in CLAUDE.md so the summary preserves exact test commands, modified files, blockers, or known-bad approaches. citeturn22search0turn25view2                                                                                                                | “`/compact` is a generic cleanup command.”                                                           |
| Output containment          | “Which large reads belong in the main context, and which belong in a subagent or paginated tool result?” Experts chunk large reads, page MCP outputs, and delegate log-heavy or research-heavy work to subagents so only summaries return. Claude Code’s costs, troubleshooting, and MCP docs all push in this direction. citeturn18view3turn5view2turn25view1turn24search6        | “If Claude needs more information, reading more of the file into the main session is always better.” |
| Thrashing diagnosis         | “Did compaction fail, or did it succeed and then get immediately refilled?” Claude’s troubleshooting docs say the common thrashing case is not failed compaction but repeated immediate refill from large files or outputs. citeturn5view2                                                                                                                                            | “Auto-compact is broken.”                                                                            |
| Thinking budget interaction | “Is extended thinking helping the task, or just enlarging spend and changing the shape of compaction?” Thinking tokens can be substantial, and as of v2.1.198 the summarization request inherits the session’s extended-thinking configuration. citeturn18view3turn18view0turn18view2                                                                                               | “Thinking is only about answer quality, not compaction behavior or cost.”                            |
| Observability               | “What does `/context` show *right now*? What do hooks say loaded on `compact`? What does the status line show over time?” Experts instrument before they speculate. Claude Code offers `/context`, `/doctor`, status lines, `SessionStart`, `PreCompact`, `PostCompact`, and `InstructionsLoaded` hooks for this. citeturn20view1turn18view1turn6view0turn6view2turn5view2        | “I can infer what happened by how Claude is behaving.”                                               |
| Version drift               | “Is this a current behavior or an old bug/folk belief?” Experts read release notes because compaction semantics and token-usage mechanics have moved significantly: stale `/context` counts, compact failure at over-limit, read-tool deduplication, large tool-result persistence, and auto-compact edge cases have all changed. citeturn12view0turn12view1turn30view0turn30view1 | “If it behaved this way before, it must still behave this way.”                                      |
| Large-codebase scoping      | “Am I paying a monorepo tax?” In large repos, experts scope CLAUDE.md, rules, worktrees, permissions, and per-directory skills to the code they actually touch, because irrelevant instructions and file reads degrade performance and fill context. citeturn25view0                                                                                                                  | “One repo-wide setup should be fine for all tasks.”                                                  |
| Recovery choice             | “Do I need `/compact`, `/clear`, `/rewind`, `/branch`, or a fresh named session?” Experts know that if a session has accumulated repeated failed approaches, `/clear` often beats trying to salvage it. Claude Code explicitly recommends clearing after repeated corrections. citeturn25view2turn20view1                                                                            | “If the session is confusing, I should just keep explaining harder.”                                 |

### The questions experts ask that intermediates often do not

An expert’s internal checklist sounds like this:

- What must survive as **exact strings**, not just gist—package names, flags, env vars, failing test IDs, migration order, API paths, or file locations? Compaction is a summary, and summaries are poor substitutes for exact operational identifiers unless explicitly preserved. citeturn15view0turn16view0
- Is the high-cost material **replayable from disk** or **ephemeral in conversation only**? If it is only in chat, it is fragile across compaction. If it is in a root memory file or task tracker, it can be reloaded or re-injected. citeturn3view0turn18view0
- Is the current context dominated by **irrelevant but expensive tokens**—old tool output, broad test logs, repeated failed attempts, giant MCP responses, or workflow instructions that should have lived in a skill? citeturn18view3turn25view1turn25view2
- If Claude went “off the rails” after compaction, did it actually lose the thing I assumed was sticky, such as a nested CLAUDE.md or a path-scoped rule? The docs say that is a very plausible failure mode. citeturn3view0turn18view0
- Am I overvaluing a 1M context window and undervaluing **smaller, higher-signal active context**? Anthropic’s engineering guidance explicitly warns that more context does not linearly improve performance; larger contexts come with diminishing returns and “context rot.” citeturn13view1turn28view0turn28view2

## A concrete scenario where the gap becomes visible

Consider a realistic monorepo debugging session:

| Item          | Example setup                                                                                                                                         |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repository    | `acme-monorepo/`                                                                                                                                      |
| Root memory   | `CLAUDE.md` says “use pnpm, not npm” and “compact should preserve modified files and exact test commands”                                             |
| Nested memory | `services/auth/CLAUDE.md` says “for auth tests, set `AUTH_EMULATOR=1`; run only `pnpm --filter @acme/auth test -- --runInBand` unless told otherwise” |
| Task          | Investigate a flaky refresh-token failure in `services/auth`, reading a large integration log and patching the bug                                    |
| Risk factors  | Nested instructions, monorepo noise, a large log file, and multiple possible test commands                                                            |

This kind of setup is exactly where Claude Code’s documented reload asymmetries matter. In large codebases, irrelevant instructions and reads can crowd the window, and only some instruction mechanisms deterministically survive compaction. citeturn25view0turn3view0turn18view0

### Inputs and CLI flow

A common intermediate workflow looks like this:

```bash
claude
```

Then, in the session:

```text
Investigate flaky refresh-token failures under services/auth.
Read artifacts/jest-integration.log, fix the bug, and verify the change.
```

A more expert workflow would split this:

```text
Use subagents to inspect artifacts/jest-integration.log and summarize only:
- failing test names
- first causal stack trace
- any auth emulator requirements
- any package-specific commands
Then work only under services/auth.
```

And, before compaction pressure rises, the expert would add a directed compaction step:

```text
/compact Preserve:
- exact package path: services/auth
- exact verify command
- required env vars
- modified files
- known-bad approaches
- current blocker and next step
```

These moves align with Claude Code’s documented guidance: use subagents to contain verbose research, use `/compact` with a focus, and encode compact instructions in CLAUDE.md when certain details must survive summarization. citeturn25view2turn22search0turn20view1

### Expected behavior versus actual behavior

| Intermediate expectation                                                                                           | Actual behavior documented by Claude Code                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| “After compaction, Claude should still know the auth-specific test command because it already learned it earlier.” | If that command lived only in earlier conversation or in a nested `services/auth/CLAUDE.md` that has not been reloaded, it can disappear after compaction. Project-root CLAUDE.md and auto memory are re-injected; nested CLAUDE.md and path-scoped rules are not automatically restored until a matching file is read again. citeturn3view0turn18view0 |
| “If auto-compact goes wrong, compaction itself failed.”                                                            | Claude Code documents a distinct thrashing mode: compaction succeeds, but the context immediately refills from a large read or tool output, so it stops retrying. citeturn5view2                                                                                                                                                                         |
| “Reading the whole big log keeps Claude better informed.”                                                          | Full-session reads can be counterproductive. Troubleshooting guidance recommends smaller chunks, focused compaction, subagents, or `/clear` when large outputs refill the window. MCP docs also warn on large outputs and provide pagination/limits. citeturn5view2turn25view1                                                                          |

### What the visible failure looks like

A typical failure sequence is:

1. Claude reads a very large log or receives a very large tool result.
2. Auto-compaction triggers near the limit.
3. The conversation is summarized.
4. Claude resumes without the nested auth-specific instruction having been reloaded.
5. Claude now runs a broad repo-level command such as `pnpm test` instead of the package-specific auth command.
6. The new test output is huge, context refills, and the session may hit the documented thrashing pattern. citeturn20view1turn3view0turn5view2turn25view1

That gap is where expert and intermediate practice visibly diverge. The intermediate practitioner often interprets step 4 as “Claude got sloppy.” The expert interprets it as “my state layout was not compaction-safe.”

### Diagnostics

A disciplined diagnostic pass is short and concrete:

1. Run `/context` and inspect what is actually loaded. Claude Code explicitly recommends `/context` for verifying which memory files loaded into the current session. citeturn3view0turn20view1  
2. Ask: was the missing fact in:
   - project-root CLAUDE.md,
   - auto memory,
   - a nested CLAUDE.md,
   - a path-scoped rule,
   - a skill body,
   - or only the chat transcript?  
     Only some of those survive or re-inject across compaction. citeturn18view0turn3view0
3. If the session shows a thrashing error, treat it as a **refill** problem, not a “bad summarizer” problem. The docs recommend chunking the file, focused `/compact`, moving the work to a subagent, or `/clear`. citeturn5view2
4. Check whether a giant output source is the refiller:
   - file read,
   - MCP tool result,
   - massive test output,
   - or repeated failed turns.  
     Claude Code warns on large MCP outputs, caps defaults, and recent releases also moved large tool results to disk sooner to reduce context-window pressure. citeturn25view1turn30view1
5. If behavior differs from what you expect, check the CLI version and changelog before forming a theory. `/compact`, `/context`, and auto-compact behavior changed in multiple releases. citeturn12view0turn12view1turn30view0turn30view2

### Remediation

The expert remediation is not “re-explain everything in chat.” It is:

1. **Reload the missing scope** by reading a file under `services/auth/` so the nested CLAUDE.md or scoped rules become active again. Nested/path-scoped instructions reload on matching file access rather than being automatically preserved after compaction. citeturn18view0turn3view0  
2. **Compact with intent**, not generically:
   
   ```text
   /compact Preserve:
   - services/auth path
   - AUTH_EMULATOR=1
   - exact verify command
   - failing test identifiers
   - modified files
   - known-bad attempts
   ```
   
   Claude Code explicitly supports directed `/compact` instructions and CLAUDE.md-based compact instructions. citeturn22search0turn25view2
3. **Move verbose analysis to a subagent**, so only the summary returns to the main context. This is one of Claude Code’s strongest documented strategies for keeping the main session clean. citeturn18view0turn18view3turn25view2
4. **Contain oversized outputs** by reading line ranges, asking for narrower functions, or paginating MCP output rather than reloading the entire artifact into the main session. citeturn5view2turn25view1
5. **Make the critical task state reloadable** by storing it in a file or using a `SessionStart` hook with matcher `compact` to re-inject a current-task summary after compaction. Claude’s hooks guide documents exactly this pattern. citeturn6view1turn6view3

A practical hook for that pattern is:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          {
            "type": "command",
            "command": "cat .claude/current-task.md"
          }
        ]
      }
    ]
  }
}
```

This works because `SessionStart` can match `compact`, and anything the hook writes to stdout is added to Claude’s context. citeturn6view1turn6view3

## The costliest reasoning error

The most costly reasoning error in Claude Code CLI context-compaction engineering is this:

**Treating compaction as semantically neutral compression instead of lossy abstraction over future work.**

That sounds subtle, but it causes a long chain of bad decisions. Once someone believes compaction is basically a smaller replay of the same state, they underinvest in externalizing exact commands and paths, overread logs into the main session, assume nested or path-scoped instructions are “sticky,” and misdiagnose post-compact drift as negligence by the model rather than an information-shape problem created by their own context design. Claude’s docs repeatedly imply the opposite mental model: compaction summarizes history, response quality degrades as conversations grow, and compaction is less ideal for work that depends on precise recall of earlier details. citeturn15view0turn16view0turn28view2

This is costly because it wastes time in the most expensive part of agentic coding loops: **re-discovery**. The model re-reads files it already read, retries commands it already learned are wrong, and replays analysis you thought had already been preserved. Community issue reports in the Claude Code repository repeatedly describe this pattern after auto-compaction: missing CLAUDE.md context, forgotten repository-path changes, repeated known mistakes, or loss of the “working memory” that the user assumed persisted. Those reports are anecdotal, but they are directionally consistent with the official survival semantics and troubleshooting docs. citeturn23search20turn23search11turn23search17turn23search6turn3view0turn5view2

As a formal matter, this reasoning error violates two closely related principles.

First, it violates the **sufficiency principle** in state design: a summary is only safe if it preserves the information sufficient for the future decisions you will ask the model to make. Claude’s own default summary prompt for SDK compaction is telling here: it tries to preserve task overview, current state, important discoveries, next steps, and context to preserve. That structure is useful precisely because a generic abridgment is not enough; you need a summary optimized for task continuation. Claude’s platform docs also explicitly mark compaction as a worse fit for tasks needing precise recall of earlier details or exact state across many variables. citeturn16view0

Second, it violates the **data processing inequality** intuition from information theory: once you replace the raw interaction history with a summary, post-processing cannot increase the information available about the original state. If the exact package path, flag, migration order, failed workaround, or file location was not preserved in the summary or in a reloadable artifact, you cannot expect the model to recover it just because it “was discussed earlier.” That is the wrong inference. citeturn29search0turn29search2

The expert correction is therefore simple but profound:

> Do not ask, “How do I make the transcript smaller?”  
> Ask, “What is the smallest state that is still sufficient for the next decisions?” citeturn28view3turn15view0

## Prioritized recommendations and diagnostic checklist

### Prioritized actions to avoid the error

| Priority  | Action                                                                                                                                                                                                                                                                                    | Why it works                                                                                                                                                                                                                                    |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Highest   | **Externalize exact task state before compaction pressure rises.** Put exact verify commands, required env vars, modified files, known-bad approaches, and next-step checkpoints into project-root CLAUDE.md, auto memory where appropriate, or a file such as `.claude/current-task.md`. | Chat-only state is fragile. Project-root CLAUDE.md and auto memory are re-injected; conversation-only instructions can be lost. Claude Code also supports custom compact instructions in CLAUDE.md. citeturn3view0turn25view2turn22search0 |
| Very high | **Instrument compaction.** Use `/context`, a status line that shows context usage, and hook-based re-injection on `SessionStart` with matcher `compact`.                                                                                                                                  | Experts do not rely on intuition. Claude Code explicitly supports `/context`, status lines, and compact-triggered session-start hooks whose stdout is injected into context. citeturn20view1turn18view1turn6view1turn6view3               |
| Very high | **Compact deliberately, not generically.** Use `/compact Preserve: ...` and make the preservation target task-specific.                                                                                                                                                                   | Claude Code documents both focused `/compact` and CLAUDE.md-based compact instructions. That directly addresses future-query sufficiency instead of generic summarization. citeturn25view2turn22search0                                     |
| High      | **Contain large reads and tool outputs.** Use subagents for research/log triage, ask for chunks, paginate MCP tools, and avoid pulling giant artifacts into the main session.                                                                                                             | This directly reduces refill/thrashing risk and keeps the main conversation high-signal. Claude’s docs recommend subagents and smaller chunks, and MCP docs expose output thresholds and limits. citeturn25view2turn5view2turn25view1      |
| High      | **Choose the right persistence surface.** Put universal, persistent rules in root CLAUDE.md; put narrow procedures in skills; use hooks for deterministic lifecycle actions; use nested/path-scoped files only when you accept their reload semantics.                                    | Different mechanisms have different load and reload behavior. Experts design with those semantics in mind rather than treating every instruction store as equivalent. citeturn3view0turn5view1turn18view3                                  |
| Medium    | **Lower the compaction trigger only after you have reduced noise.** Use `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` or window settings *after* fixing the state-design problem.                                                                                                                     | Earlier compaction can help, but threshold tuning is not a substitute for decision-sufficient summaries and output containment. Claude Code documents the override and when it applies. citeturn25view3turn24search4                        |
| Medium    | **Use `/clear` sooner.** If you have corrected Claude multiple times on the same issue or the work is now unrelated, clear the session instead of dragging stale failures forward.                                                                                                        | Claude Code explicitly recommends `/clear` after repeated corrections and between unrelated tasks because cluttered context degrades performance. citeturn25view2                                                                            |
| Medium    | **Stay changelog-aware.** Re-check current release notes before treating an observed behavior as a timeless truth.                                                                                                                                                                        | Compaction-relevant mechanics have changed repeatedly: thresholds, stale `/context` counts, `/compact` overflow failures, large-tool-result persistence, read deduplication, and more. citeturn12view0turn12view1turn30view0turn30view1   |

### Step-by-step diagnostic checklist

Use this exact sequence when a compacted session starts behaving “dumber” than it did before:

1. **Run `/context`.** Verify what is actually consuming context and which memory files are loaded now, not what you assume should be loaded. citeturn20view1turn3view0  
2. **Classify the missing fact.** Was it in project-root CLAUDE.md, nested CLAUDE.md, a path-scoped rule, auto memory, a skill, or just chat history? Different stores have different post-compaction behavior. citeturn3view0turn18view0  
3. **Check for refill sources.** Identify whether the session is being dominated by a large file read, huge test output, MCP results, or repeated failed attempts. If you saw a thrashing message, assume refill first. citeturn5view2turn25view1  
4. **Reload missing scoped instructions intentionally.** Read a file under the relevant path so nested/path-scoped rules load again. Do not assume compaction restored them. citeturn18view0turn3view0  
5. **Compact with a preservation target.** Preserve exact test commands, env vars, modified files, blockers, and known-bad approaches—not just “the important stuff.” citeturn25view2turn22search0  
6. **Move verbose work out of the main session.** Use a subagent for logs, repo exploration, or broad research. Keep implementation in the main context. citeturn25view2turn18view0  
7. **If the session is polluted, clear it.** Claude Code’s own best-practices guidance says a clean session with a better prompt often outperforms a long cluttered one. citeturn25view2  
8. **If behavior still seems inconsistent, check version-specific notes and test under reduced customization.** Use `/doctor`; if needed, restart with `claude --safe-mode` to rule out plugins, hooks, or MCP customizations. citeturn5view2

If you adopt only one habit from this report, make it this one: **before compaction, promote any task-critical exact detail out of “mere conversation” and into a reloadable, inspectable state surface.** That single habit aligns your workflow with the documented mechanics of Claude Code, with Anthropic’s context-engineering guidance, and with the formal fact that lossy summaries cannot magically preserve information you never explicitly chose to preserve. citeturn3view0turn6view1turn28view3turn29search0
