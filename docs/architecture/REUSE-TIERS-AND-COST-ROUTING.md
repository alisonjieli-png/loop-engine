# Reuse tiers, cost routing, and memory forms

Status: recorded on September 16, 2026, extending the tiered fingerprint work
in this document. The owner's direction: more tiers for input and output
differences, suggested output formats, reuse and reuse-then-modify rather
than token spend on every atomic step, multiple locality sensitive hashing blocks, hybrid retrieval,
and micro models for search, with embeddings and low rank adaptation adapters as memory.
None of this grants authority. Existing boundaries own every mechanism; the
gaps below name what does not exist yet.

## The economics the direction is right about

Most procedural work is retrieval plus small deltas, not generation. A
fingerprinted component instance that ran once costs one lookup on the
second run instead of tokens. The measured stub corpus already shows the
shape: component drafts cost roughly 300 to 700 output tokens each, and a
data_loader drafted seven times across runs is the same component seven
times. The 99 percent that fits a qualified table should ship through the
table. What the table must never do is silently serve the one percent that
only looks like a match: the recorded admission ladder (exact plus
qualified admits; near suggests only) is the guard, and the escalation
judge below is the gap that makes the guard cheap.

## Input and output tiers

Fingerprinting currently covers the invocation side. The direction asks for
tiering on both sides of a step, which decomposes into existing records:

| Tier axis | What it compares | Existing record |
|---|---|---|
| Input identity | Exact invocation fingerprint | Implemented in the stub tiered index |
| Input family | Similarity on the declared projection, locality sensitive hashing blocks | Implemented: the engine's lsh64 signature plus hybrid rank |
| Output identity | Exact artifact digest | Implemented: digests on every artifact and expected artifact |
| Output format | The response contract shape, not the bytes | Implemented as the typed output contract; not yet a comparable format tier |
| Output delta | Reuse-then-modify distance: how much of a prior output survives | Gap, see below |

An output-format tier suggests the response shape a prior, structurally
similar step used, so a new instance can be prompted for the same shape
without generating one. It records a suggestion, never a constraint: the
response contract of the current assignment always wins, and the suggestion
carries its source fingerprint so a mismatch is attributable.

Suggested output formats ride the same machinery as suggested components:
the near tier returns the prior step's response contract alongside its
draft, and the assembling layer may reuse the contract only after checking
it satisfies the current assignment's declared obligations. Format
suggestion is a context packet component, subject to the same justified
resource record.

## Reuse, reuse-then-modify, and the cost ladder

Three reuse depths, with distinct admission and accounting:

1. **Exact reuse.** Invocation fingerprint matches and the component is
   qualified: serve the retained artifact. Zero model calls. The flywheel
   already owns this relation.
2. **Reuse-then-modify.** A near-tier match provides the prior draft and its
   declared delta: the new instance receives the prior draft as a cited
   reference, produces a patch-shaped output against it, and is charged only
   for the delta. The patch applies through the existing repair machinery:
   repair creates a new candidate version, so the modified draft is a new
   fingerprint, never a silent mutation. Gap: no measured bound on what
   fraction of a draft may be reused as modification input before the new
   instance must draft from scratch; until measured, a reused reference
   carries the same response contract weight as a fresh prompt.
3. **Draft fresh.** No qualified or near match: the full instance cost.
   Recorded as the cache miss it is, so the table's hit rate is measurable.

The cost ladder for one component family, coldest to warmest: fresh draft,
reuse-then-modify, exact reuse. The stub experiment measures each rung
already; what is missing is the policy that picks the rung and records why
(gap below).

## Micro models as the librarian layer

The direction's most correct point: small classifiers beat embeddings on
negation, ordinality, and sort direction, because cosine similarity eats
the difference between top and bottom. The retrieval stack already has the
slot for this: the hybrid engine's backends are pluggable, and a micro-model
router is an additional retrieval backend, not a new runtime.

Where a micro model earns its place:

- Intent decomposition before retrieval: operation, subject, quantifier, sort
  direction, count. Feeds the fingerprint lookup a structured query instead
  of raw text.
- Escalation judgment: given a near-tier match, decide reuse, modify, or
  fresh. This is the discriminative judge the thread describes, trained on
  engineered features (similarity score, family match, contract drift,
  prior outcome). Its output is a decision, never a generation.
