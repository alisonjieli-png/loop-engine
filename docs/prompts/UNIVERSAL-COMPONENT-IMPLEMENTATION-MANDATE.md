# Loop Engine universal component implementation mandate

Paste this prompt into a fresh coding-harness session at the root of the Loop
Engine repository.

```text
Work from the current canonical branch of:

https://github.com/alisonjieli-png/loop-engine

This is an implementation mandate. Read the current repository before editing.
Follow AGENTS.md, the Constitution, architecture.yaml, terminology.yaml, the
component and contract documentation, current code, tests, examples, Git
history, and current GitHub Actions state.

Do not summarize and stop. Implement, execute, test, audit, document, commit,
push when authorized, inspect GitHub Actions, repair failures, and continue
until the requested checkpoint is proven.

Constitutional model

1. Loop is the sole concrete executable runtime.

2. Every independently governed operation and every executable graph vertex
   executes through Loop.

3. Practitioner, Intelligence, and Solution are roles. They are not runtime
   subclasses.

4. Deterministic, hybrid, and non-deterministic are selected per Loop and do
   not grant authority.

5. LoopGraphDefinition is the sole reusable executable graph authority.

6. A passive Loop component is versioned, typed, digest-pinned information.
   It does not execute, call a provider, read files through hidden I/O, grant
   permission, mutate itself, or become a graph vertex.

7. Operations that select, assemble, compare, transform, validate, invoke,
   persist, or learn from passive components are governed Loop work.

8. Do not create or export LoopNode. The phrase "loop node" may only describe
   a Loop occupying a graph position.

Universal component contract

Map each current semantic building block to the existing component contract or
the smallest conforming extension. Do not create a second identity system.

A passive component definition must identify:

- ID, semantic version, and content digest;
- registered component kind and operationality;
- payload contract and payload digest;
- role and mode affinities;
- typed input and output contract references;
- settings, policy, intelligence, capability, and verification references;
- scope, lifecycle, provenance, compatibility, and extension points;
- explicit permissions and effects when non-static;
- explicit absence of permissions and effects when static.

At minimum, cover settings, configuration, policy, preference, strategy,
profile, procedure, procedure step, question, question portfolio, persona,
guidance, context block, prompt assembly, LLM work packet, task context, Loop
context, handoff, intelligence, memory, capability, adapter, provider, route,
contracts, artifacts, results, events, reports, candidates, benchmarks, and
experiments.

Static and executable are different

Do not make every Python object inherit from Loop. Do not leave static
semantics as arbitrary dictionaries or concatenated strings either.

Use:

static component
-> inert governed information

operation on that component
-> Loop work

Keep Definition, Ref, Snapshot, runtime state, and Result separate.

Prompt and model-call architecture

Treat the model as a bounded semantic step resolver. It does not receive an
entire task and return unchecked final authority.

Every semantic call must use one passive, typed, versioned LLMWorkPacket with
separate sections for:

- persona context;
- original and normalized task context;
- global, long-, medium-, short-, parent-, and local task relationships;
- current Loop identity, role, profile, mode, relationship, checkpoint,
  permissions, budget, deadline, return contract, and verification state;
- selected Context Intelligence and questions;
- available and unavailable capability descriptions;
- deterministic and prior attempt history;
- one bounded WorkDirective;
- one output contract and policy context;
- source references and a content digest.

The packet is passive. Context selection runs through Intelligence-role Loops.
Prompt selection, ordering, combination, compression, and rendering run through
a deterministic Loop. The physical provider attempt runs through ModelGateway
and its owning model-attempt Loop.

Do not concatenate persona, task, history, and instructions in the generic
solver. Reuse the repository's provider-neutral PromptAssemblySpec. Add
versioned prompt-block components and data-driven profiles instead of another
prompt engine.

Support at least:

- minimal sufficient;
- standard balanced;
- hierarchy preserving;
- failure repair;
- references only;
- summary plus references;
- demand pull;
- adaptive expansion;
- broad firehose experiments with explicit authority.

Save a PromptAssemblySnapshot with exact block refs, order, versions, digests,
selection and rejection reasons, compression or truncation, estimated and
actual token accounting, missing context, fallback history, packet digest, and
prompt digest. Do not persist private reasoning or raw secrets.

Recursive handoff

A parent Loop must create a typed handoff for independently governed child
work. Preserve global, long-, medium-, short-, parent-, and local task context
as distinct references. Distinguish:

- available to request;
- available by reference;
- materialized for the child;
- placed in the model context;
- selected for a decision.

The child may request more context through a typed ContextNeedRequest. Never
copy parent private scratch, sibling private state, unrelated user data, raw
reasoning, or secrets into a child.

Granularity

Every semantically meaningful value exposure and transformation is a logical
Loop, including constant reads, settings and intelligence access, text
combination, formatting, template rendering, prompt assembly, context
assembly, JSON serialization, mapping transformation, path construction,
command construction, schema conversion, and validation.

Pure known operations default to deterministic mode. They use registered
atomic primitive definitions and return typed `LoopValue` or `LoopValueRef`
records with producer, input refs, digest, lineage, privacy, materialization,
and verification state.

Native `+`, `join`, formatting, JSON, mapping, and path operations are allowed
only in a tiny audited intrinsic kernel. The intrinsic kernel cannot contain
task, domain, provider, storage, permission, policy, routing, or example logic.

Keep logical and physical execution separate. A physical executor may fuse or
cache compatible pure deterministic atomic Loops, but must preserve every
logical definition ref, Loop ID, input and output digest, provenance, failure
location, fusion decision, cache decision, and replay record.

Practitioner procedure

Represent the default Practitioner as data and execute it through the same
Loop runtime:

Orient
-> Standardize and bind
-> Reconcile Horizon
-> Assess and Prepare
-> Decide Next
-> Determine How
-> Act
-> Verify
-> Integrate and Commit
-> Route
-> repeat

Each semantic model call resolves one responsibility only. READY, ORIENTED,
PLANNED, or CANDIDATE_CREATED is not completion when the task asks for a
working artifact.

Context Intelligence

Keep the four persistent layers closed:

1. Context Intelligence
2. Code Intelligence
3. Runtime History and Solution Intelligence
4. User Feedback Intelligence

Keep Core, Learned, and Plugin as namespaces and provenance. Keep Ask,
Horizon, Readiness, Deliberation, Implementation, Execution, Verification,
Integration, and Routing as non-exclusive functional metadata. Do not turn
them into new layers or folders.

Store generic personas, questions, guidance, prompt profiles, failure patterns,
verification rules, examples, and counterexamples as versioned components.
Select them conditionally. Record selected and rejected items and why.

Initial Core guidance must cover preserving the original request, separating
facts from assumptions, asking only material questions, delegated choices,
reuse before build, verified artifact completion, one bounded next action,
independent verification, unknown-is-not-no, no permission inference, and
typed output.

Settings

Represent settings as passive components. Resolve Core, organization,
workspace, project, user, and run scopes through deterministic Loop work. Save
sources considered, values selected, conflicts, rejected overrides, credential
references, and the effective digest. Preferences cannot override policy. A
run override cannot broaden authority.

Genericity

The user task is runtime data. It must not become a generic-solver branch.
Examples are black-box acceptance tests.

No generic source may contain an exact acceptance sentence, fixed dataset,
fixed model list, media effect, report graph, domain procedure, or
example-specific Solution Canvas.

Prove the same infrastructure with 50 paraphrases, multilingual requests,
noun and operator substitutions, unseen tasks, several artifact types, and at
least five domains. Honest capability gaps are valid. Fabricated success is
not.

Documentation and inventories

Reconcile one component glossary, data dictionary, interaction dictionary,
extension and parameterization rules, context-handoff ontology, prompt and
invocation architecture, and folder map. Generate machine-readable component,
interaction, redundancy, string/blob, handoff, and generalization inventories.

For each component record its purpose, source of truth, static or executable
status, input and output contracts, creators, consumers, allowed operations,
authority, prohibited authority, scope, lifecycle, versioning, storage,
materialization, extension, parameterization, compatibility, neighboring
terms, interactions, tests, and migration.

Implementation checkpoints

0. Preserve the worktree, fetch main, capture Git and CI, run baseline tests,
   conformance, package build, and clean install.

1. Prove one runtime, three roles, per-Loop modes, one graph authority, four
   intelligence layers, and passive packet/component semantics.

2. Reconcile the component ontology, glossary, data dictionary, interaction
   dictionary, extension rules, and folder map.

3. Componentize representative settings, personas, questions, guidance,
   prompt profiles, and intelligence records.

4. Implement typed horizon context, handoff, reference availability,
   materialization policy, context requests, and isolation.

5. Route every semantic model call through LLMWorkPacket,
   PromptAssemblySpec, a deterministic assembly Loop, ModelGateway, typed
   validation, format repair, and saved snapshots.

6. Complete the recursive Practitioner, dynamic Solution Canvas,
   LoopGraphDefinition execution, repair, verification, and completion loop.

7. Support raw handoff preservation and governed standardization. Deterministic
   consumers require canonical schemas. Model-led consumers must return
   canonical typed output.

8. Instrument context, questions, personas, handoffs, routes, attempts,
   verification, cost, latency, and contribution. Stage learning candidates
   only. Require independent review and negative-transfer tests.

9. Run multidisciplinary black-box proofs, including the flagship modeling
   task and a materially changed modeling task without core edits.

10. Run the separate adversarial review, repair all critical and high
    findings, build and clean-install the wheel, run the public CLI, commit,
    push main, inspect GitHub Actions, and repair every required failure.

Hard gates

Do not report completion until:

- one concrete Loop runtime remains and has no first-party subclasses;
- every executable graph vertex resolves to Loop;
- passive components cannot execute or grant authority;
- LLMWorkPacket, questions, personas, settings, events, and results stay
  passive;
- context selection, prompt assembly, model calls, and child handoffs are
  governed Loop work;
- original and normalized tasks remain separate;
- prompt blocks are versioned, selected, ordered, and digestable;
- complete deterministic attempt history reaches hybrid repair;
- child context is scoped and can be expanded through typed demand pull;
- no example-specific generic branch remains;
- the recursive Practitioner continues until verified acceptance or a typed
  blocker;
- the component documentation agrees with code and tests;
- the flagship and changed-task black-box tests pass;
- the wheel, clean install, public CLI, Run History, Studio, conformance, and
  required GitHub Actions pass.

Only print evidence-backed success labels.

Final handoff

Return exact SHAs, commits, commands, test counts, run IDs, artifact paths and
digests, CI run IDs, implemented component mappings, packet and assembly
evidence, handoff evidence, genericity evidence, clean-install evidence,
remaining exact blockers, and the final verdict. Do not end with another plan.
```
