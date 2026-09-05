# Start a coding-agent session in Loop Engine

This page applies to Codex and other coding agents working in the repository.

Use `/home/username/loop-engine` as the workspace directory for Loop Engine work.
This repository is separate from `/home/username/taedri.dev`.

## First message for a new session

```text
Work only in /home/username/loop-engine for this task.

Read AGENTS.md first. Then inspect the current branch, revision, dirty state,
active processes, and concurrent writers. Preserve all existing changes.

If a generated session_handoff/v1 packet is supplied, verify its HEAD and
worktree digest before using it. Treat missing or stale ownership as unknown.

Read README.md and docs/components/README.md. Follow only the component guides
needed for the task. Use humanizer-context.md for public writing.

Loop Engine has one universal Loop runtime. Starting, Spawned by, Queried by,
Retrieved by, and Connected from are relationships. Practitioner,
Intelligence, and Solution are roles. Run mode, step profile, thinking power,
typed contract, budget, permissions, loop condition, and exit condition are
separate settings.

Use a text or Mermaid tree when a document explains three or more architecture
branches. Start from this tree and extend one branch at a time:

Operational runtime type
└── Loop
    ├── LoopDefinition: ID, version, digest, profile, contract, modes, conditions, authority
    ├── LoopRuntimeContext: three public capability ports plus internal mechanics
    ├── Relationship: Starting, Spawned by, Queried by, Retrieved by, or Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Purpose and domain categories
    ├── Selected mode: deterministic, hybrid, or non-deterministic
    ├── Budget, permissions, and effects
    ├── Model settings when model use is allowed
    └── Run History events

Authoritative static graph
└── LoopGraphDefinition
    ├── exact LoopDefinitionRef per executable vertex
    ├── typed edges
    ├── graph inputs and outputs
    └── graph version and content digest

Never use runtime type, role, profile, category, mode, or settings as
interchangeable terms.

Treat /home/username/taedri.dev only as a semantic design reference. Do not
copy files or create parallel registries. State a missing invariant, map it to
an existing Loop Engine boundary, implement the smallest typed extension, and
verify it inside Loop Engine.

Do not commit, push, call a paid provider, rerun a completed benchmark, or
perform external effects unless the current request authorizes that action.
```

## Reading order

1. [`AGENTS.md`](../../AGENTS.md)
2. [`README.md`](../../README.md)
3. [Contract index](../contracts/README.md)
4. [Taxonomy and class map](../architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md)
5. [Work-approach instrumentation](../architecture/WORK-APPROACH-INSTRUMENTATION.md)
   when work concerns prompt, context, memory-access, delegation, or approach
   experiments
6. [Component map](../components/README.md)
7. [Older reference-source boundaries](REFERENCE-SOURCES.md) only when older
   repository material may be relevant
8. [Loop object and profiles](../components/loop-object/README.md)
9. [Intelligence layers](../components/intelligence-layers/README.md)
10. [Core Architecture](../components/core-architecture/README.md)
11. [Solution Canvas](../components/solution-canvas/README.md)
12. [Case studies](../../case-studies/README.md) only when the task concerns
   measured full-system runs

For broad continued development, use the
[universal solver continuation brief](../prompts/LOOP-ENGINE-UNIVERSAL-SOLVER-HANDOFF.md).
It is the sole broad continuation prompt. Load one prompt for the active task.
Do not concatenate it with another file from `docs/prompts/`.

The [`session_handoff/v1` schema](../contracts/session-handoff.schema.json)
defines the optional generated packet. Do not hand-write a packet to fill an
ownership or evidence gap.

When the target model is GPT-6 Astra, also read the dated
[compatibility note](GPT-6-ASTRA-READINESS-2026-09-04.md). The architecture
remains model-neutral, and access remains unproven until an authorized probe.

