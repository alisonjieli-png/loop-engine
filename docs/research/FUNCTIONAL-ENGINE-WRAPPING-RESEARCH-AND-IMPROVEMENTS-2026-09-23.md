# Functional engine wrapping: research and proposed improvements

Checked September 23, 2026. This report extends
[Engines behind fixed edges](../architecture/ENGINES-BEHIND-FIXED-EDGES.md)
and [layered harness wrappers](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md).
It does not establish a competing architecture standard or activate new engines.
The task authority remains roadmap D-19 and its existing steps.

The owner's supplied explanation is the starting point. The separate artifact
`Baltor_Functional_Component_Standard_v0.1.md` and its reported four schemas
and 42 checks were not available locally. Those counts are unverified here.
Repository inspection used source checkpoint
`390643ef42518edcd8df88a1d9b972ea9fe2c104`; the concurrent documentation commit
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4` was also incorporated. External sources
below are primary documentation, source repositories and papers. Research
inferences and proposed extensions are identified separately from working code.

## Recommendation

Keep the component, edge contract, engine, adapter and deployment distinctions.
Strengthen the definition of an engine to include the behavior it must preserve:

> A functional engine is a replaceable implementation behind a versioned
> component contract. It is eligible only for the scope in which its behavior,
> permissions, dependencies, limits and failure handling satisfy that contract.

This is proposed Baltor terminology. Use **Harness Working Directory Compiler**
for the component that prepares a harness workspace, and **Harness Working
Directory Package** and **Harness Working Directory File** for its material.
Preserve existing code and serialized identities such as `CataloguePackage`.

The highest-value improvement is a shared behavioral qualification kit for each
engine slot. Returning the expected JSON is insufficient when an engine changes
ordering, consistency, binary bytes, permissions, side effects or completion.
Keep a small direct implementation as a comparison baseline and qualify each
external and native implementation independently.

## Architectural placement

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

An engine is an implementation used by an owning Loop. A profile, package,
installation and binding are passive records. An internal wrapper needs a
separate Loop only when its work requires independent governance. Source
repositories, Docker containers and individual helper functions do not each
become executable graph vertices merely because they are replaceable.

```text
Functional component, governed by its existing owning Loop
├── Versioned edge contract exposed to callers
├── Selection and enforcement owned by the component
│   ├── eligible installations and qualified behavior
│   ├── explicit preference and permitted fallback
│   └── authority, cumulative accounting and independent acceptance
├── Selected engine composition
│   ├── exact adapter and implementation identities
│   ├── ordered wrappers and their control ownership
│   ├── native protocol and invocation mechanism
│   └── dependencies, deployment and state binding
└── Existing Run History and artifact contracts
    ├── selection decision and observed execution
    ├── candidate outputs and validation
    └── failures, unknown effects and continuation
