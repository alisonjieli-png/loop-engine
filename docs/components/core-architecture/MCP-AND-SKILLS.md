# MCP and skills

MCP tools and Agent Skills enter Loop Engine through typed Custom Plugin
adapters. MCP discovery never invokes a tool, but session initialization can
still spawn a process or open a network connection. Every discovery, tool
call, and skill load still runs through a Loop with its own effect policy.

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode: deterministic, hybrid, or non-deterministic
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the mode permits a model
    └── Run History records
```

Adapters, services, and contracts below are passive runtime mechanics. The
operation that uses them belongs to a classified Loop.

## MCP services

`McpRegistry` holds explicit server and tool registrations. A call accepts one
`McpInvocationServices` object instead of separate approval, artifact, parent,
ledger, and observer arguments.

```text
MCP call
├── Discovery
│   ├── in-process: pure
│   ├── stdio: spawns_process
│   └── HTTP or SSE: network
├── Pure tool
│   └── Typed artifact capture, then one transport attempt
└── Effectful tool
    ├── Exact McpApprovalPlan
    ├── EffectApprovalService decides and consumes it once
    ├── Typed artifact capture
    └── One transport attempt
```

`McpDiscoveryPolicy` selects which discovery effects are allowed and sets the
session timeout. Its default permits only pure in-process discovery. A stdio
or remote session must explicitly allow `spawns_process` or `network`.
Discovery may initialize and close a session, but it does not invoke a listed
tool.

```python
from loop_engine.core.mcp_adapter import (
    McpCallRequest,
    McpInvocationServices,
)
from loop_engine.core.context_artifacts import (
    ContextArtifactManager,
    ContextArtifactServices,
    ContextArtifactStore,
    ContextArtifactStoreSpec,
)
from loop_engine.core.runtime_observer import (
    RuntimeObservationServices,
)

runtime = RuntimeObservationServices(parent=parent_loop)
artifact_manager = ContextArtifactManager(ContextArtifactServices(
    ContextArtifactStore(ContextArtifactStoreSpec("/approved/run-artifacts")),
    runtime,
))
services = McpInvocationServices(
    runtime=runtime,
    approval_service=approval_service,
    artifact_manager=artifact_manager,
)

result = registry.invoke(
    McpCallRequest("catalog", "lookup", {"item_id": "A-104"}),
    services=services,
)
```

The artifact manager is required before any physical tool call. It stores the
canonical JSON output as an immutable raw artifact. A small output is returned
inline with its digest object key. A large output returns only the object key,
according to `ContextOffloadPolicy`. Tool output bodies never enter MCP or
artifact events.

Before approval consumption or transport, the registry validates the call
arguments against the exact JSON Schema returned during discovery. An invalid
schema is not registered. Missing fields, wrong types, and unexpected fields
are refused without crossing transport.

Every selected transport must state that it enforces `timeout_seconds`.
`McpSdkTransport` applies an asynchronous timeout to session setup and the tool
call. A transport that cannot enforce the timeout is refused before approval
consumption or invocation. The injected offline transport enforces timeouts
only for asynchronous handlers.

`McpServerSpec.protocol_version` is an exact connection contract. After the
official SDK initializes a session, `McpSdkTransport` compares the negotiated
version with that registered value. A mismatch closes the session and fails
before tool discovery or invocation.

Credential references have two distinct paths:

- `env:NAME` copies only that named host variable into the transport request.
- `secret:NAME` requires an explicitly supplied `McpSecretResolver`. A missing
  resolver, resolver error, or empty result fails before a process is spawned
  or a network connection is opened.

```python
from loop_engine import McpSdkTransport, McpSecretResolver, McpToolPolicy

class ProjectSecretResolver(McpSecretResolver):
    def resolve_secret(self, reference: str) -> str:
        # Read the exact reference from the application's approved secret store.
        return approved_secret_store.get(reference, "")

transport = McpSdkTransport(
    {"lookup": McpToolPolicy("pure", False)},
    secret_resolver=ProjectSecretResolver(),
)
```

The resolver value is used only while constructing the selected transport. It
does not enter server specifications, events, reports, or Studio projections.

## Exact effect approval

`McpRegistry.approval_plan()` builds the only supported approval binding for an
effectful MCP call. It binds these values into one `EffectSpec`:

- server ID
- tool name
- canonical argument digest
- declared tool effect
- approval request ID

```python
from loop_engine.loop.effect_approval import (
    ApprovalDecision,
    EffectApprovalService,
)

