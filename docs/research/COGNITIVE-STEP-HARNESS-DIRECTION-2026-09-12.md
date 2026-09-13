# Cognitive steps, harness processes, and reusable Solutions

Status: design synthesis and review, 2026-09-12. This records the owner's
current intent and distinguishes it from implemented behavior and saved
evidence. It does not replace the Architecture Constitution, typed contracts,
or component documentation. It grants no execution, spending, or promotion
authority.

The current work is review and documentation. The owner explicitly deferred
new runs and implementation. Copied projects are design references. Their
presence inside this folder does not make them part of the installed engine.

The accompanying [evidence review](../../artifacts/review-2026-09-12-JAXVkn/REVIEW.md)
contains scope, session provenance, saved Tactical run counts, reproduced
defects from the earlier review phase, and the limits of those observations.

## What we are trying to build

Loop Engine should turn a task into a reusable, verified program through a
sequence of small, independently governed reasoning operations.

A person supplies a task folder, such as a ticket with instructions and
attachments. The system determines what the task means, what information is
missing, what already exists, and what must be built. It can investigate,
try alternatives, inspect failures, change its approach, and verify the work.
The durable result should include a Solution graph that can run again under
its declared inputs and authority.

The reasoning used to discover that graph and the graph delivered to the
user have different purposes. The Practitioner graph records how the system
arrived at a solution. The Solution graph describes the work that must run
for another input. Reusing the Solution should avoid repeating the original
investigation and design work.

Some Solution Loops may still call a model when their contracts require
semantic work. Reusable does not mean every future execution must contain
zero model calls. A deterministic realization becomes possible when a
verified implementation can satisfy the contract in a defined input region.

The central research hypothesis is that explicit decomposition, selected
context, executable feedback, and accumulated reusable procedures can reduce
the reasoning burden placed on any individual model call. This could make
smaller models useful for tasks that a single large prompt handles poorly.
The advantage must be measured. Neither more iterations nor a larger
collection of harnesses establishes it by itself.

## The architecture that remains fixed

~~~text
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
~~~

A harness is an implementation used by a Loop. OpenCode, Pi, Codex, and
other compatible harnesses can provide a process body for bounded work.
They do not become competing Loop runtimes or acquire authority over
acceptance, persistent promotion, or the engine's stores.

~~~text
Loop role profiles
├── Practitioner
│   ├── reference nine-step
│   ├── compact five-step
│   ├── research
│   ├── solver
│   ├── verifier
│   ├── code execution
│   └── self-improvement task
├── Intelligence
│   ├── cross-layer search and materialize
│   ├── Context Intelligence
│   │   └── serve, search, and frame
│   ├── Code Intelligence
│   │   └── resolve, invoke, and load
│   ├── Runtime History and Solution Intelligence
│   │   └── search, replay, and compare
│   └── User Feedback Intelligence
│       └── serve, scope, and interpret
└── Solution
    ├── atomic component
    ├── pipeline
    ├── router and fallback
    ├── ensemble
    └── validator
~~~

The three public capability groups remain Intelligence Search and Retrieval,
Web Research, and Custom Plugins. Model gateways, storage, process management,
approvals, Runtime Memory, and Run History are internal mechanics.

The [work-approach decision](../architecture/WORK-APPROACH-INSTRUMENTATION.md)
already translates human-work analogies into observable operations:
questions, attention, procedures, progress monitoring, and delegation.
The project does not need a claim about reproducing biological consciousness.

## Why separate cognitive steps

A useful cognitive step has a bounded responsibility and an output that
another part of the system can inspect or consume. Examples include
identifying a missing input, comparing validation strategies, proposing a
small implementation, interpreting a failed command, or checking a claimed
result against a contract.

The step receives the information needed for that responsibility. It does
not automatically receive the entire conversation, every attachment, every
tool, or all other workers' private state.

This separation is intended to provide:

- Better context selection. The input can emphasize the facts relevant to
  this decision and keep other material behind references.
- Local repair. A failed assumption or implementation can be investigated
  without restarting the entire task.
- Interchangeable execution. A suitable native implementation or a qualified
  harness can satisfy the same bounded contract.
- Reuse. A recurring operation has a stable input/output interface and
  evidence about when a previous implementation applies.
