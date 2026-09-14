# Loop Engine instructions for coding agents

This file governs work inside the Loop Engine repository. It is intentionally
short. Follow the linked component documents for details.

## Repository identity

- Repository: `/home/username/loop-engine`
- Remote: `https://github.com/alisonjieli-png/loop-engine.git`
- Product and repository name: Loop Engine
- Python distribution and command: `loop-engine`
- Python import: `loop_engine`
- Public README title: Building with Loops

Loop Engine is a standalone repository. `/home/username/taedri.dev` is a
separate project and may be consulted as a design reference. Do not merge the
repositories or copy whole files, registries, naming systems, or governance
documents from Taedri.

## Start here

Before material work, inspect the current branch, revision, dirty state,
active processes, and concurrent writers. Then read only the documents needed
for the task:

1. `README.md`
2. `docs/architecture/CONSTITUTION.md`
3. `architecture.yaml`
4. `terminology.yaml`
5. `docs/contracts/README.md`
6. `docs/components/README.md`
7. the relevant component README
8. `humanizer-context.md` for public prose
9. `docs/context/CODEX-START-HERE.md` after a new or compacted session
10. `docs/context/REFERENCE-SOURCES.md` before consulting an older repository
11. `ASTRA.md` for the current advisory comments and suggestions for continued
    development and Claude Fable 5.1 review

Treat existing changes as user or concurrent-agent work. Do not discard,
restore, reformat, commit, or publish changes without resolving ownership.

## One Loop runtime

Every executable graph vertex is a Loop. Do not create another operational
runtime type.

Before creating a class whose name ends in `Node`:

1. Stop.
2. Confirm that no active first-party `*Node` class is permitted.
3. Represent the concept as a typed object consumed by `Loop`, a
   `LoopProfileSpec`, a payload, a reference, a result, a report, a policy,
   a contract, an artifact, or a RepositoryEntity.
4. Historical serialized `kind: loop_node` records may be read only through
   the exact migration into `LoopDefinitionRecord`.
5. Do not create a Node subclass. The canonical Loop class refuses subclassing
   at class-creation time.

Before creating a new top-level folder:

1. Identify its stable architectural boundary.
2. Explain why attributes, records, or catalog queries are insufficient.
3. Add a README and architecture contract.
4. Add import-boundary tests.
5. Update `architecture.yaml`.
6. Create an ADR when the architectural model changes.

Do not infer executable behavior from prose, tags, labels, filenames,
folder names, examples, or comments. Permissions, contracts, routing,
budgets, compatibility, and lifecycle must come from structured typed
fields.

Keep these dimensions separate:

```text
Loop
├── Operational relationship
│   ├── Starting
│   ├── Spawned by
│   ├── Queried by
│   ├── Retrieved by
│   └── Connected from
├── Role: Practitioner, Intelligence, or Solution
├── Mode: deterministic, hybrid, or non-deterministic
├── Step profile: atomic, compact, reference nine-step, or custom
├── Typed input and output contract
├── Loop condition and exit condition
├── Budget and permissions
└── Run History records
```

A Starting Loop has no incoming Loop relationship. A Spawned Loop records one
spawning Loop ID. A spawning Loop and a Loop it spawns may use different
modes. A mode never grants file, network, secret, model, spending, or
external-effect authority. Retired topology fields may appear only inside an
explicit reader for immutable legacy records. New records must not emit them.

Keep semantic relationships distinct. A Starting Practitioner may spawn a
Practitioner subproblem Loop and query an Intelligence Query Loop. That Query
Loop retrieves Intelligence Item Loops and returns typed references or
material. A Starting Solution runs deterministic pipelines through Connected
Solution Loops. Use Spawned Solution Loops only for a real dynamic branch,
fallback, repair, or ensemble member.

A Loop is the only executable graph vertex. Every displayed Loop names its
role and exact profile, its own mode, typed input and output ports, loop
condition, exit condition, and graph relationships. Passive records, services,
ports, slots, and edges are not graph vertices. A Canvas or pipeline does not
have one execution mode. It may declare only a policy for the modes permitted
on its member Loops.

