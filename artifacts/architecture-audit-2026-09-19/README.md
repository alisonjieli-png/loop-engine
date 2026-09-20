# Loop Engine system map and continuation review

Kind: working architecture review and build guide. Date: 2026-09-19.
Base revision: `48cc954322691e492aad69a465ba470a112730e7`.
The reviewed working tree includes uncommitted changes from the recovered
Claude session and this continuation. It is not yet a qualified release.

Open the [single-file development log](loop-engine-system-map.html) for your owner
checklist, engineering status, full setup guides, and high-, medium-,
and low-level diagrams, account and local-execution journeys, harness context
layout, the preserved Claude feature matrices, current work, searchable
source files and evidence limits. All styles, scripts, report data, selected
source notes and the pinned layout library are embedded. The same file works
offline when copied elsewhere. The earlier `architecture.html` route points
to this canonical report, as does the former `mvp-client-server.html` name.

The historical tables contain 77 measured feature columns, although their
original introduction says 76. Their original cells and notes remain dated
September 18; they are not silently upgraded to current vendor or runtime
qualification. The worklist is generated from `docs/roadmap/roadmap.yaml`.

The September 20 extension adds a separate, dated website-journey comparison:
nineteen identified companies from the original matrix, four adjacent
references and Baltor. It also embeds twelve review-only intelligence records
across the four persistent layers. Page links do not qualify vendor workflows,
and candidate records do not become active intelligence because the report
displays them. The current delivery and measurements are in the embedded
[checkpoint](../../docs/context/DEVELOPMENT-CHECKPOINT-2026-09-20.md).

The [component rows](COMPONENTS.md),
[full source inventory](inventory.json.gz), [graph](graph.json.gz), and
[file coverage](FILE-COVERAGE.md) are generated from the same source scan.
The exact population and counts are in [counts.json](counts.json).

The full inventory and graph also download directly from embedded compressed
data in the HTML. Their raw JSON working copies are ignored by Git because
the compressed versions preserve the same bytes with much smaller files.
The [previous client/server page](mvp-client-server-before-consolidation-2026-09-19.html)
is retained as a dated snapshot. Its companion assets support that older
snapshot only, not the current report.

The map extends the September 18 artifact beyond its 88 curated components.
It does not preserve that artifact's unsupported inference that an imported
module was called, or that passing checks prove a component correct. The
[recovered session review](../claude-session-review-2026-09-19/README.md)
records the older artifact, prompting coverage, and ten initial observations.

## Evidence labels

| Axis | Meaning | Does not establish |
|---|---|---|
| Structural inspection | The scanner read text or parsed Python syntax; exclusions are named per file. | A semantic review of every line. |
| Static import path | The module belongs to a named source import closure, including conditional and test imports. | Invocation, complete dynamic reachability, or correct integration. |
| Test declaration | A function or named check appears in source. | That it ran or passed. |
| Current recorded checks | An executed report names the owning module and matches the complete package source identity. | Complete test coverage, model quality, or provider qualification. |
| Focused review | A review names the file and its inspection scope. Source drift is shown when a reviewed hash is available. | A full audit of unrelated behavior in that file. |
| Record-type literal | A versioned string occurs in source. | A supported encoding; refusal tests also contain obsolete strings. |
| Documented vendor capability | The dated review cites primary documentation. | Independent testing of the vendor, or absence of undocumented features. |

Missing execution evidence stays missing. A release checker, export command,
or configuration tool may correctly be outside the public solve path. A
required runtime capability without an actual caller is a different finding.
Do not add imports merely to increase a reachability count.

## Canonical architecture

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

This source graph also contains files, classes, ports, passive records,
services, and stores. Those source entities are not executable graph vertices.
Only the canonical `Loop` owns governed execution.

### Client and server separation