- Inspectable alternatives. The system can retain several answers to the
  same question and compare their consequences.
- More precise learning. Outcomes can be attributed to the particular
  decision, context, tool, or procedure that contributed to them.

These are architectural opportunities. Their cost and quality benefits remain
experimental questions.

In the owner's framing, prompt engineering puts expertise into a prompt.
Iterative prompting distributes that expertise across follow-up questions.
Loop and graph engineering makes the continuation, branching, and checking
explicit. The present goal adds a separately configured execution context for
each independently governed cognitive assignment, then preserves useful
procedures and implementations for future assignments.

That external intelligence includes how to inspect, which question to ask,
what evidence to request, which tool to use, and how to recognize failure.
It can evolve independently of the underlying model. Configuring a harness
for a particular step is not itself model training; weight updates and their
evaluation would be a separate later mechanism.

Separation does not require launching an operating-system process for every
ordinary function call. The Constitution reserves independent Loops for work
that needs its own goal, contract, authority, budget, scheduling, retry,
verification, cancellation, or history identity. Low-level calculations can
remain inside the owning Loop.

Logical granularity and process lifetime are separate choices. A small
semantic assignment might require several model and tool calls inside one
harness instance. A process pool might later serve several assignments, but
only after state isolation and configuration reset are qualified.

## What one harness instance should receive

The launch material should answer five practical questions: what is my task,
what must I return, what do I already know, what may I access, and when must
I stop?

| Launch material | Intended content |
|---|---|
| Identity and objective | Exact Loop definition, activation, responsibility, and return destination |
| Input and output contracts | Required types, schemas, invariants, proposed response forms, and validation rules |
| Critical context | Task constraints, necessary facts, current observation, and unresolved questions |
| Context manifest | Small descriptions, identities, versions, sizes, and digests of optional material |
| Tools and plugins | Only the exact capabilities and effects this assignment may use |
| Skills and procedures | Selected, admitted resources, with versions and content identities |
| Working files | Explicitly staged inputs and a confined location for candidate artifacts |
| Budget and lifecycle | Work limits, cancellation, continuation, and terminal conditions |
| Recording interface | How to publish outputs, observations, usage, failures, and references |

Suggested response forms are part of the reusable intelligence. They help a
model produce something the next operation can consume. They must retain a
way to express uncertainty, an incompatible assumption, or a material gap.
A fixed format must not force the model to invent a value.

The harness may supply its own useful mechanics for reading files, invoking
tools, loading skills, and recovering from tool errors. Loop Engine should
reuse those mechanics when the integration can govern them. The engine still
validates typed effects, exact authority, outputs, and acceptance.

Today the canonical process adapters primarily implement a text-only semantic
profile. They disable native harness tools and broker model requests through
the existing gateway. That proves a narrower integration than a fully
equipped harness independently choosing tools and loading intelligence.
See [the harness guide](../../embodiments/HARNESS-GUIDE.md) and
[the semantic binding](../../src/loop_engine/core/harness_semantic.py).

## Passing context between processes

There are three useful delivery patterns. None needs to become a universal
default before comparison.

| Pattern | What the process receives | Question to measure |
|---|---|---|
| Inline delivery | A small complete packet | Is the packet sufficient, and how much unnecessary context does it contain? |
| Reference delivery | A context identity and a small manifest, with an authorized resolver | Can the process reliably find and load the right information? |
| Mixed delivery | Critical instructions and schemas inline, larger optional bodies behind references | Does selective loading preserve quality while reducing total context and retrieval work? |

The mixed pattern is a useful initial candidate. The output contract, current
responsibility, and essential constraints should be easy to see immediately.
Large source material, older observations, alternative procedures, and
supporting artifacts can remain behind references.

A reference needs enough metadata for selection. An opaque identifier alone
does not tell a worker whether it contains the information it needs. The
reference should also bind exact content, schema, scope, and provenance.
Possession of that reference is not permission to read it.

Centralized logical storage does not require one database containing every
body. The existing InformationResolver separates a value's identity from its
inline, file, or database materialization. Large immutable bodies can stay in
the artifact store while catalog records and manifests supply their metadata.
The resolver, not arbitrary SQL authored by a model, should enforce access.