call = McpCallRequest("catalog", "update", {"item_id": "A-104"})
plan = registry.approval_plan(
    call,
    loop_id=parent_loop.loop_id,
    reason="Update the reviewed catalog item.",
)

approval_service = EffectApprovalService(runtime)
checkpoint = approval_service.create(plan.approval)
decided = approval_service.resume(
    checkpoint.pending,
    checkpoint.resume_token,
    ApprovalDecision.approve(plan.approval.request_id, "project-owner"),
)

# The decided state can be saved and restored before invocation.
restored_service = EffectApprovalService(runtime)
restored_service.restore_json(decided.to_json())

result = registry.invoke(
    plan.call,
    services=McpInvocationServices(
        runtime=runtime,
        approval_service=restored_service,
        artifact_manager=artifact_manager,
    ),
)
consumed_state_json = restored_service.serialize(plan.approval.request_id)
```

The service changes decided authority to consumed before the transport call.
The same approval cannot be used again, including after consumed state is
serialized and restored. A changed argument, tool, effect, or approval request
ID is refused before transport.

The former generic `is_approved` hook is not supported. An approval provider
must be `EffectApprovalService`; a similarly named method on another object
does not grant authority.

One `McpRegistry.invoke()` call can cross the physical transport boundary only
once. A transport exception becomes one typed failed result. The Loop records
that result as the completed outcome of the single attempt and does not retry
the external effect.

Completed, failed, refused, unavailable, and approval-required results emit
one `mcp_call_terminal` observation. The canonical vocabulary maps each status
to its existing tool, pause, or rejection family.

The event records server id, tool name, effect, status, request digest, output
reference presence, approval presence, and error code. It does not record tool
arguments, tool output, credentials, commands, URLs, or approval ids.

`McpSdkTransport` uses the official MCP Python SDK. Its connected offline test
starts an official `FastMCP` stdio server, verifies the negotiated protocol,
resolves one explicit `secret:` reference, discovers its typed `add` tool, and
calls the tool through an SDK `ClientSession`. The server class is
`mcp.server.fastmcp.FastMCP` from the installed MCP Python SDK. The test uses
no model and no network connection.

Stdio launch does not copy the full host environment. It passes a short
platform allowlist, deterministic Python stream settings, named `env:` values,
and resolved `secret:` values. An unlisted host variable is absent from the
subprocess environment.

## Skill services

`SkillRegistry` discovers small candidate manifests and loads full
instructions only when selected. Discovery cannot mark a skill registered.
Pass the same `RuntimeObservationServices` object used by the spawning Loop.
In this example, `parent_loop` is the independently authorized review
Practitioner.

New manifests follow the open Agent Skills frontmatter: `name`, `description`,
and the optional `license`, `compatibility`, `metadata`, and experimental
`allowed-tools` fields. Loop Engine version, title, and tags use namespaced
metadata keys. Known older Loop Engine fields remain readable under an
explicit legacy policy and are not described as standard-compatible. Unknown
top-level fields fail closed. A directory must contain exactly one
case-insensitive `SKILL.md` file.

Discovery supports a byte-bounded startup projection. Each card includes the
skill identity, description, version, digest, lifecycle, source, and manifest
policy. It excludes full instructions, supporting paths, and requested tools.
When a card does not fit the declared projection budget, the projection records
it as omitted instead of silently exceeding the budget.

```python
from hashlib import sha256
from loop_engine import SkillAdmissionRecord, SkillLoadPurpose

candidate = skill_registry.discover(("./skills/release-review",))[0]

# The application performs the independent review and stores its evidence.
review_evidence = b"independent release review passed"
admission = SkillAdmissionRecord(
    admission_id="admission-release-review-v2",
    skill_id=candidate.skill_id,
    version=candidate.version,
    manifest_digest=candidate.manifest_digest,
    reviewer_id="independent-release-reviewer",
    evidence_refs=("review:release-review:2.0.0",),
    evidence_digest=sha256(review_evidence).hexdigest(),
)
skill_registry.admit(
    admission,
    runtime=RuntimeObservationServices(parent=parent_loop),
)

