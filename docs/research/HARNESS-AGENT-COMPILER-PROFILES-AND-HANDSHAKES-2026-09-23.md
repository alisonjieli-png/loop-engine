# Harness Working Directory Compiler: profiles and handshakes

September 23, 2026. Status: research-only contract drafts and synthetic fixtures.
The component's current human name is **Harness Working Directory Compiler**.
The earlier filename of this report retains the task's original requested name;
it does not introduce an alternative component or runtime.

This successor adjudicates the supplied
[compiler design](../architecture/HARNESS-WORKING-DIRECTORY-COMPILER-2026-09-23.md)
and [file-standards analysis](HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md).
Their exact initially inspected bytes are preserved in the
[source inventory and snapshots](../../artifacts/harness-agent-working-directory-compiler-2026-09-23/source-inputs.json),
since the shared documents have concurrent owners and may be corrected later.
The roadmap remains the single work authority. No active contract, registry,
runtime, daemon or schedule was changed by this work.

## Keep the existing objects and distinguish their jobs

The owner chose clearer human terms: a **Harness Working Directory Package**
is the existing `CataloguePackage` plus its owning catalogue metadata; a
**Harness Working Directory File** is an existing `CataloguePackageFile`.
The compiler is a functional component. A harness compatibility profile is
passive data consumed by a compiler engine. An engine is an implementation.
These names do not create replacement Python types, source layers or wire
identities. `harness_local` and the existing family identity remain unchanged.

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

```text
Harness Working Directory Compiler, work owned by a classified Loop
├── Versioned request and preview/result edge
├── Inputs: exact selected packages, assignment and authority
├── Harness compatibility profile: passive, immutable data
│   ├── Client, interface, exact version and platform
│   ├── Locations, roles, scope, precedence and activation
│   └── Evidence references and supported contract versions
├── Eligible compiler engines
│   ├── Baltor direct implementation
│   └── Qualified external implementation, including an Agent Harness adapter
└── Output: exact proposed files or a typed refusal
    ├── Source and rendered digests, expected existing state
    ├── Required capabilities, effects and unresolved requirements
    └── Binding to the independently checked runtime and current host policy
```

The profile and placement logic can change independently. Calling profile data
an engine blurs the implementation boundary. An engine may expose different
profile configurations; swapping the profile does not install new rendering
code, tool semantics or execution permissions.

## Reuse the existing names and ownership

| Existing owner | Draft evolution |
| --- | --- |
| `ClientLayoutProfile` and `CLIENT_LAYOUT_PROFILES` in `tools/install_selected_material.py` | Propose `native_client_layout_profile/v2`, retaining the record family and typed refusals |
| `native_material_install_preview/v1` in that installer | Propose `native_material_install_preview/v2` for a complete digest-bound compilation preview |
| Existing `material_install_layout` engine slot | Evolve its candidate release-time definition through the normal architecture process; no second profile or engine registry |
| `CataloguePackage`, `CataloguePackageFile`, body-store edge | Preserve canonical package and raw-file identity; renderings are explicit variants, not extra logical packages |
| `core.instance_instructions`, `core.node_provisioning`, `core.spawned_provisioning` | Supply the focused assignment and exact authority before compilation |
| `FreshInstanceRecipe` and qualified harness executor | Bind launch, isolated state, credentials and actual runtime behavior |
| Existing `EngineDescriptor`, `EngineInstallation`, `EngineQualification` and host selection policy | Own implementation identity, independent qualification and eligibility; a profile references these facts without granting them |

The current installer explicitly wires one OpenCode layout. Its observed-version
list is `1.17.9` and `1.18.31` in the inspected source. Other fresh-instance
experiments use other clients and versions, but their evidence does not silently
add profiles to this installer's table. Its current renderer adds skill
frontmatter to served text; a general multi-file compiler needs deliberate
implementation changes beyond adding path rows.

