# **Optimizing Claude Code Sub-Agents: An Exhaustive Analysis of High-Performance Agentic Delegation**

The transition from autocomplete-style artificial intelligence to fully agentic software engineering systems marks a fundamental shift in computational architecture. Within the Claude Code ecosystem, this evolution is realized through the deployment of an iterative ReAct-pattern loop operating within a highly structured operational harness. This harness utilizes a sophisticated orchestration mechanism capable of delegating arbitrary workloads to specialized, isolated sub-agents. These sub-agents operate independently, maintaining separate context windows, restricted toolsets, and distinct permission boundaries before asynchronously synthesizing their findings for a primary orchestrator1.  
However, scaling multi-agent topologies within local development environments introduces severe systemic risks. Without rigorous architectural constraints, sub-agent fan-out frequently results in cascading context pollution, schema drift, race conditions during concurrent filesystem mutations, and catastrophic token consumption4. Furthermore, generic multi-agent frameworks often fail to map optimally to Claude’s native constraints, missing the advantages of Anthropic's five-layer compaction pipeline, deny-first permission matrices, and deep integration with the Model Context Protocol (MCP)3.  
The ensuing analysis provides a definitive, operational framework for defining, designing, and instantiating high-performance Claude Code sub-agents. It establishes a canonical schema, maps complex task loads to empirically validated prompt patterns, and prescribes concrete mitigations for the unique failure modes endemic to long-horizon, autonomous code generation.

## **The Operational Definition of a "Great" Claude Code Sub-Agent**

The distinction between a functionally competent sub-agent and a structurally optimized, "Great" sub-agent lies in the transition from raw linguistic capability to engineered systemic reliability. A competent sub-agent can execute a sequence of shell commands and return a summary. In contrast, a great sub-agent autonomously manages its epistemics, actively suppresses context-window inflation, and seamlessly navigates Claude Code’s seven-tiered permission hierarchy without unnecessarily bubbling execution blockers up to the human operator or the parent orchestrator5.  
A "Great" Claude Code sub-agent is operationally defined by rigorous quantitative and qualitative criteria mapped directly to the runtime's architectural constraints.

### **Quantitative Performance Criteria**

The empirical measurement of a sub-agent's efficacy relies on metrics that evaluate resource utilization, error-recovery autonomy, and parallel concurrency limits.

| Metric | Target Threshold | Architectural Justification |
| :---- | :---- | :---- |
| **Context Overhead Ratio** | \< 15% | The token cost of spawning the sub-agent and ingesting its returned summary must not exceed 15% of the tokens that would have been consumed if the parent orchestrator executed the tools directly. Great sub-agents leverage sidechain transcripts (sessionStorage.ts) to isolate high-volume Read, Grep, and Glob outputs from the parent's history, actively avoiding the computationally expensive Auto-compact layer of the compaction pipeline7. |
| **Autonomous Error-Recovery Rate** | \> 85% Pass@1 | When executed tools return non-zero exit codes (e.g., test failures, linting errors), the sub-agent must intercept the failure, interpret the standard error output, and self-correct iteratively. The sub-agent must suppress the error from reaching the parent session until the maximum agentic turns threshold (maxTurns) is breached4. |
| **Tool-Use Orthogonality** | \> 0.95 | This metric tracks the ratio of semantically meaningful tool invocations to redundant or hallucinated calls. A great sub-agent does not repeatedly invoke Read on identical files due to context amnesia, nor does it attempt to invoke Bash commands without prior validation of the directory structure via Glob13. |
| **Parallel Concurrency Survival Rate** | 100% | In fan-out orchestration patterns (e.g., spawning up to seven parallel sub-agents), the agents must complete their tasks without triggering repository state collisions. This requires a 100% isolation rate, often achieved by utilizing the isolation: "worktree" parameter to branch the repository automatically during execution13. |

### **Qualitative Engineering Criteria**

Beyond empirical metrics, the structural design of the sub-agent must adhere to Anthropic's established values of human decision authority, safety, and capability amplification3.  
The principle of least privilege dictates that a sub-agent is initialized with the absolute minimum toolset required for its operational domain. A static analysis sub-agent designed to review code must be restricted exclusively to \["Read", "Grep", "Glob"\]. By entirely omitting the Bash, Write, Edit, and Agent tools, the architecture physically prevents the sub-agent from executing unauthorized system mutations, engaging in prompt-injection-driven network exfiltration, or initiating infinite, recursive sub-agent loops17.  
Furthermore, hand-off fidelity and schema adherence are paramount. The final return payload transmitted from the sub-agent to the orchestrator must strictly adhere to a predefined structured format (typically JSON or structured Markdown tables). The sub-agent must meticulously strip all intermediate trajectories, conversational pleasantries, and raw logs, returning only deterministic state changes, semantic findings, and standardized confidence scores15.  
Finally, the metadata triggering the sub-agent must exhibit extreme semantic precision. The sub-agent’s definition file utilizes a description field that serves as the routing mechanism for the Claude orchestrator. A great sub-agent utilizes highly calibrated, prose-based trigger scenarios that prevent overlapping responsibilities and ensure the orchestrator dispatches the correct agent for the specific task geometry20.

