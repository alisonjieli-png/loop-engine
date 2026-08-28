# Adaptive Practitioner architecture

Loop Engine treats a task as input data. The universal Practitioner does not
contain a branch for each example, domain, or sentence. It uses typed state,
registered capabilities, and repeated verification to decide what to do next.

## One runtime

```text
Operational runtime
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
    └── Contract, permissions, budget, exit condition, and Run History
```

Orientation, research, project construction, execution, verification, and
repair are work performed by configured Loops. They are not new runtime
classes.

## Practitioner cycle

The default Practitioner follows the same cycle for every task:

```text
preserve the original task
→ orient
→ build a typed work item
→ assess the current state
→ choose the next action
→ choose how to perform it
→ act through a registered capability
→ verify the actual result
→ integrate new state and evidence
→ route to continue, repair, ask, abstain, or return
```

A run repeats this cycle until the requested output passes verification or a
typed blocker stops the work. `READY`, `PLANNED`, and `CANDIDATE_CREATED` are
not successful terminal states for a task that asks for a working artifact.

## Mode behavior

Deterministic mode tries exact parsers and registered procedures. It preserves
a `DeterministicAttemptTrace` when it cannot continue. It does not guess.

Hybrid mode runs that exact attempt first. If semantic help is allowed, the
model receives the original task, current state, deterministic trace,
failures, selected intelligence, available capabilities, permissions, budget,
and required output contract.

Non-deterministic mode lets the model lead semantic orientation and action
selection. Loop Engine still controls tools, providers, permissions, files,
network access, commands, budgets, artifacts, and verification.

## Typed model exchange

The model does not control execution with free-form prose. Each semantic call
receives an `LLMWorkPacket`. The first interpretation must satisfy the
`TaskOrientationResult` contract. Later choices must satisfy the
`NextActionDecision` contract.

Each context block records its ID, kind, version, digest, source, selection
reason, position, and estimated size. Context selection runs through an
Intelligence Loop. Prompt assembly and its atomic projections, JSON
serialization, ordering, and text combination run through deterministic Loops.
The original task remains separate from the interpretation so a verifier can
detect drift.

The action vocabulary is closed and versioned. It covers user questions,
authority requests, intelligence retrieval, research, reuse, adaptation,
composition, capability construction, code execution, delegation, parallel
work, verification, repair, integration, learning, result return, abstention,
and stop.

## Research and source use

Web search and source fetch are separate capabilities:

```text
core.web.search
→ unverified candidate URLs and bounded snippets

core.web.get
→ selected source snapshot, digest, media type, and artifact reference
```

A search result is not evidence. When a run searches before project
construction, it must fetch a selected source first. Network access requires
an exact approved effect.

## Dynamic project construction

`core.generated_project` asks the model for a passive project candidate. The
candidate lists file purposes, commands, and expected artifacts. Loop Engine
validates it before asking for each file in a separate bounded model call.

The validated manifest becomes a candidate Solution Canvas and one
`LoopGraphDefinition`. Solution Loops then write and execute the files in a
confined Docker workspace. Dependency installation may use network access
only through an explicit `python -m pip install` setup command. Execution and
verification run without network access.

Malformed JSON, invalid project candidates, invalid files, failed commands,
and missing artifacts remain visible. They become repair input for the next
Practitioner pass. Loop Engine does not replace them with canned output.

Fetched inputs keep a safe authoritative filename when the URL provides one.
For example, a fetched `adult.data` resource becomes `inputs/adult.data`.
Generated Python must reference an exact supplied input path as an executable
string literal. A README mention or source-code comment does not count as
input use.

## Stalled work and strategy recovery

A deterministic monitor may identify stalled progress. It does not decide
that the task is hopeless. It records changes in unique evidence, project
attempts, verified artifacts, and governed task state. Repeated unchanged
state or repeated post-project research activates a semantic recovery panel.

```text
stalled-progress signal
→ failure-diagnosis model call
→ first changed-strategy proposal
→ materially different alternative proposal
→ independent proposal selection
→ permission and capability validation
→ normal next-action selection
→ execute the selected changed strategy
→ verify measurable progress
```

Each panel call has one typed output contract and one bounded semantic repair
attempt. The panel may recommend configuration, modification, mutation,
composition, repair, research, reframing, or delegation. It returns passive
proposals and a recovery directive. It cannot execute a tool, grant a
permission, or declare success.

Hard authority, cancellation, safety, and declared budget limits remain
deterministic. Repeated wording alone is not progress, but repeated state does
not cause an immediate deterministic stop.

## Verification scope

Every blocking gap must reference one registered acceptance criterion from the
preserved task. Optional quality improvements and proposed new requirements
have separate fields. They do not silently redefine completion.

The current semantic-step contract is also separate from the task acceptance
contract. An orientation that treats production of its own payload or schema
as the final task objective is rejected and repaired before it becomes current
task state.

## Completion evidence

Every run returns a typed result and saves Run History. The result includes
the preserved task, feedback slots, deterministic attempt, orientations,
action decisions, candidate Solution Canvases, selected graph, research
records, project attempts, verification records, Loop details, and the saved
history path.

An artifact task succeeds only when the selected project passes its declared
commands and every expected artifact exists with the required minimum size.
The semantic verifier must also accept the result against the original task.

## Tests against example overfitting

The offline acceptance suite covers 50 paraphrases, multilingual requests,
unseen tasks, noun substitution, cross-domain capability gaps, all three
modes, ambiguity handling, delegated choices, permission refusal, malformed
JSON repair, invalid project-candidate repair, premature-result refusal, and a
source scan for example-specific logic in the universal solver. It also covers
model-led stalled-work diagnosis, competing strategy proposals, recovery
selection, executable repair binding, verification-scope preservation, and
input-use enforcement.

Examples remain test data. Domain code belongs behind capabilities,
procedures, plugins, adapters, intelligence records, or portable solutions.
