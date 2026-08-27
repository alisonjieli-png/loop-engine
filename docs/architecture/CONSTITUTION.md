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
