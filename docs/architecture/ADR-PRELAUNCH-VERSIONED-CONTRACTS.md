# Pre-launch versions and compatibility handshakes

Kind: architecture decision. Date: 2026-09-19.
Status: accepted owner direction; implementation cleanup in progress.

Loop Engine has not launched and has no users requiring historical
interfaces. Keep the current contract clear. Do not build legacy support for
the project's own unpublished shapes.

## Decision

Every externally serialized contract and swappable implementation keeps its
explicit version and identity. A caller and an implementation must agree on
the contract they use. This does not require accepting an older contract.

```text
Versioned boundary
├── Identity
│   ├── component and subcomponent identifier
│   ├── supported contract and profile version
│   └── exact implementation or content digest where required
├── Compatibility handshake
│   ├── typed input and output contract
│   ├── supported behavior, mode, and required capabilities
│   └── declared effects and separately granted authority
└── Admission result
    ├── supported and admitted under the caller's authority
    └── unsupported or mismatched, with an explicit reason before effects
```

Use the existing `LoopDefinitionRef`, `LoopProfileRef`, Capability Directory
handshake, store capabilities, and adapter contracts at their owning
boundaries. Do not introduce a second universal registry or infer behavior
from a version string. Matching versions do not grant execution, network,
secret, or spending authority.

Serialization versions, component release versions, and profile versions
name different things. Increment the applicable version when its contract
changes. Do not collapse all identities into one repository version or
pretend that semantic-version ordering proves compatibility.

## Required changes

Remove automatic old-record conversion, old-field aliases, compatibility-only
imports, and constructors retained solely for unpublished consumers. Update
all current producers, consumers, fixtures, examples, package exports, and
documentation together. Do not keep both paths merely to avoid updating tests.

Unsupported records fail explicitly. Historical files remain historical
evidence; do not rewrite them or claim that a failed current reader destroyed
the evidence. A future, separately authorized offline conversion tool may
produce a new artifact with provenance if an actual use case requires it.
That tool must not become an automatic runtime fallback.

## Runtime negotiation across deployed versions

The owner subsequently clarified that independently deployed components must
be able to negotiate compatible communication at runtime. This is a required
architecture direction, distinct from keeping accidental pre-launch baggage.
It does not mean the generic multi-version negotiator is fully implemented.

A component advertises its identity, implementation version, supported
protocol and schema versions, input and output contracts, capabilities,
required effects, and security requirements. The caller supplies requirements
and an explicit preference order. Negotiation selects a mutually supported
contract and an installed qualified adapter, or returns a typed refusal.
Version-number ordering alone is not proof that two schemas are compatible.

The binding records the chosen versions and implementation identities.
Invocation revalidates that binding so a component cannot change between
selection and use. Reconnection and a changed deployment need a fresh
decision. Required permissions, tenant isolation, credential handling,
verification, and accounting cannot be weakened by a protocol downgrade.

Continuous integration verifies negotiation and known-incompatible cases.
The running wrappers make the actual decision when components connect.
Initially a boundary may support one contract version. Later releases may
deliberately support several exact versions and translation adapters with
their own tests. Do not restore every discarded historical reader to simulate
this capability.

Support for a documented external protocol is a separate choice. A supported
protocol profile needs an exact version, handshake, and qualification. Do
not silently fall back to an older protocol to make a request succeed.

## Verification

For each changed boundary, test a valid current record, an unsupported older
version, an unknown future version, malformed fields, changed content with an
old digest, and a version-compatible request without effect authority.
Failed admission must occur before writes, model calls, or external effects.
Use a counterexample that fails when the admission check is removed.

Run dependent component checks after updating callers. Run the complete test
suite and release checks on the exact exported tree before claiming that the
cleanup is integrated. Reader removal is not a reason to weaken integrity,
tenancy, permission, or independent-verification checks.

## Current cleanup scope

The continuation review identified old Loop definition encodings, Solution
encodings, product outcomes, task fingerprint parsing, ontology migrations,
wire aliases, skill metadata, and forwarding imports. These are an inventory
of work, not a claim that each path has been removed.

The [architecture review](../../artifacts/architecture-audit-2026-09-19/README.md)
and [continuation plan](../roadmap/CONTINUATION-AND-LAUNCH.md) record the
implemented slices, checks, and remaining gaps. Dated reports retain the
behavior observed before this decision.