The engine slot currently identifies `material_install_layout` as a candidate
release-time seam, with its runtime protocol/boundary fields still empty. These
draft artifacts do not make it a registered active compiler component. A future
implementation must update the existing owner, registry joins and conformance
checks before callers can use the new edge.

## Correct the evidence level of the four-path demonstration

Constructing four `ClientLayoutProfile` objects and obtaining four expected skill
paths establishes that the same path-building function can use different data.
It does **not** establish that any native client starts, discovers a skill,
activates it, loads its supporting files, observes scope rules or produces an
accepted result.

In particular, assigning the literal `2.1.280` to every client's
`observed_client_versions` field is synthetic constructor input. It is not
evidence of Codex, Gemini or OpenCode at that version. The current constructor
stores the supplied strings; it does not run those executables to verify them.
Even a true Claude Code version cannot be transferred to another client. A
report of no file writes or model calls narrows effects; it does not strengthen
the discovery claim.

Every claimed native observation should bind executable digest, reported
version, interface, operating system/architecture, effective configuration,
probe recipe, exact input files and returned observation. Keep an empty control
and a deliberately misplaced or malformed item beside the positive case. A
client's `--help` output proves a command is documented by that executable;
it cannot prove the client's instruction precedence or skill discovery.

The [earlier native observations](MADEBYWILD-AGENT-HARNESS-COMPATIBILITY-AND-ADOPTION-2026-09-23.md)
remain useful within their scopes: Codex 0.155.1 exposed a skill description from
both tested roots without initially exposing its full body. The two subagent
shapes were inconclusive. The path-construction demo must not replace or
broaden those findings.

## Draft records supplied for review

The [artifact README](../../artifacts/harness-agent-working-directory-compiler-2026-09-23/README.md)
links the two JSON Schema 2020-12 drafts and twelve fixtures.

### Compatibility profile v2

The draft extends `native_client_layout_profile`, with explicit client/interface
and exact-runtime binding; declared file role and served kind; scoped location;
package-relative path handling; activation rule; precedence/trust references;
supported compiler contracts; evidence claims; and a reference to independent
qualification. Unsupported roles refuse. A profile contains no raw secret and
does not invent approval by being present in a catalogue.

Evidence stages here describe a report's claim. They are not a new qualification
ladder. Adoption must map them to the existing `EngineQualification` scope and
ladder, including the distinctions between material listed, loaded, completed
step and independently accepted result. Policy should demand the rung needed
for the requested use, rather than one universal badge for the whole client.

### Installation preview v2

The preview binds the profile, assignment, selected inputs, authority, workspace
state, engine descriptor/installation and current host policy. Each proposed
file identifies its canonical package, source path and digest, destination,
rendering operation, final digest, size and expected prior state. A required
capability cannot be silently omitted. Installation effects and worker effects
remain separate and use the current `core.facets.EFFECTS` vocabulary.

The result can be a compiled preview without launch assessment, or an explicit
refusal. `writes_performed` and `authority_granted` are false: the record is a
plan. Even an eligible result requires the actual writer and executor to enforce
their own current authority at use. Model authority and token/call ceilings stay
in the owning assignment/runtime contracts; deterministic compilation grants no
model call.

This is an incompatible proposal, intentionally version 2. The version-1 preview
can stop before a metered body read. A version-2 preview containing **rendered
exact bytes** needs bodies already available under appropriate retrieval
authority. Do not pretend that a free metadata preview can attest unknown future
body bytes. Keep retrieval/metering, compilation and installation distinct.

The schemas include a research-only marker, and no active reader accepts them.
Adoption requires a reviewed contract change, in-repository caller updates and
explicit version negotiation. Do not add an automatic old-record reinterpretation
path to make the draft convenient.

## Scheduled compatibility watch is not a runtime handshake

