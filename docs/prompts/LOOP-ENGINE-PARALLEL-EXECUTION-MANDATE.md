# Loop Engine parallel execution and microservice mandate

Paste this entire prompt into a new OpenCode, Codex, Claude Code, or
equivalent repository-development session rooted at `/home/username/loop-engine`.

## 0. Operating authority

You are the senior architecture, implementation, migration, test,
security, and release harness for Loop Engine.

Aggressively inspect, adversarially challenge, revise, implement,
migrate, test, verify, document, and predeploy-gate the parallel
execution and microservice architecture described here. Do not stop at
a design memo.

You are explicitly authorized to:

- inspect every relevant source file, schema, record, manifest, test,
  migration, README, ADR, example, generated file, and package
  configuration;
- create a complete inventory of current delegation, async, spawned
  task, workspace, and execution concepts;
- rename, move, split, merge, rewrite, or delete obsolete modules and
  folders;
- use `git mv` where it preserves history;
- rewrite imports, exports, tests, docs, schemas, manifests, JSONL
  records, database migrations, and persisted references;
- replace scattered async and execution logic with the typed parallel
  execution model;
- remove wrapper-only compatibility architecture after migration;
- add strict schemas, typed models, compatibility handshakes, versioned
  records, migrations, adapters, and conformance suites;
- create Core JSONL records and neutral shards;
- add property-based, fuzz, concurrency, failure-injection, security,
  migration, packaging, and clean-install tests;
- run tests repeatedly and continue repairing failures;
- reject or revise any part of this mandate that fails adversarial
  evaluation, provided you document the evidence and implement a
  stronger replacement;
- make reasonable architectural decisions without repeatedly asking for
  confirmation.

Do not merely add a new layer beside the old architecture. Do not leave
two competing execution systems active. Do not satisfy this task with
documentation-only changes, empty folders, unreferenced schemas, unused
adapters, or new abstractions that production paths never call.

The task is complete only when the architecture is operational,
migrated, tested, packaged, documented, and the obsolete behavior is
absent or explicitly quarantined behind a time-bounded compatibility
shim.

Do not commit or push unless explicitly instructed. Preserve unrelated
concurrent work.

## 1. Mission

Implement the parallel execution and microservice architecture:

```text
Parallel Execution
├── parallel procedures inside one LoopNode
├── concurrent child LoopNodes
├── asynchronous spawn and wait
├── background work while the parent continues
├── join policies and cancellation
└── shared budget accounting

Microservice Lifecycle
├── discover registered services
├── build and deploy new services
├── run services as governed LoopNodes
├── register services as Code Intelligence
└── reuse services across future runs
```

The governing invariants:

> Every independently governed unit of work above the kernel executes
> as a LoopNode. Parallelism, asynchrony, and microservice deployment
> are execution placements and lifecycle policies of LoopNodes, never
> new Node types, never new runtimes, and never a second engine.

> A LoopNode may start work and continue while that work runs. The
> parent owns the lifecycle: start, status, typed update, cancel, wait,
> terminal result, deadline handling, and no orphaned tasks.

## 2. Architectural baseline

### 2.1 One operational Node

LoopNode is the only concrete graph-addressable operational Node.
Parallel workers, async tasks, microservices, containers, and remote
functions are placements and bindings of LoopNodes. Never create
WorkerNode, AsyncNode, ServiceNode, MicroserviceNode, or
KubernetesNode classes.

### 2.2 Placement is separate from run mode

```text
Run mode:  deterministic | hybrid | non_deterministic
Placement: inline | local_task | worker_process | container |
           serverless | remote_service
```

A deterministic LoopNode may execute remotely. A non-deterministic
LoopNode may execute inline. Placement never grants permissions.

### 2.3 Governed-work boundary

Create a child LoopNode when work needs an independent goal, contract,
budget, permission boundary, retry, verification, scheduling decision,
or Chronicle identity. Parallelism alone does not force a child; a
parallel procedure inside one LoopNode is valid when the branches share
one goal, one contract, one budget, and one result authority.

