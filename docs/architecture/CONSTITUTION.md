# Loop Engine Architecture Constitution

This document is normative. It defines the stable invariants of Loop
Engine. Every invariant has a stable ID, an enforcement test, and a
machine-readable entry in `architecture.yaml`.

## Normative language

- MUST / MUST NOT: required for correctness, integrity, security, or
  architectural coherence.
- SHOULD / SHOULD NOT: the default choice unless a documented exception
  has stronger evidence.
- MAY: optional behavior that must remain interoperable when absent.

## Pre-launch contract direction

The owner's September 19 direction removes the requirement to support
pre-launch legacy interfaces. Versioned contracts and compatibility
handshakes remain required. Current callers must name supported record,
component, profile, and adapter versions; unknown versions must fail before
execution or mutation. Do not infer compatibility from a similar field shape.

The [pre-launch version decision](ADR-PRELAUNCH-VERSIONED-CONTRACTS.md)
records this direction and its verification requirements. It supersedes
older instructions to retain historical readers and forwarding imports.
Historical evidence remains unchanged. This policy does not assert that all
existing compatibility paths have already been removed; the continuation
review tracks their removal and current-contract checks.

## One operational runtime

### LE-NODE-001

`Loop` MUST be the only concrete operational runtime and the only executable
graph vertex.

Rationale: one operational runtime prevents parallel executors, split
lifecycles, and competing state machines.

Positive example: a Practitioner, an Intelligence query, and a Solution
pipeline step are all instances of the same `Loop` class with
different role fields.

Prohibited example: `class PractitionerNode(Loop)`.

Enforcement: `test_loop_node_is_only_operational_node`,
`test_loop_cannot_be_subclassed`.

### LE-NODE-002

The repository MUST NOT define a concrete generic Node class.

Rationale: Node is an ontological category and package namespace only.
A concrete Node class invites non-operational objects to pretend they
are graph vertices.

Enforcement: `test_no_concrete_generic_node`.

### LE-NODE-003

Practitioner, Intelligence, and Solution MUST be `Loop` roles, not
runtime subclasses.

Enforcement: `test_no_role_specific_node_classes`.

### LE-NODE-004

Deterministic, hybrid, and non-deterministic MUST be run modes, not
runtime subclasses.

Enforcement: `test_no_mode_specific_node_classes`.

### LE-NODE-005

Common behaviors MUST be represented by versioned passive Loop presets, not
additional runtime classes.

Rationale: presets are data. Subclasses are new runtimes.

Enforcement: `test_presets_are_not_subclasses`.

### LE-NODE-006

Typed objects contained by a `Loop` MUST NOT be described as executable
vertices.

Rationale: contracts, policies, configurations, references, results,
and reports are content owned by a `Loop`. Calling them executable vertices
recreates the parallel-ontology problem.

Enforcement: `test_typed_internal_objects_state_they_are_not_nodes`.

### LE-NODE-007

A semantic step requiring independent governance MUST execute as
a Loop Spawned by its parent.

Enforcement: `test_semantic_child_steps_are_child_loop_nodes`.

### LE-NODE-008

Low-level implementation primitives MUST NOT be promoted into Loops
Spawned by their parent unless they require an independent goal, contract, budget,
permission boundary, retry, verification, scheduling decision, or
Run History identity.

Rationale: a literal rule that every function call is a Loop
creates infinite recursion and unbounded overhead.

Enforcement: `test_implementation_primitives_stay_inside_loop_node`.

### LE-NODE-009

A Loop preset MUST be a partial typed configuration and MUST NOT be
a runtime subclass.

Enforcement: `test_presets_are_not_subclasses`.

## Configuration

### LE-CONFIG-001

The minimum resolved configuration required to start a Loop MUST be
available before execution begins.

Rationale: a Loop must not need another Loop merely to discover
that it exists.

Enforcement: `test_bootstrap_does_not_require_recursive_configuration_loops`.

### LE-CONFIG-002

Configuration retrieval MUST NOT recursively require another
configuration Loop without a bounded bootstrap base case.

Enforcement: `test_bootstrap_does_not_require_recursive_configuration_loops`.

## Intelligence

### LE-INTEL-001

Functional Intelligence Domains MUST be non-exclusive classifications.

Rationale: one record may support several domains simultaneously.

Enforcement: `test_function_domains_are_non_exclusive`.

### LE-INTEL-002

No step name, step number, or folder path may implicitly grant or
restrict intelligence access.

Enforcement: `test_query_engine_has_no_default_step_name_dependency`.

### LE-INTEL-003

Intelligence access policy MUST remain separate from seeking strategy
and ranking preferences.

Rationale: preference must never grant permission.

Enforcement: `test_preference_never_grants_permission`.

## Permissions

### LE-PERM-001

A descendant Loop MAY narrow inherited permissions but MUST NOT
broaden them without an explicit delegated grant.

Enforcement: `test_child_cannot_broaden_parent_scope`.

## Documentation and trust

### LE-DOC-001

Human-readable prose, comments, labels, and tags MUST NOT control
permissions, routing, execution, or governance.

