# Runtime, graph authority, and replaceability audit

Review date: September 19, 2026. Baseline revision:
`48cc954322691e492aad69a465ba470a112730e7` on `main`.

The baseline runtime has meaningful typed boundaries and explicit refusal
states, but several apparent guarantees do not survive the actual execution
path. The most important failure is that a validated Solution graph can
declare one dataflow and execute another. Independent probes also found
permission widening in compatibility spawning, loss of unrelated settings
when modes are restricted, and a native instruction file outside the native
process's mounted workspace.

This is a focused audit, not a whole-repository correctness claim. The
[coverage record](runtime-coverage.json) initially named 39 inspected files, including
source sections, instruction documents, and one existing test fixture.
The [question register](runtime-questions.json) contains 89 concrete questions.
Its baseline had 63 answered from source, 11 disputed by a conflict or probe,
and 15 open. Subsequent questions carry the repair resolutions recorded below;
the current counts are 74 answered, three disputed, and 12 open. Answered does
not mean independently qualified or defect-free.

The report describes the baseline before the separately authorized repair
work. Findings remain historical observations if later sections record fixes.
Existing working-tree edits were preserved. No live provider, network service,
native harness process, deployment, or external effect was invoked.

## Canonical classification

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

The audit introduces no new runtime type or persistent intelligence layer.
Configuration records, harness adapters, operation registries, and graph
edges remain passive data or mechanics used by classified Loops.

## Observed call paths

The following is a source-path map. The probes exercised the smaller paths
identified in their results; this map is not a claim that a full solve ran.

```text
Public local solving
└── solve_cli -> SolveRequest -> solve_task
    └── solve_dependencies -> run_adaptive_practitioner
        ├── create_adaptive_owner -> canonical Loop
        ├── deterministic resolver path
        ├── run_kernel_passes -> adaptive step implementations
        │   ├── model step -> ModelExecutionSession.invoke
        │   │   ├── ModelGateway.invoke -> configured provider adapter
        │   │   └── optional HarnessSemanticBinding.invoke
        │   │       └── run_external_harness -> canonical Spawned Loop
        │   │           └── GatewayHarnessProcessAdapter
        │   │               └── run_harness_process -> isolated text broker
        │   └── run_spawned_tasks
        │       ├── fork_services, shared spending session, separate task context
        │       ├── provision_spawned (inactive without catalogue)
        │       └── run_spawned_kernel, serial dependency order
        └── independent task acceptance -> SolveOutcome and Run History

Compiled Solution execution
└── SolutionSpec -> build_solution_graph -> LoopGraphDefinition
    └── compile_solution -> graph record and digest
        └── run_compiled -> SolutionSpec.from_graph
            └── group-stage projection -> serial or ensemble execution
                └── canonical Solution Loop -> supplied operation callable

Typed generic delegation
└── spawn_practitioner_loop or SpawnedTaskManager
    └── DelegationSpec -> parent.spawn -> supplied executor
        ├── synchronous call, no wall-time wrapper
        └── asynchronous call with asyncio.wait_for
```

The public adaptive path, the generic delegation manager, and the semantic
harness path are distinct realizations. A test of one does not establish the
others. In particular, a fresh native process per semantic call is not the
same as a native harness owning an entire atomic assignment with selected
tools, skills, and working material.

## Ranked baseline findings

### 1. High: validated graph dataflow differs from executed dataflow

Observed through `compile_solution` and `run_compiled`. A two-stage fixture
increments an input and multiplies by ten. The modified graph removes the
first-to-second edge and binds the second stage directly to the external
input. Validation reports no violations. Input `2` should therefore produce
`20` at the second stage, but execution produces `30`.

The validator checks endpoint declarations, duplicate edge binding, cycles,
and group membership. It does not reconcile edge dataflow with group order.
`_project_group` constructs ordered stages from groups, and `_execute_spec`
passes a running value through that order. The graph's edges are not the
source of the executed bindings.

Evidence: `solution_graph_validation.py:73-192`,
`solution_canvas.py:164-182`, `solution_canvas.py:662-678`, and
`runtime-probe-05` in [the reproducer](runtime-probes.py).

Owning boundary: Solution graph validation and execution. Either execute the
declared bindings or refuse graphs outside the supported execution structure.
A corrected validator must reject this known-wrong graph or the executor must
return the value dictated by its declared binding.