| Mechanism | Purpose | Required outcome |
| --- | --- | --- |
| Scheduled source and compatibility watch | Detect changed official documentation, source, releases or controlled native behavior | Preserve observations; stage new profile/engine candidates and classify affected bindings |
| Initialization and per-launch negotiation | Match consumer/producer contracts and required capabilities to the installed client and selected engine | Bind mutually supported versions, exact identities and the applicable independent evidence; refuse unknown compatibility |
| Effect-time revalidation | Detect drift since preview or initialization | Recheck file preconditions, executable/configuration identity, current policy, package withdrawal and authority before effects |

A near-daily cadence is a reasonable research policy proposal, not a guarantee
that a customer's client did not update this minute. We did not schedule a job
or install a daemon. Use the existing scheduler and Loop work model when this is
implemented.

Many native CLIs do not implement a capability negotiation protocol for their
working-directory formats. The local adapter can negotiate its own typed edge
and attest observed native identity, then compare it with qualified scope. It
must distinguish that from a protocol handshake actually performed by the
native client. A successful MCP handshake likewise proves the protocol connection,
not instruction-file discovery or plugin activation.

Daily improvement is **Practitioner** research/self-improvement work. It may
query Intelligence for sources and invoke deterministic Solution checks. It
stages candidates for independent review and cannot approve its own changes.
Listing/probe commands are executable inputs: they need host-selected recipes,
limits and isolation. A command being called a probe does not guarantee that
it cannot load hooks, plugins, credentials or make network/model calls.

## Stop future starts on a confirmed bad binding

Preserve the old profile and evidence bytes as history. If a binding is known
incompatible, disable its eligibility for **future starts immediately** through
the existing host policy/installation and qualification machinery. Do not keep
serving it as an eligible launch profile until a replacement eventually passes
review. Unaffected client versions or alternative qualified bindings can remain
available.

An already running attempt keeps its immutable input snapshot. That does not
guarantee permission to continue after a relevant safety or authority revocation:
the existing supervisor decides whether the next effect must stop or the attempt
must be interrupted. Never hot-edit active files or silently change harnesses.
A fallback needs declared order, exact authority, preserved task state and
cumulative budget; absence of a replacement is an honest refusal.

## Data flexibility has a boundary

Path roots, fixed names, precedence references and already implemented render
operations can often change as reviewed profile data. New executable semantics
may need code: a different hook return contract, a new transport, plugin
activation, binary installation, deferred discovery or a client-specific
configuration merge. A string naming a new operation is not its implementation.

The supplied standards table is useful discovery material. Its broad rows must
be broken into scoped claims before promotion; global wording such as a single
root, no project configuration or one universal skill precedence is insufficient
without exact interface/configuration and native evidence. We did not requalify
every client in this task. Profile data must faithfully express known limits
and refuse the rest.

## Validation and its limits

Installed `jsonschema` 4.26.0 validated both draft schemas. All twelve final
fixture expectations passed: three valid records, two schema-level refusals and
seven cross-record semantic refusals. The semantic checks are research code
inside the artifact directory; they are not an active qualification engine.

The negative cases cover path traversal, unsupported record version, invented
native discovery from a path constructor, unknown rendering semantics, installed
client mismatch, disabled future starts, target collisions, enlarged worker
authority and omitted required capability. A valid refusal record is not a
successful compile. Synthetic host-qualification assumptions used to isolate
individual failures are explicitly labelled; no real profile was admitted.

The initial naming update left stale profile digests and correctly failed
validation. Its result and exact fixtures are retained beside the corrected
successor. This is evidence that changing even a human-name field inside a
digest-bound record requires new hashes; changing wording is not permission to
reuse an old binding.

Schema validation cannot establish native support, truthful evidence, rights,
independent review, secret confinement or accepted work. Remaining implementation
gates include signature/evidence resolution, complete package/dependency
verification, native profile qualification, real filesystem confinement and
precondition enforcement, effect-time revalidation, honest partial-write
reporting and measured customer task acceptance.
