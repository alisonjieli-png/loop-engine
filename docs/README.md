# Documentation

Use the [main README](../README.md) for the public quickstart.
For current development, open the
[single development HTML](../artifacts/architecture-audit-2026-09-19/loop-engine-system-map.html),
which embeds the [current checkpoint](context/DEVELOPMENT-CHECKPOINT-2026-09-20.md).
Coding agents should also follow the [context route](context/START-HERE.md),
[continuation plan](roadmap/CONTINUATION-AND-LAUNCH.md), and
[generated status](roadmap/CONTINUATION-STATUS.md).
The [client and server map](architecture/MVP-CLIENT-SERVER.md) separates
implemented local and private-pilot boundaries from the remaining subscription
service work. Its [current deployment](architecture/MVP-CLIENT-SERVER.md#current-deployment)
section is the current statement of what runs and where. Follow that section
when another document differs from it.

The [takeover checkpoint](context/TAKEOVER-CHECKPOINT-2026-09-20.md) records
the verified live state, the open findings, the private beta definition and
the working cycle. The earlier September 20 checkpoint and handoff remain
valid as dated snapshots.

Baltor is the public brand. Loop Engine is the repository, the Python package
and the technical name. The table
[Names and where they may appear](guides/product-style-guide.md#names-and-where-they-may-appear)
says where each name may appear.

## Learn the system in order

| Page | Purpose |
|---|---|
| [Repository organization](REPOSITORY-ORGANIZATION.md) | Directory ownership and the distinction between source, guides, and evidence. |
| [Constitution](architecture/CONSTITUTION.md) and [taxonomy](architecture/TAXONOMY-ONTOLOGY-AND-CLASS-MAP.md) | Canonical architecture, runtime classification, and invariants. |
| [Contract index](contracts/README.md) | Exact owning objects, current behavior, and remaining gaps. |
| [Pre-launch version policy](architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md) | Current contracts, explicit handshakes, and removal of unpublished compatibility code. |
| [Component map](components/README.md) | Select the component needed for the task. |
| [Loop object and profiles](components/loop-object/README.md) | Roles, modes, steps, conditions, and typed connections. |
| [Practitioner](components/practitioner/README.md) | Task reasoning, actions, verification, and continuation. |
| [Solution Canvas](components/solution-canvas/README.md) | Reusable Solution definitions and execution. |
| [Core Architecture](components/core-architecture/README.md) | Intelligence Search and Retrieval, Web Research, and Custom Plugins. |
| [Intelligence layers](components/intelligence-layers/README.md) | The four persistent layers, references, qualification, and separate Runtime Memory. |
| [Engineering standards](standards/README.md) | The working rules for changing the code: names, records and versions, checks and evidence, service interface conventions, and the language each component uses. |

The [generated architecture diagrams](ARCHITECTURE-DIAGRAMS.md) and
[source audit](../artifacts/architecture-audit-2026-09-19/README.md) help locate
components. Static edges and displayed files do not establish invocation or
correctness. Read the evidence limits beside each view.

## Start using Loop Engine

| Guide | Scope |
|---|---|
| [Getting started](getting-started.md) and [examples](../examples/README.md) | Installation and bounded runnable examples. |
| [Host embedding](guides/embedding-loop-engine.md) | Host-owned operations, exact authority, and independent completion gates. |
| [Providers and keys](guides/providers-and-keys.md), [settings](guides/settings.md), and [custom endpoints](guides/custom-endpoints.md) | Declared routes, credentials, capacity, and explicit live-probe authority. |
| [Queryable records and storage](guides/queryable-records-and-storage.md) | Managed-record contracts, revisions, and approved writes. |
| [Reports](guides/reports.md) | Saved Run History, reports, and playback. |
| [Harness service onboarding](guides/harness-service-onboarding.md) | Existing local commands and planned subscriber/client acceptance. |
| [Hosting procedures](guides/hosting-and-deployment-procedures.md) | Preparation for deployment families. Only the Fly.io profile is deployed, as a private pilot. The other profiles are not proof of a live deployment. |
| [Owner launch checklist](guides/launch-owner-checklist.md) | Account, payment, hosting, and live-model decisions that need explicit authority. |

The [guides index](guides/README.md) lists operating documentation.
Check each guide's implementation status and exact tested version. A local
protocol session does not establish remote authentication, durable billing,
or a complete paid service.

## Owner requirements

Preserve the full [discrete cognitive or act step Loop node explanation](context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md),
the [complete initial and fallback dimension requirement](architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md),
[flexible cognitive and action composition](architecture/FLEXIBLE-COGNITIVE-AND-ACTION-COMPOSITION.md),
and [layered harness controls](architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md).
These owner constraints remain active despite the dates of their source records.

The [configuration search guide](guides/configuration-grid-search-and-optimization.md)
separates proposed configurations, dispatched trials, independent acceptance,
and promotion. The [persistent solving decision](architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md)
governs useful continuation and failure review within declared authority.

## Evidence and history

[Verification reports](verification/README.md) and
[research records](research/README.md) are dated evidence.
Their numbers and implementation statements apply to their recorded source
and population. A historical passing count is not current release evidence.
Use the [records index](RECORDS-INDEX.md) to find the relevant record without
loading the full archive.

[Benchmarks](benchmarks/README.md) define populations and evaluators.
[Case studies](../case-studies/README.md) report measured end-to-end results.
The [showcase](../showcase/README.md) presents the architecture; it is not a
substitute for executed checks.

The [preserved documentation-index snapshot](evidence/context-route-snapshot-2026-09-19/docs__README.md.txt)
retains earlier navigation and status wording. No immutable historical report
was rewritten during the context-route cleanup.

## Coding-agent prompts

Read [AGENTS.md](../AGENTS.md), then the
[coding-agent route](context/CODEX-START-HERE.md) and the
[engineering standards](standards/README.md).
The [prompt index](prompts/README.md) distinguishes the one broad continuation
brief, focused workflows, and design history. Select guidance for the current
task; do not treat old mandates as permission to launch work.

Use [humanizer-context.md](../humanizer-context.md) and
[the writing templates](templates/README.md) for public prose.