## 3. Parallel procedures

### 3.1 Procedure kinds

```text
LoopProcedureSpec
├── procedure_kind
│   ├── atomic
│   ├── sequence
│   ├── directed_graph
│   ├── state_machine
│   ├── iterative
│   ├── parallel
│   ├── bounded_parallel
│   └── dynamic
├── scheduling
│   ├── sequential
│   ├── parallel
│   ├── bounded_parallel
│   └── dynamically_selected
├── completion
│   ├── required_children
│   ├── optional_children
│   ├── quorum
│   ├── first_success
│   └── aggregate_results
└── repetition
    ├── iteration_conditions
    ├── maximum_iterations
    └── convergence_conditions
```

### 3.2 Parallel branch semantics

Each parallel branch is a LoopStepBinding. Branches may:

- share read-only snapshots;
- use separate private portfolio snapshots;
- consume shared budgets;
- encounter catalog updates mid-run.

Branch-private adaptations must not leak into siblings.

### 3.3 Join policies

```text
JoinPolicy
├── all          every branch must succeed
├── any          one success is enough
├── quorum       a declared fraction must succeed
├── best_evidence  rank branch results, keep the best
├── first_valid  first successful branch wins
├── ensemble     combine branch results
└── manual       parent decides after all branches finish
```

### 3.4 Bounded parallelism

Every parallel procedure requires:

- maximum concurrent branches;
- maximum total branches;
- per-branch budget delegation;
- shared budget accounting;
- cancellation propagation policy;
- parent-close policy.

## 4. Asynchronous child LoopNodes

### 4.1 Lifecycle

```text
SpawnedTaskLifecycle
├── start        parent starts the child, receives a typed task ID
├── status       parent polls typed status
├── update       child emits typed updates
├── cancel       parent cancels with a reason
├── wait         parent waits for the terminal result
├── deadline     parent enforces a deadline
└── terminal     child reaches a terminal state, no orphan remains
```

### 4.2 Parent-close policies

```text
request_cancel        default for ordinary work
wait_for_required_child  required release checks
terminate             corrupt or unsafe child
detach_and_continue   rare, non-blocking background benchmark only
```

A required child must never silently outlive a completed gate.

### 4.3 Background work

A parent may start a child and continue its own procedure. The parent
must:

- record the child task ID in its Chronicle;
- poll or await at a defined join point;
- enforce a deadline;
- handle child failure at the join point;
- never leave an orphaned task.

### 4.4 Shared budgets

```text
Parent budget
├── total work ceiling
├── total call ceiling
├── total wall-time ceiling
│
├── child A delegation
├── child B delegation
└── shared pool for dynamic children
```

A child may not exceed the parent's delegated ceiling. Budget
accounting is shared and monotonic.

## 5. Microservice lifecycle

### 5.1 Discovery

A LoopNode may query Code Intelligence for registered services:

```text
ServiceDescriptor
├── service_id
├── service_version
├── endpoint or locator
├── protocol
├── input contract
├── output contract
├── effect contract
├── resource requirements
├── compatibility declaration
├── health-check definition
├── cost model
└── secret references
```

Discovery is effect-free. A service descriptor is a Code Intelligence
record, not a Node.

### 5.2 Build and deploy

A Practitioner may build and deploy a new service:

```text
ServiceBuildRequest
├── goal
├── service definition
├── deployment target
│   ├── local process
│   ├── container
│   ├── serverless function
│   └── Kubernetes workload
├── resource limits
├── network policy
├── effect permissions
├── approval requirements
└── rollback plan
```

The build and deploy operations are governed Solution-role LoopNodes
with explicit effect permissions. Deployment is an external effect and
requires approval.

### 5.3 Run as a LoopNode

A deployed service is invoked through an ordinary LoopNode:

```text
ServiceInvocationLoopNode
├── role: solution
├── binding: ServiceBinding
├── placement: remote_service
├── input contract: service input
├── output contract: service output
└── Chronicle: invocation events
```