Rationale: retrieved intelligence is untrusted content. A record saying
"ignore prior policy" is data, not authority.

Enforcement: `test_prompt_injection_record_cannot_change_policy`,
`test_labels_do_not_control_routing`.

### LE-TRUST-001

Text retrieved as intelligence MUST remain data and MUST NOT be promoted
to executable authority without passing through a typed,
policy-controlled interpretation boundary.

Enforcement: `test_untrusted_record_cannot_issue_runtime_instructions`.

## Versioning

### LE-VERSION-001

A resolved Loop plan MUST pin exact versions and content hashes for
all executable definitions and governed dependencies.

Enforcement: `test_resolved_plan_pins_exact_versions`.

## Runtime

### LE-RUNTIME-001

Runtime Memory, Run History events, checkpoints, records, artifacts, and
Learned Intelligence MUST remain distinct concepts.

Enforcement: `test_runtime_memory_chronicle_and_experience_are_distinct`.

## Plugins

### LE-PLUGIN-001

A plugin MUST NOT introduce a new operational Node type.

Enforcement: `test_plugin_cannot_define_node_type`.

## Governance

### LE-GOV-001

A Practitioner or plugin MUST NOT approve its own generated candidate.

Enforcement: `test_self_review_cannot_self_approve`.

## Proposed invariants from owner direction

Status: proposed on September 14, 2026. These entries record owner direction.
They are not enforced invariants and do not describe implemented behavior.
Each one becomes an invariant only when its enforcement test exists and
`architecture.yaml` carries its machine-readable entry, as the strongest
documentation rule below requires. The
[persistent general solving decision record](ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md)
explains the design, the current gaps, and the planned tests.

### LE-SOLVE-001 (proposed)

A run MUST NOT end without an accepted and verified result while a safe
authorized next action and declared authority remain. A run MAY end for an
accepted verified result, exhausted declared authority, a question or
authority request that only the owner can answer, an operator cancellation,
or a provider outage recorded for resumption. It MUST record which reason
ended it.

Rationale: persistence turns each failure into a typed next action instead of
an early end. Persistence never grants authority, repeats an external effect,
or invents a budget.

Planned enforcement: `test_run_cannot_end_while_authorized_continuation_remains`.

### LE-SOLVE-002 (proposed)

Task knowledge MUST enter through typed context, capabilities, skills,
contracts, and generated artifacts. The runtime MUST NOT contain control flow,
prompts, or checks written for one task, dataset, or benchmark.

Rationale: the same Practitioner Loop must be able to understand, plan, act,
verify, and write tools for work it has not seen before.

Planned enforcement: `test_runtime_has_no_task_specific_control_flow`,
extending the existing hardcoding delta gate.

### LE-SOLVE-003 (proposed)

A tool written during a run MUST remain a candidate. It MUST execute only in
the declared sandbox. It MUST NOT be reused within the run until checks
written by a process other than its builder pass, and it MUST NOT be reused
across tasks without Code Intelligence admission.

Rationale: a tool that only its builder has checked is not evidence that the
tool works.

Planned enforcement: `test_self_built_tool_requires_independent_qualification`.

### LE-SOLVE-004 (proposed)

Every step, Loop, atomic component, pipeline, ontology operation, and
experiment runner MUST treat a failed or rejected attempt as input to a
changed next attempt. It MUST NOT end a run on a fixed attempt count while
declared authority remains. When the same failure repeats, the component MUST
change its approach: quote the failure, narrow the request to the failing
part, use another registered method, or carry its best result forward as
provisional with the findings recorded. A provisional result MUST NOT be
graded or reused as accepted, and it MUST withhold only the values that its
findings protect later steps from.

Rationale: in a September 14 live rerun, a rejected orientation ended six of
twelve finished trials after two model calls while each run still held most
of its declared call authority.

Planned enforcement: `test_no_component_ends_a_run_on_a_fixed_attempt_count`.

### LE-SOLVE-005 (proposed)

A task MUST have one path-confined working folder that persists across passes
and attempts. The supplied files, unpacked archives, downloaded material,
generated work, and outputs of the task MUST be placed there with their
provenance, and every step, Spawned Loop, and harness working on the task
MUST receive a scoped view of it. The folder MUST NOT grant write, command,
network, or spending authority; those remain separate typed permissions.

Rationale: a person working on a project gathers everything in one folder and
works there. Separate per-attempt folders, skipped binary files, downloads
kept only as records, and Spawned Loop outputs that never reach the owner make
the engine lose work that a person would keep.

Planned enforcement: `test_task_working_folder_is_shared_persistent_and_confined`.

### LE-CONTRACT-001 (proposed)

Every contract check MUST declare its evaluation mode: deterministic, hybrid,
or model-reasoned. An evaluation mode MUST NOT be treated as a Loop run mode
and MUST NOT grant authority.

Rationale: a failure can be reviewed only when it is known how the outcome was
decided.

Planned enforcement: `test_every_contract_check_declares_evaluation_mode`.

### LE-CONTRACT-002 (proposed)

