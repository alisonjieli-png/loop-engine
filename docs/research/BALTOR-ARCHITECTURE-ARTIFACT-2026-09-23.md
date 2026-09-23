# Baltor architecture: one governed runtime, replaceable engines and native intelligence

Kind: dated technical companion artifact for the Baltor System Handbook.
Prepared September 23, 2026. This page maps the owner's direction to the
existing architecture and identifies proposed integration checks. It does
not replace [AGENTS.md](../../AGENTS.md), the
[architecture constitution](../architecture/CONSTITUTION.md), the
[component contracts](../contracts/README.md), or the
[roadmap](../roadmap/roadmap.yaml). Those remain authoritative for rules,
current code and work state.

## Complete runtime classification

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

This is the required classification from
[AGENTS.md](../../AGENTS.md#required-architecture-trees). `Loop` is the only
executable graph vertex. An engine, model gateway, harness process, credential
broker, intelligence file, workflow canvas, index or hosted endpoint is a
component or passive object used by an owning Loop, not another runtime type.
Role, relationship, mode, profile, step order, settings, permissions and
categories answer different questions. A category or filename never changes
authority. A Spawned Loop may narrow inherited permissions; broadening requires an
explicit delegated grant. The [constitution](../architecture/CONSTITUTION.md)
states these invariants.

## What one focused step means

A **discrete cognitive or act step Loop node** is an independently governed
instance of the `Loop` runtime responsible for one clearly defined cognitive
step or action. It can interpret information, identify a missing requirement,
compare alternatives or evaluate a result; it can also inspect a directory,
build software, run a test, create an artifact or perform an authorized
external action. Its context, instructions, skills, plugins, tools and working
files are selected for that assignment. Essential information may be placed
directly in the harness, while larger or less certain material remains
behind authorized versioned references. The step does not automatically
receive the full task history or every available tool.

A separately initialized harness process, such as OpenCode, Pi, Codex or a
custom implementation, can perform the assignment. If its policy permits,
another harness can attempt the same assignment after a failure. The
assignment's contracts, permissions, history and remaining authority persist
across attempts. The step may inspect an observation, repair an approach and
repeat until its declared completion conditions are met. Discrete refers to
the scope of the assignment; it does not limit the work to one attempt, one
model call or one output.

The step may publish an initial candidate and continue while its conditions
and authority allow, producing alternatives that may be better, worse or
useful under different conditions. Consumers must identify the exact output
used. Publication does not necessarily end the assignment. Continued work
does not authorize a repeated external effect: alternative email drafts can
continue, but sending a message requires its own exact authorization and
duplicate-effect protection. This is the
[complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation)
in operational terms; it applies to the same `Loop`, not a `Node` subclass.

## Product boundary and step path

```text
Hosted Baltor intelligence service
├── Identity, entitlement, tenant policy and metering
├── Approved immutable package release and withdrawal
├── Search index and small typed references
└── Exact authorized package delivery

Customer-side Loop Engine host
├── Starting Practitioner Loop: task, limits and acceptance
├── Intelligence Query Loop: eligible search, retrieval and framing
├── Step execution envelope: qualified engine and one fresh harness
│   ├── Client-native placement of selected approved files
│   ├── Scoped model and tool access through host-owned boundaries
│   └── Observation, continuation and candidate output
├── Independent verification and Solution Loops where needed
└── Run History, feedback and provisional improvement candidates
```

The default is **one newly started harness per focused step**, with an
isolated task root and client configuration. The host binds a versioned
client layout, exact approved package bytes, native destinations and an
observed discovery result. Some clients read ancestor or user-level
instructions even when their task directory is new, so a fresh directory
alone is not isolation. The
[native placement study](NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md)
records tested paths and the configured, rather than default, role of
`CODEX.md`. Harness-specific trust and activation requirements must be
checked for the exact client version.

Search, selecting, materializing, framing, invoking, replaying and
interpreting intelligence are Loop operations. Search returns small
references; selected bodies load after eligibility and permission checks.
An authorized fetch does not show that the client discovered a file, that
the model used it, or that the task succeeded. Record offered, fetched,
placed, discovered, loaded, used and independently verified as separate
facts. The [SaaS scale synthesis](SAAS-AND-HUNDRED-THOUSAND-EXECUTION-GATES-2026-09-22.md)
describes the proposed package release and delivery contract; it is not yet
the production implementation.

## Intelligence axes and package identity

```text
Persistent intelligence layers
├── Context Intelligence
├── Code Intelligence
├── Runtime History and Solution Intelligence
└── User Feedback Intelligence

Intelligence families
├── Loop-native intelligence: built for the Loop runtime
├── Harness intelligence: native files a standard harness reads or invokes
└── Open Knowledge Format intelligence: general open-format knowledge
```

The layers say where an item's authoritative body and lifecycle live. The
families say what the material is built to follow. A harness package can
include `AGENTS.md`, `CLAUDE.md`, a configured `CODEX.md`, a `SKILL.md` with
scripts and references, a tool, plugin, subagent definition, hook, protocol
server declaration, asset or data file. Every delivered member needs an
exact path and digest. A multi-file method is one logical package, with
separate physical-file and client-rendering counts. The
[intelligence rules](../../AGENTS.md#intelligence-rules) place native harness
bodies in the `harness_local` source layer and forbid copying an active
Loop-native Code Intelligence body there merely to inflate supply. Runtime
Memory is temporary and scoped to one run, not a fifth persistent layer.

Original and imported packages are candidates until a different process
independently approves their exact bytes, source rights, dependency and
effect properties. A derived variant for one model or harness is versioned
and checked as a derivative; changing a script or asset invalidates the
approval of that exact tree. The
[model-conditioned intelligence study](MODEL-CONDITIONED-HARNESS-INTELLIGENCE-2026-09-22.md)
and [file-kind study](HARNESS-INTELLIGENCE-FILE-KINDS-AND-ADMISSION-2026-09-22.md)
give the research basis. Review, search rank, model confidence or a
successful execution cannot approve the producer's own package.

## Fixed edges and swappable engines

The owner requires each functional component to communicate through a
typed, versioned, stable edge, with replaceable engines inside the
component. The exact component and slot design is in
[Engines behind fixed edges](../architecture/ENGINES-BEHIND-FIXED-EDGES.md).
This table is a map of ownership, not a declaration that every slot has
shipped.

| Edge | Stable request and result concern | Engine or adapter choices to qualify | Refusal that must remain stable |
|---|---|---|---|
| Intelligence search and retrieval | Task intent, tenant and permission filter, result references, no-answer and evidence | Persistent lexical search, later hybrid or graph-assisted search | An ineligible or weakly relevant result cannot become an authorized body. |
| Library ingestion and admission | Candidate source identity, rights, package tree, checks and approval record | Original generator, licensed importer, per-kind validators | A draft or changed byte cannot enter an active release. |
| Step execution | Loop assignment, harness profile, budgets, workspace, result and observations | Qualified Agent Client Protocol adapter, Codex, Claude Code, OpenCode, Pi or custom engine where supported | An unqualified client or inherited context cannot execute a step requiring fresh isolation. |
| Model access and call strategy | Exact endpoint, model, output capacity, call authority and usage | Customer-selected route, pass-through, permitted multi-model strategy | Additional calls or failover cannot exceed declared authority. |
| Workspace and effect execution | Confined paths, allowed operations, exact effect decision, unknown-commit record | Process sandbox, tool bridge, storage adapter | A path escape, unapproved tool call or uncertain effect cannot be accepted or silently replayed. |
| Evaluation and Run History | Candidate output, independent acceptance, physical usage and event identity | Registered evaluator and durable record implementation | A producing model's confidence cannot certify its own output. |

An engine preference sent by a harness or Loop is a preference within
authority, never a grant. The resolver checks declared eligibility and
runtime protocol, schema, capability and adapter compatibility before
ranking. It retains the declared order until comparable recorded evidence
meets the rule for changing it. Retry, same-provider fallback,
cross-provider failover, formatting repair, evaluator-triggered repair and
task replanning have distinct ownership. The
[wrapper design](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
also keeps cumulative budgets, cancellation and external-effect identity
across outer and native harness loops.

## Credentials and effects cross a narrower boundary

The customer-side host should hold provider and third-party connection
references and resolve them only for the selected exact operation. A fresh
harness should receive a scoped local model or tool capability, not a raw
provider key or the Baltor account key. The hosted service supplies
intelligence and does not need the customer's local-model credential.
An address such as `127.0.0.1` is relative to the calling process or
container network namespace; it cannot be assumed reachable from Baltor's
server. These are research recommendations from the
[credential delegation study](CUSTOMER-ENDPOINTS-AND-CREDENTIAL-DELEGATION-2026-09-22.md).

Discovery must be effect-free. File writes, shell, network, model calls,
spending and external mutations require typed authority. Every effect
approval binds its actual arguments. If an external operation times out
after dispatch, its commit state is unknown until reconciled; replaying it
without reconciliation could duplicate the effect. Native tools, plugins
and protocol servers remain adapters under the owning Loop. A configuration
file on disk does not prove a connection was activated or authorized.

## Current state, target state and discriminating checks

| Boundary | Observed as of the cited September 22 audit | Target check or known-wrong case |
|---|---|---|
| Hosted inventory | The packaged release has 43 single Markdown bodies; their metadata does not prove native Agent Skill pickup. | Admit and deliver exact multi-file native packages; reject a missing member or changed member digest. |
| Hosted scale | A synthetic 100,000-row manifest exceeded the current 2,000,000-byte loader limit; per-request retrieval indexing exceeded the stated 30-second request deadline and 2 GB machine profile. | Persist a release-bound index; prove tenant-filtered, paged search and exact package reads at 10,000 and 100,000 approved packages, including withdrawal and rollback. |
| Fresh client | No end-to-end invited-customer accepted native step was observed. Local client discovery probes are narrower evidence. | In a clean home, prove selected files load for the exact client version and that an unselected ancestor skill or configuration causes refusal. |
| Customer journey | Public registration, sign-up email, checkout and portal were off in the audited live deployment. | Prove invite-to-key-to-fetch-to-native-use-to-accepted-result; test each later paid-account transition independently. |
| Engine selection | The engine framework and broader native executor qualification are roadmap work; some local contracts and confined execution exist. | A second qualified engine replaces the first without changing the caller; a missing capability or incompatible version refuses before effects. |
| Credential and tool access | The confined harness has a local model relay, but a qualified per-step tool bridge and per-use secret resolution are proposed. | No raw key appears in the harness or trace; an unapproved tool argument or changed endpoint refuses before dispatch. |

The first two rows are measured in the
[live readiness audit](../verification/SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md)
and [synthetic scale probe synthesis](SAAS-AND-HUNDRED-THOUSAND-EXECUTION-GATES-2026-09-22.md).
The remaining boundaries are documented in the
[credential study](CUSTOMER-ENDPOINTS-AND-CREDENTIAL-DELEGATION-2026-09-22.md),
[native placement study](NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md)
and [engine design](../architecture/ENGINES-BEHIND-FIXED-EDGES.md).
These proposed checks belong under existing roadmap work, particularly
D-17, D-19 and S-6.40 through S-6.62; this companion does not create a
second delivery queue.

## Handbook use

Use this page for the handbook's system diagram and boundary explanation.
Use the [north-star companion](BALTOR-NORTH-STAR-ARTIFACT-2026-09-23.md)
for the product goal, the [current client and server map](../architecture/MVP-CLIENT-SERVER.md)
for deployment facts, and the [roadmap](../roadmap/roadmap.yaml) for verified
work state. Public home and How it works pages should explain tasks, each
step, selected information, tools and checked results in plain words;
internal runtime classification belongs in technical documentation.
