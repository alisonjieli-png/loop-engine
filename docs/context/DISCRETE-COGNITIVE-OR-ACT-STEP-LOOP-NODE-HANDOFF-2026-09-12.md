# Discrete cognitive or act step Loop node: complete explanation and session handoff

## Preserve the full phrase and the full explanation

The owner requested this record before changing Codex accounts on September
12, 2026. Preserve the full phrase "discrete cognitive or act step Loop node"
and the complete behavioral explanation below. Do not substitute a shorter
name, remove "node," or keep the name while dropping its explanation.

The earlier assistant wording "a Loop for a discrete cognitive or action
step" and the proposed shorthand "discrete-step Loop" are superseded by this
clarification. Those substitutions did not preserve the requested language.
Repeat the full phrase in explanations, documentation, prompts, and handoffs.
Do not introduce an acronym or alternate label for convenience.

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

## Meaning of the existing runtime

The explanation describes the intended architecture. It does not claim that
every described behavior has already passed live qualification. The existing
runtime classification remains:

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

"Loop node" describes an executable graph vertex implemented by the existing
`Loop` runtime. It does not introduce another runtime class, a `Node` subclass,
or additional roles or modes. Exact code identifiers and contract fields keep
their existing names. Keeping those identifiers intact does not authorize
shortening the descriptive phrase in prose.

A discrete cognitive or act step Loop node has typed inputs and outputs,
explicit loop and exit conditions, permissions, and its own recorded
identity. A narrowly scoped assignment may still require several internal
operations. Ordinary implementation primitives remain inside their owning
Loop unless they need independent governance.

The question "Is this what I expected?" applies to observations from model
calls, directory inspections, tool actions, and information handoffs. A
mismatch can require more evidence, a repair, a changed method, a different
permitted harness, or an honest failure. A structurally valid response is not
automatically a correct task result.

Continued candidate production must keep output publication separate from
completion. Later alternatives must not silently replace an output already
used by a consumer or repeat a committed external effect. After an activation
is terminal, additional work requires a new authorized activation rather than
rewriting the terminal history.

## Current implementation and saved evidence

For the owner's subsequent September 13 clarification, read the
[complete initial configuration and fallback dimension requirement](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md).
It supplements this behavioral explanation without changing the historical
results below. Every configuration dimension needs its own initial choice
and ordered fallback priorities.

Read the
[architecture and current-state report](../research/COGNITIVE-STEP-ARCHITECTURE-AND-STATE-2026-09-12.md)
for the complete folder and session review, intended architecture, experiment
history, defects, source locations, and proof sequence. Its terminology
predates the clarification on this page. Preserve its historical evidence;
use the full phrase and explanation on this page for continued writing.

The latest saved results remain:

| Evidence | Recorded result and limit |
|---|---|
| Separate harness execution and fallback | A real Pi-to-OpenCode structured-response recovery completed. This was a bounded response-admission experiment, not a solved Kaggle task. |
| Cognitive and action recovery diagnostics | Six runs on one previously attempted task; zero development or sealed evaluation passes; 202 known physical model calls. Three call totals remain unknown. |
| Recovery learning assessments | Nine attempts: eight task-local dispositions and one failed assessment; zero reusable candidates or promotions. |
| Task-folder coverage | Nine distinct task identities in the scoped Tactical evidence. Repeated runs are not additional unseen tasks. |
| Saved clean installation | 3,839 of 3,839 checks and 27 of 27 conformance gates passed. Optional integrations and hosted continuous integration were not all verified by that result. |
| Latest source comparison in the checkpoint | All 472 package Python files matched the checked package source at the recorded comparison. Recheck before attributing later behavior to that package. |

The source reports are
[per-step harness recovery](../verification/HARNESS-STEP-RECOVERY-2026-09-12.md),
[cognitive and action recovery](../verification/COGNITIVE-ACT-RECOVERY-2026-09-12.md),
and the [current-state evidence directory](../../artifacts/state-checkpoint-20260912-OtPgn5/README.md).
These are saved results, not tests or campaigns rerun for this handoff.

The live continued-output solution matrix, effective application of selected
repairs, reusable Solution graph delivery and replay, and independently
verified cross-task learning remain open. Do not describe the complete design
as implemented merely because it is documented here.

The next identified proof is applied recovery: provide the exact failed
contract and a small executable set of repair choices, record which change
was selected, verify that the change actually reached execution, and assess
the resulting outcome independently. Repeated diagnosis without a useful
applied change remains a stall.

## Continuation after changing accounts

The repository is `/home/username/loop-engine`. At this documentation handoff,
the branch is `main` and the revision is
`0cb7b86cb7f5b1f6a6b1b798da4e0a4a1469e00f`. The shared working directory has
substantial uncommitted and untracked work. Other coding sessions and
background processes are present; process names do not establish ownership.

These instructions and the explanation are saved as local repository files.
They do not depend on access to the previous account's conversation history.
No commit, push, or account migration was performed for this handoff. A
different machine or checkout needs these files transferred explicitly.

Read [AGENTS.md](../../AGENTS.md), this complete explanation, and the linked
architecture and current-state report before continuing. Recheck the branch,
revision, dirty paths, relevant source identities, active processes, and
ownership. Do not discard, restore, reformat, commit, publish, or delete other
work to obtain a clean checkout.

The current provider preference is Tactical Engineering with
`gemma-4-coding-abliterated`. Automatic Ollama failover is disabled. The
reported roughly 30-hour Ollama usage reset was an estimate, not a verified
reset time or permission to switch automatically. Do not print credentials
or include them in a handoff.

The latest request was documentation before an account change. Reading this
page does not authorize starting another model campaign or replaying external
effects. Continue under the next actual request and the existing typed
authority. Questions answerable through permitted inspection should be
resolved through inspection rather than unnecessary requests to the owner.

Use DuckDB or the established managed writer for generated structured records
and JSON file writing. Do not hand-author generated JSON. Canonical Run
History and managed records retain their existing writers and approval rules.
This page is hand-authored documentation, not a generated
`session_handoff/v1` packet or a new managed record collection.

Historical checkpoint databases and validation results remain fixed. Later
documentation changes can legitimately differ from their saved source
digests. Do not overwrite an earlier manifest to make those differences
disappear.

An opening instruction for the next conversation is:

```text
Work in /home/username/loop-engine.
Read AGENTS.md and
docs/context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md
in full, then read the linked architecture and current-state report.
Preserve the full phrase "discrete cognitive or act step Loop node" and its
complete behavioral explanation. Do not shorten either one.
Recheck the shared working directory and current evidence before acting.
Do not start model campaigns merely because the handoff lists future work.
```