## **Canonical File Format and Schema for Sub-Agent Definitions**

Within the Claude Code ecosystem, custom sub-agents are instantiated dynamically via Markdown files containing YAML frontmatter. These files are typically stored in .claude/agents/ for project-scoped capabilities, or \~/.claude/agents/ for globally available user-scoped capabilities16. The runtime relies exclusively on the YAML frontmatter for metadata, tool restriction enforcement, model routing, and lifecycle configuration, while the Markdown body functions as the deterministic, immutable system prompt16.  
To guarantee reproducibility, version control compatibility, and seamless parsing by the Claude runtime, the sub-agent definition must strictly obey the comprehensive schema derived below.

### **JSON Schema for YAML Frontmatter Validation**

The following JSON Schema formally defines the rigorous constraints applied to the YAML frontmatter of a Claude Code sub-agent definition. It covers all acceptable parameters, prioritizing the critical disallowedTools, mcpServers, and hooks attributes utilized for robust extensibility and security12.

JSON  
{  
  "$schema": "http://json-schema.org/draft-07/schema\#",  
  "title": "Claude Code Canonical Sub-Agent Frontmatter",  
  "description": "Defines the exact parameters for loading, versioning, and composing sub-agents within the Claude Code ReAct runtime.",  
  "type": "object",  
  "required": \["name", "description"\],  
  "properties": {  
    "name": {  
      "type": "string",  
      "pattern": "^\[a-z0-9\](\[a-z0-9-\]{1,48}\[a-z0-9\])?$",  
      "description": "Unique identifier used for namespacing and invocation. Must be 3-50 characters, lowercase, numbers, and hyphens only."  
    },  
    "description": {  
      "type": "string",  
      "minLength": 10,  
      "maxLength": 1000,  
      "description": "Routing field. Must include trigger scenarios phrased as prose noun phrases, concluding with a pointer to the 'When to invoke' body section."  
    },  
    "model": {  
      "type": "string",  
      "enum": \["inherit", "sonnet", "opus", "haiku", "fable", "fast"\],  
      "default": "inherit",  
      "description": "The target model tier. Resolves via environment variables, per-invocation parameters, or session defaults."  
    },  
    "tools": {  
      "type": "array",  
      "items": { "type": "string" },  
      "description": "Explicit allowlist of native tools. If omitted, the sub-agent inherits all tools available to the parent."  
    },  
    "disallowedTools": {  
      "type": "array",  
      "items": { "type": "string" },  
      "description": "Explicit denylist. Takes precedence over the tools array. Supports MCP server patterns (e.g., 'mcp\_\_server\_\_\*')."  
    },  
    "permissionMode": {  
      "type": "string",  
      "enum": \["default", "acceptEdits", "auto", "dontAsk", "bypassPermissions", "plan", "manual"\],  
      "description": "Overrides the active permission mode, shifting the autonomy-safety tradeoff for the isolated execution context."  
    },  
    "maxTurns": {  
      "type": "integer",  
      "minimum": 1,  
      "description": "Ceiling on the number of agentic turns executed before the sub-agent automatically halts."  
    },  
    "skills": {  
      "type": "array",  
      "items": { "type": "string" },  
      "description": "Array of skill names to preload entirely into the sub-agent's context window upon initialization."  
    },  
    "mcpServers": {  
      "type": "array",  
      "items": {  
        "anyOf": \[  
          { "type": "string" },  
          { "type": "object" }  
        \]  
      },  
      "description": "MCP servers exposed to this sub-agent. Can be string references to existing servers or full inline configurations."  
    },  
    "hooks": {  
      "type": "object",  
      "description": "Lifecycle hooks (PreToolUse, PostToolUse, etc.) scoped strictly to this sub-agent's isolated context."  
    },  
    "memory": {  
      "type": "string",  
      "enum": \["user", "project", "local"\],  
      "description": "Defines the persistent memory scope, enabling the sub-agent to preserve findings across distinct conversational sessions."  
    },  
    "background": {  
      "type": "boolean",  
      "default": true,  
      "description": "Forces the sub-agent to execute as a non-blocking background task, allowing concurrent orchestrator operation."  
    },  
    "effort": {  
      "type": "string",  
      "enum": \["low", "medium", "high", "xhigh", "max"\],  
      "description": "Overrides the reasoning effort level (Extended Thinking) specifically while this sub-agent is active."  
    },  
    "isolation": {  
      "type": "string",  
      "enum": \["worktree"\],  
      "description": "Executes the sub-agent within a temporary git worktree, providing an isolated repository copy that is discarded if no mutations occur."  
    },  
    "color": {  
      "type": "string",  
      "enum": \["red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"\],  
      "description": "Semantic display color for the terminal user interface and transcript logs."  
    },  
    "initialPrompt": {  
      "type": "string",  
      "description": "Auto-submitted first turn when the agent runs as the main session agent. Ignored when invoked hierarchically as a sub-agent."  
    }  
  },  
  "additionalProperties": false  
}

