# Astra comments and suggestions for Claude Fable 5.1

This is the main advisory development note requested by the owner. It records
comments, design suggestions, and review criteria for continued Loop Engine
work. It is not a separate constitution, an implementation-status report, or
a claim that a named model independently verified a result.

Follow [AGENTS.md](AGENTS.md), the current task authority, and the existing
typed contracts. When a suggestion below conflicts with current behavior,
identify the gap and test a candidate change. Do not turn advice into
undeclared runtime permissions or silently remove a supported option.

## September 13 integration review

The owner asked Codex to take over after Claude exhausted its usage allowance,
review the pending changes, and publish the verified work on `main`.
The [integration report](docs/verification/ASTRA-INTEGRATION-REVIEW-2026-09-13.md)
records the resulting checks and remaining limits.

Three review rules need particular care. A requested dimension must reach
the actual invocation or receive an explicit refusal. Agreement among
generated attempts cannot override failed checks or erase unresolved
requirements. A host process, working directory, or checkpoint does not
provide sandboxing or grant execution authority.

Keep the broader design open. These refusals identify bindings that still
need implementation and qualification; they do not prohibit additional
steps, native harness controls, wrapper compositions, or configuration
dimensions.

## Direction to preserve

The system should remain open to additional cognitive steps, action methods,
prompts, questions, intelligence, harnesses, tools, wrapper layers, and
configuration dimensions. The recorded inventory is a required baseline, not
an exhaustive list. Expansion and simplification are both valid directions
when their measured outcomes justify them.

An outer Loop Engine Loop may supervise a harness that runs its own inner
loop. The outer Loop can evaluate the result, continue the assignment, change
an eligible configuration, or select an authorized fallback harness. The
inner harness can plan and use its permitted tools within the shared
authority. These are nested control responsibilities, not a second Loop
Engine runtime.

## Complete behavioral explanation

A discrete cognitive or act step Loop node is an independently governed
instance of the Loop runtime responsible for one clearly defined cognitive
step or action. A cognitive step might interpret information, identify a
missing requirement, compare alternatives, or evaluate a result. An action
might inspect a directory, build software, execute a test, create an artifact,
or send an authorized email.

Each discrete cognitive or act step Loop node receives the context,
instructions, skills, plugins, tools, and working files relevant to its
assignment. Essential information can be supplied directly, while additional
information can remain in centralized storage behind authorized, versioned
references. It does not automatically need the entire task history or every
available tool.

A separately initialized harness process, such as OpenCode, Pi, Codex, or a
custom implementation, can perform the assignment. When explicitly permitted,
another harness can attempt the same assignment after a failure. The
assignment's contracts, permissions, history, and remaining authority persist
across those attempts.

Discrete describes the scope of the assignment, not a restriction to one
attempt, one model call, or one output. A discrete cognitive or act step Loop
node can examine whether an observation matches its expectations, identify a
problem, repair or change its approach, and repeat until its declared
completion conditions are satisfied.

Alternatively, a discrete cognitive or act step Loop node can publish an
initial candidate output and continue working while its continuation
conditions and authority permit. It can produce additional alternatives over
time, including alternatives that are better, worse, or useful under different
circumstances. Consumers must identify exactly which output they used.
Publishing an output does not necessarily mean that the producing assignment
has finished.

For externally consequential actions, continued operation does not authorize
repeated effects. For example, generating alternative email drafts can
continue, but sending an email requires its own authorization and protection
against duplicate delivery.

That complete explanation must remain alongside the full phrase. A shorter
label alone is not an adequate replacement.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

## Comments on harness composition

1. Keep wrapper composition separate from native control ownership. One
   wrapper, several wrappers, and the existing direct adapter can remain
   distinct qualified choices. Wrapper depth and order are not fixed.
2. Resolve ownership per control. Goal management, planning, iteration,
   retries, tool selection, compaction, session persistence, steering,
   cancellation, and completion reporting need not all have the same owner.
3. Preserve one coordinated recovery decision per failure occurrence. Native
   retries and outer retries must not independently multiply attempts.
   Transport failure, structural rejection, semantic rejection, and
   inconclusive evaluation are different conditions.