```text
Customer environment
├── Client configuration and installation
├── Starting Practitioner and task decomposition
│   ├── Spawned Practitioner assignments
│   ├── Queried Intelligence work and selected references
│   └── Connected Solution work on fresh inputs
├── Harness processes and local workspaces
│   ├── separately granted file, command, model, and network authority
│   └── exact instruction and resource identities
└── Provider adapters
    └── customer-authorized local or remote model routes

Proposed first hosted product
├── Public website and subscriber dashboard
├── Identity, subscription entitlements, and payment events
├── One intelligence service used by web and protocol adapters
│   ├── authorized metadata discovery and selection
│   ├── qualification and exact-reference checks
│   └── selected body delivery and acknowledged usage
└── Durable state behind existing storage contracts
    ├── small catalog records and search indexes
    ├── immutable bodies and program artifacts
    └── subscriptions, usage, and operational records
```

The first hosted product need not execute customer harnesses. The internal
client engine still needs working graphs, typed assignments, selection,
execution, verification, and reusable solutions. A subscription cannot grant
the customer's filesystem, provider, competition-data, or spending authority.
The website, payments, durable entitlement path, hosted authentication, and
real deployment are not established by the current local component tests.

### Data and control paths

| Work | Owning path | Representation and refusal boundary |
|---|---|---|
| Public task intake | `code_nodes.solve_runtime` and `solve_request_adaptation` | Typed request, immutable task identity, explicit settings and dependencies. |
| Practitioner lifecycle | `core.adaptive_practitioner`, `adaptive_practitioner_records`, `loop.recursive_loop` | One canonical Loop, selected actions, budgets, supervision, and Run History. |
| Stage observations | `core.practitioner_runtime.observations` | Bounded fingerprints, exposure, outcome records, and explicit degraded instrumentation. No independent task acceptance. |
| Search and selection | `core.intelligence_layers`, `retrieval`, `loop.intelligence_loops` | Four persistent layers; small references first; facets before bounded selection. |
| Materialization | `loop.loop_capsule` and the source-owning store | Selected current reference, recomputed body identity, permission and qualification checks. |
| Reusable execution | `core.reusable_capability_flywheel`, `code_intelligence_assets`, `capability_directory` | Existing qualification authority, immutable implementation identity, exact handshake, governed invocation. |
| Model use | `core.model_gateway`, `model_routes`, `model_token_preflight` | Exact route, output capacity and allocation, separate authority, provider usage preserved as known or unknown. |
| Native harness work | `core.harness_semantic`, `harness_process`, `instance_instructions` | Confined process and instruction bytes; actual native loading remains a separate qualification. |
| Graph execution | `code_nodes.solution_graph`, `solution_graph_execution`, `solution_canvas` | Exact definitions and operation bindings, named ports, edge-driven input routing, refusal before incompatible execution. |
| Accepted outcome | `core.independent_verification`, `adaptive_practitioner_verification`, `product_outcome_store` | Exact subject-bound verification and current saved outcome. A successful model response is not task acceptance. |
| Independent export | `code_nodes.solution_export` | Complete manifest identity, confined declared files, explicit exact local execution approval; no implied operating-system sandbox. |

### Persistent storage and Runtime Memory

```text
Information ownership
├── Four persistent intelligence layers
│   ├── Context Intelligence
│   ├── Code Intelligence
│   ├── Runtime History and Solution Intelligence
│   └── User Feedback Intelligence
├── Runtime Memory
│   └── temporary, scoped to one run and detached at boundaries
└── Storage mechanics
    ├── CatalogStore and embedded database adapters
    ├── RecordOperationService for managed collections
    ├── immutable artifact references and bodies
    └── derived search and reporting projections
```

Harness Intelligence is a provisioning view over source material, not a fifth
persistent intelligence layer or an independent admission authority. Catalog
metadata, large bodies, search projections, and temporary memory must not be
treated as interchangeable storage.

