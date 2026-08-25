# MCP and skills

MCP tools and Agent Skills enter Loop Engine through typed Custom Plugin
adapters. MCP discovery never invokes a tool, but session initialization can
still spawn a process or open a network connection. Every discovery, tool
call, and skill load still runs through a Loop with its own effect policy.

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
from loop_engine.static_architecture.mcp_adapter import (
    McpCallRequest,
    McpInvocationServices,
)
from loop_engine.static_architecture.context_artifacts import (
    ContextArtifactManager,
    ContextArtifactServices,
    ContextArtifactStore,
    ContextArtifactStoreSpec,
)
from loop_engine.static_architecture.runtime_observer import (
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

## Shared observer

`RuntimeObservationServices` resolves one supplied observer, Loop ledger, or
spawning Loop. Without any of those, it uses a no-op observer. It never creates a
second event store.

`LedgerRuntimeObserver` accepts `RuntimeObservation` objects only. Each event
kind has a closed field allowlist and required fields. Unknown event kinds,
extra fields, unbounded text, invalid digests, negative counts, and unknown
terminal statuses fail before the ledger write.