```

The structure above is component containment. It adds no runtime, public
capability group, intelligence layer, universal registry or separate event store.

## What to clarify in the six-part model

| Concept | Precise meaning | Compiler example |
| --- | --- | --- |
| Functional component | One responsibility and its owning boundary | Harness Working Directory Compiler |
| Edge contract | Versioned request, result, behavior and interaction obligations | Selected packages and target profile produce a proposed placement with explicit losses or refusals |
| Engine slot | The component's replaceable implementation position | Existing `material_install_layout` candidate slot |
| Engine | A concrete implementation with explicit candidate or qualified status | Direct Baltor placement or an Agent Harness renderer adapter |
| Adapter | Code translating the operation to the selected implementation | Build upstream inputs, invoke an exact renderer and normalize its result |
| Harness compatibility profile | Data describing a native interface/version, discovery behavior and evidence status | Required filename, loading phase, precedence and probe evidence |
| Execution binding | The resolved way this invocation reaches the implementation | Direct function or supervised subprocess with a specific protocol |
| Installation and deployment | Available executable/dependencies and where they run | Pinned package in a local worker or a container image |
| State binding | State owner, format, generation and permitted lifetime | Fresh attempt workspace or an explicitly persistent index |
| Qualification | Evidence for this exact implementation and required behavior | Byte preservation, conflict handling and native loading tests |

The original binding list mixes several dimensions. HTTP is a transport;
MCP is an application protocol; subprocess describes a process relationship;
Wasm describes an executable format/runtime interface. Store these separately.
A Wasm component may run in a subprocess exposed over HTTP without creating
three alternative implementations of the underlying algorithm.

Likewise, a model by itself is not an executable integration. A configured
model route, adapter, request contract and authorized invocation provide the
callable implementation. Deterministic, hybrid and non-deterministic remain
Loop modes. A filename or engine label grants no model authority.

## 1. Preserve behavior, beyond the type signature

Liskov and Wing distinguish compatible method signatures from preservation of
the properties a caller relies on, including state invariants and history
constraints. Applying that principle to engine replacement is an engineering
inference: the engine must preserve the guarantees of the particular operation.
Their paper does not establish performance or liveness guarantees for Baltor.
[Behavioral subtyping paper](https://www.cs.cmu.edu/~wing/publications/LiskovWing94.pdf).

Declare applicable obligations at each existing edge:

- Input meaning: units, encoding, null handling, ordering and identity.
- Output meaning: exact versus approximate results, quality floor and freshness.
- State: consistency, transaction scope, cursor lifetime and read-after-write.
- Effects: permitted destinations, mutation domain and idempotency behavior.
- Failure: partial outputs, unknown outcomes, recoverability and cancellation.
- Acceptance: independent checks and the evidence needed to publish an output.

Examples: a queue cannot silently become a stack; eventual consistency cannot
replace a required immediate read; a retrieval score cannot substitute for a
relevance guarantee; UTF-8 decoding cannot preserve an arbitrary binary asset.
These obligations are specific to the component. Avoid a universal request
dictionary that erases the useful distinctions among components.

Pact is useful for checking communication expectations between services. Its
own documentation distinguishes these checks from functional tests of actual
effects. Baltor needs both communication and behavioral checks where applicable.
[Pact testing scope](https://docs.pact.io/consumer/contract_tests_not_functional_tests).

## 2. Separate identity, compatibility, authority and approval

An immutable package digest identifies bytes. A signature can establish an
authenticated assertion about those bytes. Provenance can describe their build.
Qualification establishes bounded behavioral evidence. Current authority permits
this caller to perform this action. None of these facts implies the others.
[OCI descriptors](https://github.com/opencontainers/image-spec/blob/v1.1.1/descriptor.md),
[SLSA verification](https://slsa.dev/spec/v1.2/verifying-artifacts).

Bind the existing engine records to separately identified facts:

| Identity or condition | Why it matters |
| --- | --- |
| Edge contract and engine protocol versions | Callers and implementations can evolve independently |
| Implementation, adapter and dependency digests | A stable package name does not freeze executable behavior |
| Installation settings and wrapper order | The same binary can behave differently under different configuration |
| Native harness interface and exact release | CLI, editor, SDK and hosted interfaces can expose different controls |
| Target profile and required capabilities | A documented optional feature may be essential for this step |
| State schema and generation | Prevent an old cursor or index from being interpreted under a new binding |
| Qualification scope and current lifecycle | A withdrawn or expired qualification must invalidate cached eligibility |
| Current authority and data recipient | Selection cannot expand access or disclose material to a new destination |

These are proposed refinements to existing owners, not a new universal record
to bypass them. Reuse `EngineDescriptor`, `EngineInstallation`,
`EngineQualification`, `SelectionScope` and the component's native declaration.
Version a changed active contract and update its readers together.

HashiCorp go-plugin is a useful subprocess integration reference: its handshake
separates core protocol from application protocol. Its magic cookie is a launch
check, explicitly not authentication. It illustrates why a successful handshake
alone cannot authorize an engine.
[Handshake design](https://github.com/hashicorp/go-plugin/blob/main/docs/internals.md),
[handshake source](https://github.com/hashicorp/go-plugin/blob/main/server.go).

## 3. Make initialization and switching explicit

Scheduled research detects potential drift. Qualification checks an exact
candidate. Initialization negotiates a usable binding. The operation boundary
checks that binding and current authority at use. A daily documentation fetch
cannot replace any of the last three activities.

Discovery reads approved metadata without executing an unknown plugin. Starting
a binary to ask for capabilities is execution and needs its declared limits.
An authenticated network health probe has network and credential effects even
when it performs no business mutation. Bind its observations to a timestamp and
expiry; availability is not a timeless property of an implementation digest.

OpenFeature offers a useful lifecycle example: initialize a provider before
use, expose readiness/error states, and shut down a replaced provider when it
is no longer used. Adopt the ownership pattern where relevant; do not adopt
feature-flag fallback behavior as a general rule for task execution.
[Provider lifecycle](https://openfeature.dev/specification/sections/providers/),
[provider replacement](https://openfeature.dev/specification/sections/flag-evaluation/).

Choose the binding lifetime per operation:

| State scope | Permitted change point | Required evidence |
| --- | --- | --- |
| Independent stateless call | Next call after eligibility checks | No hidden cross-call state |
| Transaction or stream | Completion, confirmed quiescence with reconciled effects, or a supported transfer | Ordering, partial-delivery and transaction semantics |
| Harness session | Fresh attempt by default; explicit supported continuation | Workspace and conversation identities remain distinct |
| Persistent index or database | Qualified migration with an atomic owner switch | State schema, source population, permissions and recovery |
| Durable workflow | Compatible replay/version transition | Saved history and new code remain compatible |

A stateful transition may require draining work, fencing the old writer,
exporting a logical snapshot, validating it, importing it, and conditionally
switching the active reference. Rollback can require a reverse migration or
reconciliation; selecting the previous image cannot undo committed writes.
Temporal's replay requirements illustrate why arbitrary code replacement is
not automatically compatible with durable history.
[Workflow determinism](https://docs.temporal.io/workflow-definition).

In-flight bindings normally remain fixed. A revoked permission or known unsafe
engine may still require termination under supervisor policy. Preserve the
historical binding and record the interruption instead of rewriting history.

## 4. Give nested wrappers explicit control ownership

Keep wrappers focused, but judge them by responsibility and behavior rather
than a line-count target. A protocol adapter can require substantial error,
streaming and authentication logic while preserving a small public interface.

Each composition should declare which component owns initialization, retries,
timeouts, cancellation, resource release, credentials, accounting and acceptance.
Record wrapper identities and order. A transform before instruction loading has
a different effect from the same transform after the harness has initialized.
Pluggy's explicit hook ordering and around-call wrappers are useful Python
precedents; importing a plugin still runs ordinary Python with host privileges.
[Pluggy specification and wrappers](https://pluggy.readthedocs.io/en/stable/).

Assign one retry owner for each failure class and effect. A provider SDK may
have transport retries while the supervisor owns semantic repair, but their
attempt accounting and remaining deadline must compose. Disable hidden retries
or expose them accurately. A timeout after an external write is an unknown
effect until reconciled, not permission to try another engine.

Bind idempotency to the caller's logical intent, tenant, target and request.
Two intentional actions can have identical parameters; hashing parameters alone
does not distinguish them. A retry keeps the operation identity and receives a
new attempt identity. Changing engines may change the deduplication domain,
so reusing the same key is insufficient evidence that repetition is safe.
[AWS idempotent API design](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/).

Cancellation request, cancellation acknowledgment, local process termination
and confirmed cessation of remote effects are different observations. Keep
unknowns explicit. gRPC documents that cancellation cannot roll back preceding
changes. This remains true when another wrapper hides the transport.
[gRPC cancellation](https://grpc.io/docs/guides/cancellation/).

Nested calls receive the remaining deadline, not a fresh timeout. Use a
monotonic clock locally; a machine-local monotonic timestamp is not portable
across hosts or restarts. Give queueing, credential refresh and cleanup explicit
budget treatment. Fence late writers with the current state generation when
ownership changes. Existing synchronous callback deadlines are non-preemptive
acceptance deadlines; a wrapper must not claim that they terminate execution.
[gRPC deadlines](https://grpc.io/docs/guides/deadlines/).

Nested engine selection must terminate. Resolve a finite composition with
explicit dependencies and refuse accidental recursive bindings. A deliberate
iterative task remains work of a governed Loop with continuation and exit
conditions. Do not have an unbounded chain of selectors selecting selectors.

## 5. Use measured selection without claiming universal optimality

The proposed PIN, PREFER and AUTO names can be useful descriptions. They are
not a universal standard or three new Loop modes. Existing records already
include `pin`, `prefer`, `exclude`, `declared_order_only` and `objective`.
`AUTO` is not an implemented general selector in the inspected tree.

There is also a concrete PREFER distinction to settle. Existing
`ExplicitOrderPreference` refuses an identity absent from its eligible
snapshot. Softly skipping a known but unavailable preferred installation would
require deliberate resolver behavior that records the omission. Continue to
reject unknown identities and invalid configuration. A preference by itself
never authorizes failover or another paid attempt.

Use the existing parameter-precedence owner. Project and user scope are useful
product concepts, but they are not a new parallel hierarchy to insert around
`ParameterSourceKind`. Bind a sender's claimed precedence to trusted caller
context; a supplied field saying explicit invocation is not proof of its origin.

Apply the following order through the existing framework:

1. Resolve explicit caller requirements and permitted narrowing preferences.
2. Exclude incompatible, disabled, unqualified or unauthorized installations.
3. Preserve an exact pin, or follow the permitted ordered choices.
4. Use reviewed, comparable evidence only under the configured evidence rule.
5. Record the selection and rejected alternatives before dispatch.
6. Revalidate at use; preserve consumed authority across any permitted fallback.

Success means accepted work under the customer's constraints. The objective can
include quality, elapsed time, money, memory, privacy and availability. Fewer
tokens or fewer wrappers are not universal goals. Record the objective's units,
quality floor and tradeoffs before measuring. Include initialization, copying,
serialization, queueing, retries, verification and failed work in comparisons.

Use matched tasks, evaluator, model route and environment where the comparison
depends on them. Retain failures and unknown usage. Insufficient evidence keeps
the declared order; it does not justify an invented optimality claim. The
existing design restricts generalized learned ranking. Any later relaxation
needs a separate reviewed change and discriminating evidence.

Selection across several components can interact: an inexpensive embedding
engine can force a costly reindex, or a fast compiler can produce a workspace
that starts slowly. First enforce compatibility among the selected bindings.
Then measure the composed operation as well as each part. Selection work must
consume a bounded share of the same overall resources.

## 6. Make the compiler return an inspectable proposal

Keep the existing compiler and materializer ownership:

```text
Selected approved packages and exact harness compatibility profile
    → dependency and capability resolution
    → eligible compiler engine
    → proposed native files, transformation report and explicit refusals
    → independent package/path/effect checks
    → authorized confined materialization
    → observed native discovery and activation
    → harness execution
    → independent task validation and Run History
