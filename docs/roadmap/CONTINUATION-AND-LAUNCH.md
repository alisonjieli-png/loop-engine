# Continuation and first release

Kind: living execution plan. The step authority is [roadmap.yaml](roadmap.yaml).
The [current status artifact](CONTINUATION-STATUS.md) is generated from it.
Update the authority after each reviewed batch, then regenerate the artifact.

The [single HTML system map](../../artifacts/architecture-audit-2026-09-19/loop-engine-system-map.html)
combines the whole engine architecture, hosting and owner instructions, account and execution journeys, historical
feature matrices, the source explorer and the running worklist. It embeds
its own styles, scripts, layout library and data. The
[client and server note](../architecture/MVP-CLIENT-SERVER.md) separates
implemented local paths from proposed hosted connections. The
[Supabase and Vercel profile](../guides/supabase-and-vercel-launch-profile.md)
is an alternative managed-service arrangement. The owner's preferred compute
host is Fly.io, with Supabase considered for managed data and identity. Account
selection does not authorize a deployment or charge.

The original target was a launch decision by September 20, 2026 at 10:12:54
Eastern time, 24 hours after that planning window began. It is a historical
planning target, not a current release forecast. The intended product is a
website, a subscriber dashboard, payments, and an authenticated intelligence
service that customers connect to their own harnesses. Hosted customer
execution is an optional deployment profile. Task decomposition and the
internal engine still need to work.

Customer execution stays local for the first release. The account and
intelligence service can be hosted separately; its local profile supports
development and self-hosting. LangGraph is not a required dependency or a
second runtime. Optional engines remain behind the existing authority and
lifecycle contracts.

The local service has durable tenant, revocation, disclosure, metering and
signed-payment-event behavior. Real loopback web and protocol clients exercise
that domain. The [durable checkpoint](../../artifacts/architecture-audit-2026-09-19/durable-service-checkpoint.md)
and [transport checkpoint](../../artifacts/architecture-audit-2026-09-19/http-service-checkpoint.md)
record exact tests and limits. Live account setup does not block further local
integration, packaging, restart, refusal and browser checks.

The owner clarified the requirements during planning:

1. Prepare every major hosting family without selecting one vendor.
2. Serve all four persistent intelligence layers, Harness Intelligence, and
   templates through the Model Context Protocol or the same service API.
3. Preserve decomposition into graphs, subgraphs, and atomic reasoning or
   building assignments. Each governed assignment can have its own harness.
4. Wire and test internal functionality even when the first interface does not
   expose it. A smaller interface is not permission to leave hidden dead code.
5. Provide installation, authentication, client configuration and existing
   model-endpoint setup in the frontend. Optional local provider and Kaggle
   guides remain separate; customers do not need to host models themselves.
6. Continue code repair, organization, research, competitive comparison,
   qualification, and the broader improvement programme.

The target does not establish that all of this fits in one day. The initial
review found ten defect or integration-gap observations despite 5,316 passing
checks. If a required gate remains open at the deadline, publish the exact
release-candidate state and continue the work. Do not rename an incomplete
candidate a paid launch.

The [September 20 checkpoint](../context/DEVELOPMENT-CHECKPOINT-2026-09-20.md)
records the deployed private pilot, exact current evidence, owner preparation
and ordered remaining work. The public site uses benefit-led language and a
light default appearance. Those presentation changes do not close runtime,
onboarding or paid-release gates.

The [Fable 5.1 handoff](../context/FABLE-5-1-HANDOFF-2026-09-20.md) records the
prepared provider access, the account code shipped in release 7 and safe
continuation. The [takeover checkpoint](../context/TAKEOVER-CHECKPOINT-2026-09-20.md)
records the state verified after that handoff, the repairs that followed, the
private beta definition and the working cycle for tests, checkpoints and
releases. The public website uses Baltor and each step. Canonical
runtime names remain in technical documentation and GitHub, not the homepage
or How it works. This changes audience presentation, not the architecture.

## Expanded implementation and verification plan

The delivery packages in `roadmap.yaml` expand existing steps into actions
and verification cases; count them in the roadmap, not here. They cover domain and mail, accounts,
payments, cloud records, retrieval, native file use, unattended local
execution, reviewed expertise, reusable solutions, measured benefits, customer
experience, release operations, security boundaries, intelligence review,
reliability, installation, the private beta and the waiting list. Each names acceptance dependencies, a failure control and an
authority limit. The generated status and main HTML render the same records.