### **The Architecture of the Markdown System Prompt**

The textual body of the Markdown file constitutes the system prompt injected into the sub-agent's isolated context window. An optimized system prompt for Claude Code strictly partitions behavioral instructions from triggering heuristics.  
A hallmark of Anthropic's internal plugin architecture is the mandatory inclusion of a "When to invoke" section20. Because the YAML description field is injected into the parent orchestrator's context to facilitate routing decisions, it must remain flat, concise prose21. However, the detailed, worked scenarios that ground the sub-agent's understanding of its own purpose must reside within the Markdown body, as this content is exclusively loaded when the sub-agent is actually invoked20.

### **Canonical Sub-Agent Implementation Instance**

The following represents a production-grade implementation of a highly specialized security auditing sub-agent. It illustrates the precise interplay between the YAML frontmatter constraints and the structural requirements of the Markdown system prompt. The implementation explicitly restricts tools to prevent unauthorized mutation, designates the haiku model for high-velocity analysis, and utilizes the dontAsk permission mode to enable frictionless, asynchronous execution9.

## **name: security-auditor-haiku description: Use this agent when you need to perform a read-only security analysis on a specific module. Typical triggers include proactive review after writing database code, user-requested security checks, and pre-commit validation. See "When to invoke" in the agent body for worked scenarios. model: haiku tools: \["Read", "Grep", "Glob"\] disallowedTools: \["Agent", "Bash", "Write", "Edit", "NotebookEdit"\] permissionMode: dontAsk background: true effort: medium color: red**

You are an expert application security auditor specialized in identifying vulnerabilities, injection flaws, and logic errors in source code. You operate in a strictly read-only capacity.

## **When to invoke**

* **Proactive review after writing database code.** The orchestrator has just authored database access code or SQL queries and must check for injection risks before declaring the task done.  
* **User-requested security check.** The human operator explicitly asks for a security review of recent code modifications.  
* **Pre-commit validation.** The orchestrator signals readiness to commit changes to a sensitive authentication or authorization module.

## **Process**

1. Use the Glob tool to identify all target files within the requested directory or module.  
2. Use the Read and Grep tools to analyze the source code for insecure patterns (e.g., hardcoded secrets, lack of input sanitization, unsafe deserialization).  
3. Cross-reference your findings against the architectural rules defined in the project's CLAUDE.md hierarchy.

## **Output Format**

You must return your findings as a strictly formatted JSON array. Do not output any conversational text, introductory pleasantries, or markdown formatting outside of the JSON block. \[ { "file\_path": "string", "line\_number": "integer", "severity": "CRITICAL|HIGH|MEDIUM|LOW", "description": "string", "remediation\_suggestion": "string" } \]

## **Task-to-Pattern Mapping: Prompt, Toolset, and Harness Co-Design**

The architecture of a Claude Code deployment must dynamically adjust to the topological requirements of the task. Deploying a computationally expensive opus model with full filesystem access for a trivial repository search incurs unacceptable latency and context overhead25. Conversely, attempting to execute a massive, multi-file refactor using a single, sequential agent loop guarantees context window saturation, leading to cascading cognitive collapse1.  
The co-design of the prompt pattern, the toolset, and the evaluation harness must be precisely calibrated to the task load. The decision matrix below maps arbitrary workloads onto the optimal orchestrator-to-worker topologies.

