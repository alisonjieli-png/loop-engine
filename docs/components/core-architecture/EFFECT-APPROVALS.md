# Effect approvals

An effect approval pauses one exact action before a Loop calls an effectful
capability. The reviewer can approve it, edit it, or reject it. The approval
object records authority but does not execute the action.

The implementation is `loop_engine.loop.effect_approval`.

## Known effect classes

`EffectClass` separates local reads, local writes, command execution, network
reads, network writes, external messages, external submissions, money spend,
secret access, data deletion, and deployment.

An unknown class fails during construction or deserialization. It does not
fall into a general effect class. This behavior prevents a model or plugin
from creating a new effect name that bypasses policy.

## Pause and resume

```python
from loop_engine.loop.effect_approval import (
    ApprovalDecision,
    ApprovalRequest,
    EffectApprovalService,
    EffectClass,
    EffectSpec,
)
from loop_engine.loop.approval_state_store import (
    LocalJsonApprovalStateStore,
)
from loop_engine.loop.recursive_loop import LoopLedger
from loop_engine.core.runtime_observer import (
    RuntimeObservationServices,
)

ledger = LoopLedger()
approvals = EffectApprovalService(
    RuntimeObservationServices(ledger=ledger),
    store=LocalJsonApprovalStateStore("/approved/approval-state"),
)

effect = EffectSpec(
    effect_class=EffectClass.EXTERNAL_SUBMISSION,
    operation="submit",
    target="competition:example",
    parameters=(("artifact_digest", "abc123"),),
)
request = ApprovalRequest.create(
    loop_id="submission-loop",
    effect=effect,
    reason="Submit the reviewed prediction file.",
)
checkpoint = approvals.create(request)

# Keep checkpoint.resume_token in the caller's protected state.

decision = ApprovalDecision.approve(
    request_id=request.request_id,
    decided_by="project-owner",
)
resolved = approvals.resume(checkpoint.pending, checkpoint.resume_token, decision)
authorized_effect = resolved.authorized_effect()
```

The serialized pending state stores a SHA-256 digest of the resume token. It
does not store the plain token. Resume requires an exact token and an exact
request ID. A resolved approval cannot be resumed again.

Version 2 adds a consumed state. `EffectApprovalService.consume()` compares the
approved `EffectSpec` with the exact effect about to execute. A match changes
the service state from decided to consumed before the caller crosses the
effect boundary. Consumed authority returns no executable effect and cannot be
consumed again. The in-process transition is locked so concurrent callers
cannot both consume the same decision.

```text
Effect approval state
├── pending, revision 0
├── decided, revision 1
│   ├── approved
│   ├── edited
│   └── rejected
└── consumed, revision 2
    └── terminal one-use authority
```

The service records safe requested and decided events on the same Loop ledger.
It stores no reason, target, reviewer, token, or token digest in those events.

If the token is lost, the caller must create a new approval request. It should
not weaken the comparison or invent a replacement token.

The service accepts one `ApprovalStateStore`. The built-in
`LocalJsonApprovalStateStore` uses an explicit base directory and stores each request
under a SHA-256 filename. The JSON envelope has its own state digest. Writes
use file flush, `fsync`, and atomic replacement. A per-request lock coordinates
threads, and `flock` coordinates processes on platforms that support it.

```text
ApprovalStateStore
└── LocalJsonApprovalStateStore
    ├── create or restore one state only when absent
    ├── load and verify request and state digests
    └── compare-and-swap
        ├── expected revision and exact state must match
        └── replacement advances exactly one revision
```

When a store is supplied, two `EffectApprovalService` instances read the same
canonical state. Only one service can decide or consume a revision. A stale
copy, duplicate request ID, conflicting restore, or second consumer fails.
Pending, decided, and consumed states survive a service restart.

## Edit and reject

An edit decision carries a complete replacement `EffectSpec`. After resume,
`authorized_effect()` returns the edited effect instead of the original one.
The executing Loop must log and run only that returned object.

A rejection returns no authorized effect. It is terminal for that approval
request.

## Separation from policy and execution

The approval object does not decide which actions need review. Operating
settings and the spawning Loop make that decision. It also does not run a tool.
A capability Loop must compare the authorized effect with the exact request it
will execute.

This separation supports durable human review without giving a pending object
execution authority.

## MCP integration

`McpRegistry.approval_plan()` converts one effectful MCP call into the generic
approval contract. The resulting effect binds the server ID, tool name,
canonical argument digest, and declared tool effect. The approval request ID
is also copied to the bound MCP call.

`McpRegistry.invoke()` accepts only the native `EffectApprovalService`. It
consumes exact decided authority once before transport. A changed argument,
tool, effect, or request ID fails closed. A failed transport does not restore
or reuse the approval.

The former generic `is_approved` hook is not an approval authority and is no
longer accepted.