The next proof should show that a producer can publish a value, terminate its
process, and leave a reference that a separately launched consumer can resolve
under its own grant. It should also distinguish a missing object, changed
digest, stale revision, incompatible schema, and denied scope.

Existing foundations include
[InformationResolver](../../src/loop_engine/core/information_access.py),
[context artifacts](../../src/loop_engine/core/context_artifacts.py),
[spawned Runtime Memory ports](../../src/loop_engine/loop/spawned_runtime_port.py),
and [delegation contracts](../../src/loop_engine/loop/delegation_runtime.py).
The copied
frame manifests (`new_overnight_build/poc/frames.py`), packet composition
(`new_overnight_build/poc/packet.py`), and ledger pull interface
(`overnight/core/ledger_pull.py`) in the copied overnight repositories, which
sit next to this working tree and are not tracked here, supply reference
ideas. Their interfaces and security claims require qualification inside
Loop Engine before adoption.

A pointer saves model context only when the worker avoids loading material
it did not need. A small initial packet followed by a complete reload of the
archive does not establish a saving. Count the actual loaded material, tool
traffic, full harness envelope, failures, and provider-reported usage.

## A first answer can arrive before the producer finishes

This is a central requirement, not a minor output-format option.

A Loop may return one candidate quickly and continue investigating. Later
candidates may be better, worse, different, or inconclusive. Consumers should
be able to use an appropriate available candidate without waiting for every
possible improvement.

Four questions need separate answers:

| Dimension | Example answer |
|---|---|
| Response contract | Each emission is one value conforming to a named schema |
| Production lifecycle | Produce once, or continue producing while the activation remains authorized |
| Emission policy | Publish a provisional candidate, a verified candidate, or a candidate meeting an improvement policy |
| Serving policy | Read a named candidate, the first verified candidate, the current best under one policy, or a portfolio snapshot |

A single expected response type can therefore have several candidate
instances over time. A response containing a list is another matter. Neither
the response's shape nor a consumer's number of outputs determines whether
the producer remains active.

Each emitted candidate should bind the producing activation, input revision,
definition, payload digest, and independent evaluation state. An event saying
that an output was admitted is different from an independently verified
answer or a completed task.

A consumer must record the exact candidate it used. A later arrival must not
silently replace the input to completed work. The owning Practitioner can
choose to compare, create another branch, or rerun affected pure work.
Committed external effects require their existing reconciliation rules.

A terminal activation stays terminal. Further improvement after completion
can use a new activation in the existing reactive series. Reading a portfolio
does not start that activation.

The current implementation has several relevant pieces:

- The new LoopContract and LoopConfig output settings support a single output
  or a bounded portfolio of admitted outputs.
- In multiple-output mode, Loop.result() can expose the currently accumulated
  portfolio while a Loop remains active.
- Reactive profiles, candidate records, evaluations, leases, and output stores
  support more detailed lifecycle and serving policies.
- The embodiment lab contains incremental portfolio and durable activation
  experiments.

These pieces do not yet establish one qualified, live harness workflow that
publishes an early answer, continues producing alternatives, and updates a
consumer graph correctly. The new single/multiple setting also needs to keep
input cardinality distinct from output cardinality and producer lifetime.
See [reactive contracts](../../src/loop_engine/loop/reactive_contracts.py),
[candidate outputs](../../src/loop_engine/loop/reactive_outputs.py), and
[the output store](../../src/loop_engine/core/reactive_output_store.py).

## What should become Intelligence

Resource distribution and intelligence classification are different decisions.
A Markdown file is a format. A plugin is a delivery mechanism. Neither defines
a new persistent intelligence layer.

| Layer | Material worth considering for admission |
|---|---|
| Context Intelligence | Procedures, question sets, useful prompt fragments, response templates, failure explanations, and selection guidance |
| Code Intelligence | Verified reusable functions, adapters, transformations, validators, and packaged Solution components |
| Runtime History and Solution Intelligence | Exact attempts, candidate graphs, decisions, failures, comparisons, verification, and observed reuse outcomes |
| User Feedback Intelligence | Scoped preferences, corrections, rejection reasons, constraints, and explicit human decisions |