Every operational boundary must appear in the existing
`core.boundary_registry` with runtime type `Loop` and either an
exact registered role profile or a validated typed profile source. Static
Architecture has only three public capability groups: Intelligence Search and
Retrieval, Web Research, and Custom Plugins. Providers, settings, workspaces,
approvals, stores, Runtime Memory, Run History, reports, playback, and provider
adapters are internal runtime mechanics. A capability or internal mechanic is
not a graph vertex, but the work that uses it must be owned by a classified
Loop. Missing, extra, unknown, unversioned, or role-incompatible boundaries
fail conformance.

Self-improvement is a Practitioner task. It stages candidates for independent
review and cannot approve its own work.

## Required architecture trees

Use text trees or Mermaid trees whenever a document explains three or more
architecture branches. A flat paragraph is not enough for the Loop hierarchy.
Start with the complete classification tree before showing a specialized
branch.

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

Use the words precisely:

- Runtime type answers, "What operational object runs?" The answer is always
  `Loop`.
- Relationship answers, "How did this Loop enter the active structure?" The
  answer is Starting, Spawned by, Queried by, Retrieved by, or Connected from.
- Role answers, "What broad responsibility does it have?" The answer is
  Practitioner, Intelligence, or Solution.
- Profile answers, "Which reusable versioned behavior preset does this Loop
  use?"
- Category answers, "How is this work classified for search, organization, or
  reporting?" A category does not create a class or runtime.
- Mode answers, "How is this Loop allowed to resolve its work?"
- Step profile answers, "Which ordered steps can it run?"
- Settings answer, "Which contracts, budgets, permissions, provider routes,
  thinking power, and conditions apply?"
- Loop and exit conditions answer, "When may this Loop continue, and exactly
  when does it finish?"
- Graph relationships answer, "Was this Loop starting, spawned, queried,
  retrieved, or connected from another Loop?"

Show the role profile branches when the document discusses role-specific
behavior:

```text
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
```

The Loop runtime defines three modes. A registered profile and an installed
executor may support a subset. The in-process Solution runner supports all
three modes when a compatible executor and exact model authority are supplied;
without them, it returns a typed unavailable-executor failure. Thinking power
and model routing apply only when a hybrid or non-deterministic Loop is
authorized to call a model. They are not additional run modes.

## Typed boundaries and encapsulation

- Prefer small immutable data classes and named configuration objects over
  long positional argument lists or unstructured keyword dictionaries.
- Give every Loop and Solution connection explicit typed input and output
  ports. Refuse incompatible connections before execution.
- Version public contracts, Loop profiles, serialized records, and adapter
  handshakes.
- Keep role, mode, step profile, effort budget, thinking power, provider, and
  effect permissions as separate fields.
- Separate discovery, eligibility, ranking, selection, materialization,
  execution, evaluation, acceptance, and promotion.
- Extend existing registries and event vocabularies. Do not create parallel
  stores, event systems, runtime classes, or sources of truth.

## Intelligence rules

The four persistent intelligence layers are:

1. Context Intelligence
2. Code Intelligence
3. Runtime History and Solution Intelligence
4. User Feedback Intelligence

Runtime Memory is separate, temporary, and scoped to one run. Source formats
such as Markdown, skills, repositories, packages, transcripts, and vectors do
not define new intelligence layers.

Searching, selecting, materializing, framing, invoking, replaying, and
interpreting intelligence are Loop operations. Search returns small typed
references. Load a large body only after selection and permission checks.

Imported and self-generated intelligence remains candidate-only until an
independent process approves it. Never infer promotion from retrieval,
execution, a good score, or model confidence.

Code Intelligence must include an immutable source identity, provenance,
license state, version, dependency information, typed contract, effects,
tests, independent verification, and a digest before it is active.

## Managed notes and records

For a host-configured managed note or report collection, use
`loop-engine records` or `RecordOperationService`. Do not directly rewrite its
database rows, current-reference metadata, immutable revision artifacts, or a
future generated view. Preserve schema, namespace, expected revision, and exact
write approval. Unknown commits are not successes.

Ordinary source-code, schema, test, and hand-authored documentation edits remain
permitted within the task. This does not migrate Run History or historical
reports. Reuse the existing catalog/artifact contracts rather than creating a
parallel store. See `docs/guides/queryable-records-and-storage.md` and
`examples/24_managed_records/` for the current bounded tool.

## Models and providers

