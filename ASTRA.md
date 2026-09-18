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

## September 14 best-available resolution requirement

Owner requirement: a missing task file, unavailable component, unanswered
question, or other task-level constraint must not produce an empty blocked
result. The Practitioner should do what a capable person can still do. It
should analyze available material, state what can and cannot be completed,
map missing pieces, make labeled assumptions, prepare scenario or pro forma
analysis, use clearly labeled synthetic examples where useful, give estimates
with uncertainty, examine similar or analogous solutions, derive a
first-principles approach, and prepare supplemental artifacts and next steps.

Current implementation after this requirement:

```text
Public solve projection
├── Verified requested outcome
│   └── COMPLETED_VERIFIED
├── Unverified task-level outcome
│   └── COMPLETED_PARTIAL plus task_resolution_package/v1
└── Operational interruption
    ├── provider terminal with accumulated work preserved
    └── cancellation terminal with no invented continuation
```

The resolution package is a completed response, not acceptance of the
original requested outcome. It preserves observed evidence, model analysis,
assumptions, provisional file bodies, missing or unverified material,
alternatives, questions, and next actions. The model-facing runtime policy and
question portfolio require the broader methods above before a non-safety
stop. Current checks establish the contract and local projection. They do not
prove that every model will use every method well on every task.

An absent permission or approval still cannot be invented. The Practitioner
must complete preparatory work that does not require the effect, then state
the exact remaining authority. Only a question bound to a typed user
clarification may be presented to the owner. The runtime must answer its own
capability and workspace questions.

## September 14 action-vector continuation requirement

Owner requirement: the system must distinguish a successful language model
response from the quality of the observable work process and from satisfaction
of the requested output. Every cognitive step and action needs its own vector
of intended and observed direction. The Practitioner should use those vectors
to continue, improve, adjust, reframe, retrieve, repair, or compare another
approach instead of treating response completion as a reason to stop.

This requirement applies to the custom Practitioner and to Practitioner work
realized through registered harnesses such as OpenCode, Codex, and Pi. The
owning Loop retains the task, vector policy, continuation decision, effects,
accounting, and acceptance. A native harness completion event remains an
observation and cannot accept the task or grade its own result.

Current implementation after this requirement:

```text
One selected action
├── action_intent_vector/v1
│   └── direction, expected delta, check, fallback, and decision coordinates
├── action_vector_assessment/v1
│   └── observable process, output, progress, and continuation checks
├── outcome_vector/v2
│   └── tri-valued signals with unknown kept distinct from false
└── route guard
    ├── continue or adjust while safe authorized work remains
    └── stop only after continuation is resolved or a hard boundary applies
```

The process check observes typed decisions, plans, selected evidence,
assumption labels, capability execution, artifacts, and verification. It does
not request or persist private model reasoning. The custom and external
harness paths receive the same policy through the canonical semantic packet.
The external harness result records only mechanical execution before the
owning Loop performs semantic and task checks.

Current offline checks exercise the vector contract, exact selected-action
lineage, stop-route guard, core cognitive-stage projections, custom and named
harness boundaries, and source-incomplete task intake. They do not establish
that every live model will make a good process assessment or that OpenCode,
Codex, and Pi native-control profiles are all installed and qualified.

## Direction to preserve

The owner clarified the scale requirement after asking about Hyperlambda:
the entire task catalog stays in scope for admission, with no fixed
100-task sample limit. Configuration spaces may contain billions of possible
solutions. Grid, Bayesian, genetic, covariance-adaptation, vector-based, and
future methods should help choose which configuration to try next and which
configurations suit particular tasks. The search method and its settings
are themselves configuration choices, not one permanent optimizer.

Preserve separate counts for represented, applicable, proposed, dispatched,
evaluated, independently verified, and promoted work. Exhaustive traversal
of a declared finite grid remains an option; adaptive search must not be
reported as exhaustive coverage. Complete reports need exact links among
the task, configuration, action occurrences, physical model calls, code,
Solution Canvas, outputs, and independent evaluation. A displayed Canvas
without executable artifacts and a successful fresh-input run is incomplete.