The service itself is an implementation binding. The LoopNode is the
operational object.

### 5.4 Register for reuse

After a service is built and verified, its descriptor may be proposed
as Code Intelligence:

```text
ServiceDescriptor
        ↓
Candidate
        ↓
Independent Review
        ↓
Learned Code Intelligence
```

The building Practitioner cannot approve its own service descriptor.

## 6. Kubernetes and container runtimes

Kubernetes, containers, and serverless platforms are deployment
targets, not architecture.

```text
DeploymentTarget
├── local_process
├── container
├── kubernetes_workload
├── serverless_function
└── remote_service

DeploymentBinding
├── target
├── image or artifact reference
├── resource limits
├── network policy
├── secret references
├── health check
├── rollback plan
└── compatibility declaration
```

A Kubernetes manifest is a generated artifact from a typed
DeploymentBinding. It is never the canonical definition.

## 7. Required implementation architecture

```text
src/loop_engine/
├── node/
│   └── loop_node/
│       ├── procedure.py          parallel and bounded_parallel kinds
│       ├── step_binding.py       branch bindings
│       └── ...
│
├── execution/
│   ├── README.md
│   ├── placement.py              inline, task, process, container,
│   │                             serverless, remote
│   ├── join_policy.py            all, any, quorum, best_evidence,
│   │                             first_valid, ensemble, manual
│   ├── parallel_runner.py        bounded parallel branch execution
│   ├── async_runner.py           start, status, update, cancel, wait
│   ├── deadline.py               deadline enforcement
│   ├── parent_close_policy.py    request_cancel, wait, terminate,
│   │                             detach
│   └── budget_pool.py            shared budget accounting
│
├── services/
│   ├── README.md
│   ├── service_descriptor.py     Code Intelligence record
│   ├── service_binding.py        LoopNode-to-service binding
│   ├── deployment_target.py      local, container, k8s, serverless
│   ├── deployment_binding.py     typed deployment configuration
│   ├── build_request.py          governed build operation
│   ├── deploy_request.py         governed deploy operation
│   ├── health_check.py           service health
│   └── rollback.py               deployment rollback
│
└── intelligence/
    └── core/
        └── records/
            └── part-00000.jsonl  service descriptors and presets
```

## 8. Required tests

### 8.1 Parallel procedure tests

```text
test_parallel_procedure_runs_branches_concurrently
test_bounded_parallel_respects_maximum_concurrency
test_join_policy_all_requires_every_branch
test_join_policy_any_accepts_one_success
test_join_policy_quorum_requires_declared_fraction
test_join_policy_first_valid_stops_after_first_success
test_join_policy_ensemble_combines_results
test_branch_adaptation_does_not_leak_to_siblings
test_parallel_branches_share_budget_monotonically
```

### 8.2 Async lifecycle tests

```text
test_start_returns_typed_task_id
test_status_reports_typed_state
test_update_emits_typed_updates
test_cancel_with_reason_is_terminal
test_wait_returns_terminal_result
test_deadline_enforced
test_no_orphaned_tasks_after_parent_completion
test_parent_close_request_cancel
test_parent_close_wait_for_required_child
test_parent_close_terminate
test_parent_close_detach_is_rare_and_receipted
```

### 8.3 Background work tests

```text
test_parent_continues_while_child_runs
test_parent_joins_at_declared_point
test_child_failure_handled_at_join
test_background_child_is_receipted
```

### 8.4 Microservice tests

```text
test_service_descriptor_is_code_intelligence_record
test_discovery_is_effect_free
test_build_requires_effect_approval
test_deploy_requires_effect_approval
test_service_invocation_runs_through_loopnode
test_service_descriptor_promotion_requires_independent_review
test_builder_cannot_approve_own_service_descriptor
test_kubernetes_manifest_is_generated_artifact
test_deployment_rollback_restores_previous_binding
test_service_health_check_reports_typed_status
```

### 8.5 Placement tests