- Use real configured providers for provider integration and performance
  claims. A stub or injected transport may test a local contract, but it does
  not prove provider integration or model quality.
- Never silently replace a failed model call with canned or synthetic output.
- Resolve output capacity from a source-backed record for the exact provider
  and model. Without an explicit allocation, request that full capacity, not
  an invented smaller default. A reasoning Loop or user may supply a typed
  `ModelOutputAllocation` within the known capacity, bound to the route and
  decision evidence. Capacity, selected allowance, and total-run authority
  are separate. Unknown capacity requires an explicit unknown result; do not
  turn a total budget or semantic size estimate into a provider limit.
- Keep retry, same-provider fallback, cross-provider failover, formatting
  repair, evaluator-triggered repair, and task replanning distinct.
- Do not enable failover unless the run contract explicitly permits it.
- Preserve provider-reported token usage. Missing usage and cost remain
  unknown, not zero.
- Never write API keys, authorization headers, private prompts, or raw secrets
  to source files, events, reports, or exported traces.

## Effects, workspaces, and external tools

- Discovery must be effect-free.
- File writes, shell commands, network access, model calls, spending, and
  external mutations require explicit typed authority.
- Bind approvals to the exact requested effect. A changed effect needs a new
  decision.
- Use path-confined workspaces. Refuse path traversal, symlink escape, and
  unsafe overwrite.
- Run untrusted code in a declared sandbox with bounded resources and network
  policy.
- MCP tools, skills, providers, and external harnesses are adapters used by
  Loops. They are not executable graph vertices or new runtime types.
- Do not replay a committed external effect silently.

## Evidence and benchmarks

State observed, inferred, assumed, missing, and disputed facts separately.
Preserve failures and excluded attempts with the same prominence as successes.

A full-system Loop Engine benchmark requires:

```text
frozen real task population
  -> Starting Practitioner
  -> reviewed Context and executable Code Intelligence
  -> bounded Spawned Loops
  -> candidate comparison and verification
  -> compiled and executed Solution Canvas
  -> independent evaluator
  -> verified Run History, playback, and report
```

A component test, provider probe, deterministic replay, or partial path is not
a full-system benchmark. Report the exact denominator, selection rule, metric
direction, evaluator, failures, physical model calls, token-accounting
completeness, elapsed time, cost state, artifacts, and limitations.

For the current first benchmark campaign, selected solutioning runs are
non-deterministic. Deterministic Spawned Loops may retrieve, execute, validate,
and grade. Do not turn that campaign choice into a universal product rule.

Published results from another harness may be cited as external evidence only
with exact task population, model, harness version, evaluator, source, and
limitations. Do not imply a fair head-to-head comparison when those controls
differ.

## Public writing

Follow `humanizer-context.md`.

- Do not use shorthand or introduce abbreviated aliases in explanations,
  documentation, prompts, or handoffs. Repeat the full descriptive term even
  after defining it. Preserve exact existing code identifiers and contract
  fields rather than renaming them through prose.
- Preserve the full phrase "discrete cognitive or act step Loop node" and its
  complete behavioral explanation. Do not shorten the phrase, remove "node,"
  substitute an acronym, or replace the explanation with a label. Read
  [the complete explanation and session handoff](docs/context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md).
  This describes an executable graph vertex implemented by the canonical
  `Loop`; it does not introduce a runtime class, role, or mode. Exact existing
  code identifiers remain unchanged.
- Preserve the complete initial configuration and ordered fallback priorities
  for each dimension in
  [the configuration dimension requirement](docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md).
  Read it before changing configuration, selection, recovery, or experiment
  coverage. Do not reduce the requirement to harness and model choice or
  mistake a documented requirement for implemented and qualified behavior.
  The recorded dimensions are a required baseline, not an exhaustive list or
  a maximum. Actively identify additional dimensions, refinements, and
  interactions. Map each proposal to an existing owning boundary, state its
  initial and fallback choices, and define a discriminating test. Keep
  proposals distinct from approved contracts and qualified implementations.
- Follow the [flexible cognitive and action composition direction](docs/architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md)
  and [configuration grid search guide](docs/guides/configuration-grid-search-and-optimization.md)
  when extending behavior or designing comparisons. Support additional steps,
  prompts, questions, intelligence, actions, and resource combinations as well
  as compact procedures. Do not make minimal step count, prompt count, context,
  or model use the universal objective. Preserve supported alternatives and
  test both additions and removals. Artificial general intelligence is a
  research ambition, not a new runtime, role, mode, or achieved capability claim.