This is planning detail, not a second source of task status. The existing
step states and eight release gates remain authoritative. Acceptance
dependencies do not block independent local preparation while a grant is
missing. Review source and live state before choosing a package, rather than
following the historical launch-order list mechanically.

| Sequence | Packages | Practical outcome |
|---|---|---|
| Review first | D-01 | Resolve the current account and conformance findings without weakening guards. |
| Private beta | D-17 | Invited people sign in, create personal client keys, connect a supported client and use a reviewed starter catalogue. Releases come only from a committed revision. No payment and no public registration. |
| Access requests | D-24 | A visitor leaves an address on the waiting list, an operator invites one entry with a discount the payment account holds, and an address is erased on request. A service without a waiting list makes no offer. |
| Service journey | D-02, D-03, D-04, D-05 | A real customer can confirm identity, connect, retrieve permitted material and exercise a test subscription. |
| Useful work | D-06, D-07, D-08 | Selected material reaches an actual step; supported local work survives interruption and produces reusable checked results. |
| Evidence and experience | D-09, D-10 | Measure proposed benefits and complete understandable customer journeys. Copy improvements can proceed independently of account integration. |
| Boundaries and operations | D-13, D-14, D-15, D-16 | Qualify execution and service security boundaries, intelligence ingestion and withdrawal, reliability and the customer data lifecycle, and installation and compatibility. |
| Release | D-11 | Qualify the exact source and deployment, recovery, support and owner-approved paid access. |
| Continued development | D-12 | Compare interchangeable engines and reviewed improvements without delaying unrelated delivery. |

The [benefit guide](../guides/launch-benefits-and-evidence.md) translates the
owner's three launch themes into falsifiable checks. Overnight work requires
real long-running local-model evidence and safe recovery. Token savings
require complete matched accounting at a preserved quality floor. Useful
expert context requires actual loading and task outcomes, including cases
where adding information is better. No draft becomes a public claim merely
because a planning row is complete.

## One architecture, several delivery surfaces

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

The proposed product composition is:

```text
Loop Engine product
├── Public website
│   ├── explanation, catalogue previews, and accurate pricing
│   └── installation, client setup, provider, and task guides
├── Subscriber dashboard
│   ├── account, subscription, billing portal, and access management
│   ├── catalogue, templates, versions, downloads, and client setup
│   └── task graphs, permitted history, usage, and failure explanations
├── One service boundary
│   ├── website API
│   ├── Model Context Protocol adapter
│   ├── payment event adapter and entitlement decisions
│   └── durable records, telemetry, administration, and package delivery
├── Intelligence access through existing contracts
│   ├── Context Intelligence
│   ├── Code Intelligence
│   ├── Runtime History and Solution Intelligence
│   ├── User Feedback Intelligence
│   └── Harness Intelligence and templates as qualified referenced views
└── Client or local execution
    ├── canonical task graph and typed subgraphs
    ├── separately initialized harnesses for atomic assignments
    └── independently checked solutions, exports, and later reuse
```

The service and client use the same definitions, catalogues, permissions,
qualification records, and package identities. A remote protocol adapter does
not create another graph authority, scheduler, intelligence store, or runtime.

## The best initial service shape

Build one Python service over the existing catalogue and provisioning
boundaries. Use a maintained asynchronous web and protocol library after
pinning compatible versions. The browser API and Model Context Protocol
adapter call the same application operations. A web framework choice does
not belong in the Loop runtime.

Use an established identity provider with a versioned authorization adapter.
Website sign-in, remote protocol authorization, and subscription entitlement
are separate checks. Avoid implementing a new identity service inside Loop
Engine. Preserve a local development profile with explicit test identities.