Runtime Memory contains temporary working state for one run. Useful material
can become a candidate for persistent intelligence through a separate review
process.

Harness binaries, provider credentials, process supervisors, and approval
services remain runtime mechanics. A useful usage guide may become Context
Intelligence; an admitted executable asset may become Code Intelligence.
This does not move the engine's authority into retrieved text.

Context and code produced during a run remain candidates until independent
qualification and explicit promotion. Code admission needs source identity,
provenance, license state, dependency information, contracts, effects, tests,
verification, and a digest. A high score does not supply those requirements.

## Fingerprints and learned shortcuts

The project needs several identities for different purposes.

| Identity | What it can establish |
|---|---|
| Occurrence identity | Which exact activation or decision happened |
| Exact computation identity | Whether all relevant inputs, state, implementation, environment, and contracts match a previously qualified computation |
| Semantic or shape signature | Which prior work is worth considering |
| Embedding or locality hash | A search neighborhood for candidate retrieval |

An approximate match proposes a candidate. It cannot establish that two
computations have the same answer.

Current stage signatures intentionally omit some values and provenance.
The review confirmed that changing known facts and artifact references can
leave a stage signature unchanged. That is useful for finding related
situations and insufficient as a sole result-cache key.

Reuse is already implemented in a bounded form. The
[Reusable Capability Flywheel](../components/intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md)
supports qualification, promotion, eligibility checks, deterministic
invocation, and output verification. Its offline fixture includes an adaptive
Practitioner using a promoted capability with zero model calls.

The Retrieval Engine also has lexical and vector paths, optional model2vec
support, and SimHash metadata. The exact n-gram implementation has its own
explicit precision contract. These facts should not be collapsed into either
“all reuse is finished” or “there are no embeddings or fingerprints.”

The missing product proof is a reliable connection from a recurring cognitive
need to applicable prior material or an executable realization, with retained
failures, independent evaluation, and an appropriate fresh comparison.
Generalizing a trained routing policy requires evidence. Using a known,
verified deterministic function does not require millions of prior runs.

## Choosing harnesses and resource bundles

The owner wants an open comparison, including Pi, OpenCode, Codex, and other
qualified options. No universal winner is selected here.

There are at least four separate experimental choices:

1. Which logical step or subproblem should run?
2. Which permitted mode and model route should resolve it?
3. Which qualified harness or native implementation should carry out the work?
4. Which context, files, skills, tools, and plugins should it receive?

Changing all four at once makes the result difficult to explain. The initial
comparison should hold the task contract, information access, model route,
evaluator, and work allowance fixed while varying one identified factor.
Harness-added prompts and tool behavior are part of the measured difference.

A later runtime selector can choose among eligible implementations. It first
needs facts about supported protocols, available tools, isolation, context
loading, output handling, interruption, usage accounting, and installed
versions. Ranking then uses evidence relevant to the particular work and
declared objective. Unknown suitability remains unknown.

Until routing evidence is qualified, an authorized model can propose a
selection from the eligible set and record its reason. A task name, folder
name, or an arbitrary keyword must not silently choose the solution.

The native path remains a useful comparison. It helps determine whether a
harness supplies useful behavior or mainly adds startup and prompt overhead
for that particular step.

## The Solution graph is a deliverable

A completed task should expose what can be run again: exact component
definitions, named typed ports, dependencies, configuration, artifacts,
verification, and the required environment and authority.

The graph must distinguish building a model, loading a model, producing
predictions, and evaluating predictions when those are different operations.
Evaluation labels must stay outside the candidate's training and prediction
boundary.

LoopGraphDefinition already supplies a versioned, digest-bound graph, and
render_canvas() emits JSON and Mermaid views. Solution execution and the
development dependency-wave executor also exist. The normal solve path does
not yet generally produce and execute a multi-slice development plan through
that wave executor. It has a smaller per-action Solution compilation path and
serial governed delegation.

An exported graph declaration is not a demonstrated portable deployment
package. The next export proof should run the accepted Solution in a fresh
workspace with its declared artifacts and dependencies, without relying on
the original investigative transcript or undeclared local paths.
Kubernetes or another scheduler can be a later execution adapter.