The [generation component](src/loop_engine/generation/README.md) describes the
current proposal interfaces. The [Hyperlambda and wide-search review](docs/research/HYPERLAMBDA-AND-WIDE-SEARCH-2026-09-13.md)
separates external design ideas from local implementation and qualification.
The [run-path and dimension coverage map](docs/verification/RUN-PATH-AND-DIMENSION-COVERAGE-2026-09-13.md)
lists executable, proposal-only, and unqualified paths, with all baseline
dimensions and a rule for individual, fallback, interaction, and sequence
coverage. Its inventory checks must not be reported as behavioral coverage.

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

## Meta-selectors and configuration setters

The current provider direction is Ollama Cloud after the owner's estimated
quota-reset window, through the existing shared gateway. Restoring Tactical
is not required. The stopped Tactical monitor, its task queue, and its failed
run evidence are retained. Do not infer readiness from a model listing.

The [experiment-driven self-improvement guide](docs/guides/experiment-driven-self-improvement.md)
records the owner's request to use this machinery for broader solution
experiments and recursive self-improvement. Keep candidate generation,
controlled execution, independent evaluation, acceptance, and promotion
separate. A producer may stage a change, not approve it.

Before expansion, check actual terminal provider codes and effective settings.
Do not learn successful work from a failed model invocation, count repeated
events as independent runs, delete referenced history, or treat a crash marker
as proof that external effects are reconciled. The current evidence-summary
helper is a gap inventory, not an independent acceptance authority.

The [Ollama and self-improvement preparation report](docs/verification/OLLAMA-AND-SELF-IMPROVEMENT-PREPARATION-2026-09-13.md)
records the corrected history interpretation, provider-failure handling,
activation controls, and isolated verification. A primary Ollama worker is
time-gated; the other prepared model routes are not launched. This is not a
claim that the full task population or the complete improvement cycle works.

The owner asked whether different meta-selectors or agents could choose the
best configurations and grid parameters. Treat model preference engines,
harness preference engines, selector portfolios, and the method that selects
those engines as configurable choices. Give each an initial choice and
ordered fallback priorities. Preserve abstention when the evidence is missing
or incompatible; do not imply a universal best configuration.

The [configuration preference guide](docs/guides/configuration-preferences-and-meta-selection.md)
separates the implemented in-memory setter and advisory preference interface
from proposed autonomous selector portfolios. It also records additional
dimensions for support discovery, change phases, deployment, objective
tradeoffs, feature representations, effective-setting confirmation, and
independent requalification. The inventory remains open.

Review the integration in this order: existing eligibility checks, exact
candidate and engine identities, meta-selector recommendation, parameter
precedence, authorized application, invocation-time revalidation, and
independent evaluation. An unsupported choice cannot become eligible because
a model recommends it. A supplied agent proposal does not prove that a model
call occurred. A selector's own favorable score cannot approve the selector.

Compare selector methods as well as the configurations they propose. Retain
proposal overhead, failed selectors, fallback transitions, and evaluation
partitions. Model-led joint configuration, Bayesian search, evolutionary
search, vector-based transfer, and future methods can be composed when their
contracts and authority permit. The current component checks do not qualify
an autonomous live portfolio or automatic joint model and harness selection.

The [September 13 preference verification report](docs/verification/CONFIGURATION-PREFERENCES-AND-META-SELECTION-2026-09-13.md)
records the offline source and clean-installation checks, six search-method
composition controls, the failed vector fixture, and the remaining live gaps.

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

Advisory comment. The owner's September 16 direction asks for adaptive
cognition: learned procedural control that executes familiar work fluently
and reopens deliberation when circumstances change, and atomic harness
instances small enough to fingerprint. Almost every named mechanism maps to
an existing typed boundary, recorded with its qualification state in
[the adaptive cognition direction](docs/architecture/ADAPTIVE-COGNITION-AND-ATOMIC-HARNESS-INSTANCES.md).
The genuine gaps are a declared cognitive-control dimension, a negative
transfer record, an attention or salience classification on interruption
signals, a measured method-selection prior, and an assembled per-invocation
fingerprint. None is implemented. Any experiment that measures them follows
the benchmark evidence rules with a frozen population, exact denominators,
recorded failures, and independent review before any claim.

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