| Task Load Profile | Optimal Orchestration Topology | Model Selection | Tool Set Constraint | Evaluation Harness / Hooks |
| :---- | :---- | :---- | :---- | :---- |
| **Broad Codebase Discovery** *(e.g., "Analyze the routing patterns across these 8 microservices")* | **Parallel Exploration**4. Fan-out 4-8 sub-agents concurrently, mapping one agent per discrete directory. | haiku (Optimized for speed and high-volume read operations) | \["Read", "Grep", "Glob"\]. Explicitly disallow Bash, Write, and Edit to prevent accidental mutation. | PostToolUse hook enforcing maximum token return limits on the sub-agents to prevent orchestrator context bloat. |
| **Repetitive Application** *(e.g., "Generate unit tests for these 15 React components based on this template")* | **Parallel Pipeline**. Orchestrator isolates one component per sub-agent, dispatching them simultaneously to generate tests in isolation13. | sonnet (Balanced implementation and coding capabilities) | \["Read", "Write", "Bash"\]. Restrict Bash execution strictly to local test runners (e.g., npm test). | PreToolUse hook validating Write target paths to strictly prevent git merge conflicts across the parallel workers13. |
| **Complex Multi-File Refactoring** *(e.g., "Migrate the authentication layer from JWT to session cookies")* | **Spec-Driven Development (SDD)**4. Orchestrator generates a TASKS.md specification in plan mode, then spawns sequential workers. | opus (Orchestrator) sonnet (Workers) | Full native toolset. isolation: "worktree" enabled to isolate experimental changes and prevent main branch corruption16. | PostToolUse hook triggering test suites automatically. Sub-agents must autonomously resolve exit codes \> 0 before returning4. |
| **Quality Assurance / CI Gate** *(e.g., "Audit this PR for security flaws and style violations")* | **Reflexion / Self-Correction**. Sub-agent reviews orchestrated code, triggers linters, and loops until zero errors are reported. | sonnet | \["Read", "Bash"\]. Bash restricted via regex patterns to static analysis tools only. | Model-based evaluation utilizing a type: "prompt" hook to vote on code quality prior to signaling task completion23. |

### **Implementing the Hook Pipeline for Evaluation Harnesses**

The evaluation of a sub-agent's output should rarely be left to the model's own immediate self-assessment, as large language models exhibit a documented tendency to confidently praise their own mediocre work11. Instead, evaluation criteria must be enforced deterministically via Claude Code's hook pipeline.  
Spanning 27 distinct event types (e.g., PreToolUse, PostToolUse, SessionEnd, ConfigChange), hooks intercept the agentic ReAct loop and execute user-defined shell commands, HTTP endpoints, or specialized LLM evaluation prompts23. By attaching a type: "command" hook to the PostToolUse event for the Write tool, the system can automatically trigger a test suite or linter the moment a sub-agent modifies a file. If the hook script returns an exit code of 2 or higher, the runtime blocks the tool execution and feeds the error output directly back into the sub-agent's context window, forcing a self-correction loop without human intervention23.

## **Recent Agent Prompt Patterns Adapted for Claude**

Generic prompt engineering patterns extracted from academic literature often fail to leverage the specific constraints of the Claude Code architecture. Recent empirical research (2024-2026) demonstrates that Claude models achieve maximum efficacy when generation is strictly separated from evaluation, and when architectural plans are crystallized as immutable artifacts on disk prior to execution11.

### **Spec-Driven Development (SDD) and Plan-and-Execute**

The most significant advancement in long-horizon coding tasks is the formalization of Spec-Driven Development (SDD)28. Instead of prompting an agent to "build a feature," the optimal Claude-native pattern bifurcates the cognitive load.  
First, the orchestrator is forced into plan permission mode. In this mode, the model retains read access but all write operations and destructive shell commands are physically blocked by the runtime9. The orchestrator utilizes this phase to read the codebase, draft architecture diagrams, and ultimately output a highly structured TASKS.md specification file. This specification breaks the feature down into atomic, testable units using the Easy Approach to Requirements Syntax (EARS)28.  
Once the human operator approves the specification, the permission mode is shifted to acceptEdits or dontAsk. The orchestrator then spawns sequential sub-agents. The critical adaptation here is that the sub-agent is not passed the entire conversation history; rather, its prompt simply passes a file pointer to the TASKS.md specification. The sub-agent operates in a fresh context window, reads the specific task it is assigned, implements the code, and commits the atomic change. This prevents the sub-agent's execution trajectory from polluting the orchestrator's planning context4.

### **"Interview Before Implementation" Pattern**

To further reduce architectural hallucinations, high-performance sub-agents employ the "Interview Before Implementation" pattern4. The sub-agent's system prompt mandates that, prior to utilizing the Write or Bash tools, it must synthesize its understanding of the codebase and utilize the AskUserQuestion tool to surface any ambiguities regarding third-party library versions, internal API contracts, or unhandled edge cases. This forces a deterministic pause in the ReAct loop, ensuring that design decisions are explicitly validated by the human principal before destructive actions occur.

### **Constitutional Constraints via the Memory Hierarchy**

Rather than injecting massive lists of coding standards into every sub-agent prompt, Claude-native deployments leverage the CLAUDE.md memory hierarchy. The runtime automatically parses CLAUDE.md files from the current directory up to the repository root, injecting them as user-context messages immediately prior to the model call10.  
By defining project-specific constitutional AI constraints (e.g., "Never utilize any types in TypeScript," "All database queries must use parameterized inputs to prevent SQL injection") within the CLAUDE.md file, the system ensures that every sub-agent automatically inherits these rules without requiring redundant prompt engineering. Because these constraints are loaded into the user-context layer, they survive the aggressive Snip and Microcompact phases of the context compaction pipeline, maintaining their influence over the model regardless of conversation length7.

