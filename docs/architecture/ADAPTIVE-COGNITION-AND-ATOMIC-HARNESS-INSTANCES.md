# Adaptive cognition and atomic harness instances

Status: design direction recorded on September 16, 2026, at the owner's
request. This document maps the requested behavior to existing typed
boundaries, names the genuine gaps, and records the smallest proposed
extensions. It does not enable anything, grant authority, create a runtime,
role, mode, or capability claim. Where a mechanism exists, this document says
which boundary owns it and what its current qualification state is. Where one
does not exist, this document says so.

Read with the [flexible cognitive and action composition
direction](FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md), the [open-ended
dimension inventory](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
and the [complete project synthesis](../COMPLETE-PROJECT-CONSTITUTION.md).

## The owner direction

Two related requests were made:

1. The system should support adaptive cognition: muscle memory, deterministic,
   hybrid, and non-deterministic methods, and intelligence the way a person
   works. A person given a task takes a number of conscious and subconscious
   steps and may research, reuse, rebuild, and orient.
2. Every harness instance should be as atomic and small as possible so that
   fingerprinting is easy: one fixed operation, on explicitly bound inputs,
   producing one primary result, returning control.

Neither request changes the one-runtime rule. Both are execution profiles and
learning targets on the existing Loop runtime, its roles, and its three
modes.

## What exists already

The requested mechanisms map to existing typed boundaries almost one to one.
This is the mapping, verified against source:

| Requested mechanism | Existing typed boundary | Qualification state |
|---|---|---|
| Situation representation (goal, assignment, plan, knowns, unknowns, assumptions, capabilities, dependencies, expected observations) | `TaskOrientationResult` in `core/adaptive_practitioner_records.py`: ultimate and immediate goal, current and desired state, inputs and outputs, knowns, unknowns, assumptions, ambiguities, delegated choices, blocking and research questions, subproblems, dependencies, verification obligations | Implemented, live-exercised in every model-led run |
| The distinction between execution mode and cognitive control | Execution mode is a Loop field: deterministic, hybrid, non-deterministic. Cognitive control is supervision: the escalation ladder, the action fence, stall detection, budget phases, and the fast-path allowance | Implemented; the distinction is already structural |
| Fast habit before deliberation | `allow_fast_path_resolution` on `AdaptivePractitionerRequest` and `SolveRequest`: registered exact resolvers run before the first model call; a completed verified fast path finishes with zero model calls; the undeclared default keeps the recorded policy | Implemented, offline-verified; live qualification pending |
| Procedural memory with applicability, recognition, parameters, interruption conditions, experience | `ProceduralMemoryRecord` in `memory/procedural/record.py`: applicability, trigger, preconditions, postconditions, contracts, required capabilities and permissions, allowed effects, rollback and retry behavior, idempotence, known limitations and failure modes, successful and failed episodes | Implemented as records; candidate-only until independently promoted |
| Evidence-backed procedural control, including deliberative fallback | `ProceduralControlAssessment` in `memory/procedural/control_assessment.py` with seven required probe kinds, including deliberative fallback and negative transfer | Implemented offline candidate assessment; live benefit unproven |
| Surprise detection, the signal that interrupts a routine | `detect_stall` in `core/adaptive_practitioner_supervision.py` (signal-only), the `ActionFencePolicy` and its ledger, and the identical-state-action-failure check | Implemented; the fence fires after two identical raised failures |
| Method selection based on the actual obstacle | The Practitioner's `decide_next` step with typed `NextActionDecision` candidates and the full action vocabulary (retrieve, recall, reuse, parameterize, mutate, compose, propose, build, generate, run, spawn, verify, repair, return, abstain, stop) | Implemented; the model selects, runtime validates |
| Advisory model ordering from experience | `ModelLadder` and `ModelLadderEvidencePolicy` in `core/model_demand.py` | Implemented as advisory only, per route, unknowns stay visible |
| Specialized reasoning and action step tools | The per-step layer catalogue in `core/opencode_step_layers.py` plus `core/step_content.json`: fourteen step layers, twenty-seven skills, each one named after its operation (check-assumption, falsify, hypothesise, measure, narrow-scope, recompute, reproduce, review-adversarially, source-ledger, and peers) | Implemented for the OpenCode realization; hand-written layers win over generated ones |
| Atomic single-operation verification | The independent verifier's criterion judgment: the task, one registered criterion, the inspected text, one model call, deterministic grounding of every quoted passage | Implemented, offline-verified; live qualification pending |
| Learning capture without self-promotion | `capture_recovery_learning` in `core/recovery_learning.py`: one scoped cognitive question, an unvalidated bundle, never added to active intelligence | Implemented, opt-in |
| Reuse of qualified work with zero model calls | The reusable capability flywheel: candidate, validated, registered, deprecated, quarantined, rejected, superseded, retired lifecycles; `CapabilityResolver`; deterministic exact reuse | Implemented offline vertical slice |
| Composition becoming a tool again | The Solution Canvas projects selected candidates into one authoritative graph; `ReactiveSeriesDefinition` keeps finite activations behind stable identities | Implemented |
| Episode, procedure, and control memory as separate kinds | Episodic, semantic, and procedural record classes with `MemoryLifecycle` transitions; rejected and tombstoned are terminal; producer cannot promote its own candidate | Implemented |

## The genuine gaps

These are the pieces the direction asks for that no typed boundary owns yet.
Each maps to an existing owning boundary for its smallest extension.

### Gap 1: cognitive control is not a declared dimension

Automatic, attended, and deliberative control exist as behaviors (the
fast-path allowance, the action fence, recovery panels, budget phases) but
not as a declared per-assignment control policy with initial choice and
ordered fallbacks. The configuration dimension requirement says every
dimension needs exactly that record.

Proposed smallest extension: add a cognitive-control entry to the dimension
inventory as a cross-cutting dimension related to run mode, model call
strategy, and supervision, with the existing mechanisms named as its
initial choices and its fallback ladder. A cognitive control field on
`SupervisionPolicy` (versioned, default preserving current behavior) would
carry the declared choice into runs. Discriminating test: a declared
deliberative-first policy must measurably differ from an automatic-first
policy on the same frozen cell population.

### Gap 2: no negative transfer record

The procedural control probes include negative transfer as evidence, but no
boundary records where a previously reliable procedure stopped applying and
why. Without negative knowledge, increasing reuse can repeat mistakes: a
learned routine applied to a superficially similar but incompatible task
fails the same way each time.

Proposed smallest extension: extend `ProceduralMemoryRecord` with a typed
inapplicability record (conditions that disqualify, evidence, source
episodes) alongside its applicability field, admitted through the existing
memory lifecycle. Discriminating test: a run offered a procedure whose
inapplicability record matches the current situation must not select it.

### Gap 3: no attention or salience policy

Every unusual event currently weighs the same. The direction asks for
attention sensitive to goal relevance, uncertainty, consequence, novelty,
and blockage, so that an irrelevant anomaly does not interrupt a routine
while an assumption-invalidation does.

Proposed smallest extension: this belongs to `detect_stall` and the action
fence, which already own interruption signals. A typed salience classification
on the stall signal (goal-relevant or not, consequence-bearing or not) would
let the recovery panel treat them differently without a new runtime.
Discriminating test: a harmless anomaly must not escalate while a changed
input that invalidates a plan assumption must.

### Gap 4: learned method selection has no measured shortcut

The direction's central learning target is choosing among research, reuse,
adaptation, construction, and delegation based on the actual obstacle, with
the choice itself improving from experience. Today the model re-derives that
choice each pass from candidates the runtime offers. Rational metareasoning
(choosing computations by expected decision contribution under cost) is not
owned by any boundary.

Proposed smallest extension: this is a Practitioner task through the existing
self-improvement profile and the stage-assistance evidence foundation. The
smallest step is an offline paired trial: one frozen cell population, one arm
with the current candidate offering, one arm with a learned method-selection
prior added to the packet, an independent evaluator, and the exact
denominators recorded. The grid search guide already supplies the protocol.

### Gap 5: invocation fingerprints are not assembled into one comparable record

Atomic instances need a fingerprint that answers which exact recorded
inputs, context, state, and realization were supplied. The pieces exist:
`SemanticStageFingerprint` digests semantic stages, the work packet names its
context, harness configurations are digest-pinned, run history carries exact
occurrence identities. No boundary assembles a per-invocation fingerprint
across all of them for similarity-based reuse.

Proposed smallest extension: a read-only projection in the stage evidence
foundation that assembles realization fingerprint plus input bindings plus
context packet digest into one invocation fingerprint record, without
granting any reuse authority. Similarity may suggest candidates; only an
exact qualified match executes deterministically. Discriminating test: two
invocations differing only in a consumed constraint must fingerprint
differently, and repeated trials must keep separate occurrence identities.

## What the direction explicitly does not ask for, and the repository would refuse

These are named so the record is complete and future sessions do not
implement them by accident:

- A second runtime, a Node class, or per-node agent classes. The one-runtime
  rule stands. Specialized steps are step layers, profiles, and passive
  contracts.
- Cached outputs from world-touching steps. The direction's own memoization
  framing says cache the resolved method, not the live artifact. The
  repository's rule is stronger and stands: a matching fingerprint is never
  permission to repeat an external effect, and stale artifacts are never
  silently re-served. Effects need their own authorization and
  duplicate-delivery protection regardless of any cache.
- Fuzzy equivalence for reuse preconditions. A step is reusable if it
  satisfies the contract exactly. Similarity gets a candidate; only an exact
  qualified match executes.
- A fifth intelligence layer. Muscle memory spans procedure representation,
  implementation, evidence, and learned selection inside the existing four
  layers and the memory kinds. Source formats and cognitive labels do not
  define new layers.
- Hidden scope expansion. An atom that finds missing information returns that
  finding; a separate instance retrieves and reassesses. Missing information
  never triggers an unrecorded expansion of the current assignment.
- An opaque multi-step run counted as an atom. Where a native harness cannot
  expose or restrict its autonomous substeps, the adapter is not eligible for
  the strict atomic profile; its per-step composition through the core and
  step layers is.

## The atomic execution profile

The owner's atomicity requirement is recorded as a strict execution profile
over the existing per-step composition, not a new mechanism:

- One fixed operation with one primary result, on explicitly bound inputs and
  the smallest sufficient context packet, selected before execution.
- One bounded attempt per activation. A repair is a new activation with its
  own effective configuration, not a hidden retry.
- Configuration fixed during the instance: instructions, model, tools, skills,
  wrappers, and generation settings, all resolved and fingerprinted, with no
  silent defaults.
- Return control after the result, including an explicit missing-information
  or failure status. Orientation, research, recovery, and improvement are
  compositions of small instances, not bundled capabilities inside each one.
- Independent assessability: an atom's output can be evaluated without
  judging the whole workflow, another realization can be tried against the
  same contract, and repeated attempts keep separate occurrence identities.

The existing step layers and the verifier's criterion judgment are the
reference examples of this profile. The strict_atomic granularity option on
solve requests and the core and step layer split in
`opencode_step_composition.py` are the existing surfaces that carry it.

## The evaluation the direction requires

The direction's own test is whether the system becomes measurably more
intelligent, not whether it describes itself better. A meaningful comparison
needs at least: an always-deliberative baseline, a fixed-procedure baseline,
and the adaptive system, on one frozen cell population, with controlled
removals of memory, interruption, and learned method selection, and an
independent evaluator. The measured questions:

- Transfer: does a learned procedure help on different instances rather than
  replay one case?
- Limit recognition: does the system avoid applying a familiar routine to a
  similar but incompatible task?
- Attention allocation: are important surprises investigated without
  interrupting routine operations?
- Recovery quality: is the failed part changed instead of rebuilding good
  work?
- Objective change: does the system stop using a shortcut when the desired
  outcome changes?
- Strategy selection: does experience improve the choice among research,
  reuse, adaptation, construction, and delegation?

No live experiment has measured any of these yet. Any experiment that does
must follow the benchmark evidence rules: frozen population, exact
denominators, recorded failures, complete token accounting, and independent
review before any claim.

## Relationship to the proposed invariants

This direction reinforces the existing proposed invariants rather than adding
new ones. Persistent general solving (LE-SOLVE-004) is the rule that turns a
failed attempt into a changed next attempt. The fast-path allowance is a
mechanism of the same family as LE-SOLVE-005's working folder: persist and
reuse what experience established, within declared authority. The atomic
profile serves LE-SOLVE-002 by keeping the runtime free of task-specific
control flow: general mechanisms at small, named boundaries. When a rule from
this document becomes important enough that violating it would break the
ontology, it enters the Architecture Constitution with an enforcement test
and a machine-readable entry first, then this document references it.

## The formal atomic provisioning profile

Status: recorded on September 16, 2026, as the formal specification of the
atomic execution profile named above. The generalized rule is: give each
harness instance one independently assessable operation, then supply the
smallest justified set of information, capabilities, and execution resources
needed to perform that operation correctly. Decomposition and provisioning
are two linked processes, and neither one model call nor one short prompt
establishes either property. These are proposed constraints on definitions,
step profiles, harness bindings, and qualification, not new runtime types.

### The twelve operating rules

Each rule names the existing boundary that enforces it, or records the gap.

| Rule | Required behavior | Existing enforcement or gap |
|---|---|---|
| 1. One responsibility | Name one coherent operation and its result; reject hidden bundles. | Step layers and the work directive's one-step objective enforce this for registered steps. |
| 2. Explicit scope | Identify the subjects, goal, conditions, and limits of the conclusion or effect. | The typed output contract and `TaskOrientationResult` carry scope. |
| 3. Complete prerequisites | Supply the information needed to interpret the inputs, not merely the inputs. | `runtime_facts` and the packet's verified problem state; interpretation dependencies are the packet assembler's duty. |
| 4. Justified resources | Every context item, tool, skill, and permission serves a named prerequisite. | Gap: no resource justification record exists. See gap 6 below. |
| 5. No ambient access | Do not inherit unrestricted history, filesystem, credentials, tools, or mutable state. | Structural per-step tool grants; write-capable tools including delegation tools denied on read-only steps. |
| 6. Fixed effective configuration | Bind actual instructions, resources, model settings, and environment before execution. | Digest-pinned harness bindings; resolved generation settings; the work packet's render digest. |
| 7. Explicit insufficiency | Missing information or capability produces a typed gap, not guessing or silent expansion. | `MaterialQuestion`, `CAPABILITY_GAP`, the verifier's unavailable report, and the resolution package's authority-required method. |
| 8. Separate proposal from effect | Deciding what should happen does not authorize or execute it. | Effect approval: one exact effect, durable one-use decision, refusal after replay or argument drift. |
| 9. Separate output from acceptance | Producing a result does not establish that it satisfies its contract. | Independent verification, the verifier role profile, and harness completion as a mechanical axis only. |
| 10. Preserve occurrence identity | Distinguish definition, request, semantic occurrence, physical attempts, output, evaluation. | `StageOccurrenceIdentity` separates activation, semantic call, and similarity; physical retries do not change the semantic occurrence. |
| 11. Test minimality | Resource removal must preserve required behavior across relevant tests, not one example. | Gap: no removal-testing boundary exists. See gap 7 below. |
| 12. Learn within an applicability region | Reuse a minimal configuration only where its assumptions and qualification remain applicable. | Procedural memory applicability and lifecycle; the flywheel's exact-match deterministic reuse. |

These rules constrain the harness assignment, not the owning Loop's
lifetime. The Loop can continue, obtain missing information, or use an
authorized alternative without enlarging the original operation invisibly.

### Variations are dimensions, not agent types

Semantic variations (what the step is asked to accomplish) and realization
variations (how it is performed) stay separate. Semantic dimensions include
operation family, subjects, relation or property, quantifier, scope,
conditions, evidence standard, and result type. Realization dimensions
include algorithm, reasoning method, mode, model, prompt bundle, tools,
context representation, environment, and allocation. Replacing a model must
not silently change the question being answered. The repository's semantic
runtime already separates the implementation-independent specification from
its realizations, and the existing mode vocabulary is unchanged.

Three superficially similar quantifier variations make the point: find one
counterexample, find every counterexample in a finite supplied set, and
establish whether any exists are different assignments, not phrasings of
one. Change one dimension when diagnosing; test combinations when
optimizing; never call a multi-dimensional improvement evidence that one
dimension caused the gain.

### The operation vocabulary

A starting vocabulary, not a universal set of indivisible thoughts. Reasoning
families: locate, extract, disambiguate, normalize, compare, apply a rule,
classify, derive, hypothesize, predict, assess evidence, select, identify a
gap, propose a revision. Action families: read, query, compute, measure,
modify, communicate, reconcile. Coordination uses the same discipline:
planning, supervision, and improvement decompose into operations such as
identify an unmet dependency, select an eligible next action, classify a
failure, choose a recovery method, propose a graph revision, evaluate a
candidate procedure. The mechanism that chooses the next atom is as
inspectable as the atom it chooses. The existing step layers
(check-assumption, falsify, hypothesise, measure, narrow-scope, recompute,
reproduce, review-adversarially, source-ledger, and peers) are the reference
implementations of this vocabulary for the OpenCode realization.

### Provisioning works backward from the required result

The central question is what this instance must know to produce and justify
this particular result, not what is generally relevant to the topic. Assemble
context by tracing prerequisites backward from the output contract. Include
interpretation dependencies: a numeric value needs its unit, denominator, and
measurement definition; a quoted sentence needs its referent and
qualifications; a previous result needs its provisional, rejected, or
accepted state and which version it concerns.

The two possible situations test discovers missing distinctions: if two
situations consistent with the supplied packet could require different
correct outputs, the packet is missing the distinction. The test is useful
for discovery, not a proof that nothing else is missing.

Preserve relevant parent constraints as a projection, not the whole
conversation. Preserve source coverage and uncertainty: not present in the
supplied excerpt must not become does not exist, and none found in the
searched collection must not become none exists anywhere. The existing
block sources in the work packet (authority and policy, objective and
success, hard constraints and tools, verified problem state, selected
evidence, attempt history) are the model-facing view; executor bindings and
controller records stay outside the model's view. The model does not see a
secret because an authorized executor needs one to authenticate.

### Authority is scoped, not counted

One unrestricted shell is not a smaller grant than three tightly scoped
tools. Each tool binding specifies operation, object scope, argument
restrictions, data extent, version conditions, effects, delegation reach,
and lifetime. Indirect access is checked: a read-only step set is not
read-only if a delegation tool can start a worker with write permissions,
which the write-capable tool list already denies structurally. The strict
profile defaults to no tools for reasoning over already supplied evidence.

### Insufficiency is a provisioning decision, not self-expansion

A bounded operation returns a typed gap: what is missing, why it is needed,
what the permitted current result is. The owning Loop then decides the next
authorized operation: retrieve, select another realization, request
authority, or preserve a provisional result. The request is data, not a
grant. The assembled effective request is re-fingerprinted after provisioning
changes; nothing is silently appended inside a bound instance. Failure causes
route differently: absent information provisions it, poor representation
changes representation, a failing method investigates the realization, an
unavailable executor restores or selects one, unavailable verification
repairs the verification path rather than rewriting a correct candidate, and
an uncertain external effect reconciles before any further mutation.

### Minimality is experimentally qualified, not promised

The smallest sufficient bundle is the smallest tested configuration that
satisfies the required correctness, completion, evidence, and safety
conditions for a declared task population and realization. Sufficiency is
established first against the original requirements, then removal is tested.
The qualification ladder: sufficient, single-removal tested, locally minimal
under those tests, group-removal tested, and globally minimum only for an
explicitly bounded search space with exhaustive or formal evidence. An
inconclusive removal test stays inconclusive. Two individually redundant
examples may be jointly necessary; representations may substitute; removal
may change ordering rather than content. Model-led operations use repeated
trials and report uncertainty. Mandatory protections, privacy constraints,
authority checks, protected instructions, and independent acceptance are
never pruning candidates. Minimize within the contract, never by weakening
it. The grid search guide supplies the experiment protocol for this testing.

### Computation is allocated separately from context and authority

A small operation may be difficult. Information, capability, computation,
and authority are separate budgets and are not inferred from one another. A
short output schema does not prove a small generation allowance suffices.
Source-backed provider capacity, the selected allowance, and total-run
authority remain separate, per the existing output-management contract.
Several useful configurations may exist: more context with less
computation, smaller context with stronger reasoning, or a deterministic
implementation. Minimality is a set of trade-offs, not one winning number.

### Additional gaps this profile records

Beyond the five gaps recorded above, the formal profile adds these:

### Gap 6: no resource justification record

Each included resource needs a compact justification: exact identity and
permitted extent, the named prerequisite it serves, how it is materialized,
its validity state, and what becomes unsupported without it. The
justification is a proposal for inspection and testing, not proof of
indispensability. Smallest extension: a typed record beside the work
packet's context blocks, validated with the packet and recorded in Run
History. Discriminating test: a packet whose justification names a
prerequisite absent from its contract is refused.

### Gap 7: no removal-testing boundary

The qualification ladder above needs an owner. Smallest extension: an
offline paired-trial mechanism in the configuration-search space that
removes one declared-optional resource from a qualified packet, re-fingers
the request, and compares results under the same evaluation.
Discriminating test: removing a resource the justification marks as
required must fail the gates, and removing one marked optional must be
recorded as a tested removal.

### Gap 8: semantic variation dimensions are not declared configuration

The quantifier, scope, evidence standard, and result type of an assignment
should be declared fields of the operation contract rather than implicit in
prompt prose. Smallest extension: typed optional fields on the step request,
validated by the response contract, defaulting to the current single
implicit interpretation. Discriminating test: two steps differing only in
declared quantifier must not be fingerprinted as the same assignment.

### The final acceptance test

Before calling a harness instance atomic and minimally provisioned, require
defensible answers to: what exact result is it responsible for; why can its
assignment not be usefully split further; what prerequisite justifies each
supplied resource; what prevents it from reaching undeclared resources; how
does it report insufficiency without guessing or expanding itself; what
evidence supports the sufficiency and minimality claims; and which changes
invalidate that evidence.

The principle in one sentence: minimize the responsibility until it is
independently meaningful, supply its complete justified dependencies, enforce
the narrowest authority that supports the work, freeze the effective
configuration, test both sufficiency and removal, and learn the resulting
applicability conditions.

## The inter-step rules: meaning, dependency, concurrency, and learning

Status: recorded on September 16, 2026, extending the formal profile above.
These twenty proposed rules govern what happens between atomic steps: how
meaning survives handoffs, how dependencies change results, how concurrent
work stays coherent, and how the system improves without corrupting its own
evidence. They are proposed constraints on definitions, connections,
scheduling, evaluation, and the intelligence lifecycle. Each rule names the
existing boundary that enforces it, or records a gap.

### Preserving meaning across decomposition

Rule 1, obligation coverage: every decomposition must preserve a mapping
from each original requirement to the work and evidence that will satisfy
it, held as a compact controller record rather than broadcast to every
harness. Some obligations belong to the composition and need their own
check. Existing enforcement: the independent probe plan already refuses
coverage that does not match the registered criteria exactly, and the
resolution package already assesses every registered method once. Gap: no
boundary carries an obligation-to-assignment map for decomposed
practitioner work generally. Test: remove one requirement from a proposed
decomposition; the system must detect the uncovered obligation before
claiming completion.

Rule 2, semantic compatibility: a connection must establish that the
producer's established output properties satisfy the consumer's actual
prerequisites, not just schema shape. An estimated date and a confirmed date
share a schema and are not interchangeable. Existing enforcement: Canvas
slots check type compatibility and connection compatibility; the contracts
index records full value schemas as a current limit. Gap: value schemas are
not enforced at every edge, which the contract index already states. Test:
supply a structurally valid result with the wrong unit, scope, or evidence
status; the connection must reject it or require an explicit adapter.

Rule 3, status preservation: information must not become more authoritative
by passing through more steps. An assumption does not become a fact because
another harness summarized it; three summaries of one document remain one
source, not three confirmations. Existing enforcement: the constitution
separates observed, inferred, assumed, missing, and disputed facts, and
orientation carries assumptions as a distinct field. Gap: no typed status
tag travels with values through composition generally. Test: pass a marked
hypothesis through several synthesis steps; it must remain conditional
unless qualifying evidence is added.

Rule 4, dependency recording: every important derived result should name
its premises and versions, so withdrawing one premise reconsiders affected
results without restarting everything. A lost premise makes a conclusion
unsupported, not automatically false. Existing enforcement: stage evidence
records already invalidate overlapping mutable addresses when lineage
changes, and configuration changes already invalidate previous
qualification. Gap: no truth-maintenance record connects an arbitrary
derived result to its supporting premises. Test: withdraw one assumption;
affected results lose support while independently supported results remain
available.

### Fingerprints that describe behavior

Rule 5, invariance and sensitivity: a behavioral fingerprint needs both
sides. Irrelevant perturbations, such as swapping two claims in a
contradiction check, should not change the substantive result; relevant
perturbations, such as changing a measurement's unit, must. A model that
ignores both is insensitive, not robust. Existing enforcement: mutants in
development discipline and the falsification history in benchmarks. Gap: no
general paired-perturbation probe set per operation family. Test: pair an
irrelevant with a relevant perturbation and require different responses.

Rule 6, fingerprint the context-selection procedure: two failures can look
identical when one is a selection omission and the other is a reasoning
failure. Record the selection identity, source scope, and transformation
applied, alongside the solver identity. Existing enforcement: the work
packet records selected intelligence and memory references. Gap: the
selection procedure itself is not fingerprinted as a separate dimension.
Test: hold the solver constant and vary the assembler, then the reverse.

Rule 7, hidden-state isolation testing: a manifest claiming five inputs does
not prove the implementation consults nothing else. Run the same intended
request in a clean worker, after an unrelated task, after conflicting
instructions, and with unrelated local files changed. Existing enforcement:
per-step composition writes a fresh instance directory and denies ambient
access structurally. Gap: no isolation probe requirement in qualification.
Test: seed a distinctive irrelevant instruction in prior worker state and
verify it does not appear in the next assignment's output. This establishes
which observable isolation properties were tested, never the absence of
every hidden dependency inside a hosted provider.

Rule 8, cache eligibility: three different decisions need separation:
reusing a retained result, reusing a procedure on new inputs, and repeating
an external action. Reusable results need explicit validity conditions:
source versions, relevant state, freshness, objective, and authorization
scope. A similarity signature suggests what to inspect; it never
authorizes. Existing enforcement: the flywheel requires exact eligible
matches for deterministic reuse; effects require their own authorization
regardless of any match. Gap: validity conditions on retained results are
not a typed field. Test: change a dependency that matters while holding the
visible request constant; the cached result must become ineligible.

### Concurrent execution coherence

Rule 9, temporal coherence: several correct reads can describe a state that
never existed. Each composition must declare what temporal consistency it
needs: an exact shared revision, a stated interval, or independently dated
observations. Existing enforcement: staged execution rechecks scoped
workspaces before execution and stage evidence binds exact occurrence
references. Gap: no declared snapshot requirement on multi-source reads.
Test: change a source between reads; the system must obtain a compatible
snapshot, detect the mismatch, or preserve the inconsistency explicitly.

Rule 10, effect footprint: an action contract should declare what it may
read, what it may change, and what it must leave unchanged, including
indirect dependencies through shared artifacts. Existing enforcement:
EffectSpec binds one exact effect and its parameters; generated projects
declare expected artifacts and refuse undeclared writes. Gap: a read and
preserve declaration is not part of the action contract. Test: introduce an
unrelated valid artifact before execution; the action must neither change
nor incorporate it unless permitted.

Rule 11, join semantics: every join must declare what counts as enough:
all named results, the first acceptable candidate, an exact version, or a
specified combination. No result yet, producer completed without a result,
and producer unavailable are distinct states. Existing enforcement: the
wave executor admits safe ready tasks per dependency wave; reactive joins
happen through portfolio policies. Gap: no explicit join-condition type on
composition edges. Test: deliver a duplicate, an outdated version, and a
failure; none may accidentally satisfy the wrong join condition.

Rule 12, concurrency at the owning boundary: admission rate, shared
accounting, cancellation propagation, and retry ownership belong to the
owning execution policy, not to each instance. Producers should not create
work faster than consumers process it. Local retry limits route the owning
Loop to its next permitted path rather than redefining the task impossible.
Existing enforcement: budgets, the shared session accounting, one bounded
attempt per activation, and the escalation ladder. Gap: no declared
backpressure policy between compositions. Test: slow a downstream operation
and fail a provider temporarily; queues, attempts, and resource consumption
must stay within declared policy.

### Choosing and repairing work

Rule 13, named uncertainty: every investigative step should name the
decision it could change. Existing enforcement: orientation carries
research questions and blocking questions as distinct fields. Test: an
investigation with no connection to a goal, uncertainty, or declared
exploration objective is refused admission.

Rule 14, repetition with a reason: repeating a stochastic trial to measure
reliability differs from repeating a failed semantic request without
learning. Method switching needs a material trigger, not a score
fluctuation. Existing enforcement: the identical-failure fence, the
escalation ladder, and the persistent-solving rule to change the approach
when the same failure repeats. Test: present the same unresolved failure
repeatedly; the engine must recognize the unchanged condition and choose a
permitted diagnostic, adaptation, wait, or escalation.

Rule 15, repair the responsible dependency: the last visible output is not
necessarily the cause. A repair proposal names its suspected target and the
observation that would distinguish that diagnosis from alternatives.
Existing enforcement: the failure review classifies correct failures, wrong
expectations, over-strict checks, environment defects, and ambiguity before
repair; the verifier-unavailable path restores evaluation rather than
rewriting the candidate. Test: make the evaluator unavailable with a valid
candidate unchanged; the engine must attempt to restore evaluation first.

Rule 16, conditional expertise: a procedure excellent for one input family
can be unreliable for a similar one, so retain applicability regions,
exclusions, alternatives, and selection evidence. Existing enforcement:
procedural memory applicability, negative transfer probes, and lifecycle
promotion. Gap recorded above as the negative transfer record. Test: change
the goal or input family while preserving superficial similarity; the old
procedure must be reconsidered.

### Improvement claims that resist accidental faking

Rule 17, optimize the composition: a smaller packet that raises retrieval,
repair, or verification cost downstream is not an improvement. Compare
provisioning, execution, coordination, verification, recovery, and the
retained usable result together, keeping local and end-to-end measurements
separate. Existing enforcement: the grid search guide's task-level
evaluation and the refusal to make minimal steps the universal objective.
Test: compare a candidate configuration inside its real composition, not as
an isolated prompt.

Rule 18, three-way evaluation: each operation needs a valid case that
passes, a near-miss that fails for a specific reason, and an
underdetermined case that stays unresolved. A verifier that rejects
everything is not task execution; one that accepts every well-formed
response is not verification. Existing enforcement: mutation discipline in
development, the verifier's refusal classes, and honest-unknown
accounting. Test: remove the enforced behavior and the check must fail;
supply a valid alternative formulation and the check must not depend on one
wording.

Rule 19, evaluation provenance: split evaluation populations by lineage,
not only row number. Protected answers, stored failure reports, generated
skills, and near-duplicate tasks can leak evaluation information into
learning. Existing enforcement: sealed final evaluation cannot guide search
in the configuration space; candidate content never self-promotes. Gap:
indirect memory and context paths into learning are not traced by lineage.
Test: seed a protected answer fragment and trace whether it can enter a
candidate's supplied resources.

Rule 20, requalification scope: every learned change states where previous
qualification no longer applies: affected contracts, input regions,
dependencies, probes, and downstream compositions. For changes to the
improver itself, assess whether it produces better successors on separate
tasks, not whether its self-description improved. Existing enforcement:
interpreter profile changes require independent regression qualification and
roll back on failure; changed values invalidate configuration
qualification. Gap: no general requalification scope attached to arbitrary
learned changes. Test: change a dependency a qualified procedure uses; its
qualification is no longer current until the required checks pass.

### Where the rules are enforced

Enforcement belongs at existing boundaries, never in the model's prompt as
policy reading: definition and graph admission own coverage, compatible
contracts, join conditions, and permitted effects; context assembly owns
selection, provenance, interpretation dependencies, and protected-data
exclusion; harness binding owns configuration, scoped resources, isolation,
and attempt records; scheduling owns concurrency, cancellation, version
coherence, and invalidation; evaluation owns behavioral relations,
near-misses, controls, uncertainty, and mutation tests; the intelligence
lifecycle owns applicability, lineage, qualification, promotion, and
requalification scope. The model-facing packet carries only what its
operation needs.

The five additions to prioritize first are semantic handoff checks between
producer properties and consumer prerequisites, dependency-based
invalidation records, paired invariance-and-sensitivity probes, hidden-state
isolation tests in qualification, and provenance-separated evaluation
lineage. Together they make small harness instances easier to fingerprint
and make those fingerprints useful for diagnosis and learning.

## Tiered fingerprints: exact identity and similarity suggestion

Status: implemented as experiment-local plumbing in the stub experiment
(`.loop-engine-dev/stub-experiments-20260916/atomic-kaggle-pipeline/tiered_fingerprints.py`),
over the existing hybrid retrieval engine, with a self-test of eight checks.
Not a product boundary; the relation it enforces is the one the reusable
capability flywheel already owns.

Exact fingerprints establish identity; similarity fingerprints suggest
candidates. The two never share authority. The admission ladder:

- **Exact tier.** An invocation fingerprint match identifies the same
  recorded setup. Combined with a qualified component, it admits reuse.
  Exact without qualification names a reference and still starts a new
  instance.
- **Near tier.** The hybrid engine (FTS5 lexical plus deterministic hash
  vectors, with the engine's own locality sensitive hashing signature on every hit) ranks the
  record first for a reworded same-family query, and the query and record
  share declared-projection tokens. Near suggests what a new instance may
  compare against. It never admits.
- **Unrelated tier.** No shared tokens: visible, ranked, never admitted.
  Rank alone never promotes a record the projection says shares no tokens
  with the query, because the FTS5 OR-match can rank a zero-overlap row
  when the query tokenizes poorly.

The similarity projection uses declared fields only: subject, component id,
purpose, contract, and cell dimensions. Private prompt bytes never enter the
index. The measured result on the harvested stub corpus of thirty-six
component instances: a reworded loader query reaches the near tier through
the engine's rank one; a training query reaches its own family; an unrelated
query stays unrelated; and the admission ladder keeps unqualified matches
honest.

The product-owned home for this relation, when the stub experiment graduates,
is the existing flywheel: similarity proposes, exact qualification admits.
The stub's contribution is the measured corpus and the threshold behavior,
not a new authority.