loaded = skill_registry.load(
    "release-review",
    "2.0.0",
    purpose=SkillLoadPurpose.TASK_USE,
    runtime=RuntimeObservationServices(parent=parent_loop),
)
assert loaded.admission == admission
```

`SkillAdmissionRecord` is the typed authority for task use. It binds the
decision to the exact skill id, version, manifest digest, reviewer, evidence
references, and evidence digest. The registry verifies that binding. It does
not perform or invent the independent review. `to_dict()` includes a record
digest, and `from_dict()` refuses changed serialized fields.

Admission itself runs as a Verifier Practitioner Loop. Directly registering a
manifest with `lifecycle="registered"` is refused, even when the caller also
passes an admission record.

A selected manifest that completes or fails during verified loading emits
`skill_load_terminal`. The event contains the skill id, version, lifecycle,
manifest digest, file count, status, and error code. It omits the base path,
supporting paths, instructions, and file bodies.

Skill discovery always creates candidate Context Intelligence. Passing
`lifecycle="registered"` to discovery is refused. A candidate cannot enter an
active task context. It can load only with
`SkillLoadPurpose.CANDIDATE_REVIEW`, inside a review Loop. Normal task loading
requires `admit()` with a matching `SkillAdmissionRecord`. A changed manifest
cannot reuse the record. Loading a skill does not register it, execute its
scripts, approve effects, or promote it.

The repository also contains an offline passive state-context candidate based
on the SKILL.state research direction. It combines one admitted procedure, an
exact state schema, a trusted state snapshot, the latest observation, and any
explicitly selected history material. It preserves task, run, branch, graph,
Loop, tenant, privacy, destination, revision, digest, and byte-budget
bindings. State-sufficiency flags require selected history material rather
than silently discarding a potentially relevant observation.

This candidate is not connected to the product prompt renderer. It does not
read Run History, update state, call a model, execute a tool, or grant
authority. Product integration must resolve its history and materialization
references through existing authoritative services and preserve the separate
trust and privacy class of every part. See the dated
[long-horizon research review](../../research/LONG-HORIZON-RECURRENT-SKILLS-AND-STATE-2026-09-04.md).

## External harness boundary

`HarnessRegistry` accepts explicitly supplied, versioned adapters under bounded
identifiers. An identifier never causes a module import, installation, or domain
route. `run_external_harness` resolves the requested exact Practitioner profile
and invokes the adapter once inside the canonical Loop runtime.

`HarnessExecutionRequirements` declares required mechanics, preemptive limits,
and acceptable isolation. `HarnessExecutionCapabilities` describes what an
adapter supports. The boundary also derives requirements from supplied tools,
skills, context, workspace, approval policy, routes, and contract effects.
An unsupported requirement is refused before adapter execution. Declarations
are compatibility facts, not independent qualification or permission grants.

For example, an effectful delegate can require this exact mechanics profile
on its `HarnessRunRequest`:

```python
from loop_engine.core.harness_execution_contracts import HarnessExecutionRequirements

requirements = HarnessExecutionRequirements(
    required_features=("tool_refs", "skill_refs", "approval_policy"),
    required_limits=("total_tokens", "cost"),
    allowed_isolations=("container",),
)
```

The current built-in adapters refuse this profile. Supplying a compatible host
adapter does not grant tool or deployment authority; those permissions still
need independent admission and enforcement. The profile contains no industry
name or task-specific controller.

The four optional SDK adapters expose a bounded text/model subset. A context
reference in their prompt is not proof that its body was hydrated. Native tool,
skill, MCP, and plugin discovery does not bypass Loop Engine admission. Internal
subagents are not automatically canonical Spawned Loops.

The OpenCode process adapter and deprecated client refuse execution. Discovery
is passive and launches no version or model probe. The old raw-host path is
quarantined until a pinned execution profile can enforce approved configuration,
tools, environment, filesystem/network isolation, and cancellation. A working
directory is not a sandbox.
The removed path also exposed prompts in process arguments, inherited ambient
credentials/configuration, and persisted raw NDJSON. A replacement must prove
private prompt transport and raw-event handling, plus credential and
configuration isolation.

`HarnessBudget` retains post-run acceptance limits. A caller needing prevention
before spending must require the corresponding `enforced_limits`; the current
built-in declarations do not promise those guarantees. No live integration or
generalized task-quality gain follows from the offline contract checks. The
[storage, harness, and memory audit](../../research/STORAGE-PACKAGES-HARNESSES-AND-MEMORY-2026-09-04.md)
compares alternatives and records remaining limits.
The [architecture decision](../../architecture/ADR-EXTERNAL-HARNESS-REALIZATIONS.md)
records why this remains one optional realization boundary.

## Shared runtime observer

`RuntimeObservationServices` resolves one supplied observer, Loop ledger, or
spawning Loop. Without any of those, it uses a no-op observer. It never creates a
second event store.

`LedgerRuntimeObserver` accepts `RuntimeObservation` objects only. Each event
kind has a closed field allowlist and required fields. Unknown event kinds,
extra fields, unbounded text, invalid digests, negative counts, and unknown
terminal statuses fail before the ledger write.