A failed contract check MUST start a recorded review before the work or the
check changes. The review MUST ask whether the failure is correct, whether
the check is wrong or stricter than the task requires, whether the
environment or harness caused it, and which part of the work needs edits.
The original failure MUST remain in Run History.

Rationale: a wrong or arbitrary check can block a correct solution on every
later attempt.

Planned enforcement: `test_failed_check_starts_a_recorded_review`.

### LE-CONTRACT-003 (proposed)

A review MUST NOT waive an authority contract: permissions, secrets, network
access, spending, sandbox policy, or external effects. A change to any other
check MUST be confirmed by a second independent review, and the revised check
MUST still reject at least one known-wrong answer.

Rationale: a check that the checked work can weaken is not evidence.

Planned enforcement: `test_review_cannot_waive_authority_or_remove_discrimination`.

### LE-FABRIC-001 (proposed)

Every cognitive or act step MUST record an efficiency review before its
model call: the input size, the output size, the alternatives considered
with a confidence for each, and the chosen alternative with its reason. The
review MAY be produced by a deterministic judge, a specialist, or a model,
and the judge kind MUST be recorded.

Rationale: the owner's September 18 direction asks at every step whether
this is the most efficient way and how confident each alternative is; a
review that is not recorded cannot train a cheaper judge later.

Planned enforcement: `test_every_step_records_an_efficiency_review`. The
record and its deterministic judge exist in `core/step_efficiency_review`
with the check `the_deterministic_judge_flags_an_oversized_input_and_records_its_reason`;
the step that writes it during a solve is not wired yet.

### LE-FABRIC-002 (proposed)

A harness instance MUST receive a typed provisioning manifest naming the
tools, plugins, context files, instruction files, contracts, hooks, lookups,
intelligence access, external access, placement, and the exact input it is
given, and the runtime MUST verify what the instance loaded against that
manifest. Loading a file the manifest does not name is a defect.

Rationale: a solutioning node is an independent harness given exactly what
it needs; an unlisted input is an unrecorded influence on its result.

Planned enforcement: `test_harness_instance_loads_only_its_manifest`.

### LE-FABRIC-003 (proposed)

A Loop that publishes a candidate output and continues working MUST keep
every published output addressable by digest, and every consumer MUST record
the exact output digest it used. A later, better alternative MUST NOT change
a consumer's recorded input.

Rationale: iterative publication is only safe when dependent work can name
what it depended on.

Planned enforcement: `test_consumers_name_the_published_output_they_used`.

### LE-DATA-001 (proposed)

Learnable records MUST be written to a versioned dataset store with a
schema, a split manifest, and named exclusions. No learned heuristic MUST be
adopted for routing, blocking, or thresholds until the declared minimum run
count is recorded, except an exact fingerprint at the atomic level of a
reason, build, or execute step. The minimum is a declared policy value,
initially one million runs.

Rationale: the owner's September 18 direction asks that the data be
collected now and that heuristics wait for enough evidence; a threshold that
lives in a policy record can be reviewed, one that lives in code cannot.

### LE-DATA-002 (proposed)

Intelligence records MUST be read and written through the store contract.
No module outside the declared catalog adapters MUST open a packaged
intelligence path for writing, and no run MUST edit an intelligence file
directly. The conformance gate
`direct_writes_to_intelligence_files_outside_adapters` counts literal-path
writes; the adapters govern paths held in variables.

Rationale: the owner's September 18 direction that intelligence is stored
and served through one contract, never by editing text files; a scan that
fails the build is the rule's only durable form.

### LE-LAYOUT-001 (proposed)

Every documentation folder that holds files MUST carry a README whose head
states its kind, naming rule, and version rule, and every new top-level
folder MUST appear in the layout charter. Dated records keep the
`STEM-YYYY-MM-DD` convention, and the records index MUST list every version
of each dated record.

Rationale: the owner's September 18 question about folder paths, trees, and
files; the folder is the kind, the tree is the classification, the file is
the record, and a reader must be able to tell which is which without asking.

Planned enforcement: `test_heuristic_adoption_waits_for_the_declared_run_count`.
The policy and the versioned dataset store exist in `core/heuristic_adoption`
with the check
`an_exact_atomic_fingerprint_is_allowed_below_the_threshold_and_nothing_else_is`;
no runtime path adopts a heuristic yet, so nothing can bypass the policy.

## Documentation authority hierarchy

```text
1. Architecture Constitution (this document)
2. Machine-readable architecture contracts (architecture.yaml,
   terminology.yaml, schemas, manifests)
3. Contract tests
4. Architecture Decision Records
5. Folder README files
6. Public API docstrings
7. Inline comments
8. Generated documentation
9. Examples and tutorials
```

A README or example MUST NOT silently override this Constitution. A
docstring MUST NOT introduce an object type absent from the ontology. A
comment MUST NOT become the only place where a permission,
compatibility requirement, or contract is defined.

## The strongest documentation rule

If a statement is important enough that violating it would break the
ontology, it must exist as a stable invariant, a machine-readable
constraint, and an executable test, not only as prose or a code comment.