### 2. High: compatibility spawning manufactures permission names

Observed: a compatibility spawning Loop with no permissions accepts an exact
spawned definition requesting `audit_permission`. Its resulting context gains
that permission. The same definition is refused by the strict-context control.

`Loop.spawn` builds a new compatibility context from the requested definition
instead of checking the spawning context. This is not an isolated test path:
ordinary adaptive ownership uses the established constructor when no host is
installed, and the Solution runner also creates compatibility contexts.

Evidence: `recursive_loop.py:856-860`, `runtime_context.py:275-291`,
`adaptive_host_verification.py:33-44`, `solution_canvas.py:265-281`, and
`runtime-probe-03`.

Scope: this establishes a typed authority contradiction, not an
operating-system escape. Real effect boundaries can still enforce their own
approval. The compatibility bridge must not create permission authority from
the request it is meant to validate.

### 3. High: restricting modes resets supervision and output settings

Observed: requesting a spawned Loop with a custom supervision policy and
`output_type="multiple", max_outputs=2` under a narrower delegation policy
silently produces default supervision and `single, None`.

The manual `LoopConfig` reconstruction in `Loop.spawn` copies only some
fields. Restricting modes therefore changes independent configuration
dimensions and discards an output obligation.

Evidence: `recursive_loop.py:795-815`, `LoopConfig` fields at lines 187-190,
and `runtime-probe-02`. Owning boundary: canonical spawning. Use a typed
replacement of the requested record and change only the validated mode and
thinking fields. Test future fields as well as these two examples.

### 4. High for provisioning: instructions are outside the native mount

The semantic binding installs `InstanceInstructionWriter` at the step
directory. Its `AGENTS.md` is written there. `run_harness_process` then creates
a nested `harness-*` directory, and `_sandbox` mounts only that directory's
`work` subdirectory at `/work`. The supplied instruction file is outside
that mount. The pure sandbox-argument probe confirms the mismatch without
starting a process.

Evidence: `harness_semantic.py:335-386` and `614-628`,
`instance_instructions.py:392-409`, `harness_process.py:246-249` and
`349-357`, `runtime-probe-06`.

`run_external_harness` copies the writer's digest into its result. That is
evidence of writing, not loading. The public solve dependency assembler also
omits the separate `harness_catalogue` and `guardrails` fields, so the new
Spawned provisioning hook returns `no_catalogue_installed` on that path.
These are distinct integration gaps.

Owning boundaries: native workspace construction, instruction delivery,
and public dependency assembly. Verify the exact material inside the real
native process before claiming it was loaded or used.

### 5. Medium: compiled identity does not bind callable implementations

Observed: the identical compiled graph returns `30`, then `1020`, after the
caller replaces `registry["increment"]`. The graph digest is unchanged:
`9b824fbb4089740b54e1e545ddf300e8e26c7c5558360e12b153210cc5dc0beb`.

Compilation checks callability. Execution resolves the name again and calls
the supplied function. No implementation digest is bound by this interface.
Generated Solution definitions declare pure effects, but arbitrary supplied
Python callbacks run directly in the host process.

Evidence: `solution_compiler.py:51-91`, `solution_canvas.py:397-431`,
`solution_graph.py:670-683`, and `runtime-probe-04`.

This is a trusted-host replacement seam, not an untrusted-code execution
exploit. The graph digest proves the graph's identity only. Claims of exact
replay, qualified code reuse, or pure effects require an admitted executable
binding with implementation and dependency identities at the existing owning
boundary.

### 6. Medium: synchronous delegation ignores wall-time allowance

Observed: a synchronous executor that waits 30 milliseconds succeeds with a
five-millisecond `DelegationBudget.wall_time_seconds`. The measured run took
about 31 milliseconds. The asynchronous method uses `asyncio.wait_for`; the
synchronous method directly invokes its executor and never checks wall time.

Evidence: `delegation_runtime.py:443-460`, `690-709`, `716-753`, and
`runtime-probe-08`.

The default executor also returns `act:done` under the requested
`clean_row/v1` role. This is structural protocol completion, as documented by
`default_handler`, not normalization of the supplied row. The current
delegation check tests the role and lifecycle, not the intended operation.

