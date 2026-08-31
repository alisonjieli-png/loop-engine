# Coding harness architecture review

This review compares the control loops documented by Codex, Claude Code,
OpenCode, Gemini CLI, OpenHands, and Aider. It identifies practices that fit
Loop Engine without adding another runtime or a second product path.

Sources were reviewed on 2026-08-31. Product details can change. The linked
official documentation remains the source for each external system.

## Shared architecture

The reviewed coding harnesses use the same basic cycle with different context,
permission, editing, and execution policies.

```text
Coding harness
├── Input and context
│   ├── user task and conversation
│   ├── project instructions
│   ├── selected repository material
│   └── tool definitions
├── Model decision
│   ├── return an answer
│   └── request one or more tools
├── Governed tool execution
│   ├── read and search
│   ├── edit files
│   ├── run commands and tests
│   └── call external tools
├── Observation
│   └── return tool results to the model
└── Continuation
    ├── repeat when more work is needed
    ├── repair after concrete failure
    └── return a final result or explicit failure
```

The important difference is not whether a system has a loop. The differences
are how it selects context, represents edits, controls effects, preserves
state, handles failures, and decides that work is complete.

## Codex

Codex uses one focused repository session to inspect files, edit code, run
installed tools, review changes, and continue through follow-up work. Project
instructions enter through `AGENTS.md`. The user can inspect or change model,
reasoning effort, permissions, and review mode. The same CLI can run
interactively or through `codex exec` in scripts and CI. Skills, plugins, MCP,
subagents, session resume, record and replay, local environments, cloud
environments, and worktrees extend the same coding loop.