- Output-format suggestion: predict the response contract shape from the
  operation family.

A micro model never answers open-domain questions and never admits. It
routes and judges; the hybrid engine retrieves; the admission ladder
decides; the qualified table serves. The micro-model router itself is
fingerprinted like any component instance, so a routing change is a
measurable configuration change.

## Memory forms

Embeddings and low rank adaptation adapters are memory materializations, not new
intelligence layers. The existing rule stands: source formats never define
layers. Mapping:

| Memory form | Owning boundary | State |
|---|---|---|
| Vector embeddings of component instances | The retrieval engine's vector backends (deterministic hash, model2vec, LanceDB) | Available; stub index uses it |
| locality sensitive hashing blocks | The engine's lsh64 signature on every hit | Available; multiple blocking keys would be a backend extension |
| low rank adaptation adapters as procedural memory | Gap. A qualified low rank adaptation would be a Code Intelligence asset with the same admission record: immutable source identity, provenance, license, version, typed contract, tests, independent verification, digest. Nothing in the repository trains or serves adapters today. | Recorded as the contract it must satisfy, not an implementation |
| Drift detection | Gap. The thread's own warning: a 2024 pattern matching a 2026 case deceptively. Validity conditions on retained results (the inter-step Rule 8) need periodic revalidation and invalidation on distribution shift. | Gap |

## Tool output and the CPU tax

The thread's diagnosis is correct and the boundaries already exist: bounded
tool output is enforced (`max_output_bytes` on every command), serialization
of a messy tool response into tokens is charged as real output, and the
400-page-PDF failure mode is refused upstream by the context budget and the
justified resource record. What the direction adds is worth keeping as a
provisioning rule: when a tool response exceeds the model-facing budget,
transform once into a digest-addressed artifact plus a bounded excerpt with
exact coverage statements, so repeated steps over the same material retrieve
the excerpt rather than re-serializing the buffer. This is the existing
context artifact compaction contract; the gap is only that component
instances in the stub do not yet route oversized tool output through it.

## The escalation judge and the one percent

The thread's pushback is recorded as a design requirement, not a rebuttal to
dismiss: the money is in the cases where the situation looks like X but is
not X, and a system trained on procedure-worked has no signal for
walk-away-from-the-procedure. The admission ladder's near tier never
admits, so a near miss always costs a fresh instance today. The escalation
judge closes that gap cheaply: a small discriminative model whose only job
is to flag that a near match should not become reuse-then-modify, before
the modified draft reaches assembly. Its failure modes are measured like any
component: false blocks and false admits both count, per the adaptable
policies direction's dual measurement rule.

## Gaps recorded, in priority order

1. **Reuse-rung policy.** A versioned policy field on the cell
   configuration that picks fresh, modify, or reuse from the tiered lookup
   result and records the choice and its reason per component. Smallest
   extension: a field on the stub cell plus the lookup result already
   returned.
2. **Escalation judge.** A micro-model (or calibrated feature classifier)
   over the lookup result's similarity, family, and contract-drift features,
   deciding reuse-then-modify versus fresh. Discriminating test: a seeded
   near-miss whose 30 percent difference is the operative fact must be
   judged fresh, and a true sibling must be judged modify.
3. **Output-format tier.** The response contract as a comparable tier in
   the index, suggesting formats through the near tier. Discriminating
   test: a suggested format that fails the current assignment's obligations
   is refused and recorded.
4. **Multiple locality sensitive hashing blocking keys.** The engine's single lsh64 becomes a
   family of block signatures (projection, contract, cell) whose
   intersection orders candidates. Backend extension; no authority change.
5. **Validity windows and drift invalidation.** Retained results carry
   revalidation deadlines and distribution-shift triggers per inter-step
   Rule 8. Discriminating test: a dependency change invalidates the
   retained result the window names.
6. **low rank adaptation admission contract.** If adapter memory is ever implemented, the
   existing Code Intelligence admission record governs it unchanged. This
   is recorded so the option exists without implying work.

None of these is implemented by this document. Each maps to an existing
boundary, each carries a discriminating test, and the admission ladder and
flywheel remain the only reuse authorities.