## **Unique Failure Modes and Concrete Mitigations**

Operating autonomous sub-agents within an interactive, local software environment introduces unique systemic failure modes that differ significantly from conversational chatbot architectures or isolated sandbox environments. Claude Code's runtime architecture mitigates many of these risks inherently, but developers must architect specific schemas and prompt constraints to eliminate the remainder.

### **1\. Context Pollution and the Auto-Compact Cascade**

**The Failure Mechanism:** A sub-agent conducts a massive discovery operation across a repository, utilizing the Read and Grep tools dozens of times. While the sidechain transcript successfully isolates these raw tool calls from the parent orchestrator, the sub-agent eventually synthesizes its findings and returns a highly verbose, 4,000-word conversational summary to the orchestrator. The orchestrator's context window inflates rapidly.  
Once the context window exceeds the configured pressure threshold, Claude Code's five-layer compaction pipeline activates7. If the lightweight layers (Budget reduction, Snip, Microcompact, Context collapse) fail to relieve the pressure, the system triggers the computationally expensive fifth layer: Auto-compact. This layer forces a full model-generated summary of the entire conversation history7. This destructive compression frequently obliterates nuanced architectural decisions, resulting in a cascading loss of coherence where the orchestrator forgets its original objective.  
**The Concrete Mitigation:** Enforce structural brevity at the schema level. Append the following rigid constraint to all sub-agent system prompts: *"You must return only the final mutated state or a strict JSON array of your findings. You are strictly forbidden from outputting conversational text, describing your methodology, or explaining your tool usage. Limit your total response to a maximum of 250 words."*15.

### **2\. Premature Tool-Call Termination**

**The Failure Mechanism:** A sub-agent designed explicitly to orchestrate further downstream tools (e.g., routing tasks to specific MCP servers) analyzes the user's request and outputs a highly detailed natural language explanation of its intended plan, but ultimately fails to emit the structured XML/JSON payload required to actually invoke the tool. The ReAct loop halts prematurely, requiring human intervention to prompt the agent to continue26.  
**The Concrete Mitigation:** While generic multi-agent frameworks handle this through complex middleware retry loops, Claude Code native configurations can emulate strict API-level tool forcing. At the API level, setting tool\_choice: {"type": "any"} forces the model to emit a tool use block without prepending natural language32. Because sub-agent YAML definitions do not currently expose the tool\_choice parameter directly32, this must be enforced via the prompt constraint: *"You are an execution agent. You must invoke a tool in every turn. You are strictly forbidden from outputting natural language explanations before your tool use block."*

### **3\. Schema Drift and Agent Amnesia**

**The Failure Mechanism:** During long-horizon tasks (e.g., a sub-agent session exceeding 15 agentic turns to implement a complex feature), the sub-agent gradually "forgets" the highly specific JSON schema or formatting constraints requested in its initial prompt. It begins returning malformed outputs, causing downstream parsing failures4.  
**The Concrete Mitigation:** Implement Spec-Anchored Development. Rather than relying on the sub-agent's internal context window to retain the schema indefinitely, require the sub-agent to utilize the Read tool to reference a physical contract file (e.g., SCHEMA\_CONTRACT.md) on disk periodically. Furthermore, utilize PostToolUse command hooks to pipe the sub-agent's final output through jq or a similar JSON validator. If the validation fails, the hook returns an exit code of 1 with the validation error, forcing the sub-agent to automatically regenerate the output in the correct format before the orchestrator ever sees it4.

### **4\. Concurrent Modification Collisions**

**The Failure Mechanism:** An orchestrator spawns multiple sub-agents in parallel to rapidly implement boilerplate code. Two sub-agents attempt to utilize the Edit tool on the exact same target file simultaneously. The race condition results in one agent's changes silently overwriting the other's, or triggers severe git merge conflicts that halt the entire process13.  
**The Concrete Mitigation:** Parallel sub-agents must be strictly path-isolated at the moment of invocation. The orchestrator's prompt must contain the constraint: *"When spawning parallel workers, you must assign strictly disjoint file paths to each worker. You are strictly forbidden from permitting multiple sub-agents to access the same directory or file."*13. For ultimate safety, configure the parallel sub-agents with isolation: "worktree" in their YAML frontmatter, ensuring each operates in a completely isolated branch that is only merged upon verified success12.

## **Annotated Before/After Prompt Examples**

The transition from generic prompt engineering to Claude-native optimization requires abandoning conversational personas in favor of rigid, structurally bounded instructions that map directly to the system's routing and execution mechanics.