Source: [Codex CLI documentation](https://learn.chatgpt.com/docs/codex/cli).

Relevant Loop Engine lesson: keep one public solve session, show commands and
progress as they occur, preserve continuity, and make review a normal part of
the same path.

## Claude Code

Claude Code documents its Agent SDK loop directly. The model receives the
prompt, system instructions, tools, and history. It may return text or tool
calls. The SDK executes the calls and returns results. This repeats until the
model returns no more tool calls. The final result includes usage, cost,
session identity, and the model stop reason.

Hooks can validate, modify, block, or log tool calls before and after
execution. Subagents use fresh context and return a summary. Automatic
compaction and selective tool schemas control context growth.

Sources: [Claude Code agent loop](https://code.claude.com/docs/en/agent-sdk/agent-loop)
and [Claude Code hooks](https://code.claude.com/docs/en/agent-sdk/hooks).

Relevant Loop Engine lesson: provider stop reasons, tool decisions, context
compaction, and spawned work must remain visible. A transport or output-limit
stop must not be reported as a generic provider failure.

## OpenCode

OpenCode defines reusable agent profiles from a system prompt, model
preference, tool permissions, and display metadata. Primary agents run the
main session. Subagents run spawned sessions with fresh context. Permissions
can allow, ask, or deny each built-in, custom, or MCP tool, including command
patterns and access outside the workspace. OpenCode also exposes an explicit
stuck-loop recovery permission.

Sources: [OpenCode agents](https://opencode.ai/docs/agents/) and
[OpenCode permissions](https://opencode.ai/docs/permissions/).

Relevant Loop Engine lesson: keep role profiles passive and versioned, and
keep permissions separate from model choice. Spawned sessions must not become
orphaned alternate product paths.

## Gemini CLI

Gemini CLI separates its terminal frontend from a core package that owns API
calls, prompt construction, state, tool registration, and tool execution. The
model requests tools. The core validates and executes them, often after user
confirmation for file or shell effects. Tool output returns to the model.
Gemini CLI supports file, shell, web, memory, and MCP tools. It can isolate
tool execution through Docker, Podman, or platform sandboxing.

Sources: [Gemini CLI architecture](https://google-gemini.github.io/gemini-cli/docs/architecture.html),
[Gemini CLI tools](https://google-gemini.github.io/gemini-cli/docs/tools/), and
[Gemini CLI sandboxing](https://google-gemini.github.io/gemini-cli/docs/cli/sandbox.html).

Relevant Loop Engine lesson: the CLI should remain a projection over one core
service. Sandbox execution and effect approval belong below the model loop,
not inside a prompt.

## OpenHands

OpenHands gives arbitrary code execution a dedicated sandbox runtime. Its
backend sends actions to an execution server inside a Docker container. The
server executes shell, file, Python, and plugin actions and returns structured
observations. Content and dependency hashes support reproducible runtime image
reuse.

Source: [OpenHands runtime architecture](https://docs.openhands.dev/openhands/usage/architecture/runtime).

Relevant Loop Engine lesson: preserve the current confined workspace and
pinned runtime. Generated code must execute in the same production sandbox
used by public solve, not through a special test runner.

## Aider

Aider uses a compact repository map containing selected files, symbols,
signatures, and important definition lines. It ranks the dependency graph to
fit useful repository context inside a token target. Aider also chooses an edit
format for each model. Whole-file output is simple but expensive. Search and
replace or unified-diff formats reduce output size. Architect mode separates
solution reasoning from syntactic edit production. Lint and test failures can
be returned to the model for repair.

Sources: [Aider repository map](https://aider.chat/docs/repomap.html),
[Aider edit formats](https://aider.chat/docs/more/edit-formats.html), and
[Aider linting and testing](https://aider.chat/docs/usage/lint-test.html).

Relevant Loop Engine lesson: generated files should not always be requested as
one giant response. Select a response format based on the task and model. Reuse
file checkpoints and pass digests, interfaces, or selected dependency excerpts
instead of every earlier file body.

## Loop Engine position

Loop Engine currently has a broader governed execution model than the basic
coding loop described by these tools.

```text
Operational runtime type
└── Loop
    ├── Relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic
    ├── typed contract, conditions, permissions, and effects
    ├── candidate, verification, authorization, and commit transitions
    ├── Run History
    └── reusable capability qualification and promotion
```

This structure is useful only when the public path is dependable. Current
evidence proves a real model-led solve, generated-project repair, one promoted
reusable capability, and one zero-model warm invocation. It does not yet prove
that automatic harvesting and persistent resolution are wired into every
public CLI solve.

The main product gaps are:

- one simple public cold-to-warm path with no injected resolver;
- resumable generated-file checkpoints across run restarts;
- specific provider failure and termination records;
- authorized same-tier model and provider failover;
- bounded context that does not repeat complete generated file bodies;
- response formats chosen for the output, including section or diff based
  generation when whole-file output is too large;
- semantic response validation using the same admission and repair policy;
- progress that explains current goal, active Loop, model call, tool action,
  artifact, verification, and next decision.

## Decisions for the next production proof

Use one path:

```text
public loop-engine solve
  -> Starting Practitioner
  -> deterministic capability lookup
  -> model-led solution when no exact active capability exists
  -> typed response admission
  -> confined generated-project execution
  -> independent verification
  -> asynchronous candidate harvest
  -> independent qualification and explicit promotion
  -> persistent search projection
  -> differently worded public solve
  -> exact deterministic invocation with zero model calls
```

The first task is text-field whitespace normalization over JSON records. It
does not need external data, web research, graphics, machine learning, address
parsing, or a large project. It still exercises the complete product circuit.

Do not add a second test-only solve path. Do not add fixed global pass, token,
or model-call ceilings. Safety limits for one provider call, sandbox process,
or explicit user policy remain separate from semantic completion.

## Practices not to copy directly

- Do not turn each external harness agent type into a Loop subclass.
- Do not make a repository map or graph an execution authority.
- Do not use a global turn cap as the meaning of task completion.
- Do not retry authentication, payment, invalid-request, permission, or unsafe
  output failures through another provider without new authority.
- Do not hide malformed output repair inside a provider adapter.
- Do not count a provider probe, injected fixture, or partial run as a solved
  production task.