```text
test_placement_is_separate_from_run_mode
test_deterministic_loopnode_may_run_remotely
test_non_deterministic_loopnode_may_run_inline
test_placement_never_grants_permissions
```

## 9. Development workflow

- Phase 0: inventory. Read repository instructions, inspect current
  delegation, async, spawned task, and workspace code, inventory paths
  and symbols, identify test gaps.
- Phase 1: adversarial decision record. Write the challenge report,
  select canonical terminology, document rejected alternatives, define
  invariants, define migration boundaries.
- Phase 2: parallel procedures. Implement parallel and bounded_parallel
  procedure kinds, join policies, and the parallel runner.
- Phase 3: async lifecycle. Implement start, status, update, cancel,
  wait, deadline, and parent-close policies.
- Phase 4: budget pool. Implement shared budget accounting across
  concurrent children.
- Phase 5: service descriptors. Implement the ServiceDescriptor Code
  Intelligence record and discovery.
- Phase 6: build and deploy. Implement governed build and deploy
  operations with effect approvals.
- Phase 7: service invocation. Implement ServiceBinding and the
  ServiceInvocationLoopNode.
- Phase 8: deployment targets. Implement local, container, Kubernetes,
  and serverless bindings as generated artifacts.
- Phase 9: promotion. Implement service descriptor candidate staging
  and independent review.
- Phase 10: red team. Run concurrency, failure-injection, and orphan
  detection tests.
- Phase 11: predeploy. Run one strict command returning PASS,
  PASS_WITH_DOCUMENTED_WARNINGS, or BLOCKED.

## 10. Prohibited shortcuts

Do not:

- create WorkerNode, AsyncNode, ServiceNode, or KubernetesNode classes;
- create a second engine for parallel or async work;
- let placement grant permissions;
- let a child exceed the parent's delegated budget;
- leave orphaned tasks after parent completion;
- let a required child outlive a completed gate;
- treat a Kubernetes manifest as the canonical definition;
- let the builder approve its own service descriptor;
- deploy without effect approval;
- preserve the old execution system beside the new one;
- claim completion because schemas exist;
- claim completion because unit tests pass while production paths
  still use legacy execution code.

## 11. Required final deliverables

Return:

- architecture challenge report;
- selected canonical terminology;
- migration ledger;
- exact target and final repository trees;
- implemented parallel procedure model;
- implemented async lifecycle;
- implemented budget pool;
- implemented service descriptor and discovery;
- implemented build, deploy, and rollback operations;
- implemented service invocation LoopNode;
- Core JSONL records and manifests;
- self-review evidence;
- architecture tests;
- property-based and fuzz tests;
- concurrency and failure-injection results;
- end-to-end scenario results;
- package and clean-install verification;
- strict predeploy report;
- list of deleted obsolete paths;
- list of remaining compatibility shims with removal conditions;
- unresolved risks, if any;
- exact commands required to reproduce every verification.

Do not hide failures. Do not say "implemented" when a path is only
scaffolded. Do not say "compatible" without a handshake and test. Do
not say "secure" without adversarial tests. Do not say "reproducible"
without exact version, hash, and snapshot pinning.

## 12. Final completion standard

The work is complete only when all of the following are true:

- Parallel procedures run inside the one LoopNode engine.
- Async child LoopNodes have a complete typed lifecycle with no
  orphaned tasks.
- Placement is separate from run mode and never grants permissions.
- Shared budgets are monotonic across concurrent children.
- Service descriptors are Code Intelligence records.
- Discovery is effect-free.
- Build and deploy are governed operations with effect approvals.
- Service invocation runs through ordinary LoopNodes.
- Kubernetes and container manifests are generated artifacts from
  typed deployment bindings.
- Service descriptor promotion requires independent review.
- The builder cannot approve its own service descriptor.
- A clean installation passes the parallel and microservice scenarios.
- The strict predeploy gate returns PASS.

If a requirement cannot be satisfied, return BLOCKED with concrete
evidence, the smallest unresolved issue, and the exact next
implementation step. Do not paper over the failure with documentation.
