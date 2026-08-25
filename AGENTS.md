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
2. `docs/contracts/README.md`
3. `docs/components/README.md`
4. the relevant component README
5. `humanizer-context.md` for public prose
6. `docs/context/CODEX-START-HERE.md` after a new or compacted session
7. `docs/context/REFERENCE-SOURCES.md` before consulting an older repository

Treat existing changes as user or concurrent-agent work. Do not discard,
restore, reformat, commit, or publish changes without resolving ownership.

## One Loop runtime

Every executable graph vertex is a Loop. Do not create another operational
runtime type.

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
`static_architecture.boundary_registry` with runtime type `Loop` and either an
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
executor may support a subset. The current in-process Solution runner supports
deterministic Solution Loops only. Thinking power and model routing apply only
when a hybrid or non-deterministic Loop is authorized to call a model. They are
not additional run modes.

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

## Models and providers

- Use real configured providers for provider integration and performance
  claims. A stub or injected transport may test a local contract, but it does
  not prove provider integration or model quality.
- Never silently replace a failed model call with canned or synthetic output.
- Request the exact provider-supported maximum output for the selected model.
  Do not invent a smaller default. If the maximum cannot be established from
  a source-backed capability record or provider response, fail with an
  explicit unknown state.
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

## Verification and completion

Run the smallest relevant check first, then the owning component checks,
self-test, conformance, clean installation, examples, and browser or playback
checks when the claim depends on them.

Do not report completion from intent, file presence, narrow tests, or an
unverified diagram. Completion requires current evidence for every requested
behavior and no known required work left.