### **The Naive Implementation (Merely Competent)**

This prompt relies entirely on the model to infer its boundaries. It leads to tool hallucinations, verbose responses that pollute the orchestrator's context, and a lack of clear triggers for the dispatcher.

## **name: code-reviewer description: Helps review code**

You are a helpful code reviewer. Please look at the code I just wrote and tell me if there are any bugs. Make sure to fix them if you find them. Use whatever tools you need. Give me a detailed report of everything you did.  
**Architectural Critique:** The description lacks prose-based trigger scenarios, virtually guaranteeing that the orchestrator's routing mechanism will fail to dispatch this agent autonomously20. The prompt grants implicit permission to modify code ("fix them"), directly violating the principle of least privilege. Furthermore, requesting a "detailed report" ensures catastrophic context pollution when the orchestrator receives the highly verbose summary, risking the activation of the Auto-compact layer7.

### **The Optimized Implementation (Claude-Native Excellence)**

This prompt utilizes Anthropic's recommended internal structures, exact semantic triggers, explicit tool restrictions, and rigid structured output constraints20.

## **name: code-reviewer description: Use this agent when you need to review source code for logical errors, style guide adherence, and performance issues. Typical triggers include user-requested code review, proactive review after a complex feature implementation, and pre-PR sanity checks. See "When to invoke" in the agent body for worked scenarios. model: sonnet tools: \["Read", "Grep", "Glob"\] disallowedTools: \["Write", "Edit", "Bash", "Agent"\] color: blue effort: high**

You are a senior principal engineer tasked with rigorous, read-only code review. You evaluate code against the architectural instructions found in the CLAUDE.md hierarchy.

## **When to invoke**

* **User-requested code review.** The user explicitly asks for a review of a specific file or module.  
* **Proactive review.** The orchestrator has finished a complex refactoring task and requires validation before proceeding to the next sequential step.  
* **Pre-PR sanity check.** The user is preparing to commit and open a pull request.

## **Process**

1. Accept the target\_path provided by the orchestrator.  
2. Utilize Glob to map the directory, then Read the target files and relevant interface definitions.  
3. Compare the implementation against CLAUDE.md standards.

## **Output Format**

You are strictly forbidden from outputting conversational text or explaining your methodology. You must return your findings exclusively as a strict Markdown table. If no issues are found, return exactly: "STATUS: PASS".

| Severity | File:Line | Issue Description | Suggested Fix |
| :---- | :---- | :---- | :---- |
| ... | ... | ... | ... |

## **Implementation Appendix: API Parameters, Message Roles, and Tool Schemas**

Transitioning these theoretical architectural patterns into production requires an exact understanding of the specific parameters and configurations exposed by the Claude Code Agent SDK and CLI environments.

### **The Agent Tool Parameter Schema**

When the primary orchestrator determines that delegation is necessary, it invokes the native Agent tool (which was renamed from the Task tool in version 2.1.63, a change that requires updating any legacy tool\_name hook matchers)16. The parameters passed by the orchestrator strictly dictate the sub-agent's initial state and execution context.  
The input schema for the Agent tool requires the following arguments:

| Parameter | Type | Required | Description |
| :---- | :---- | :---- | :---- |
| subagent\_type | string | Yes | Identifies the specific agent to spawn. This string must exactly match the name field defined in the target sub-agent's YAML frontmatter35. |
| prompt | string | Yes | The highly specific, self-contained task instruction passed into the sub-agent's fresh context window. This must include all necessary file paths and contextual data, as the sub-agent cannot read the parent's history15. |
| description | string | Yes | A concise, 3-5 word summary of the task utilized for the terminal user interface rendering35. |
| run\_in\_background | boolean | No | Controls execution blocking. As of v2.1.198, sub-agents run in the background by default. Setting this explicitly to false forces the orchestrator to block and wait synchronously for the sub-agent's result18. |
| resume | string | No | The specific Session ID or Agent ID of a previously executed sub-agent. If provided, the runtime reconstructs the session state from the sessionStorage.ts sidechain transcript, allowing the sub-agent to continue its previous work17. |

(Note: While earlier versions of the schema allowed the orchestrator to dynamically override the model tier via a model parameter, recent updates have stripped this from the schema (additionalProperties: false), forcing model resolution to fall back to the YAML frontmatter, environment variables, or parent inheritance36.)

### **Hook Pipeline Registration Matrix**

To enforce the deterministic mitigations outlined in this report—such as blocking unsafe commands, validating schemas, or executing autonomous linting—developers must register hooks within the .claude/settings.json file. The configuration necessitates defining the lifecycle event, applying a regex-based matcher, and specifying the action payload23.