For storage, structured notes, file/database queries, or memory-reference work,
read [queryable records and storage](../guides/queryable-records-and-storage.md)
and the [record-operation decision](../architecture/ADR-SCOPED-RECORD-OPERATIONS.md).
The [verification report](../verification/RECORD-ACCESS-AND-MEMORY-AUDIT-2026-09-04.md)
records the tested storage slice and open memory incidents. The
[package, harness, and memory audit](../research/STORAGE-PACKAGES-HARNESSES-AND-MEMORY-2026-09-04.md)
maps existing authorities before adding another abstraction. Its follow-up
closes the reproduced alias/snapshot defects and compares harness alternatives.
The [fresh hardening report](../verification/HARNESS-AND-MEMORY-HARDENING-2026-09-04.md)
records full source/clean-wheel results and the typed session handoff.
The later [output and mode-policy checkpoint](../verification/REASONED-OUTPUT-AND-MODE-POLICY-2026-09-05.md)
adds reasoned output allocations, shared three-mode views, conservative frontier
outcomes, and single-flight token accounting. Strict live requests still need a
qualified exact-request token bound. Do not replace missing bounds with a
character estimate or reuse archived live-run spending authority.
OpenCode execution is quarantined; do not restore its old raw-host path to make
a smoke test pass. The [harness boundary](../components/core-architecture/MCP-AND-SKILLS.md#external-harness-boundary)
documents capability refusal, explicit registration, and post-run budget limits.
Use the host-configured record tool for managed notes. Do not directly edit its
database or immutable revisions. Existing authority Markdown and historical
evidence have not been migrated, and generated session views remain planned.

For the latest new-task attempt and generalization boundary, first read the
[live Kaggle pilot checkpoint](../verification/KAGGLE-LIVE-PILOT-2026-09-05.md).
It records a real provider probe, explicit no-total-token-ceiling authorization,
source-integrity fixes, and a model-generated tool whose own passing tests missed
defects found by independent review. No Kaggle score exists in that checkpoint.
Its follow-up preserves the stopped repair and withdraws the agent-imposed
50-call ceiling. Call and pass limits already support `None`; do not invent a
replacement ceiling. The static path screen was corrected, but the saved
candidate still needs input bindings and independent execution checks. CI's
hardcoding audit also remains unresolved. The user's
no-monetary-ceiling instruction does not qualify strict token bounds or approve
raw competition-data export.

For the preceding diagnostic, read the
[new-task diagnostic report](../verification/UNSEEN-TASK-DIAGNOSTIC-AND-GENERALIZATION-2026-09-04.md).
Two real-provider attempts on one generated Kaggle-shaped case produced no
verified task completion. The second reproduced a post-dispatch token-budget
overshoot and left invalid, unexecuted candidate code. Live expansion stopped.
The next probe is sound pre-dispatch token reservation, not a larger budget.
Its [research note](../research/MODEL-ARCHITECTURES-COMPOSITION-AND-DEVICE-MESH-2026-09-04.md)
keeps domain knowledge in the four existing intelligence layers; device and
industry examples are test populations, never privileged runtime workflows.
The [coverage index](../research/ARCHITECTURE-COVERAGE-MATRIX-2026-09-04.json)
lists reviewed subsets and remaining research gaps.

For earlier learning work, read the
[learning-integrity implementation report](../verification/LEARNING-INTEGRITY-AND-RESEARCH-2026-09-04.md)
and its [research synthesis](../research/LEARNING-FROM-VERIFIED-LOOP-OUTCOMES-2026-09-04.md).
They record the later fixes for verifier-subject binding, adaptive accepted
state, and thin model-ladder evidence. The live paired gate remains open.

For broad architecture review, read the
[mesh and corpus audit](../verification/ARCHITECTURE-MESH-CORPUS-AUDIT-2026-09-04.md).
It records full Markdown coverage and local history inventory, separates
runtime behavior from proposals, and reproduces an unresolved verifier-subject
binding defect plus adaptive accepted/speculative state gaps. That audit
made no runtime fixes; use the later implementation report for their current
status. Other documented gaps remain open.

When the task concerns stage learning, hydrated material, action lineage, or
predictive-state evidence, including the mechanism-only control manifest and
its unresolved controls, first read the
[offline verification report](../verification/PREDICTIVE-STATE-PROCEDURAL-MEMORY-AND-STAGE-ASSISTANCE-2026-09-04.md),
with the later audit's subject-binding limitation.
Use the dated
[stage assistance integration audit](../verification/STAGE-ASSISTANCE-INTEGRATION-AUDIT-2026-09-04.md)
only as the historical defect trail; its intermediate counts are superseded.
When it concerns long-horizon skills, execution state, recursive inference,
recurrent models, or test-time memory, read the dated
[primary-source research review](../research/LONG-HORIZON-RECURRENT-SKILLS-AND-STATE-2026-09-04.md).
When it concerns procedural reuse, predictive state, information measurements,
or the "AI muscle memory" research metaphor, read the narrower
[procedural-memory evidence note](../research/PROCEDURAL-MEMORY-PREDICTIVE-STATE-AND-INFORMATION-VALUE-2026-09-04.md).
For adaptive computation, repeated-task transfer, distillation, or cognitive
Loop templates, read the
[cognitive mesh research and design](../research/ADAPTIVE-COGNITIVE-MESH-AND-AMORTIZED-COMPUTATION-2026-09-04.md).
Its accompanying JSON catalog contains unbound design examples, not installed
profiles or qualified shortcuts.
When it concerns the Kaggle campaign, read the
[120-competition metadata report](../verification/KAGGLE-120-ACCESS-PREFLIGHT-2026-09-04.md).
Do not load these dated reports for unrelated work.

## Working-directory check

Run this before changing files:

```bash
pwd
git rev-parse --show-toplevel
git remote get-url origin
git branch --show-current
git rev-parse HEAD
git status --short --branch
git diff --name-status
git ls-files --others --exclude-standard
git worktree list --porcelain
ps -eo pid=,ppid=,etime=,stat=,comm=
```

The first two paths should both resolve to `/home/username/loop-engine`. The
remote should resolve to the Loop Engine GitHub repository. The process list
omits arguments and environment values because they may contain private data.
A matching working directory or process name does not prove ownership. Record
an owner only from an explicit claim.

## What not to include

Do not paste the full Taedri Constitution, Taedri reference manual, old Loop
Intelligence README, historical benchmark transcripts, or an entire prior chat
into a new Loop Engine session. Those sources contain project-specific or
stale details that can override the simpler Loop Engine architecture.

Bring over one verified invariant at a time. Keep its source revision and
reason visible in the resulting design note or change.