Stripe is the proposed first payment adapter, subject to the owner's account
and pricing decisions. Use hosted checkout and the billing portal. Signed
subscription events update the durable entitlement record; both browser and
protocol reads consult that record. Repeated or delayed events require
idempotency and reconciliation. A browser redirect is not payment evidence.
See [Stripe subscription events](https://docs.stripe.com/billing/subscriptions/webhooks).

The authenticated service should initially serve small metadata references
and fetch a selected body only after access and qualification checks. Large
packages can use an authorized object-store delivery adapter. Keep catalogue
metadata and immutable bodies separate, with one authoritative record identity.
Persist tenant state, entitlements, usage, and telemetry outside disposable
application instances. The existing embedded database profiles remain useful
for a single-host install; horizontal deployments need a suitable shared
store behind the same contract.

The current Model Context Protocol revision must be treated explicitly. The
2026-07-28 Streamable HTTP specification uses a POST endpoint and removes the
older GET stream and protocol-level sessions. Support for an older client
must be a tested compatibility profile. Do not mix the two protocols in one
unversioned handler. The implementation must also satisfy the selected
authorization specification and test the installed clients and library.
[Transport specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/streamable-http),
[authorization specification](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization).

The protocol is a connection surface. It does not supply the product's
subscription rules, catalogue admission, durable storage, or independent
qualification by itself.

## Proposed service operations

These are requirements for adapters over existing boundaries, not a claim
that the commands or remote endpoints are installed today.

| Operation family | Required behavior | Existing authority |
|---|---|---|
| Discovery and search | Filter permitted intelligence and templates by declared dimensions; return bounded references and pagination. | Intelligence Search and Retrieval, catalogue query contracts. |
| Manifest and body access | Return exact versions, digests, license state, dependencies, effects, and qualified bodies after disclosure checks. | Harness Intelligence, Code Intelligence admission, provisioning. |
| Template selection | Return reviewed task, graph, prompt, contract, and harness templates as typed references. | Template library, Loop profiles, prompt resources. |
| Task planning | Accept a task or a client-produced proposal and resolve it to canonical graphs, subgraphs, and typed atomic assignments. | Practitioner planning and `LoopGraphDefinition`. |
| Provisioning | Resolve assignment resources, scoped access, instruction files, and client-side preparation without granting undeclared execution. | Existing provisioning, credential leases, workspace contracts. |
| Observations and history | Accept bounded, attributed client observations and preserve server observations separately. | Run History, stage/call identities, record storage. |
| User guidance | Read and write permitted human guidance with scope, provenance, revision checks, and applicable approval. | User Feedback Intelligence and managed-record operations. |
| Administration | Inspect tenant usage, revoke access, manage approved packages, and review failures through role-scoped operations. | Existing service, qualification, and record boundaries. |

Searches must cover the four layers, even if a particular deployment has zero
records in one of them. An empty result needs an honest population count.
Harness Intelligence is the delivery-oriented view over those identities.
Changing the canonical layer vocabulary requires the separate recorded
architecture decision; the dedicated harness catalogue need not wait for it.

## Original delivery windows and acceptance

The windows below preserve the initial planning attempt. They are not the
current schedule or a forecast for the expanded work. Use the delivery
packages above and current source evidence for the next batch.

| Target window | Work | Required evidence |
|---|---|---|
| Hours 0 to 3 | Capture the plan, repair confinement and unresolved guardrails, repair call identity and retention, bind the catalogue to durable records. | The ten recorded observations become discriminating checks; ordinary reads cannot serve unqualified or unauthorized bodies. |
| Hours 3 to 7 | Identity, subscription entitlements, payment adapter, and portable deployment definitions. | Tenant separation, signed-event handling, replay/order checks, and plans with explicit resources and secrets references. |
| Hours 7 to 12 | Connect the protocol service, usage persistence, task decomposition, provisioning, credential leases, and resource admission. | Real public and internal entry points execute the intended work; restart and refusal paths preserve records and authority. |
| Hours 12 to 18 | Website, dashboard, starter packages, onboarding, native harness qualification, internal generation, solution publication, and integration inventory. | A new user completes the journey; an exact harness loads selected material; an independent process checks the result; exported work runs on new inputs. |
| Hours 18 to 22 | Freeze the release candidate and run the full assurance sequence. | Exact-source checks, clean installation, browser and playback checks, failure injection, backup restore, and rollback rehearsal. |
| Hours 22 to 24 | Deploy an authorized pilot, exercise the actual hostname and payment integration, and record the release decision. | Observed client access, durable state, measured usage, working revocation, and explicit hosted and paid-launch evidence. |

These windows overlap where dependencies permit. Their combined scope is
ambitious. Reforecast after each milestone against observed work, rather than
quietly dropping internal integration or exposing unverified features.
Research and narrowly isolated organizational work can continue independently.

The generated artifact lists exact dependencies. It has separate gates for
the user product, serving, intelligence, internal integration, onboarding,
operations, hosted pilot, and paid launch. A deployed health endpoint alone
passes none of the complete product journeys.

## The recurring development loop

1. Inspect revision, dirty state, process ownership, and relevant instructions.
   Select the first eligible continuation step, not the first old roadmap row.
2. Reproduce the failure or missing behavior at its owning entry point. State
   whether the work, the check, or the environment is wrong.
3. Make the smallest general change at that boundary. Preserve supported
   alternatives, public contracts, record readers, and existing user work.
4. Run the focused checks, including a known-wrong case. Then run the owning
   component checks. A stub verifies a local contract, not a provider claim.
5. Run the required conformance, full self-test, documentation, clean-install,
   examples, and browser or playback checks in proportion to the claim. Before
   a commit, run the continuous-integration commands on an export of the exact
   tree and show that new guards detect removal of their required behavior.
6. Obtain independent review at the required qualification boundary. Record
   source identity, commands, failures, exclusions, and evidence limits.
7. Update the step, its distinct evidence dimensions, research findings,
   deployment profile status, and the activity log. Regenerate the artifact.
8. Commit only owned and verified changes under the repository's publishing
   rules. Check for concurrent changes before staging explicit paths. Continue
   with the next eligible task.

A repeated failure requires a changed approach or a precise authority,
environment, or provider finding. An arbitrary attempt count does not complete
the work. Unknown external commits require reconciliation before retry.

## Durability and flexibility requirements

Every configurable boundary needs initial choices, ordered fallbacks,
compatibility checks, observable effective settings, and a saved transition.
The [complete configuration inventory](../architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md)
remains the baseline. Additional dimensions remain welcome when a distinct
decision and a discriminating test justify them.

| Boundary | Initial development choice | Ordered alternatives or failure response | Discriminating check |
|---|---|---|---|
| Hosting | Same versioned image and explicit external state contract. | Select a qualified profile for the target; otherwise prepare it and report unavailability. Never silently move tenant data. | Run the same acceptance suite on each advertised target and replay upgrade/rollback. |
| Protocol | A pinned client/library/specification combination. | A separately qualified older protocol profile, then the same scoped web API. | Incompatible versions refuse without losing access checks or changing semantics. |
| Storage | Existing catalogue adapter suitable for the deployment's writer model. | Another conformance-tested adapter with an explicit migration and rollback. | Restart, optimistic-write conflict, interrupted commit, restore, and cross-tenant query. |
| Harness | Exact installed and qualified adapter with observed loading. | Authorized compatible adapter or recorded unavailability. | Missing resource, wrong version, cancellation, and changed harness preserve task and remaining authority. |
| Models | Customer-selected exact route and source-backed capacity. | Declared same-provider alternatives; cross-provider failover only when authorized. | Physical-call accounting, missing usage, quota outage, and refusal before unauthorized dispatch. |
| Intelligence | Qualified reference-first access to the relevant material. | Alternative qualified sources or an explicit gap, followed by candidate generation. | Changed body, revoked scope, stale applicability, candidate state, and later-run use. |
| Payment | Stripe behind a payment-event adapter. | Another provider behind the same entitlement contract after qualification. | Forged, repeated, reordered, and missing events do not create false access. |
| Recovery | Resume exact durable state when its effects are reconciled. | A compatible checkpoint or a typed escalation. | A lost response cannot produce a second committed effect or erase an outstanding liability. |

Keep runtime state out of image layers and package resources. Separate
transactional writes, immutable artifacts, and analytical projections.
Declare migration versions and retention policies. Exercise at least one
restart, one failed write, one rollback, and one restore on each release
profile. A pause that retains memory is not hibernation.

## Code and directory organization

Start with the [measured flat-core proposal](../architecture/FOLDER-DEPTH-AND-THE-FLAT-CORE-2026-09-18.md)
and the existing component map. Move a coherent owning family only after its
behavior is covered. Review its dependency graph, import strings, public
exports, serialized identifiers, tests, and documentation together.

The first structural work should separate service composition from domain
rules and extract responsibilities from the largest runtime records module.
Choose the exact first move after measuring its import impact. Update callers
to the current owning modules and remove compatibility-only imports. The
owner's [pre-launch version policy](../architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md)
requires explicit versions and handshakes, not support for unused older shapes.
Do not move hundreds of files solely to make the tree look deeper.

Use existing folders: `core` for mechanics, `loop` for runtime contracts,
`catalog` for storage contracts, `code_nodes` for existing application
composition, `templates` and `strings` for their owning resources, `tools` for
development commands, `examples` for runnable setups, and the established
documentation kind folders. New subpackages need a stated owning boundary and
README. A new top-level boundary requires the architecture contract and tests.

## Research that continues with development

The six interrupted Claude tracks are retained in `roadmap.yaml`. The owner
also authorized three parallel research tasks covering capability competitors,
prior art, and funding or strategic paths. Their findings must update the
comparison without turning intentions into present capabilities.

Evaluate counterexamples: other systems already distribute skills, executable
tools, and evaluated context. Investigate whether our particular combination
of qualification, versioned graph use, client-side authority, and reuse has
measured value. Do not claim novelty merely because one comparison omitted a
competitor. A possible acquirer is a thesis about strategic fit, not evidence
of interest.

Experiments preserve development, validation, and untouched final evaluation
populations. Compare additional steps and material as well as removals.
Retain failures and overhead. The owner-declared minimum of one million runs
for learned heuristic adoption, with the exact atomic fingerprint exception,
remains separate from collecting data and testing candidates.

## Artifact management and owner actions

The machine-readable roadmap is the current planning authority. The generated
status page includes tasks, dependencies, release gates, hosting procedures,
all earlier initiatives, and an activity log. The historical Claude artifact
stays linked. No connected editing surface for that hosted copy is available
in this session, so changes are maintained in the repository and can be
published from the same source when access exists.

Run after each batch:

```bash
.venv/bin/python tools/build_continuation_status.py
.venv/bin/python tools/build_continuation_status.py --check
.venv/bin/python tools/build_continuation_status.py --next
```

The [owner checklist](../guides/launch-owner-checklist.md) separates account and
business decisions from engineering work. The
[style guide](../guides/product-style-guide.md) governs the public site,
dashboard, setup pages, and status language. The
[onboarding plan](../guides/harness-service-onboarding.md) maps the installation
and integration guides to executable acceptance checks.

## Complete behavioral explanation

A discrete cognitive or act step Loop node is an independently governed
instance of the Loop runtime responsible for one clearly defined cognitive
step or action. A cognitive step might interpret information, identify a
missing requirement, compare alternatives, or evaluate a result. An action
might inspect a directory, build software, execute a test, create an artifact,
or send an authorized email.

Each discrete cognitive or act step Loop node receives the context,
instructions, skills, plugins, tools, and working files relevant to its
assignment. Essential information can be supplied directly, while additional
information can remain in centralized storage behind authorized, versioned
references. It does not automatically need the entire task history or every
available tool.

A separately initialized harness process, such as OpenCode, Pi, Codex, or a
custom implementation, can perform the assignment. When explicitly permitted,
another harness can attempt the same assignment after a failure. The
assignment's contracts, permissions, history, and remaining authority persist
across those attempts.

Discrete describes the scope of the assignment, not a restriction to one
attempt, one model call, or one output. A discrete cognitive or act step Loop
node can examine whether an observation matches its expectations, identify a
problem, repair or change its approach, and repeat until its declared
completion conditions are satisfied.

Alternatively, a discrete cognitive or act step Loop node can publish an
initial candidate output and continue working while its continuation
conditions and authority permit. It can produce additional alternatives over
time, including alternatives that are better, worse, or useful under different
circumstances. Consumers must identify exactly which output they used.
Publishing an output does not necessarily mean that the producing assignment
has finished.

For externally consequential actions, continued operation does not authorize
repeated effects. For example, generating alternative email drafts can
continue, but sending an email requires its own authorization and protection
against duplicate delivery.