The [storage review](intelligence-storage-and-exports.md#stores-authorities-and-projections)
names the actual adapters, older parallel interfaces, and durability limits.
The [write repairs](storage-write-repairs.md) cover atomic preconditions,
detached values, immutable revisions, and acknowledged shared-memory writes.
The [access repairs](intelligence-access-repairs.md) cover active Code admission,
body identity, qualification bindings, global query limits, and backend failure.
These bounded repairs do not establish a complete server-database migration,
concurrent multi-process governance journal, or production recovery service.

## Review and repair records

| Scope | Detailed record | Current limitation |
|---|---|---|
| Runtime, graph wiring, replacement, and deadlines | [Runtime review and repair evidence](runtime-and-replaceability.md) | Native provider behavior and complete public task decomposition need separate qualification. |
| Storage, retrieval, and export baselines | [Intelligence review](intelligence-storage-and-exports.md) | Baseline defects are retained even when later repair records close a bounded case. |
| Storage writes and exact revisions | [Write repairs](storage-write-repairs.md) | Generic catalog writes are not managed-record approval and do not supply deployment backups. |
| Code admission and selected reference identity | [Access repairs](intelligence-access-repairs.md) | All-layer hosted admission and tenant disclosure remain a separate serving boundary. |
| Organization, collection, service scoping, and image delivery | [Delivery review](organization-tests-and-delivery.md) | Local image checks and workflow changes do not establish a newly published image. |
| Independent review of root implementation | [Independent review](root-changes-independent-review.md) | Names exact inspected source hashes and seven independently reproduced repair cases; not a whole-release sign-off. |

The [question register](questions.json) combines the independently maintained
runtime, intelligence, and organization registers. Each question retains its
source, answer state, and evidence. Open and disputed answers stay visible.
The [continuation status](../../docs/roadmap/CONTINUATION-STATUS.md) assigns work
to the existing roadmap rather than creating another execution authority.

## Current-only contracts and replaceable implementations

The [owner's pre-launch policy](../../docs/architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md)
requires current versions and explicit compatibility handshakes, not active
support for unpublished record shapes. Old readers, aliases, and forwarding
modules are being removed with their current callers and tests. Historical
evidence bytes remain unchanged.

Safe replacement binds the input and output contract, supported modes,
effect declaration, exact implementation identity, and required capabilities.
The supervisor owns selection and authorized fallback. A version match or
successful registration cannot grant an effect, qualify code, or accept work.
Failure must identify whether the implementation, contract, environment,
authority, or source evidence prevented progress.

## Research and history coverage

The [current competition review](../continuation-research-2026-09-19/competitors.md)
adds direct overlaps in paid protocol delivery, versioned skills, executable
reuse, local downloads, and task evaluation. The September 18 absence claims
must not be used as proof of uniqueness.

The [prior-art review](../continuation-research-2026-09-19/prior-art-and-research.md)
compares graph decomposition, skills, learned reuse, and evaluation methods.
The [funding and strategic review](../continuation-research-2026-09-19/funding-and-strategic-paths.md)
separates possible fit from demonstrated investor or acquisition interest.
No organization was contacted and no application was submitted.

The source inventory includes tracked hidden files and eligible pending source.
It excludes credential-bearing paths and records binary or oversized files as
metadata-only. Dependency caches, generated run directories, and separate
repositories are not silently counted as reviewed source.

The Claude review read the latest relevant session and queued owner directions.
The OpenCode history review used read-only indexed queries scoped to Loop
Engine rather than scanning or copying its very large database. The Codex
history inventory located project-scoped session headers; it did not establish
a semantic review of every session body. Raw private prompts, credentials,
unrelated personal material, and unrelated repository histories are not copied
into this report. Complete semantic review of every historical byte remains
unperformed.

## Reproduction and update procedure

```bash
npm ci --prefix tools/architecture_report --ignore-scripts --no-audit --no-fund
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tools .venv/bin/python -m unittest tools.test_architecture_audit tools.test_practitioner_runtime_boundary tools.test_build_continuation_status
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tools .venv/bin/python tools/export_component_inventory.py --repository-wide
.venv/bin/python tools/build_continuation_status.py
.venv/bin/python tools/build_continuation_status.py --check
```

Run `tools/capture_architecture_checks.py --output PATH` against a frozen
source export to capture the existing complete offline suite. The destination
must be new. Review the result before selecting it as `verification.json` for
the map. A changed source population makes that evidence stale. Preserve failed
captures as failures; do not overwrite them with later passing output.

The remaining launch gates include actual authenticated client setup,
subscription and payment lifecycle, durable usage reconciliation, qualified
starter material, complete internal integration, real native harness loading,
fresh-input solution reuse, and an authorized hosting acceptance run. Neither
the map nor a passing component suite closes those gates by itself.