- Consider [layered harness wrappers and native control](docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
  as independent configuration dimensions. Wrapper depth and order need not be
  fixed. Resolve ownership of each native control, initial choices, and
  fallback priorities explicitly. Wrappers remain internal mechanics unless
  their work needs a separately governed canonical Loop. Native controls
  never grant broader authority or replace independent task acceptance.
  An outer Loop Engine Loop may govern a native harness's inner loop. Keep
  cumulative authority, retry ownership, cancellation, and independent
  acceptance explicit across both. Read `ASTRA.md` for the advisory criteria.
- Use plain English suitable for a reader using English as a second language.
- Start at the highest level and move toward details.
- Use direct statements, useful examples, and ordinary names.
- Avoid hype, AI slang, em dashes, en dashes, decorative slogans, and vague
  evidence metaphors.
- In public documents, prefer report, record, log, contract, event history, or
  evidence when that word is accurate.
- Keep current behavior separate from planned behavior.
- Do not publish benchmark or provider claims that exceed saved evidence.

## Semantic integration from Taedri

Port an idea from `/home/username/taedri.dev` only when it fills a verified
Loop Engine gap.

For each proposed port:

1. State the invariant in plain language.
2. Map it to an existing Loop Engine component and public term.
3. Check that no equivalent contract already exists.
4. Implement the smallest typed extension at the authoritative boundary.
5. Add positive, negative, ambiguous, adversarial, and unrelated tests when
   the risk warrants them.
6. Record provenance and the exact source revision used for design input.
7. Verify the integrated behavior through Loop Engine, not through a copied
   Taedri test harness.

Do not import Taedri-specific authority levels, campaign paths, business
claims, internal identifiers, or legacy terminology merely because they exist.
The reference-source map is in `docs/context/REFERENCE-SOURCES.md`.

## Persistent general solving

The owner's September 14 direction is recorded as proposed invariants in the
[Constitution](docs/architecture/CONSTITUTION.md#proposed-invariants-from-owner-direction)
and designed in the
[persistent general solving decision record](docs/architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md).
Apply it to engine behavior and to your own development work:

- Build general mechanisms. Do not add control flow, prompts, or checks
  written for one task, dataset, or benchmark.
- Persist within declared authority. Turn a failure into a typed next action.
  End only for a verified result, exhausted declared authority, a question
  that only the owner can answer, a cancellation, or a provider outage
  recorded for resumption, and record which one.
- When a check fails, first decide whether the work, the check, or the
  environment is wrong, and record why. Do not weaken a check to make it
  pass. A revised check must still reject a known-wrong answer.
- Never let a review waive a permission, secret, network, spending, sandbox,
  or external effect contract.
- Treat a tool written during a run as a candidate until a different process
  qualifies it.
- Never end work on a fixed attempt count. When the same failure repeats,
  change the approach: quote the failure, narrow the request to the failing
  part, try another registered method, or carry the best result forward as
  provisional with its findings recorded.
- Work like a person with one project folder. The proposed task working
  folder gathers supplied files, unpacked archives, downloads, generated
  work, and outputs, persists across attempts, and is shared with Spawned
  Loops through scoped views. Its first parts are implemented: supplied
  archives are unpacked into a materials folder that the source inventory
  walks, supplied binary files can be selected for a project's inputs, and
  new task database campaign spaces supply every attachment as a source
  file. Downloads kept as files and scoped views for Spawned Loops are not
  implemented yet.
- Run live experiments only under explicit owner authority. Record every
  trial, including failures and outages, keep runners waiting through a
  provider outage within a declared wait, and stop before an allowance is
  drained.
- Before committing, run the continuous integration commands on an export of
  the exact tree, lint the full documentation scope, and confirm with mutants
  that each new check fails when its behavior is removed.

## Verification and completion

Run the smallest relevant check first, then the owning component checks,
self-test, conformance, clean installation, examples, and browser or playback
checks when the claim depends on them.

Do not report completion from intent, file presence, narrow tests, or an
unverified diagram. Completion requires current evidence for every requested
behavior and no known required work left.
