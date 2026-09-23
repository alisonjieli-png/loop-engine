# Harness Working Directory Compiler

Dated component design, September 23, 2026. The owner selected this exact name.
The architectural direction is accepted; the complete component, profiles and
standing compatibility jobs are not yet implemented or qualified. The
[roadmap](../roadmap/roadmap.yaml), particularly D-19 and S-6.44, owns the work.
The [original supplied draft](../../artifacts/harness-file-standards-supplied-2026-09-23/inventory.json)
is preserved. This consolidation corrects its profile/engine distinction,
constructor-proof claim, stale-profile policy and data-only evolution claim.

## Runtime ownership

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

The Harness Working Directory Compiler is a functional component used by work
owned by a classified Loop. It creates no runtime type, graph vertex or
intelligence layer. Refer to the
[complete behavioral explanation](DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md#complete-explanation)
for the fresh-harness-per-step design and its continuing authority.

## Exact terms

| Term | Responsibility |
| --- | --- |
| Harness Working Directory Package | A selected versioned bundle, represented by `CataloguePackage` and its owning catalogue metadata |
| Harness Working Directory File | One exact member, represented by `CataloguePackageFile` |
| Harness Working Directory Compiler | The typed functional boundary that resolves a package and target profile into a proposed file set |
| Compiler engine | An implementation behind that boundary, including a Baltor engine and a qualified external adapter |
| Harness compatibility profile | Passive versioned data describing an exact client/interface/runtime and supported loading behavior |
| Placement operation | Authorized application of a checked plan through the existing confined writer |

Existing serialized names, intelligence families and `harness_local` retain
their identity. Changing backend prose does not silently migrate active records.

## Component and selectable engines

```text
Harness Working Directory Compiler
├── Typed, versioned input
│   ├── Selected exact package trees and dependencies
│   ├── Assignment, scope and effective authority
│   ├── Target harness/interface/runtime and host policy
│   └── Explicit advisory variants and fallback choices
├── Passive configuration
│   ├── Harness compatibility profile
│   └── Supported placement and transformation rules
├── Eligible compiler engines
│   ├── Baltor direct implementation
│   ├── Qualified madebywild Agent Harness adapter
│   └── Other qualified implementations behind the same contract
└── Output
    ├── Proposed exact paths, bytes, roles and digests
    ├── Source-to-output lineage and required capabilities
    ├── Expected pre-existing files and conflict decisions
    └── Typed unresolved requirements or refusal
```

Compilation does not write the customer workspace, acquire credentials, start
hooks, install dependencies or call a model. A model-assisted preparation engine
may propose source material in separately authorized work; it cannot grant
permissions or approve its own result. The existing writer applies only the
exact authorized plan, checks expected current bytes and verifies the result.

Run an external compiler in an isolated staging workspace when its interface
requires filesystem writes. Inspect all resulting files through the same
package and permission rules. Preserve opaque binary bytes and explicit modes;
text substitution applies only to declared templates. Raw provider settings
must not silently replace an approved executable or broaden effects.

Default selection starts with the qualified direct engine. Agent Harness is an
optional engine for an explicitly selected compatible workflow. A declared
fallback can choose another eligible engine only while preserving required
semantics and cumulative authority. No fallback silently drops a required hook,
changes an input/output contract or switches to an unapproved model.

## Extend the existing seam

`ClientLayoutProfile`, `NativeLocation` and the installer refusals in
`tools/install_selected_material.py` are the starting contracts. The existing
`material_install_layout` slot is a candidate release-time seam. Its active
runtime protocol/boundary bindings still need implementation and conformance.
Do not create another layout registry or task executor.

The [draft contract artifacts](../../artifacts/harness-agent-working-directory-compiler-2026-09-23/README.md)
propose `native_client_layout_profile/v2` and
`native_material_install_preview/v2`. These reuse record families already
owned by the installer. The twelve synthetic fixtures validate draft shape and
cross-record constraints. They do not qualify any native harness.

The supplied constructor experiment successfully mapped a skill identity into
four configured paths. It did not launch four clients, verify discovery, bind
real client versions, inspect inheritance or execute a checked task. Its repeated
version 2.1.280 value was synthetic input, not observed version evidence. The
[profile review](../research/HARNESS-AGENT-COMPILER-PROFILES-AND-HANDSHAKES-2026-09-23.md)
keeps those limitations explicit.

## Standing compatibility maintenance and runtime handshakes

```text
Compatibility lifecycle
├── Scheduled maintenance, near-daily when authorized
│   ├── Read pinned upstream release and specification changes
│   ├── Run authorized isolated discovery/conformance probes
│   └── Stage a candidate profile for independent review
├── Before a new attempt
│   ├── Bind exact executable/interface/version and effective configuration
│   ├── Confirm eligible engine, profile and required capabilities
│   └── Freeze selected package, dependency and placement digests
├── At connection and use
│   ├── Negotiate the applicable protocol/capability contract
│   └── Revalidate the binding and authority before effects
└── On a known incompatible change
    ├── Disable new starts for the affected binding
    ├── Preserve historical profile and evidence
    └── Handle active attempts under their supervisor/cancellation policy
```

Scheduled profile improvement is Practitioner work. Intelligence operations may
retrieve the underlying evidence. Active qualification probes have explicit
process, network and model authority as needed; metadata discovery itself stays
effect-free. `--help` output is documentary evidence, not proof of instruction
loading. A profile cannot approve its own update.

A daily check cannot replace launch-time compatibility. Equal version strings
can hide changed builds, global settings, managed policy or plugins. Bind those
sources where observable and mark unknown requirements as unknown. Keep native
protocol negotiation distinct from configuration-file compatibility. Modern MCP
and different Agent Client Protocol revisions have different wire lifecycles.

Do not keep knowingly incompatible profiles serving new attempts while waiting
for a replacement. Preserve valid old bindings for their still-qualified exact
runtimes. Never mutate a running attempt's frozen files merely because a new
profile was approved.

## Flexible placement and explicit variants

A file role can map to several paths or require explicit invocation. Aider's
read configuration, a Claude import wrapper, a native plugin and a Python helper
are different mechanisms. A new location using an existing supported renderer
can be a data change. New syntax, binary handling, import semantics or lifecycle
behavior can require a new engine capability and code change.

When a native difference requires a distinct file, retain one source package
identity with an explicit rendered variant and its own bytes and digest. Report
logical package counts, payload file counts and rendered variants separately.
Do not copy a global catalogue into every working directory.

## Required negative controls

| Case | Required outcome |
| --- | --- |
| Required file role has no supported native mechanism | Refuse before placement or launch |
| Two packages claim one path or native tool name incompatibly | Refuse or resolve through an explicit checked policy |
| A file changes after preview | Refuse stale expected-state binding |
| A path escapes through a symbolic link | Refuse at the actual filesystem boundary |
| Text conversion changes binary bytes | Refuse digest mismatch |
| Unsupported mandatory hook is omitted | Refuse semantic loss |
| Raw settings widen tool/network authority | Refuse final configuration |
| Runtime/build/profile binding changes | Requalify or select a declared eligible fallback |
| File exists but native discovery does not expose it | Record placement only; do not claim loading |
| A result is valid JSON but semantically wrong | Independent task acceptance refuses it |

Use the same positive, refusal and partial-failure population for Baltor's own
engine and every reused implementation. Performance comparisons measure accepted
work under the customer's constraints. Fewer files, tokens or steps alone do
not establish the better engine.
