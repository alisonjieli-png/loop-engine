# Layered harness wrappers and native control

The owner asked Loop Engine to consider one or more wrapper layers around a
harness and to treat native harness controls as a configuration dimension.
This document records that design consideration. It does not enable native
goals, create a new runtime, or claim a qualified layered implementation.

Two decisions must remain separate: which wrappers compose the implementation,
and who controls each part of its lifecycle. Different assignments can use
different wrapper depths, orders, native capabilities, and fallback policies.
The design should support those alternatives without imposing one fixed stack.

Read the [open-ended dimension inventory](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
[flexible cognitive and action composition](FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md),
and [configuration search guide](../guides/configuration-grid-search-and-optimization.md)
with this proposal.

## Complete explanation

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

Wrappers are internal implementation mechanics unless the work needs its own
independent goal, contract, authority, schedule, verification obligation, or
Run History identity. In that case, the work belongs to another classified
Loop with an exact registered profile and an explicit relationship.

A wrapper does not become another runtime class, role, execution mode,
intelligence layer, or public Core Architecture capability group. A native
harness process remains an adapter used by its owning Loop.

## Wrapper composition as a dimension

The following is a containment example inside one governed assignment. It is
not an execution graph or a required set of layers:

```text
Owning Loop
├── Assignment definition, contracts, authority, and Run History
└── Selected implementation composition
    ├── Optional task and instruction preparation
    ├── Optional context, intelligence, and resource preparation
    ├── Optional native session and goal-control bridge
    ├── Optional observation and evaluation integration
    ├── Transport, effect enforcement, and lifecycle integration
    └── Registered native harness process
        ├── Selected native controls
        ├── Permitted model and tool operations
        └── Native events, state, and candidate outputs
```

The selected implementation may combine responsibilities into one wrapper,
separate them into several wrappers, or use the existing direct adapter with
no additional wrapper as a comparison baseline. The owning Loop's governance
is always present. More layers are neither automatically better nor
automatically undesirable.

A composition description needs exact wrapper identities, versions, order,
settings, dependencies, typed input and output expectations, and initialization
and teardown responsibilities. Declare what information each wrapper may
inspect or transform. Bind the compiled composition to the assignment before
execution.

Layer order can change behavior. For example, instruction preparation before
native session initialization differs from preparation after a session has
already loaded its instructions. A resource wrapper that grants access must
not be confused with one that only describes available resources.

Record an initial composition and ordered fallback compositions. Specify
which failures permit a different wrapper, reordered composition, native
session restart, or different harness. A fallback must preserve the exact
assignment, required contracts, consumed authority, and committed effects.

## An outer Loop around a native harness loop

Loop Engine can own an outer control loop around a harness that performs its
own inner iteration. The outer Loop governs the assignment and its permitted
continuation. The native harness can choose internal model and tool operations
under the selected control policy.

This is a control-flow sketch within the preceding runtime classification,
not a second executable graph type:

```text
Owning Loop: outer control
├── Bind the assignment, wrapper composition, resources, and authority
├── Start or continue the selected harness
│   └── Native harness iteration: internal adapter behavior
│       ├── Plan within the delegated control policy
│       ├── Invoke permitted model and tool operations
│       └── Return observations, state, and candidate outputs
├── Independently evaluate the observed result
└── Accept, continue, reconfigure, select a permitted fallback, or stop
```

For example, the native harness may finish a candidate while the outer Loop
finds an unmet requirement. The outer Loop can request more evidence or start
another permitted round with changed resources. A terminal native activation
keeps its historical result; later work uses a permitted continuation or new
activation rather than rewriting what happened.

Outer and inner iteration must share cumulative accounting, effect identity,
and cancellation. Define who owns each retry and how control passes between
layers. Native completion is a candidate observation, not an automatic
acceptance decision. This design does not require every native tool call to
become another Loop unless it needs independent governance.

## Native control ownership as a dimension

Native control is not one switch that enables or disables every harness
feature. Resolve ownership separately for each control, including goal
management, planning, iteration, tool selection, retry, compaction, session
persistence, interruption, and completion reporting.

Possible design choices include control by the owning Loop, delegation to
the native harness within explicit authority, and supervised native control
with a defined coordination protocol. Disabled, unsupported, and unknown
states must remain distinguishable. These are control-ownership choices, not
new execution modes.

| Control | What the configuration must decide | Coordination requirement |
|---|---|---|
| Goal creation and changes | Whether a native goal represents the assignment, its exact identity, and who may change it. | Native goal changes cannot silently change the owning task or replenish its authority. |
| Planning and continuation | Which layer chooses the next internal operation, when another turn may run, and how expectations are checked. | One resolved continuation decision must govern each transition; conflicting decisions need an explicit resolution rule. |
| Tool and resource use | Which qualified native tools, skills, prompts, hooks, plugins, and intelligence access are available. | Native selection stays inside the owning Loop's exact grants; enabling goal control grants no tool or effect authority. |
| Retry and fallback | Which layer owns each failure category and which alternative it may choose. | Do not let independent retry layers multiply attempts without one shared accounting and transition policy. |
| Context and session state | Which layer loads, compacts, retains, resumes, or transfers context and working state. | Preserve source identities, trust boundaries, and declared visibility; native persistence is not automatic cross-task sharing. |
| Steering and queued work | Who may inject a message, when it takes effect, and how queued work is acknowledged. | An accepted queue command is not proof that the requested work ran or succeeded. |
| Pause, cancellation, and shutdown | How outer stop decisions reach native sessions, tools, processes, and queued work. | Distinguish request acknowledgment, stopped execution, and reconciled external effects. |
| Completion and output publication | Which native events produce candidate outputs and which independent checks establish the owning task's result. | A native goal marked complete is not automatically an accepted Loop result or promoted intelligence. |

A configuration may delegate planning to a native harness while retaining
verification and effect approval in Loop Engine. Another may keep continuation
in Loop Engine and use the native harness for one response. A third may retain
a native session while an outer supervisor decides whether another round is
allowed. None is a universal default established by this document.

## Integration requirements

Each wrapper boundary needs a versioned handshake with declared capabilities
and tested behavior. Use existing harness registrations, model authority,
workspace services, effect approval, and Run History. Do not create another
registry or approval service solely because the implementation has layers.

Preserve a mapping from the owning run and Loop identity to native session,
goal, turn, tool-call, and attempt identities where the harness exposes them.
Record commands separately from acknowledgments and observed effects. Missing
native state remains unknown.

Physical model calls and external effects are counted once even when several
wrappers observe them. Native counters can supplement the owning record, not
replace it. A process restart, new native goal, or wrapper fallback cannot
reset elapsed time, tokens, spending, or other authority already consumed.

Exactly one resolved policy must decide recovery for each failure occurrence.
For example, a semantic rejection, a transport outage, and an inconclusive
evaluation need different decisions. A native transport retry must not bypass
an outer semantic-recovery restriction.

Cancellation propagates inward, and evidence of quiescence propagates outward.
If an adapter cannot prove that an operation stopped or whether an effect
committed, report that uncertainty and reconcile before replay. Control a
process by its owned handle or process group, not by searching for a shared
process name.

Native instructions, models, or extensions must not bypass the wrapper to
obtain undeclared network, file, secret, or spending access. A wrapper that
only observes traffic cannot claim it enforces those permissions.

## Published native controls and current recipe limits

Codex documents persistent goal management through `thread/goal/set`,
`thread/goal/get`, and `thread/goal/clear`, corresponding to its interactive
`/goal` control. Its documentation says that replacing the objective resets
native usage accounting. A wrapper must therefore preserve the owning
assignment's cumulative accounting independently of such a reset.
See [official OpenAI documentation](https://learn.chatgpt.com/docs/app-server#manage-a-thread-goal).

OpenCode documents session continuation with `--continue` and `--session`.
Pi documents `prompt`, `steer`, `follow_up`, and `abort` in its remote
control protocol. These interfaces are not interchangeable implementations
of one universal goal command. See
[OpenCode session controls](https://opencode.ai/docs/cli/)
and [Pi control protocol](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/rpc.md).

The currently inspected Codex recipe disables `goals` and uses
`exec --ephemeral`. The Pi recipe uses print mode with native sessions,
tools, and extensions disabled. The OpenCode recipe uses a custom agent with
native tools denied. These are existing restricted text-response profiles,
not proof that native control is unsuitable.
See the [Codex recipe](../../src/loop_engine/core/harness_responses_recipes.py),
[Pi recipe](../../src/loop_engine/core/harness_process_relay.py),
and [OpenCode recipe](../../src/loop_engine/core/harness_opencode_recipe.py).

The proposal is to retain those profiles while qualifying additional wrapped
profiles where native capabilities are useful. Recheck exact harness,
provider, model, and protocol versions before using a control. A published
feature is not automatically supported by the installed adapter.

## Compare compositions and control policies

Extend the existing configuration search with wrapper composition and native
control ownership. Compare the current restricted profile, one additional
wrapper, and deeper compositions where each layer has a justified purpose.
Vary native controls independently when compatibility permits.

Test initial settings and fallback transitions, not only final outputs. Useful
controls include:

1. The same task and resources with continuation controlled by Loop Engine
   versus a qualified native controller.
2. A native session retained across rounds versus a fresh session, with exact
   context and authority boundaries.
3. The same wrappers in different valid orders, with observed instruction
   loading and resource visibility.
4. A native retry occurring at the same time as an outer recovery decision.
5. Cancellation while a model call, tool effect, queued message, or output
   publication is in progress.
6. A native goal replacement or resume operation that resets native counters.
7. A native completion claim rejected by the owning task's independent check.
8. An unavailable native feature, lost acknowledgment, stale session identity,
   or incompatible wrapper version.
9. A permitted fallback from native control to Loop Engine control without
   replaying an uncertain or committed effect.

Keep the task population, evaluator, non-treatment settings, and source
identities fixed for a matched comparison. Report wrapper overhead, native
calls, useful outcomes, failed attempts, control conflicts, cancellation
behavior, accounting completeness, and unknown cost. Layer count itself is
not a quality metric.

## Design status

The owner requested consideration of layered wrappers and native controls.
The dimension choices, ownership matrix, and qualification requirements here
are a proposal for that work. No native goal mode was enabled and no adapter
or runtime implementation was changed to create this document.

The machine-readable runtime contracts continue to describe installed
behavior. A later implementation must reconcile these proposed dimensions
with existing contracts and add the smallest typed extension where needed.
The open-ended inventory is not permission to accept unknown executable
fields or to claim that this layered design has passed live qualification.