Owning boundary: the synchronous executor contract. Refuse unsupported
preemptive deadlines or use a qualified execution mechanism. Do not report
structural fixtures as arbitrary-task execution evidence.

### 7. Medium: an empty derivation adds a deterministic executor

Observed: deriving from a context whose sole executor is `hybrid` produces
`deterministic`. `derive` validates an empty requested executor set, then
substitutes `("deterministic",)` in the result.

Evidence: `runtime_context.py:243-270` and `runtime-probe-01`. This directly
contradicts the method's no-widening contract. Owning boundary: context
derivation. Empty requested authority must remain empty or use an explicitly
validated inherited choice.

### 8. Medium: ordinary provider failover defaults to enabled

Observed in pure selection: `ModelGatewayConfig` with two provider routes and
no failover argument retains both providers. Setting `allow_failover=False`
retains the first. The default is `True`, unlike the separate evaluator
failover flag, which correctly defaults to `False`.

Evidence: `model_gateway.py:222`, `827-873`, and `runtime-probe-07`. This
conflicts with the repository requirement for explicit failover permission.
No physical request was dispatched. Owning boundary: model authority
construction and compatibility migration for existing callers.

## Implemented guards and deliberate unsupported states

These positive source observations must remain visible beside the failures.

| Boundary | Guard observed | Evidence limit |
|---|---|---|
| Canonical runtime | Class creation refuses Loop subclasses. | Does not prove every operational call is correctly bound. |
| Exact definitions | Profile, role, supported and installed modes, effects, content digests, and strict start requirements are validated. | Compatibility spawning has the separate widening defect above. |
| Harness replacement | Adapter object and registration facts are checked before every attempt. | Does not qualify the adapter's declared behavior. |
| Semantic harness recovery | Physical calls, known token usage, and elapsed time remain shared across alternatives. Uncertain effects and accounting stop recovery. | Native tool effects are disabled in this realization. |
| Native process boundary | Pinned software, isolated namespaces, brokered text calls, byte limits, and process cancellation are explicit. | This audit did not run the native process. |
| Wrapper composition | Nonempty wrapper stacks are refused as `composition_without_executor`. | No wrapper executor is implemented in this path. |
| Native controls | Even declared support is refused as `declared_without_executor`. | No native goal, retry, or session-control handoff is implemented here. |
| Model session | Single-flight lock, bound authority identity, and uncertainty refusal prevent silent repeated spending. | A replacement `session_factory` is checked mainly for member presence and needs behavioral qualification. |
| Response evaluation | Structural admission, response evaluation, and task acceptance are separate. Evaluator failover requires a separate flag. | Registration does not prove the callback is a correct input-dependent oracle. |
| Adaptive Spawned work | Separate task context, scoped workspace, bound dependency references, shared spending authority, and explicit summaries exist. | Current execution is serial and receives the selected mode from the spawning request. |
| Host acceptance | Current-state observation verification is separate from final task completion. | Host callback and effect enforcement require their own qualification. |

## Swap boundaries and interface obligations

| Replaceable element | Actual entry interface | What replacement must preserve |
|---|---|---|
| Loop behavior | Versioned profile, `LoopDefinition`, `LoopStartRequest`, step handler | Exact role, contract, modes, continuation, permissions, and event identity. |
| Solution operation | `registry[operation_ref](value, params)`, or one-argument router/evaluator | Declared port roles and operation result. Current seam lacks implementation pinning and payload-schema enforcement. |
| Model provider | `ProviderSpec` with `chat_maxout`, `verify`, `live_models`, `output_capability_for`, `DEFAULT_MODEL` | Exact route and output-capacity facts, physical call accounting, deadlines, and provider usage. |
| Model session | `ModelExecution.session_factory(authority)` | `invoke`, `results`, `calls_used`, and `accounting_uncertain` are checked; complete authority behavior still needs conformance tests. |
| Harness adapter | `info() -> HarnessAdapterInfo`, `run(request, services) -> HarnessRunResult` | Required features, effects, identity, limits, result capture, physical call detail, and inability to self-accept. |
| Spawned executor | `SpawnedExecutionRequest -> SpawnedLoopResult`, sync or async | Profile and ports, terminal lifecycle, counters, summary policy, and supported deadline/cancellation mechanics. |
| Generated project executor | Injected `AdaptivePractitionerDependencies.project_executor` | Workspace effects and independent output verification through the existing project boundary. |
| Host integration | `HostRuntimeBinding` and issued verification reports | Frozen manifest, exact effect decisions, current-state verification, and distinct task-complete acceptance. |