The owner subsequently requested resolution of all experiment-readiness
issues and described the direction as an AGI fabric. Treat that as a research
and engineering requirement, not as proof of general intelligence. Use the
[September 14 readiness checklist](docs/verification/EXPERIMENT-FABRIC-READINESS-2026-09-14.md)
for source freezing, exact invocation accounting, independent evaluation,
adaptive selection, recovery, and large-population reporting. Keep the
full configuration inventory extensible. Do not infer readiness from a
large address space, a diagram, a registered adapter, or a successful probe.

The original delayed Ollama worker was stopped before its first task.
Replacement workers later made real Ollama calls. The September 14 readiness
report records their cancellation and provider-allowance failures. Preserve
their queues, interrupted occurrences, and records.
Verify the current task-database location and launch record before claiming
that a replacement is running. Do not restart an old frozen manifest by
silently accepting changed code or changed source paths.

The owner's subsequent direction includes system-level recursive improvement,
the four intelligence layers, and comparison with Discovery Loop. Read
[recurrent models and system-level improvement](docs/research/RECURRENT-MODELS-AND-SYSTEM-IMPROVEMENT-2026-09-14.md)
for the research, architectural placement, additional experiment dimensions,
and proof sequence. Read the
[Discovery Loop comparison](docs/research/DISCOVERY-LOOP-COMPARISON-2026-09-14.md)
for primary sources and the distinction between similar research aims and
demonstrated comparative performance.

These are research and review inputs. They do not create runtime types,
activate imported intelligence, enable undisclosed model controls, or approve
the system's own improvements. Preserve task-local repair, reusable
cross-task improvement, and improvement of the discovery process as separate
claims. Automated evaluation feedback belongs in experimental history, not
in User Feedback Intelligence disguised as a human instruction.

Resolved cross-session review finding, September 14: the full offline
suite failed `wrong_frozen_source_state_is_refused_before_execution` while
the staged supervision change was being edited. In that staged version,
`effective_supervision` and `supervision_policy_record` were inserted before
the end of `AdaptivePractitionerRequest.__post_init__`. The remaining source
reference and frozen-state validation became unreachable after a method's
return. The owning session restored the validation before committing
`ba05d472c248d56689d008a88719a16938ea0d9e`. The source-state negative test and
the other 19 solve-adaptation checks passed after that commit. The preserved
failed suite describes the earlier staged version, not the corrected source.