JSON  
{  
  "hooks": {  
    "PreToolUse": \[  
      {  
        "matcher": "Bash",  
        "hooks": \[  
          {  
            "type": "command",  
            "command": "./scripts/audit-bash.sh $TOOL\_INPUT"  
          }  
        \]  
      }  
    \],  
    "PostToolUse": \[  
      {  
        "matcher": "Edit|Write",  
        "hooks": \[  
          {  
            "type": "command",  
            "command": "jq \-r '.tool\_input.file\_path' | xargs npx prettier \--write"  
          }  
        \]  
      }  
    \]  
  }  
}

In this configuration, the PreToolUse hook intercepts every Bash invocation before it reaches the shell sandbox10. If the audit-bash.sh script returns an exit code of 1, the tool call is blocked, and the JSON decision reason is fed back to the model23. The PostToolUse hook executes immediately after any codebase mutation (Edit or Write), passing the target file path via jq to an external formatter (prettier), guaranteeing formatting consistency without requiring manual intervention from the LLM27.  
By offloading deterministic enforcement to the hook pipeline and restricting the LLM purely to heuristic reasoning, the Claude Code sub-agent architecture achieves the requisite reliability for production-grade, autonomous software engineering.

#### **Works cited**

1. Claude Sub Agents and Agent Teams: When to Delegate Inside Claude \- HatchWorks AI, [https://hatchworks.com/blog/claude/claude-sub-agents-and-agent-teams/](https://hatchworks.com/blog/claude/claude-sub-agents-and-agent-teams/)  
2. Claude Code's Five-Layer Architecture Explained: How MCP, Skills, Agent, Subagents, and Agent Teams Work Together | Gerald Chen's Tech Blog, [https://chenguangliang.com/en/posts/claude-code-five-layer-architecture/](https://chenguangliang.com/en/posts/claude-code-five-layer-architecture/)  
3. Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems \- arXiv, [https://arxiv.org/pdf/2604.14228](https://arxiv.org/pdf/2604.14228)  
4. Spec-Driven Development with Claude Code in Action | alexop.dev, [https://alexop.dev/posts/spec-driven-development-claude-code-in-action/](https://alexop.dev/posts/spec-driven-development-claude-code-in-action/)  
5. A Deep Architecture Review of Claude Code: 5 Critical Gaps That Reveal the Future of Agentic AI | by Yi Zhou, [https://www.agenticengineeringinstitute.com/blog/a-deep-architecture-review-of-claude-code-5-critical-gaps-that-reveal-the-future-of-agentic-ai](https://www.agenticengineeringinstitute.com/blog/a-deep-architecture-review-of-claude-code-5-critical-gaps-that-reveal-the-future-of-agentic-ai)  
6. \[Feature\]: Five-Layer Context Pipeline \+ Plan-Mode — Coordinated Core Agent Parity with Claude Code and Codex \#35325 \- GitHub, [https://github.com/NousResearch/hermes-agent/issues/35325](https://github.com/NousResearch/hermes-agent/issues/35325)  
7. Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems \- arXiv, [https://arxiv.org/html/2604.14228v2](https://arxiv.org/html/2604.14228v2)  
8. Claude Code engineering \- Fluid Attacks, [https://fluidattacks.com/blog/claude-code-ai-agents-engineering](https://fluidattacks.com/blog/claude-code-ai-agents-engineering)  
9. Important Claude Code Permission Modes Every Developer Should Know \- BezKoder, [https://www.bezkoder.com/claude-code-permission-modes/](https://www.bezkoder.com/claude-code-permission-modes/)  
10. \[論文評述\] Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems \- Moonlight, [https://www.themoonlight.io/tw/review/dive-into-claude-code-the-design-space-of-todays-and-future-ai-agent-systems](https://www.themoonlight.io/tw/review/dive-into-claude-code-the-design-space-of-todays-and-future-ai-agent-systems)  
11. Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems \- arXiv, [https://arxiv.org/html/2604.14228v1](https://arxiv.org/html/2604.14228v1)  
12. Claude Code Subagents and Multi-Agent Orchestration Guide \- Delegation, Parallel Fan-Out, and Custom Agent Definitions | hidekazu-konishi.com, [https://hidekazu-konishi.com/entry/claude\_code\_subagents\_and\_orchestration\_guide.html](https://hidekazu-konishi.com/entry/claude_code_subagents_and_orchestration_guide.html)  
13. Building Multi-Agent Workflows in Claude Code: A Practical Tutorial \- Developers Digest, [https://www.developersdigest.tech/blog/building-multi-agent-workflows-claude-code](https://www.developersdigest.tech/blog/building-multi-agent-workflows-claude-code)  
14. Tools \- Claude Platform Docs, [https://platform.claude.com/docs/en/managed-agents/tools](https://platform.claude.com/docs/en/managed-agents/tools)  
15. Claude Code Sub-Agents: 3x Output with Parallel Tasks \- AI Builder Club, [https://www.aibuilderclub.com/blog/claude-code-sub-agents-guide](https://www.aibuilderclub.com/blog/claude-code-sub-agents-guide)  
16. Create custom subagents \- Claude Code Docs, [https://code.claude.com/docs/en/sub-agents](https://code.claude.com/docs/en/sub-agents)  
17. How Sub-Agents Work in Claude Code: A Complete Guide | by Kinjal Radadiya | Medium, [https://medium.com/@kinjal01radadiya/how-sub-agents-work-in-claude-code-a-complete-guide-bafc66bbaf70](https://medium.com/@kinjal01radadiya/how-sub-agents-work-in-claude-code-a-complete-guide-bafc66bbaf70)  
18. Subagents in the SDK \- Claude Code Docs, [https://code.claude.com/docs/en/agent-sdk/subagents](https://code.claude.com/docs/en/agent-sdk/subagents)  
19. How to Use Sub-Agents in Claude Code to Manage Context and Speed Up Research, [https://www.mindstudio.ai/blog/sub-agents-claude-code-context-management](https://www.mindstudio.ai/blog/sub-agents-claude-code-context-management)  
20. claude-plugins-official/plugins/plugin-dev/skills/agent-development/SKILL.md at main, [https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/agent-development/SKILL.md](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/agent-development/SKILL.md)  
21. claude-plugins-official/plugins/plugin-dev/skills/agent-development/references/triggering-examples.md at main \- GitHub, [https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/agent-development/references/triggering-examples.md](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/agent-development/references/triggering-examples.md)  
22. claude-plugins-official/plugins/plugin-dev/skills/agent-development/SKILL.md at main \- GitHub, [https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/agent-development/SKILL.md?plain=1](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/agent-development/SKILL.md?plain=1)  
23. Hooks reference \- Claude Code Docs, [https://code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks)  
24. agent-creation-system-prompt.md \- claude-plugins-official \- GitHub, [https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/agent-development/references/agent-creation-system-prompt.md](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/agent-development/references/agent-creation-system-prompt.md)  
25. Claude Code Models | Build This Now \- BuildThisNow, [https://www.buildthisnow.com/blog/models/model-selection](https://www.buildthisnow.com/blog/models/model-selection)  
26. Understanding Claude Code: How AI Agents Really Work Under the Hood \- Albin Thomas, [https://albint.medium.com/understanding-claude-code-how-ai-agents-really-work-under-the-hood-01bb362f5399](https://albint.medium.com/understanding-claude-code-how-ai-agents-really-work-under-the-hood-01bb362f5399)  
27. Automate actions with hooks \- Claude Code Docs, [https://code.claude.com/docs/en/hooks-guide](https://code.claude.com/docs/en/hooks-guide)  
28. Claude-code-spec-workflow \- PromptLayer Blog, [https://blog.promptlayer.com/claude-code-spec-workflow/](https://blog.promptlayer.com/claude-code-spec-workflow/)  
29. Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems \- Zhiqiang Shen, [https://zhiqiangshen.com/projects/Claude\_Code\_Report/Claude\_Code\_Report.pdf](https://zhiqiangshen.com/projects/Claude_Code_Report/Claude_Code_Report.pdf)  
30. Choose a permission mode \- Claude Code Docs, [https://code.claude.com/docs/en/permission-modes](https://code.claude.com/docs/en/permission-modes)  
31. Debug your configuration \- Claude Code Docs, [https://code.claude.com/docs/en/debug-your-config](https://code.claude.com/docs/en/debug-your-config)  
32. Add toolChoice parameter to agent definitions · Issue \#20071 · anthropics/claude-code, [https://github.com/anthropics/claude-code/issues/20071](https://github.com/anthropics/claude-code/issues/20071)  
33. Tool use with Claude \- Claude Platform Docs, [https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)  
34. Task→Agent tool rename in v2.1.63 breaks hook payloads (undocumented breaking change) · Issue \#29677 · anthropics/claude-code \- GitHub, [https://github.com/anthropics/claude-code/issues/29677](https://github.com/anthropics/claude-code/issues/29677)  
35. Claude Code Tools, [https://blog.thepete.net/claude-code-tools/](https://blog.thepete.net/claude-code-tools/)  
36. Agent tool missing 'model' parameter for team agent model selection · Issue \#31027 · anthropics/claude-code \- GitHub, [https://github.com/anthropics/claude-code/issues/31027](https://github.com/anthropics/claude-code/issues/31027)  
37. Agent tool model parameter should support context window variants (e.g. opus\[1m\]) · Issue \#36100 · anthropics/claude-code \- GitHub, [https://github.com/anthropics/claude-code/issues/36100](https://github.com/anthropics/claude-code/issues/36100)