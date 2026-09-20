# Tenant disclosure and metering repair

Date: September 19, 2026. This is a local component repair record, not a
deployment, independent source qualification campaign, or full-system result.
The earlier architecture audit and baseline probes remain unchanged historical
evidence. No model, cloud, purchase, or untrusted exported program was run.

## Outcome

The current serving path requires an exact host-installed tenant grant and a
matching qualification decision before it discloses any item metadata or body.
Payment entitlement, request effect names, and classification tags cannot
substitute for that authority. Unknown and unapproved items are absent from
discovery counts, listing results, withheld identities, manifests, and bodies.

Required-meter reads now return a successful body only after a matching typed
committed acknowledgment. Missing meters refuse before body loading. Unknown
commitment is a typed refusal, not a zero charge or a successful metered read.
Explicit host grants can permit unmetered local use; these responses say
`metered: false` and have no acknowledgment.

## Existing architectural boundary

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

The serving component is an internal mechanic, not another executable runtime.
The separate transport work owns its classified Loop and protocol adapter.

```text
ProvisioningServer, an existing serving boundary
├── Authentication: immutable host tenant identity and key digest
├── Metadata disclosure
│   ├── Exact tenant grant
│   ├── Exact source, body digest, and descriptor digest
│   ├── Read-only host qualification resolver
│   └── Existing kind, style, and effect filters
└── Body disclosure
    ├── Subscription entitlement and exact body grant
    ├── Selected body reader and measured digest and byte count
    ├── Rechecked source and disclosure authority
    └── Explicit unmetered grant or exact committed meter acknowledgment
```

The catalogue and four intelligence layers were not replaced. Grants are
immutable host configuration with a derived lookup index, not a second source
or approval database. `HarnessIntelligenceItem` and `node_provisioning` schemas
were not changed by this repair.

## Contracts and authority

[`provisioning_server.py`](../../src/loop_engine/core/provisioning_server.py)
now emits server, request, discovery, list, manifest, body, and refusal version
2 contracts. Unsupported versions are refused. There is no automatic version
1 reader or compatibility constructor.

`ProvisioningItemBinding.from_item` binds identity, source layer, source
reference, body digest, and a digest over the complete catalogue descriptor.
Changing a purpose, license, source, body identity, tags, or another descriptor
field invalidates the old grant. The grant independently names the tenant,
body permission, and metering policy. A body subscription is an upper bound,
not permission to disclose every catalogue item.

`ProvisioningQualificationResolver` is a versioned, typed, host-installed
metadata-only adapter. Its exact decision has a source binding, status, basis,
and approval evidence reference. Missing, untyped, failed, mismatched, or
unapproved decisions disclose nothing. A resolver cannot silently fall back
from a refused authoritative decision to host attestation.

`host_attested` deliberately means explicit host review. It does not establish
independent qualification in an intelligence layer. `authoritative` is a host
adapter claim that the owning source has established the exact approval. The
server trusts the installed adapter to resolve that evidence and to honor its
read-only contract; it cannot prove a Python callback has no hidden effects.

There is still no uniform all-layer admission resolver. Code Intelligence has
`CapabilityAuthority.active_spec` and current exact admission evidence, but a
Harness Intelligence `source_ref` alone does not encode a universally typed
asset version and qualification identity. A production host must install an
appropriate owning-source resolver, or explicitly use reviewed local host
attestation. This repair does not invent a parallel admission database or
claim that all-layer independent qualification is complete.

`replace_access_policy` is a host configuration operation. It serializes with
active requests in one server instance. Authority is also rechecked after a
body read and meter callback, including reentrant revocation. The transport
must not expose policy replacement or source-reader installation to clients.
Effect names supplied by a client narrow metadata selection; they never
authorize execution of the supplied material.

## Metering semantics

`ProvisioningMeterRequest` binds tenant, caller-provided request identity,
exact item binding, unit, and quantity. The server accepts only a typed
`ProvisioningMeterAcknowledgment` for that exact request, with literal
`committed=True` and a nonempty receipt reference. An exception, no response,
untyped response, refused or unknown commitment, or different tenant or body
does not return a successful body.

The existing `RecordedMeter` remains an in-process reference meter. It is now
thread-safe and idempotent for exact retries. A different effect cannot reuse
a committed request identity. It reports `durability: volatile`; restarting
it loses its state. Production durable billing, cross-process idempotency,
subscription mutation, and durable revocation still belong to host adapters
and are not established by this local check.

A meter may commit and then lose its response. The caller must retry the same
request identity to recover the same receipt. A refusal after the metering
attempt, including revocation before final disclosure, does not prove that no
charge occurred. The response adapter must preserve that uncertainty. No
exactly-once network delivery or automatic refund is claimed.

## Verification

The saved [verification result](provisioning-access-verification-results.json)
passes 99 checks: 40 owning serving checks and 59 dependent checks across the
catalogue, classification tags, local assignment provisioning, spawned
provisioning, external-service references, harness bridge, and service
application. It records exact source digests. No check was marked untested.

All 14 known-wrong implementations were rejected. These independently remove
tenant scoping, descriptor identity, qualification status or binding, body
permission, scoped counts, body integrity, exact acknowledgment identity,
commitment proof, revocation checks, retry idempotency, effect identity, or
version refusal. Mutants run in memory and do not rewrite runtime source.

Reproduce with the saved [runner](provisioning-access-verification.py):

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src HF_HUB_OFFLINE=1 python3 artifacts/architecture-audit-2026-09-19/provisioning-access-verification.py
```

Two initial runner failures are retained in the
[correction record](provisioning-verification-runner-corrections.json): a wrong
dependency module path and an indentation mismatch in a mutant source target.
Both were verification-runner defects. No runtime check was weakened.

## Exact repair ownership and handoff

Runtime edits in this slice are limited to
`src/loop_engine/core/provisioning_server.py` and the new owning helper
`src/loop_engine/core/provisioning_server_checks.py`. The existing server
`self_test` entry remains the collected check entry point.

The parent agent owns map registration, the client/server diagram, full-tree
integration, installation, and final conformance. Another agent owns the
actual Model Context Protocol transport and its installed-library checks;
those checks are not counted here. This component checkpoint is frozen for
integration. The remaining pre-launch Python reference alias cleanup is
explicitly queued and was not started after the freeze request.