```

This is a lifecycle, not a second operational graph. The direct Baltor compiler
and the proposed Agent Harness adapter should return equivalent existing
package/placement concepts. Avoid introducing an unrelated `ArtifactBundle`
store. Compilation that writes a scratch folder has filesystem effects even
when it leaves the customer workspace unchanged.

The [pinned Agent Harness audit](MADEBYWILD-AGENT-HARNESS-ARCHITECTURE-AND-OWNERSHIP-2026-09-23.md)
found binary conversion, unsafe path/ownership behavior and incomplete preset
inheritance. The [compatibility audit](MADEBYWILD-AGENT-HARNESS-COMPATIBILITY-AND-ADOPTION-2026-09-23.md)
also found unsupported provider features. Use an isolated compilation workspace
and the shared confined writer before considering upstream `apply` in customer
directories. The source is pinned at
`2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17`; these findings do not characterize
every future release.

The proposed transformation report records each requirement as preserved,
translated, externally enforced, unsupported or unknown, with exact evidence.
Required losses refuse. Optional losses require explicit policy and remain
visible. Do not silently remove a hook or replace enforced policy with prose.

Preserve the distinction between reviewed source material and its rendered
bytes. Installing a transformed file as approved library material requires a
qualified, explicitly permitted derivation or independent review of the exact
output. Record the source approval, transformation identity and rendered digest.
Fresh task-specific instructions have their own assignment/authority binding;
they do not become approved reusable library material through compilation.

| File or resource | Compiler obligation | Separate runtime qualification |
| --- | --- | --- |
| Instructions and task context | Preserve essential task/acceptance meaning; render native entry point | Precedence, inheritance and actual loading |
| Skills and references | Preserve names, descriptions and relative dependencies | Discovery versus activation; referenced resources available |
| Scripts and compiled binaries | Exact bytes, executable metadata, runtime and platform requirements | Supported interpreter/ABI and confined invocation |
| Wasm components | Exact component and declared imports/exports | Runtime feature set, host capabilities and resource limits |
| Hooks and plugins | Preserve lifecycle event and required behavior | Host-specific activation and enforcement |
| MCP configuration | Translate protocol connection fields without embedded secrets | Connection, authentication, negotiated features and selected tools |
| Schemas and validators | Preserve schema version and local dependency closure | Structural and semantic checks actually run |
| Code graphs and indexes | Bind source snapshot, index format and embedding settings | Freshness, permission filtering and query compatibility |
| Handoff and state files | Preserve task identity, accepted upstream artifacts and open issues | Explicit consumer loading; a filename alone establishes nothing |

## 7. Treat plugin composition as a first-class compatibility problem

The published Agent Plugins 1.0.0 specification defines portable skills and
MCP configuration; other types use client-specific extensions. It permits
some invalid or unsupported components to be skipped while the remaining
plugin loads. A Baltor step requiring such a component must refuse even when
the external loader follows its own specification correctly. Keep external
format validity and Baltor eligibility as separate findings. Version 1.1.0 was
still a working draft when inspected.
[Published specification](https://agent-plugins.org/specification),
[working draft](https://github.com/agentplugins/agent-plugins-spec/blob/main/spec/1.1.0.md).

A September 20 preprint, *Packaged, But Not Portable*, studies public GitHub
plugin manifests and highlights capability-name collisions, duplicated manifest
drift and missing composition semantics. Its measurements concern a discovered
static corpus, not native execution, customer incidence or Baltor compatibility;
the experiments were not reproduced here. It is useful research input for
qualified names, explicit conflicts and testing installed combinations.
[Paper, version 1](https://arxiv.org/html/2609.23809v1).

Proposed Baltor behavior: retain canonical package/file identities, generate
explicit native aliases, detect dependency and path conflicts before writing,
and preserve provenance across projections. Never let installation or traversal
order silently choose among different implementations of the same required
capability. Test the selected package set as well as individual packages.

## 8. Choose the lightest qualified execution binding

These are composable deployment patterns, not mutually exclusive values of one
field. Keep invocation mechanism, application protocol, runtime and isolation
separate in the actual binding.

| Binding pattern | Useful starting case | Qualification requirement |
| --- | --- | --- |
| Direct function | Trusted deterministic transform in the same process | Contract, effects and shared-state discipline |
| Supervised subprocess | Existing CLI or language/runtime separation | Exact executable, bounded environment, process tree and output limits |
| Wasm Component Model | Portable constrained computation with a small host interface | Exact WIT world, runtime/toolchain, imports and budgets |
| MCP or purpose-specific HTTP | Existing tool/service boundary | Exact protocol, authenticated endpoint, data recipients and failure semantics |
| Container or isolated worker | Untrusted dependencies or stronger process/filesystem separation | Actual isolation configuration, resource limits and deployment evidence |

WIT describes typed imports, exports and resources. It does not establish
algorithm correctness or a portable checkpoint for arbitrary resource handles.
An embedding can grant broad access through its host functions, so qualify the
imports and their transitive effects as well as the guest.
[WIT](https://github.com/WebAssembly/component-model/blob/main/design/mvp/WIT.md),
[Wasmtime security](https://docs.wasmtime.dev/security.html).

For large tabular inputs, Arrow illustrates another useful distinction:
its C Data Interface shares data across runtimes within a process, while IPC
supports cross-process exchange and persistence. Reuse an appropriate existing
representation rather than serializing every large payload through JSON.
[Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html).

Containerization remains selectable. The default fresh harness per step does
not require a new database, credential service or container for every helper
call. Shared services need explicit tenant/run scope and reset guarantees.

## 9. Keep credentials and endpoint location outside package bodies

Use a typed credential reference resolved by the authorized host at execution.
The proposed broker must bind the lease to caller, endpoint, operation, expiry
and permitted scope. Record the reference and observed authorization result,
never the secret. A fallback engine may need a different grant or recipient;
sharing a contract does not authorize credential forwarding.

For local endpoints, declare which machine and network namespace owns the
address. `127.0.0.1` inside a container or hosted worker refers to that runtime.
An explicit local executor or authenticated customer connector is needed to
reach the customer's machine. Reject silent rewriting to another address or
forwarding credentials across an unapproved redirect.

The package format itself is not a secrets manager. Agent Plugins 1.0.0 treats
configured headers and environment values as visible package data and leaves
authorization storage to the client. Baltor's credential-broker work remains
under S-6.61; this research does not claim it is implemented.
[Agent Plugins authorization and configuration](https://agent-plugins.org/specification).

Existing `core.credential_leases.LeaseBroker` primitives track instance and
scope metadata, but resolving a lease ID alone does not authenticate the caller
as that instance. The future transport must enforce that association and the
requested operation. Keep token audiences distinct when bridging protocols;
MCP HTTP authorization forbids forwarding a client's token through to another
service as a substitute for that service's authorization.
[MCP authorization, 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).

## 10. Preserve authoritative accounting across observability wrappers

Reuse Run History as the authoritative record. Telemetry is a projection with a
versioned mapping and stated omissions. Keep requested versus observed model,
logical operations versus physical sends, and reported versus measured usage
separate. Deduplicate by canonical operation/attempt identities before summing
cost. Missing provider usage stays unknown.

OpenTelemetry's HTTP conventions describe physical request attempts, while the
GenAI client operation can encompass automatic retries. Summing both levels
would double-count the same work. The GenAI conventions are in a separate
repository and marked Development at the inspected commit. Pin that mapping;
do not invent a stable schema URL or log raw prompts and credentials by default.
[HTTP conventions, v1.44.0](https://github.com/open-telemetry/semantic-conventions/blob/v1.44.0/docs/http/http-spans.md),
[GenAI conventions at 8ffdf568](https://github.com/open-telemetry/semantic-conventions-genai/blob/8ffdf568e1b4391a99adb081db16e8102e36918e/docs/gen-ai/gen-ai-spans.md).

The inspected `core.otel_export` projects model events to zero-duration spans.
That representation does not establish measured model latency. Extend existing
measurement ownership before using such a projection to rank engines.

## 11. Actual repository status

The inspected slot catalogue has 45 declarations: 38 candidate, seven planned,
zero active. These are shared-framework adoption states. Several underlying
components already have working implementations and local selection behavior.
The catalogue itself does not construct or dispatch engines.

| Existing source owner | Observed implementation | Boundary of the claim |
| --- | --- | --- |
| [Shared records](../../src/loop_engine/core/engines/records.py) and [selection records](../../src/loop_engine/core/engines/selection_records.py) | Versioned descriptors, installation/policy/decision shapes and checks | Passive records; no generic `core/engines/selection.py` dispatcher |
| [Slot catalogue](../../src/loop_engine/data/engine_slots.yaml) and [joins](../../src/loop_engine/core/engines/slot_index.py) | Source-level slot, registry, boundary and suite checks | Declaration is separate from runtime adoption |
| [Preference resolution](../../src/loop_engine/core/configuration_preferences.py) | Eligible snapshots, ordered ranking bindings, bounded fallback and cycle detection | Reuse this owner; it is not already applied to every component |
| [Harness selection](../../src/loop_engine/core/harness_selection.py) | Matched independently reviewed evidence or declared order | Existing quality-first ranking differs from a universal overhead optimizer |
| [Model gateway](../../src/loop_engine/core/model_gateway.py) | Typed routes, configuration and explicit failover policy | Its working selection is component-specific |
| [Host operations](../../src/loop_engine/core/host_runtime.py) | Pinned callbacks, state and input/output/effect checks | Trusts embedding host; not a qualified remote plugin platform |
| [Retrieval bindings](../../src/loop_engine/core/retrieval_backends.py) | Lexical/vector extension contract and embedding identity | [Hosted search](../../src/loop_engine/core/service_runtime/catalogue_search.py) still has a separate fixed index path |
| [Library ingestion](../../src/loop_engine/core/library_ingestion/selection.py) | Local effect-free availability selection and declared order | Not general evidence-based AUTO |
| [Storage handshake](../../src/loop_engine/catalog/handshake.py) | Capability negotiation with explicit refusal/limited access | Does not migrate live data or transactions |
| [Layered wrapper design](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md) | Typed configuration foundations exist | Nonempty layer compositions/native-owned controls remain unavailable in the executor |
| [Compiler prototype](HARNESS-WORKING-DIRECTORY-COMPILER-PURE-PREVIEW-PROTOTYPE-2026-09-23.md) | Isolated package-preview experiment around existing types | Artifact-only; not a production Agent Harness compiler integration |
| [Credential leases](../../src/loop_engine/core/credential_leases.py) | Host-side lease primitives | Authenticated broker delivery and operation binding remain planned |
| [Task checkpoints](../../src/loop_engine/loop/spawned_task_checkpoint.py) | Restore nonterminal tasks as interrupted | Does not replay arbitrary reasoning or resume arbitrary engines |

The [wave A integration findings](../verification/ENGINE-FRAMEWORK-WAVE-A-INTEGRATION-2026-09-23.md)
remain relevant: embedded record validation, mutable eligibility, installation
authority and qualification matching need completion in the shared selector.
The research recommends extending these existing owners rather than introducing
a second framework with similar schemas.

## 12. Qualification and evolution plan

The following cases are proposed acceptance requirements. They are not claims
that this research executed new engines or completed the shared selector.

| Known-wrong case | Required discriminator | Existing owner |
| --- | --- | --- |
| Same result shape, wrong ordering or units | Independent semantic oracle rejects the result | Edge contract and component checks |
| Required feature omitted by translation | Preflight reports the exact missing requirement | Compiler/profile and executor requirements |
| Plugin package loads but required hook does not | Native probe blocks the step's readiness claim | Material loading and qualification |
| Binary asset is converted or mode lost | Exact bytes and metadata disagree before publication | Package and confined writer |
| Executable or configuration changes after selection | At-use binding refuses the changed identity | Engine installation and native registry |
| Lower-scope preference enables a disabled engine | Selection rejects the preference | Existing parameter precedence and selection |
| Retry after a lost write acknowledgment | Reconcile or preserve unknown effect; no blind repeat | Interaction contract and fallback owner |
| Cancellation acknowledged while work continues | Termination/effect state remains unresolved | Supervisor and native lifecycle adapter |
| Old resource handle reaches a new engine | Scope/state generation mismatch refuses | Component state owner |
| Wrapper graph contains an accidental cycle | Composition refuses before initialization | Existing dependency and configuration owners |
| Two individually valid plugins shadow one capability | Set-level conflict or explicit resolution | Package resolver and native profile |
| Stale ranking evidence favors a changed engine | Discard that comparison; retain declared order among eligible engines | Engine evidence owner |
| Qualification is expired, withdrawn or for another profile | Exclude the engine even if it is first in declared order | Engine qualification and selection owner |
| Provider reports no model or usage | Record unknown, never fill from requested values | ModelGateway and Run History |
| Shadow comparison repeats a paid or external action | Separate authority required; otherwise refuse | Existing effect and experiment policy |

For each implementation change, keep positive, negative and removed-guard
controls tied to the actual risk. Structural schema checks, source inspection,
isolated execution, native activation and accepted customer tasks are separate
evidence levels. Qualification is specific to the tested profile and population.

### Next implementation sequence within the roadmap

1. **S-6.30:** complete the shared selection and at-use binding procedure using
   existing records. Close nested-record validation and mutable eligibility
   gaps before adding automatic ranking. Test one engine slot end to end.
2. **S-6.44:** turn the compiler preview into the active existing placement
   boundary with complete-package byte handling and confined materialization.
   Qualify direct Baltor placement and one pinned Agent Harness adapter against
   the same contract, with explicit unsupported cases.
3. **S-6.31 and S-6.42:** prove native loading and accepted work with two exact
   harness profiles. Preserve fresh attempts, cancellation and consumed authority.
4. **S-6.61:** implement the scoped credential/connection binding needed for
   local, container and customer-hosted execution.
5. **S-6.32 and S-6.41:** collect comparable search/execution outcomes, then
   enable evidence-based selection only for qualified scopes.

For every adopted repository: identify the useful operation, pin source and
rights, map it to an existing component, wrap the smallest required surface,
qualify it, and build the corresponding bounded Baltor variation. Compare both
under the same contract. A native variation needs its own qualification; it
does not inherit approval from the upstream implementation. Record maintenance
cost, upstream changes, retirement and rollback for every retained engine.

### Decisions

Use the current engine framework as the authority. Add behavioral obligations,
state/lifecycle binding and explicit translation losses at existing owners.
Keep compiler profiles as data and compiler engines as code. Use external
standards at the layers they actually cover. Preserve exact native capabilities
through qualified extensions when needed. Prefer measured accepted outcomes
under customer constraints, with declared order when comparative evidence is
insufficient. These changes make replacement testable without multiplying
runtime types, registries or invisible fallback behavior.

## Review and limits

Three independent reviews covered primary standards, reliability and actual
repository adoption. A further synthesis review corrected eligibility versus
ranking evidence, rendered-byte approval lineage, composable binding patterns
and stateful cancellation. Final source review resolved all 21 local links
and found no remaining source-accuracy issue. Markdown structure checks passed.
These are documentation reviews, not execution qualification or performance
measurements for the proposed engines.