The serving release can expose subscription-based intelligence discovery and
delivery while keeping these mechanisms internal. That public product choice
does not establish their integration or qualification. The ordinary public
solve path remains important internal acceptance evidence.

## Reproducer and recorded results

The complete source is [runtime-probes.py](runtime-probes.py). Run from the
repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python artifacts/architecture-audit-2026-09-19/runtime-probes.py
```

Baseline execution exited zero and reported `provider_calls: 0`. All eight
`finding_present` flags were true. A finding flag means a problem was
observed, not that a product acceptance check passed.

| Probe | Recorded result |
|---|---|
| `runtime-probe-01` | Before `hybrid`; after `deterministic`. |
| `runtime-probe-02` | Supervision `audit.custom` became `loop.supervision`; output `multiple, 2` became `single, null`. |
| `runtime-probe-03` | Empty permission set gained `audit_permission`; strict context refused. |
| `runtime-probe-04` | Same graph digest; output changed from 30 to 1020 after callable replacement. |
| `runtime-probe-05` | Validation true, no violations; declared external input implied 20, execution returned 30. |
| `runtime-probe-06` | Instruction path outside all generated mounts; native work mounted from the nested work directory. |
| `runtime-probe-07` | Default failover true, two providers selected; explicit false selected one. |
| `runtime-probe-08` | Five-millisecond budget, approximately 31.4 milliseconds elapsed, status succeeded, output act:done. |

No broad self-test or live integration claim is made by this audit run. Source
registration coverage, offline structural checks, an exercised callable path,
independent outcome qualification, and public-path integration must remain
separate status dimensions. `boundary_report` validates registration and
profile relationships; it does not execute the registered public paths.

## Exact coverage and exclusions

[runtime-coverage.json](runtime-coverage.json) is the machine-readable file
list. Source inspection concentrated on constructors, validators, dispatch,
ownership, fallbacks, argument and result contracts, and the reproducer's
existing fixture. Larger modules were read in relevant sections. Filename
searches and symbol inventories are not treated as whole-file review.

Not qualified here: actual provider readiness, real native instruction
loading, operating-system sandbox behavior, hosted authentication or billing,
tenant isolation, arbitrary schema compatibility, untrusted operation
execution, multi-process cancellation, or general performance. These remain
separate audits or explicit checks in the question register.

The baseline source hashes before authorized repairs are:

- `runtime_context.py`: `2c9042a989767ea10a3236cfcf75aaeaa20286df94c361b6487943edb0aec52f`.
- `recursive_loop.py`: `49afcafe932b9a409a7767eac5a6722d29f8e32ba8227c66b8b772b2570c5793`.
- `runtime-probes.py`: `a4cad7c911452ae0da3f8b519fad087b9ae28a7611aacaf3be71cf186c67b2f8`.

## Authorized runtime repairs and verification

The owner authorized implementation after this audit. Three runtime repairs
are now saved in the working tree. Findings 2, 3, and 7 above remain the
historical baseline; their reproduced behaviors are corrected.

- `runtime_context.py` retains the exact requested executor set, including
  an empty set, after derivation.
- `recursive_loop.py` uses `dataclasses.replace` when restricting modes, so
  supervision, output obligations, and future independent fields survive.
- Compatibility spawning now checks requested permissions against its owning
  context before creating the compatible service declarations. Existing
  compatibility capability construction remains available; it cannot grant
  missing permission names.

`loop_definition_checks.py` adds positive and negative checks, including an
actual two-output execution after mode restriction. It is the fortieth file
in the updated focused coverage list. No other runtime file was changed by
this first repair batch.

All six owning suites passed: recursive runtime 54/54, definition and context
25/25, mode control 19/19, delegation 28/28, Spawned Practitioner 1/1, and
kernel runtime 28/28. Total: 155/155. `git diff --check` was clean for these
files. The audit probes now report false for findings 1, 2, and 3 in their
probe numbering, and the other baseline observations remained reproducible
when this repair batch was checked.

[runtime-repair-mutants.py](runtime-repair-mutants.py) mutates methods only in
memory. Four separate mutants were detected: implicit deterministic executor,
removed permission check, reset supervision, and reset output obligation.
The last mutant also fails the executed-output-quota check. No source file
was rewritten by mutation testing.

Exact repaired source hashes:

- `runtime_context.py`: `46c608af8bb6269890f5082d6897cdfcd6f3c88c4ea7869c10490e6a5c83d417`.
- `recursive_loop.py`: `1325f58a48f70b1f5c93757bfee13fdd712ae4f5fe06aac96ba189d9ea97e235`.
- `loop_definition_checks.py`: `8ff69a2ae12c5735fb77dac5fb08a484584450bb7ca94097f2c6137b5cf8ac55`.

Full exported-tree verification, manifest updates, and integration are owned
by the coordinating session. No commit was made in this repair batch.

## Authorized graph and implementation-identity repairs

Findings 1 and 5 are now corrected for the declared supported execution
structures. Pipeline inputs come from the graph's actual external ports and
edges. Stages run when those dependencies are ready. A branch-and-join can
deliver several independent typed roles, and the returned result comes from
the declared external output ports. Groups continue to control ensembles and
fallback alternatives. Unsupported cross-group control bypasses and cyclic
stage scheduling refuse explicitly before execution.

Positive checks cover changed external input binding, reordered stage
presentation, branches and joins, multiple external input and output ports,
an early-stage external output, and a fallback with its own external input.
The original counterexample now returns 20, as its declared graph requires.
The Canvas renderer displays all external ports and each Loop's role,
versioned profile, mode, typed ports, continuation condition, and exit condition.

Compilation now creates a `solution_operation_identity/v1` record inside each
operation's exact Loop definition. The binding includes code, referenced
bindings, interpreter identity, and binding scope. It is checked before a
compiled run and again immediately before each operation invocation. Tests
refuse replaced registry entries, code changed in place, and replacement of a
later operation by an earlier operation. An equivalent function with the
same content identity remains usable. Compilation leaves the source graph
unchanged and does not silently overwrite an existing compiled binding.

The public function signatures and graph record shape remain available.
Historical graph records without operation identities remain readable, but
`run_compiled` refuses them until the caller explicitly compiles their graph
against the intended implementations. This is a new compilation, not a rewrite
of the historical artifact. A portable function binding was serialized and
successfully replayed in a fresh interpreter, producing 12 for input 5.

The identity mechanism is not Code Intelligence admission or a sandbox.
Opaque mutable host objects are explicitly process-bound. Their identity is
retained while their internal mutable state remains host-owned. Imported
module descriptors record name and version, not an independently qualified
digest of every transitive native dependency. Stronger qualification and
effect guarantees still belong to existing Code Intelligence and execution
authority contracts. The in-process callable registry remains trusted code.

Two coherent helper modules were created within `code_nodes`, with old imports
kept as facades. `solution_graph_execution.py` owns port values, dependency
scheduling, and execution identity projections. `solution_operation_identity.py`
owns the passive implementation identity record. No size exception was added.
At this checkpoint, `solution_canvas.py` has 786 lines and `solution_graph.py`
has 767 lines. The focused coverage list now contains 46 files; it still does
not claim whole-file correctness.

Checks passed: graph checks 28/28; Solution Canvas 45/45, which includes graph
checks; compiler 8/8; model port 17/17; Canvas-specific checks 17/17; playback
7/7; core engine proofs 6/6. These overlapping suite totals are not a count of
unique behaviors. One initial check command named a nonexistent `self_test`
entry in `solution_canvas_checks`; it was corrected to the existing
`solution_canvas_self_test_checks` and passed. There was no product failure
behind that command error.

[graph-repair-mutants.py](graph-repair-mutants.py) detected all eight mutants:
sequential value handoff, stage-list scheduling, ignored output bindings,
ignored code identity, skipped invocation validation, silent implementation
rebinding, duplicate external input binding, and removed control-topology
validation. Two mutants produced exceptions on otherwise valid graph fixtures;
the others produced named failing checks. Mutants changed methods in memory
only and made zero provider calls.

The combined audit probes now show the five repaired failures absent. The
coordinating session changed the harness instruction-material contract while
this work proceeded, so the old synthetic mount fixture is explicitly marked
superseded and unknown, rather than asserting a result from field presence.
Its real binding and native loading checks belong to that separate repair.

Graph source hashes at this settled checkpoint:

| File | SHA-256 |
|---|---|
| `solution_canvas.py` | `2d8a35ff1259fa8804d5ba55af0f29bb16e1af6a3815de6b3b4b4cb9253c8df8` |
| `solution_graph.py` | `2a5ff1a0385c4d64731a77642c9d35020c5df937fd4afffb9b4a828a6a16fdeb` |
| `solution_graph_validation.py` | `4ad66e450a2891b60abb968d5341c19e67149bf1258608d6d8a2e174976bccb7` |
| `solution_compiler.py` | `29036221c846ab9e70ad235fa1bfd19b85925b42f62656c4c673040c2fa89634` |
| `solution_graph_checks.py` | `40c32e851f629aaf497ca9982b51f1722f5407a16159ad34e20bf347363c11c9` |
| `solution_graph_execution.py` | `8181a0af94ea97b9b04a3ae9aaedac726743203fdb6926e8242a460b615bc2f3` |
| `solution_operation_identity.py` | `e1f7cf67e44fdb7d17db4d5ddfbfc8aa767f0749454d4d3b44c44315be88b36b` |

## Authorized synchronous-deadline and failover repairs

Findings 6 and 8 are now corrected within their stated scope. Synchronous
dispatch measures elapsed time from admission through callback return. If the
deadline expires before dispatch, the callback does not start. If an admitted
callback result arrives late, its outputs, summary, and counters remain in a
failed result with `DEADLINE_EXCEEDED`. It is not published as success.

A versioned `SpawnedDeadlineAssessment` records whether the callback returned,
elapsed time, the deadline, and the enforcement phase. It explicitly records
that physical cancellation was not confirmed and replay was not authorized.
Effects from a late callback remain unreconciled. The synchronous interface
cannot preempt arbitrary Python code; `require_preemptive_deadline=True`
therefore refuses before spawning or invoking the callback. This requirement
is also forwarded by `spawn_practitioner_loop`. Existing asynchronous timeout
handling remains cooperative and is not claimed to terminate arbitrary
physical work.

The new `loop/spawned_deadline.py` contains deadline observations and the
existing synchronous and asynchronous dispatch mechanics. Existing methods
remain facades over the same manager and canonical Loop. The owning checks
are in `loop/spawned_deadline_checks.py`, collected by the existing delegation
suite. `delegation_runtime.py` is reduced to 779 lines, without a size exception.

`ModelGatewayConfig.allow_failover` now defaults to `False`. A route list or
discovered alternative does not itself authorize another provider attempt.
Explicit `allow_failover=True` remains supported, and authentication refusal,
token accounting, remaining-budget checks, and the independent evaluator
permission remain tested. Three accounting fixtures initially failed because
they described authorized failover without setting that permission. Those
fixtures and the two-route evaluator fixture now set it explicitly. Expected
usage, failure, and evaluation assertions were preserved. The authentication
test also grants ordinary failover so that its stronger refusal remains tested.

Owning checks passed: delegation 35/35, Spawned Practitioner 1/1, gateway 22/22,
gateway accounting 33/33, harness fallback 55/55, harness selection 31/31, and
model port 17/17. Seven separate in-memory mutants in
[deadline-failover-mutants.py](deadline-failover-mutants.py) were detected:
late success, discarded late outputs, false cancellation, callback replay,
ignored preemption requirement, implicit failover, and ignored explicit
failover authority. The mutation harness retains the same injected clock for
mutated methods, so deadline failures are not caused by a changed test clock.

The combined audit now reproduces none of the seven defects assigned to this
agent. The old instruction-mount fixture remains marked superseded and unknown
because the coordinating session owns its new binding checks. The generic
default delegation executor still returns structural `act:done`; this work
does not turn that fixture into an arbitrary-task solver.

The focused coverage list now contains 50 inspected files. Full exported-tree
integration and the architecture-map registrations remain with the
coordinating session. No provider was called and no commit was made.

| Changed file | SHA-256 at this checkpoint |
|---|---|
| `loop/delegation_runtime.py` | `d8a20d6b30da9006fd60a66477de672c50a90c61008e70c12898abfe7cf92a86` |
| `loop/spawned_practitioner.py` | `68cd7bad11162ec23e23dd3ae5dd8836dd231d928f8a87dc469ec82ceb57ef45` |
| `loop/delegation_runtime_checks.py` | `f0636570a4d7a60e97f75fd1045dd80883b3b87ff3e352b4af8e295f343ccb3e` |
| `loop/spawned_deadline.py` | `db0b835578bab3ce088dc0510c461bb476367ac6dbfa4e7ba3f098ca74fe29cf` |
| `loop/spawned_deadline_checks.py` | `7a80ab47cbf9c628829d0c3a5a6165a894f598ba33a6131e94d62dd2167f2692` |
| `core/model_gateway.py` | `04bb94a757b18e0711edaf3c7fb6bda8fcb8789e01a2a13acffbcd4287c8d8c0` |
| `core/model_gateway_accounting_checks.py` | `0815f7ae8fadf70181024c3b99070367c3474ac70f763203254eeff0e4719005` |
| `core/harness_selection_checks.py` | `983635365d5792bfcddfed20c9f630be26bc3571a612e379ab3a6807128be50c` |

## Current graph contract after the pre-launch policy change

The owner subsequently rejected legacy reader and compatibility-only forwarding
requirements. The earlier graph checkpoint above remains historical evidence,
not the current reader contract. Current graphs emit and accept
`loop_graph_definition/v2`. The old compiled specification reader was removed,
and the compiler checks explicitly refuse the old specification encoding and
version 1 graph records. `SolutionSpec` uses `permitted_loop_modes`; its old
constructor-only `allowed_modes` alias was removed and the example caller was
updated. Callers import `SolutionOperationIdentity` from its owning module,
not from a forwarding graph import. Existing graph construction convenience
functions that produce the current typed contract remain supported.

Graph checks 28/28, Canvas checks 45/45, and compiler checks 8/8 passed after
this change. Historical files were not migrated or rewritten. The two newly
extracted module descriptions now include their ownership and limits.

## Public assignment-folder provisioning checkpoint

The public `SolveRequest` now carries a named, immutable
`HarnessProvisioningConfiguration`. Dependency assembly passes that exact
object, and request adaptation binds its content digest into the source-state
identity. Both scope allocation and folder preparation recheck the admitted
configuration identity. The helper lives in `core/practitioner_runtime`, with
no import back into the adaptive request-record module.

The configuration snapshots catalogue reference metadata and guardrail rules
as canonical JSON, separately identifies absent and deliberately empty
catalogues, pins each selected resource's identity, digest, source layer, and
source reference, and supports exact assignment-identifier overrides. Mutating
the caller's original catalogue or rules does not change the snapshot.
Materializing a snapshot returns fresh typed metadata objects. It does not
materialize resource bodies or install executable code.

Assignment behavior is now an explicit reason or build choice. It is no longer
inferred from a file-write flag. A reason choice narrows actual Spawned
Practitioner workspace-write and sandbox-command permissions; a build choice
does not create those permissions. Model authority in assignment instructions
requires an installed model session and a compatible run mode. Preparation
writes have a separate explicit Boolean grant. None of these settings grants
network access, spending, candidate-code admission, or native control.

An absent configuration records `not_configured` and writes no assignment
folder. An explicit assignment-only configuration can prepare the folder while
reporting absent intelligence. With selected eligible references, the public
path creates the atomic assignment folder, typed task record, supported
instruction filenames, and provisioning record before child execution.
Guardrail refusal and preparation-authority refusal prevent the child resolver
from running. Per-assignment decisions, including absence and refusal, remain
in returned summaries, Run History, and the saved public outcome.

An arbitrary host capability binding is an independent authority boundary.
For a configured reason assignment, a binding that declares effects beyond
filesystem reads is refused because the existing host adapter has no general
per-assignment narrowing mechanism. This is an explicit unsupported
combination, not evidence that prompt instructions constrain host effects.

The public result explicitly records zero installed resource bodies,
`resource_admission_established=False`, and `native_loading_observed=False`.
Catalogue membership and digest pinning are not independent Code Intelligence
admission. This checkpoint does not claim that a native harness read the
prepared assignment folder, that wrapper composition is executable, or that
task outcome quality improved. Native process control and materialization
remain governed by their existing separate boundaries.

Only `before_provisioning` guardrails are enforced by this connector.
`before_effect` rules are explicitly labelled as guidance-only instruction
text, not effect or dispatch enforcement. Supplied `before_dispatch`,
`on_output`, and `before_publication` rules refuse configuration because this
connector has no installed owning path for those points. Their future
integration belongs at the existing dispatch, result, and publication
boundaries rather than in a provisioning prompt.

Offline checks passed: public provisioning 9/9; spawned provisioning 18/18;
adaptive scope 37/37; request adaptation 20/20; public solve 28/28, including
the nine provisioning checks; dependency bindings 50/50; adaptive Practitioner
66/66; node provisioning 14/14; instruction composition 9/9; harness catalogue
7/7; guardrails 7/7; core engine proofs 6/6; extracted-helper import boundaries
3/3. These suite totals overlap and are not a unique behavior count.

The current-only outcome test now rejects version 3, 4, 5, and an unknown
future version while retaining the version 6 round trip and malformed-record
checks. This aligns the public adapter check with the storage agent's current
reader policy; it does not rewrite historical outcomes.

[provisioning-mutants.py](provisioning-mutants.py) detects fourteen in-memory
mutants: omitted public wiring, omitted request identity, unauthorized
preparation, role inferred from writes, ignored exact pins, unselected
references, retained reason-write permissions, dropped guardrails, invented
native loading, invented model authority, ignored assignment overrides, and
skipped configuration revalidation, accepted unsupported guardrail points,
and guidance presented as enforcement. The first mutation run retained imported
function aliases and therefore missed several mutations. The test harness now
patches the actual calling bindings, and the corrected run detected all fourteen.
No provider calls, native processes, commits, or external effects were used.

Files added in this checkpoint are
`core/practitioner_runtime/provisioning.py`,
`core/spawned_provisioning_checks.py`, and
`code_nodes/solve_provisioning_checks.py`. The coordinating session owns their
architecture-map registration and the full exported-tree integration run.
The focused coverage list now includes the files inspected for this work; it
still does not claim full-file correctness or a repository-wide review.

The validated coverage list contains 62 unique existing paths. The question
register contains 97 unique questions: 82 answered, three disputed, and twelve
open. A resolved question retains its historical evidence and separately
names the corrective observation. The shared request-record file includes
the coordinating session's extraction edits; its whole-file hash below does
not assign those changes to this agent.

| Provisioning checkpoint file | SHA-256 |
|---|---|
| `core/practitioner_runtime/provisioning.py` | `29bbe0ee1585deb1660ab300a00921b99e0d9f75b3036f22e39265888c182559` |
| `core/spawned_provisioning.py` | `7f4d11ed5c81b2dc5d1f6d48b0962afef787fa5ad1cefd60828099cbec796dcb` |
| `core/spawned_provisioning_checks.py` | `4a2d52485e99e836553f88b5223b3aec3cc655b74c058db6617c45bdba5c5c54` |
| `core/adaptive_practitioner_scope.py` | `936a9a71b451c8386b949510b4bc687da1f5f10be602a415729f9d280069ddea` |
| `core/adaptive_practitioner_scope_checks.py` | `2bd5db7e7ec76a24b57e7776c83331271c55ffb416b4663a7eae7abea572d9e6` |
| `core/adaptive_practitioner_records.py` | `88092b749d4389d889543b0ffe09adef9dfb8ae11f6998caf3a5fcd1c8d01ddc` |
| `core/node_provisioning.py` | `ce77e0abb85869561c0ec8846c5fde29ba78b7601fe063b3277e9c0a6da5d5df` |
| `code_nodes/solve_runtime.py` | `60fbf01f47e0b18041f1481b3896ea4631e118fe8372704858f09a8387321f75` |
| `code_nodes/solve_request_adaptation.py` | `90c7451c58df4be3e5372b2d3e5d5a1d1973da8aac813ba20246b7903c4a189f` |
| `code_nodes/solve_provisioning_checks.py` | `2bb1e0da969ea220eebb00b43cdf65b4a940065de3a25d92cd4991386f789d01` |
| `core/practitioner_runtime/README.md` | `8a50e6de3563c29305e0985604fe2d87a1abf29d001e2bde008edc4c55f9cbf5` |