The owner also requested research and experiments on fixed-weight harness
optimization, including the reported $49.97 OpenCode search. The
[fixed-weight harness section](docs/research/RECURRENT-MODELS-AND-SYSTEM-IMPROVEMENT-2026-09-14.md#fixed-weight-harness-optimization)
records the supplied claims, unresolved source details, primary research,
and concrete treatments for verification before completion, continued work,
and malformed tool-call repair. Continue research without waiting for the
owner to locate sources. Never turn these treatments into mandatory behavior
for every task or confuse additional sampling with reusable improvement.

Implemented controls in this iteration: declared call and pass ceilings reach
campaign execution and can be independent configuration axes; frozen spaces
are read as records rather than rebuilt from defaults; integer-range report
axes preserve cardinality without allocating every possible level. These
changes permit wider controlled experiments. They do not prove that the
full grid was run or that an adaptive selector is independently qualified.

[CLAUDE.md](CLAUDE.md) imports the shared repository rules and this note for
Claude Code. [Harness development instructions](embodiments/AGENTS.md) and
[development-tool instructions](devtools/AGENTS.md) provide narrower guidance
for those directories. Their local `CLAUDE.md` files import the corresponding
`AGENTS.md` files.

Read the [harness guide](embodiments/HARNESS-GUIDE.md) and
[session orientation](docs/context/CODEX-START-HERE.md) for current source and
evidence pointers. These instruction files do not change executable harness
manifests, launch flags, or native-control settings.

## Persistent general solving, September 14

Owner requirement. The owner asked for generalized solving in which every
applicable approach is tried, the work is highly persistent, and the system
does not give up. The owner asked for a general cognitive and action
Practitioner Loop that thinks, acts, and writes tools as needed, not one-off
solutions. When any check fails, a waterfall of reviews should ask whether the
test is the problem, whether it is too arbitrary, or whether other edits are
needed, across every aspect of the work. Every contract should be
deterministic, hybrid, or model-reasoned, so that a failed contract can be
asked whether it was supposed to fail or failed unreasonably. These rules
belong in the Constitution and the governing Markdown files.

Proposal. The
[persistent general solving decision record](docs/architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md)
and the
[proposed invariants in the Constitution](docs/architecture/CONSTITUTION.md#proposed-invariants-from-owner-direction)
place these directions in existing boundaries. Persistence stays within
declared authority. A review cannot waive a permission, secret, network,
spending, sandbox, or external effect contract. A changed check needs a second
independent review and must still reject a known-wrong answer. A tool written
during a run stays a candidate until a different process qualifies it.

Observed result. A read-only map of the solve path at commit `89553f2` found
that a declared supervision policy never reaches a solve run, that a format
repair stall ends a run, that the recovery panel's stop is adopted without the
action vector route guard, and that the independent verifier gets no JSON
repair. These are the first implementation targets.

Observed result. During reconciliation, eleven failed self-test checks first
looked like a runtime regression. Review showed that the stricter verification
contract was correct and the scripted fixture was stale, so the fixture
changed and the contract did not. That review was a manual instance of the
waterfall described above.

Unresolved question. Which model route and context should perform each review
stage when only one provider route is authorized.

## Persistence at every component, September 14

Owner requirement. Later on September 14 the owner asked for persistence in
every component, ontology operation, Loop, atomic component, and group, as a
persistent human worker would provide: a person who gives up on a task is not
kept on, so giving up is not acceptable. The owner then asked why runs kept
ending completely, noted that a person continues with full flexibility to
adjust their environment, and asked whether the engine truly generalizes how a
person works: gathering every file sent for a project into one folder,
downloading material into it, using it as the working directory, and verifying
there.

Observed result. A live Ollama Cloud rerun of the first campaign's cells on
commit `cd3bc85` finished 12 of 27 trials before a provider outage stopped the
experiment runner. None produced an accepted result. Six ended after two model
calls: the prompt showed the orientation step objective as the task's
immediate goal, the model copied it, and orientation raised after two rejected
attempts. On repair the models also copied the repair instruction into the
immediate goal, so repeating a whole-record request was not enough. Five used every allowed call without acceptance, and one ended on a
provider outage after its second call.

Observed result. Orientation now repairs the whole record, then the fields its
findings name, and then carries an orientation forward with the findings
recorded. The recovery panel's route passes the action vector guard, and the
independent verifier repairs response formats within declared calls. These
changes pass offline checks, and mutants confirm that each new check fails
without its behavior.

Observed result. A matched live rerun on commit `d3bda30`, which contains these
changes, completed 6 of 27 planned trials before the host stopped its runner
for low memory during the seventh. No completed trial ended early. CS-001 was
independently verified after 50 model calls. The other five ended
`COMPLETED_PARTIAL` with complete resolution packages after 41 to 60 calls,
where the `cd3bc85` rerun had stopped four of them after two calls. In each of
those five, an attempt passed its own checks, but every independent
verification report was unavailable. Every inspected oracle review returned
only the example criterion reference that its response contract showed, a
refused probe case named no field to repair, a probe file response omitted its
path, and some verifier calls reached the output limit. The
[persistent general solving decision record](docs/architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md#current-state)
records the evidence and the later changes. No live rerun has qualified those
later changes yet.

Proposal. Proposed invariants LE-SOLVE-004 and LE-SOLVE-005 in the
[Constitution](docs/architecture/CONSTITUTION.md#proposed-invariants-from-owner-direction)
record persistence at every component and one task working folder. A matched
rerun on the runtime with the verifier and attachment file changes, with an
experiment runner that waits through provider outages within a declared wait,
is the next live qualification step.

Observed result. In a live rerun on `2aaa5d5`, oracle reviews refused every
check program that searched a customer reply for literal phrases, so a
natural-language deliverable could be neither accepted nor rejected. The
independent verifier now offers a hybrid contract for such a criterion. A
deterministic rule holds the case to one registered criterion, a separate
model call judges it, and deterministic grounding passes the judgment only
when its quoted passages appear in the printed deliverable. No live rerun has
qualified it yet.

Observed result. In the same rerun an approved probe failed a correct FIN-001
report on five later attempts, because the retained check was reused and
nothing asked whether it was wrong. A failed independent check is now reviewed
as the decision record's review sequence describes. An isolated call
classifies the failure with quoted evidence, a second isolated call must
confirm any claim that the check is wrong, and a revised check must fail on
the subject with its authored and produced files emptied before it runs.
Confirmation on a different model route, and routing for environment defects
and ambiguous requirements, are not implemented yet.

Unresolved question. Whether a model step should wait and retry inside the run
when the provider is unavailable and the recovery reasoning call cannot
answer, and which declared authority would bound that wait.

Observed result. In the September 14 matched rerun, ten of twenty-seven cells
spent their entire declared call authority and ended `BUDGET_EXHAUSTED`,
several with earlier passing work left unverified. A supervision policy can
now declare budget-phase thresholds: at the first fraction of remaining call
authority the route step demotes exploration routes to consolidation, and at
the second it presents the best available result for verification. The
demotion is recorded, never touches a verified success or an honest stop, and
without declared thresholds nothing changes. No live rerun has qualified the
phase routing yet; the next rerun should declare thresholds for its cells and
compare the budget-exhausted outcome rate against the September 14 record.

Observed result. The recorded model-led policy skipped the deterministic
attempt entirely, so a task a registered exact resolver could already
complete still spent a full reasoning loop. A model-led solve may now
declare `allow_fast_path_resolution` (command line `--allow-fast-path`):
registered exact resolvers run before the first model call, a completed
verified fast path finishes with zero model calls, and an incomplete trace
stays preserved as hybrid-repair evidence. The default policy is unchanged
when the allowance is not declared. A live rerun has not qualified the
declared fast path yet; the next rerun should give some cells the
allowance and record how often the fast path resolves or informs the run.

Observed result. In the September 15 proactive flash cell SCM-001, the
subject report satisfied every registered criterion and passed its own
checks, but the independent probe resolved the subject directory from its
own file location and failed at execution with a missing source file, so
the cell ended `VERIFICATION_FAILED` over correct work. The probe prompts
now state the exact container binding (`/workspace`, subject files at
`/workspace/subject/<name>`, probe files under `checks/`), the oracle
review refuses location inference, and plan validation refuses that probe
shape at plan time with a repairable diagnostic before any sandbox run.
The same campaign also recorded a fresh budget-exhaustion cell and two
further verification-failed cells; a rerun on the current working tree
should carry declared budget-phase thresholds and the repaired probe
prompts together.

Advisory comment. The owner's September 16 direction asks that rules be
adaptable: adjustable when too tight, with different rules for development
versus production. Much of it exists: the failure review already questions a
faulty check, module-size exceptions are scoped with recorded rationale,
stage assistance runs shadow and advisory arms, and the supervision ladder
is a preauthorized adaptation range. The recorded direction adds rule
categories with change authority, lifecycle applicability profiles, an
enforcement ladder of advise, warn, and block, a compact generalized
policy-challenge record, and conditional defaults replacing over-rigid
formulations. Its three first actions are classification, lifecycle
declaration, and one challenge record, each through existing boundaries.
Read
[the adaptable policies direction](docs/architecture/ADAPTABLE-POLICIES-AND-LIFECYCLE-APPLICABILITY.md).
None of it is implemented yet; none changes an invariant until the
authoritative contract and its tests are revised.

Advisory comment. The owner's September 16 direction asks for reuse tiers
for input and output differences, suggested output formats, reuse-then-
modify instead of token spend on every atomic step, multiple LSH blocks,
hybrid retrieval, micro models for search, and embeddings or LoRA adapters
as memory. The economics are right and the tiered fingerprint index already
serves the qualified table; the recorded direction adds the output-side
tiers, the reuse-rung policy, the micro-model escalation judge, blocking
key families, validity windows, and the LoRA admission contract if adapter
memory is ever built. Read
[the reuse tiers direction](docs/architecture/REUSE-TIERS-AND-COST-ROUTING.md).
Nothing in it is implemented yet; the admission ladder and the flywheel
remain the only reuse authorities.

Observed result. A September 16 review found the task-campaign gates leak
their holdout: the gate shuffles the full training CSV and scores a 20
percent subset, while the staged solution trains on the full CSV, so the
"holdout" rows were in training. Measured on the passing atomic stub run:
0.766 in-sample versus 0.613 honest. Every score recorded on those gates,
including the September 10 campaign arms, was in-sample. The stub
experiment now uses a corrected gate that performs the split itself and
stages only the train side to the solution; honest scores for the atomic
pipeline are 0.6065 on 20-newsgroups and 0.9804 on Kannada-MNIST, both
above their floors. Campaign cells scored on the leaked gates keep their
records with this correction attached; regrading them needs the corrected
evaluation, not a silent edit.

## Model calls, the model ontology, and the two spaces, September 18

Owner requirement. The owner asked that every component be sectioned off so
it can be replaced without reprogramming its interfaces; that the space
where the Practitioner works be called the solutioning space and the space
of published solutions be called the solutions space, plural, with the
Solution Canvas as one member; that a language model call be wrapped as a
model call under a model ontology covering deterministic and
non-deterministic models, large, small, and specialized language models,
extractors, custom-trained models, image, forecasting, and tabular
foundation models; that heavy models run on separate systems so a tool may
call a model but never loads a large one; and that every call log its
metadata, prompt, and a suggested output shape (for example a ranked list of
candidates with a confidence, top ten) so the records can train smaller
models and answer engineering-lab questions later.

Observed result. The
[adversarial project audit](docs/verification/ADVERSARIAL-PROJECT-AUDIT-2026-09-18.md)
recorded the gaps. This iteration lands the model ontology and typed
`ModelProfile`, the tool placement rule on capability handshakes, the
`ModelCallRequest` boundary that refuses non-text kinds by name, the
`SuggestedOutput` contract with its advisory deviation diagnostic and its
first use on `decide_next`, the response contract registry that the route,
verify, criterion judgment, and failure confirmation steps now name, the
`SolutionsSpaceRecord`, and six terminology entries. Offline checks and
mutants cover each rule. No route declares a profile yet, no non-text route
exists, the run does not write the solutions space, and nothing here
changes which provider a run may call.

Owner requirement, later on September 18. Whenever a contract is proposed,
decide how it is matched: an exact match, a purpose match, a semantic
match with blocking on the decisive facts, or a judged match. Making every
contract exact makes the engine brittle. `core/contract_matching.py` owns
the five modes, and the criterion rubric is the first exact comparison
relaxed to canonical text; a review of every remaining exact comparison
against this rule is open work.

Owner clarification, later on September 18. Contracts that ensure
compatibility between connected nodes in the solutions space can be
strict, so that typed input and output ports match; the solutioning space
needs the flexible modes (purpose, semantic with blocking keys, judged).
The matching modes already exist; applying strict modes to solution ports
and flexible modes to solutioning-space comparisons is the intended use.

Observed result, later on September 18. Nineteen adjacent companies were
compared on packaging, pricing, and a binary feature matrix from their own pages in the
[competitive landscape and monetization record](docs/research/COMPETITIVE-LANDSCAPE-AND-MONETIZATION-2026-09-18.md).
No memory vendor executes, verifies, or keeps executable capability; the
metering units that fit Loop Engine's thesis are verified completions,
avoided model calls, optimize hours, and judgment depth, with governance
and hosting behind the paid line and outcome records never metered.

Observed result, later on September 18. The full raia-live/amfs repository
was read at b9547b4 and its evidence model, action priors, and
preregistered benchmark are recorded in the
[SenseLab research record](docs/research/EXTERNAL-SENSELAB-2026-09-18.md).
Its first benchmark run is a negative result the owner should know: every
memory arm had a stale-pick rate of 13 to 16 percent with no downward
trend, lower first-attempt success than no memory, and five to seven
times the tokens. Loop Engine now holds the typed pieces that reading
argued for: reuse evidence with a surprise weighted, credit split
posterior and a regime-shift event; learnable model call records with a
run-level split and named exclusions; operation cost records; the
engineering-lab question forms; and a dependency-direction ratchet with
the measured debt as its ceiling. None of these is wired into a live run
yet, and no live rerun has measured them.

Unresolved question. Whether `core` should keep importing `code_nodes` or
the two should be re-layered, which steps beyond `decide_next` should carry
suggested outputs, and where a hosted judgment service would keep its
records without receiving private prompts.