Multiple candidate graphs are legitimate. Searching every combination is
usually a separate, much larger task: five alternatives at each of ten
positions give 9,765,625 combinations. A typed search policy should decide
which branches to evaluate, retain, revise, and stop. More branching is not
automatically more learning.

## What the saved Tactical runs establish

The read-only review found 66 surviving campaign cell records and 73 saved
Run History files in the scoped campaign and probe locations. Those histories
contain 3,362 model-invocation records. Of these, 3,356 name provider tactical
and model gemma-4-coding-abliterated; six have unknown identity and usage.

The known token subtotals are 67,629,533 input tokens and 1,831,776 output
tokens. These are sums of saved event fields, not a complete billing ledger.
Health probes and overwritten or missing attempts prevent treating them as
an exact total of all endpoint traffic. Cost remains unknown.

The records show substantial model traffic, structured semantic responses,
separate harness launch material, real candidate source files, and many
failed or incomplete attempts. They do not establish which harness is best
for general solutioning or that this remote route represents local inference.

The three positive surviving gate records are two OpenCode artifacts and one
Codex artifact. All three retain BLOCKED_MATERIAL_INPUT as the engine terminal
code. A later gate pass and engine completion are distinct recorded outcomes.

The two reported perfect scores cannot support a held-out performance claim.
Their saved solutions train on the full CSV that the evaluator subsequently
samples as a holdout. All eight adapted evaluators also pass the target label
into predict(row). A synthetic label-copying control passed all eight before
the owner deferred further tests. Preserve those results as diagnostic history
and repair the evaluation boundary before using it for new comparisons.

The current task database contains 318 raw task directories and eight adapted
tasks. Directory count is not an eligible benchmark population. The proposed
70-to-200-task campaign should come after harness/context/output qualification
and task/evaluator admission.

## The next proof sequence, when runs resume

These are proposed experiments, not work started by this review.

| Order | Question | Required observable result |
|---|---|---|
| 1 | Can separately launched processes exchange exactly the intended information? | Producer/consumer identities, exact packet or reference resolution, version and scope checks, and retained failures |
| 2 | Which launch resources are sufficient for a bounded cognitive task? | Comparable inline, reference, and mixed delivery; selected resources and actual loaded bytes recorded |
| 3 | Can a producer return useful work and keep improving it? | Early candidate, later alternatives, independent evaluations, correct consumer binding, and explicit terminal behavior |
| 4 | Which eligible harness/resource combination works well for which step? | Same frozen contracts and model route, with all failures, usage uncertainty, startup cost, and time to a usable output retained |
| 5 | Can a solved task produce a reusable executable graph? | The delivered Solution runs from declared inputs in a fresh workspace and passes a separate evaluator |
| 6 | Does qualified reuse improve a later task? | Exact applicability checks, independent output verification, fresh comparison, and visible negative transfer |
| 7 | Does this hold across a larger task population? | Admitted tasks, protected holdouts, frozen selection rules, correct accounting, and no post-hoc removal of failures |

Correctness prerequisites include the evaluator leakage, verifier process
termination, saved-definition compatibility, and output-lifecycle distinctions
described in the evidence review. They are reasons to prepare a sound
experiment, not reasons to replace the central architecture.

## Folder organization and JSON records

The copied projects should remain clearly identified references. The active
package, experimental launch surfaces, reference implementations, and saved
evidence have different authority and maturity. A short map is more useful
than an immediate move that breaks absolute paths, worktrees, or running jobs.

No copied reference folder was moved or deleted for this review. A later
cleanup should first bind source revision, ownership, active-process use, and
all known references. Preserve unique source and saved failures. Do not erase
session history merely because it is large.

The owner now prefers database-managed JSON writing. This review uses DuckDB
for its structured data and generates JSON through database exports. The
review database is a disposable projection of source files and saved records,
not a new product authority.

Loop Engine's managed notes must continue through RecordOperationService or
the records command, with exact approval and expected revision. Canonical Run
History retains its existing writer. Git-controlled contracts and schemas
retain their existing authority. See
[queryable records and storage](../guides/queryable-records-and-storage.md).

The desired endpoint remains concrete: a task enters, bounded Loops investigate
and construct alternatives, independently checked work becomes an executable
Solution, and qualified parts become useful starting points for future work.
