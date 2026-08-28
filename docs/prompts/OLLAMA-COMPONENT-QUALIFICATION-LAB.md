# Ollama component qualification lab mandate

Use this prompt in a fresh coding session outside the Loop Engine repository.

```text
Create a standalone repository named loop-engine-qualification-lab.

The lab is an independent black-box reference and falsification harness for
Loop Engine. It may execute the installed loop-engine command and inspect
public JSON artifacts. It must not import loop_engine source modules, share its
runtime, copy its implementation, read private scratch state, or declare Loop
Engine correct because its own tests pass.

Use Ollama as the only semantic model provider. Keep the model advisory. All
permissions, process execution, file access, budgets, schemas, evidence,
comparison, and terminal verdicts belong to the lab runtime.

Goal

Qualify one component, interaction, state transition, layer, or architecture
classification at a time. Start with atomic contracts. Build toward one full
Practitioner pass only after every lower gate is independently green.

Do not begin with a flagship end-to-end task.

1. Lab contracts

Implement passive records equivalent to:

QualificationCase
├── case_id
├── version
├── subject_kind
├── subject_ref
├── goal
├── preconditions
├── supplied_inputs
├── expected_outputs
├── invariants
├── questions
├── positive_cases
├── negative_cases
├── ambiguous_cases
├── adversarial_cases
├── mutation_cases
├── deterministic_oracles
├── semantic_review_policy
├── evidence_requirements
├── comparison_policy
├── budget
└── content_digest

QualificationAttempt
├── attempt_id
├── case_ref
├── input_digest
├── deterministic_observations
├── selected_questions
├── Ollama requests and typed responses
├── candidate diagnoses
├── candidate changes
├── adjudication
├── engine observations
├── differences
├── failures
├── unknowns
├── artifacts
└── terminal state

QualificationVerdict
├── case_ref
├── PASS | FAIL | UNKNOWN
├── invariant results
├── exact evidence refs
├── counterevidence
├── remaining uncertainty
├── next qualified dependency
└── blocked promotion reason

2. Qualification ladder

Run gates in this order:

Component qualification
├── Gate 1: identity, version, digest, and source of truth
├── Gate 2: passive versus executable semantics
├── Gate 3: one typed input and output contract
├── Gate 4: one atomic deterministic operation
├── Gate 5: one producer-to-consumer interaction
├── Gate 6: one state integration rule
├── Gate 7: one verification criterion
├── Gate 8: one continue, repair, and exit decision
├── Gate 9: two-component composition
├── Gate 10: one complete Practitioner pass
└── Gate 11: bounded multi-pass work

A gate may use only dependencies already qualified at a lower gate.

3. One prompt per semantic responsibility

Do not create one giant review prompt. Store small, versioned question and
persona records. Render one packet for one responsibility.

For each case, use separate Ollama calls for:

OBSERVE
→ Describe only the supplied evidence and unknowns.

INTERROGATE
→ Answer the case's selected questions.

DIAGNOSE
→ Identify the smallest evidenced failure cause.

IDEATE
→ Generate two or more materially different correction candidates.

ADVERSARIAL REVIEW
→ Try to falsify each candidate.

ADJUDICATE
→ Select one next test or correction, or return UNKNOWN.

VERIFY
→ Map the observed result to registered invariants.

No call may claim that code ran or authority was granted.

4. Stalled-work protocol

A deterministic monitor may detect a stall. It may not decide that the task is
hopeless merely because snapshots repeat.

Use:

deterministic stall signal
→ independent failure-diagnosis Ollama call
→ first repair or mutation proposal call
→ materially different alternative proposal call
→ adversarial comparison call
→ adjudication call
→ deterministic schema, permission, and capability validation
→ execute the selected changed strategy
→ verify measurable progress

Measure progress through exact state changes:

new verified evidence digest
new artifact identity
new project attempt
new satisfied acceptance criterion
resolved unknown
changed method or capability
reduced uncertainty with evidence

Changing prose is not progress.

Only hard authority, safety, cancellation, or exhausted declared budget may
force a deterministic terminal state. A semantic stop recommendation must be
typed, evidence-backed, and validated.

5. Component families

Create qualification packs for:

Runtime
├── Loop identity
├── role profile
├── per-Loop mode
├── relationship
├── input and output ports
├── permissions and effects
├── loop condition
├── exit condition
└── Run History

Passive components
├── settings
├── policy
├── persona
├── question
├── guidance
├── intelligence record
├── prompt block
├── work packet
├── capability descriptor
├── procedure
├── graph definition
└── result

Interactions
├── select
├── materialize
├── assemble
├── invoke
├── execute
├── verify
├── integrate
├── route
├── spawn
├── join
└── return

Architecture axes
├── runtime type
├── role
├── mode
├── relationship
├── profile
├── persistent intelligence layer
├── catalog namespace
├── functional intelligence domain
├── capability group
├── lifecycle
└── scope

6. Interaction qualification

For each producer-consumer pair, test:

exact compatible version
compatible older reader
incompatible version
missing required field
unknown field
wrong digest
wrong component kind
permission omitted
permission broadened
timeout
cancellation
partial success
duplicate delivery
retry of non-idempotent effect
stale context
private context leak
conflicting sibling results

Every interaction result must identify the producer, consumer, operation,
request contract, output contract, compatibility result, authority, evidence,
and terminal state.

7. Verification-scope qualification

Require each blocking verification gap to reference one registered user
acceptance criterion. Keep separate:

blocking contract failure
unknown evidence state
advisory quality improvement
new requirement proposal

A verifier may not silently turn a preference, best practice, anomalous metric,
or optional improvement into a new hard acceptance condition.

8. Black-box comparison with Loop Engine

For each qualified case:

1. Freeze the case input and expected invariant results.
2. Run the lab reference path.
3. Run the installed public Loop Engine path when applicable.
4. Save stdout, stderr, exit code, JSON result, artifacts, and Run History.
5. Compare contract fields and state transitions, not prose similarity.
6. Preserve disagreements as FAIL or UNKNOWN.
7. Generate the smallest reproducible defect fixture for Loop Engine.

The lab must detect at least:

verified artifact state later overwritten
repair action with no executable capability
same evidence fetched repeatedly
same verification gap repeated without changed strategy
route continues with no measurable state change
terminal success without the requested artifact
pass budget exhausted without an exact terminal reason
model proposal broadens permission
provider failure becomes canned output
parent private context leaks to a child

9. Required commands

Provide commands equivalent to:

qualify list
qualify render CASE_ID
qualify run CASE_ID --model MODEL
qualify replay ATTEMPT_ID
qualify compare CASE_ID --engine-result PATH
qualify audit-run PATH
qualify report CASE_ID
qualify suite --through-gate N

Every command emits canonical JSON. Human text is a projection.

10. Required tests

test_case_identity_is_versioned_and_digest_bound
test_each_case_has_one_bounded_prompt
test_model_response_requires_exact_schema
test_unknown_is_preserved
test_model_cannot_grant_permission
test_stall_detector_does_not_choose_terminal_route
test_stall_runs_independent_diagnosis_calls
test_stall_generates_materially_different_changes
test_recovery_adjudication_selects_registered_capability
test_repeated_action_without_progress_is_rejected
test_verified_artifact_state_survives_later_failure
test_blocking_gap_maps_to_acceptance_criterion
test_advisory_improvement_does_not_block_completion
test_layer_namespace_function_and_scope_are_distinct
test_one_loop_graph_authority
test_black_box_comparison_preserves_failures
test_no_loop_engine_internal_import

11. Completion

Do not report that Loop Engine is qualified. Report exact component and gate
coverage.

Return:

Repository:
Starting SHA:
Ending SHA:
Cases implemented:
Gates reached:
Deterministic oracles:
Ollama calls:
Component passes:
Component failures:
Interaction passes:
Interaction failures:
State-transition defects:
Loop Engine differences:
Unknowns:
Artifacts:
Tests:
Remaining blockers:
Final verdict:

Allowed verdicts:

QUALIFIED THROUGH GATE N
QUALIFICATION FAILED WITH REPRODUCTION
QUALIFICATION INCOMPLETE
```

The current repository includes a starter implementation in
[`devtools/qualification_lab`](../../devtools/qualification_lab/README.md).