4. Preserve consumed authority across native goal changes, session restarts,
   wrapper changes, and harness fallback. Count physical calls and committed
   effects once, even when several layers observe them.
5. Treat native completion as an observation. The owning Loop's required
   independent evaluation determines task acceptance. Publishing an output
   and completing the assignment remain separate events.
6. Keep restricted text-response profiles available while qualifying richer
   native-control profiles. A limited experiment profile is not a universal
   rule that native capabilities must remain disabled.
7. Model wrapper internals as existing adapters or passive typed
   configuration unless the work needs independent governance. Such work
   becomes another canonical Loop with an exact profile and relationship.

Read the [layered harness design](docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
and [flexible cognitive and action composition](docs/architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md)
for the full proposal. These comments do not imply that every proposed
composition or native control is currently installed.

## Suggestions and acceptance criteria

| Suggestion | Evidence required before claiming it works |
|---|---|
| Resolve the complete wrapper composition before execution. | Exact wrapper versions, ordering, resource bindings, typed interfaces, and compatibility checks reach the actual invocation. |
| Support an outer Loop around native harness iteration. | An observed inner result causes the correct outer decision, with preserved task identity, remaining authority, and exact output references. |
| Make native controls individually selectable. | Enabled, disabled, unsupported, and unknown states are distinct; changing one control does not silently enable another. |
| Compare initial choices and fallback policies. | Both successful and failed transitions are retained, including transitions that were configured but never exercised. |
| Retain state where useful without leaking authority. | Fresh-session and resumed-session controls verify exact state transfer, source identity, privacy, and budget continuity. |
| Test cancellation and uncertain effects. | Only owned processes or sessions are stopped, completion is observed rather than assumed, and uncertain commits are reconciled before retry. |
| Preserve legitimate repeated trials. | Trial-occurrence identity prevents double-counting one observation without rejecting valid repetitions on the same subject or collapsing distinct occurrences in one Run History. |
| Compare additional steps, prompts, and intelligence. | Matched controls and interaction tests measure contribution to verified outcomes, not simply more stored records or fewer calls. |
| Stage reusable conclusions for review. | Suitability and intelligence remain candidates until independent qualification and approval; later retrieval and use are measured separately. |
| Verify instruction loading. | The selected harness actually loads the intended files and versions. File presence alone is not proof, particularly for isolated profiles that disable project context. |

Use the [configuration search guide](docs/guides/configuration-grid-search-and-optimization.md).
Do not declare a universal winning harness, minimal workflow, or fixed
dimension count. Do not invent a total-run resource ceiling that the owner
did not provide. Per-run authority and provider output capacity remain
separate.

## Review and cleanup discipline

A past review finding is not automatically a current defect. Check the exact
source revision and working-file identities, reproduce the condition, and
record whether it remains open, was fixed, or was superseded. Likewise, a
passing historical test does not qualify new work.

Keep represented contracts, connected workflows, offline tests, and live
qualification as separate statuses. Test semantic and inconclusive outcomes
as well as transport and schema failures. Confirm that acceptance checks
actually fail when their required behavior is absent.

Preserve concurrent work, staged changes, immutable evidence, failed
attempts, and external reference snapshots. Do not modify installed harness
dependencies or a historical record to make a check pass. Use owned process
handles for test cleanup; a process name or shared command argument does not
prove ownership.

This file is hand-authored development guidance, not a managed-note database
or generated session handoff. When extending it, state whether an entry is an
owner requirement, a proposal, an observed result, or an unresolved question.
Link to the authoritative implementation or evidence instead of copying
historical status into a new source of truth.

## Reading and instruction entry points

[CLAUDE.md](CLAUDE.md) imports the shared repository rules and this note for
Claude Code. [Harness development instructions](embodiments/AGENTS.md) and
[development-tool instructions](devtools/AGENTS.md) provide narrower guidance
for those directories. Their local `CLAUDE.md` files import the corresponding
`AGENTS.md` files.

Read the [harness guide](embodiments/HARNESS-GUIDE.md) and
[session orientation](docs/context/CODEX-START-HERE.md) for current source and
evidence pointers. These instruction files do not change executable harness
manifests, launch flags, or native-control settings.
