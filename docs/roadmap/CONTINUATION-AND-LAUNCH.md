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
| Go fully live | D-25 | Registration, the paid funnel, a verified first load in the customer's own harness, every built page live, status and support. |
| Packages at scale | D-26 | 10,000, then 100,000 approved packages, then 100 to 1,000 more a day from scouts, watchers, producers and a three-family panel. |
| Clear components | D-27 | One generated component index, contract test kits for engines alone, in groups and end to end, and one home for every topic and term. |
| Selectable engines | D-28 | Pinned, preferred and automatic selection at every slot, and a Baltor-native engine beside every adopted project. |
| Agents that manage the system | D-29 | Reusable workflows and recurring reviews whose output is always a report or a candidate, later run as Practitioner Loops. |
| A release train | D-30 | Release records for every kind, a customer changelog, feature flags and upgrades of the local engine. |

The [benefit guide](../guides/launch-benefits-and-evidence.md) translates the
owner's three launch themes into falsifiable checks. Overnight work requires
real long-running local-model evidence and safe recovery. Token savings
require complete matched accounting at a preserved quality floor. Useful
expert context requires actual loading and task outcomes, including cases
where adding information is better. No draft becomes a public claim merely
because a planning row is complete.

## Launch and scale program

On September 23, 2026 the owner asked to take the product fully live, to grow
the library to at least 100,000 harness packages and then add 100 to 1,000 a
day, to manage and improve the system with agents, to onboard and upgrade
customers, and to ship new features, packages and engines continuously. The
owner also asked for simple, separated and contracted components with engines
that can be swapped, tested alone and in groups, and for one index that keeps
discussions and names from conflicting. The owner's words are recorded in the
evidence of each step.

The program has six parts. Each part is a delivery package in
[roadmap.yaml](roadmap.yaml), which holds its steps, verification cases,
authority limits and rollback. The table above lists them with the earlier
packages. This section is planning detail, not a second source of task state.

### Order of work

The owner column names who holds the work today: the Codex session that owns
the September 23 consolidation line, the Claude Code session that wrote this
plan, engineering in general, recurring agents, or the owner. Only one item
asks for the owner, and it has a fallback: OWNER-03 closes the identity
provider's back-door sign-up so that Baltor's own sign-up can open to everyone.
If it does not happen, engineering neutralizes the back door with a
service-side guard instead. Engineering decides everything else and records the
reason, as the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md says.

| When | Owner | Work | Roadmap steps | Done when |
|---|---|---|---|---|
| Tonight | Codex | Push the consolidated tree after full continuous integration on the exact tree: catalogue re-anchoring, email-first sign-up (switched off), documentation pages, search effects, library tools and the review panel repairs. | S-6.29, S-6.62 | Continuous integration passes on the pushed revision and every line the tree added survives the merge. |
| Tonight | Claude | Commit or archive every remaining piece of work: the Astra compiler handoff, the naming resolution, the reusable workflows, this session's research records and wave 5 candidates; list anything archived in the work archive register. | S-6.29, S-6.76 | No uncommitted work without an owner remains in the shared checkout; everything is on main or in the register. |
| Tonight | Owner | OWNER-03, about 30 seconds: in Claude Code run /mcp and sign in to baltor-supabase, so engineering can close the identity provider's back-door sign-up. Baltor's own sign-up stays open to everyone; this is what makes opening it safe. | S-6.65 | Engineering confirms the back door is refused and opens registration. |
| Tonight | Engineering | Release 22 from the consolidated main through the guarded workflow, run the live checks on all eight hostnames and record the release with its rollback image. | S-6.35, S-6.78 | The running image digest equals the built digest and every hosted check passes. |
| Next 72 hours | Engineering | Fallback that needs nobody: a service-side guard that honours only accounts Baltor created and replaces a provider-created account when the real person signs up, with the pre-hijacking case as its known-wrong test. | S-6.65 | An account created through the provider's endpoint never reaches Baltor, and the real person's sign-up wins. |
| Next 72 hours | Engineering | Stage the two sign-up secrets through standard input and the account email host block, switch registration on, and run the live sign-up journey with its negative controls. | S-6.65 | A fresh address signs up live; the provider's public path is refused. |
| Next 72 hours | Engineering | One way in: every customer account comes from Baltor's sign-up; staff get superadmin, developer or analytics roles fixed in code; invitations, the waiting list, hand-issued customer keys and the provider's raw sign-up are retired as ways in. | S-6.85 | A named check refuses every other way to open an account. |
| Next 72 hours | Engineering | Run the paid funnel with a staff test account: subscribe, portal, cancel; Get set up returns one exact path; the first package load is verified from the harness's own record. | S-6.66, S-6.21, S-6.48 | Each fact (entitled, set up, loaded) is recorded separately. |
| Next 72 hours | Engineering | Serve every built page: /models, /use-cases and its pages, /status, the documentation pages, per-hostname pages, robots.txt, sitemap.xml, canonical and social tags; switch the site map check on. | S-6.67, S-6.33 | The site map check passes on every hostname. |
| Next 72 hours | Engineering | Fix what the responsive lab found: the pricing button, headings at 200% text, the reader's text size, layout shift, 44 pixel targets and a 68 character measure; rerun the lab on three engines. | S-6.67, S-6.33 | The lab passes within the scroll budgets. |
| Next 72 hours | Engineering | Calibrate the three-family panel on the malicious and benign controls with Ollama Cloud models and the Codex command line; record the error gate and the throughput per hour. | S-6.63, S-6.69 | The panel meets its gate; throughput is measured, not assumed. |
| Next 72 hours | Engineering | Adjudicate the round two approval conflicts and release only the correctly approved subset; verify isolation and the demonstration digests. | S-6.62 | No item is released without a valid three-family approval. |
| Next 72 hours | Engineering | Put wave 5 and the Codex twelve-package cohort through the panel and release what passes. | S-6.69 | Approved packages appear in a catalogue release with notes. |
| Next 72 hours | Engineering | Run the overnight proof with Gemma 4 on Ollama Cloud within its 600-request ceiling and put the measured result on /models. | S-6.47, S-6.37 | The dated report shows accepted work, time, tokens and failures. |
| Next 72 hours | Engineering | Pass the 100,000-row serving probe with paged listing and an index built once for each catalogue release. | S-6.70 | The probe passes its unchanged thresholds. |
| This week | Engineering | Scale the factory to the panel's measured capacity: daily waves from the gap matrix and search misses, producers of two or more families, daily catalogue releases. | S-6.69, S-6.62 | Per-day counts of generated, approved and released packages and their files are recorded. |
| This week | Engineering | Serve multi-file packages in each harness's own layout through the Harness Working Directory Compiler, native engine first, agent-harness as an optional engine for text configuration, binaries and modes written byte for byte. | S-6.44, S-6.75 | Two harnesses load the same package with every byte and mode intact. |
| This week | Engineering | Add the index-backed search engine behind the search slot, calibrate the relevance floor on the held-out set and turn on the anti-scraping quotas. | S-6.32, S-6.52, S-6.39 | Recall, refusal accuracy and latency are recorded against the current engine. |
| This week | Engineering | Adopt the functional component standard after independent review: the extended rule 6 in AGENTS.md, one standard document extending the engine slot design, the terms in terminology.yaml, and the first enforcing checks. | S-6.84, S-6.30 | Each rule maps to a field, record or check; no second registry appears. |
| This week | Engineering | Generate the component index and add its drift check; settle the compiler and package names in terminology.yaml; start the topic index. | S-6.71, S-6.73 | The index check fails on a stale page and on a term with two definitions. |
| This week | Engineering | Give the step executor, search and material install layout slots their contract test kits; add group and journey tests; run isolated bindings in containers. | S-6.72 | A deliberately broken engine fails the kit that a real engine passes. |
| This week | Engineering | Map pinned, preferred and automatic selection onto the slot fields with decision records. | S-6.74 | A pinned engine never falls back; every selection is recorded. |
| This week | Engineering | Commit the reusable workflows and declare the recurring reviews; choose the scheduler and record the first scheduled runs. | S-6.76 | Each recurring job has a recorded run and an effect policy. |
| This week | Engineering | Support address, status view from the hosted checks and the incident runbook, exercised once. | S-6.68 | A forced check failure shows on the status view. |
| This week | Engineering | Release records for every kind, a customer changelog page, and feature flags through host configuration, starting with registration. | S-6.78, S-6.79 | A flag turns a feature on for one account and off again without a release. |
| Next two weeks | Engineering | Record the 10,000 approved packages milestone with its catalogue release, then keep the daily rate toward 100,000. | S-6.69 | The milestone names the release, the package count and the file count. |
| Next two weeks | Engineering | Source scouts for skills, plugins, protocol servers and harness files, and release-note watchers for the supported harnesses and tools. | S-6.81, S-6.82 | Finds become candidates with licences or idea records; nothing restricted is copied. |
| Next two weeks | Engineering | Plugins and setup paths: Claude Code plugin listing, Codex, OpenCode, Pi, Hermes and OpenClaw, and a protocol server bundle; one exact path per harness and hardware. | S-6.48, S-6.49 | Each plugin's session records the package offered, fetched, loaded and used. |
| Next two weeks | Engineering | The harness executor slot delegates one real step to each supported harness, including through the Agent Client Protocol. | S-6.31, S-6.42 | One step per harness is recorded as configured, loaded, used and verified. |
| Next two weeks | Engineering | With-and-without comparisons through Harbor on their own subdomains: data cleanup, tickets overnight on a small model, and a data science competition. | S-6.37, S-6.47 | Each comparison states its task population, models, failures and cost. |
| Next two weeks | Engineering | Weekly Harness File Profile refresh and the first maintenance Practitioner Loop. | S-6.80, S-6.77 | A changed harness convention becomes a candidate profile change. |
| Next two weeks | Engineering | Publish the local engine to a package index with an upgrade command, and write the scale plan from measured load. | S-6.78, S-6.57, S-4.6 | An upgrade negotiates versions and keeps settings; the scale plan names its trigger. |
| Continuous | Agents | Daily state review, nightly library wave, weekly harness profile refresh, weekly research and news sweep, weekly plan validation, weekly restore drill. | S-6.76, S-6.80, S-6.82 | Every run is recorded; no job pushes, approves or publishes on its own. |
| Continuous | Engineering | Maintain the library at scale: re-verify on harness changes, merge near-duplicates, withdraw with reasons, rank by measured use and learn from retrieval. | S-6.83, S-6.51 | The library stays correct as it grows. |
| Continuous | Engineering | Wrap every newly adopted outside project behind a slot with a Baltor-native engine beside it. | S-6.75 | Swapping the two is a configuration change. |

### The package factory

The factory turns sources into approved packages and keeps them correct. Its
milestone unit is a distinct approved package, as decided on September 22,
2026. The files inside the packages are counted beside that number, and a
candidate is never counted as approved.

```text
Package factory
├── Sources
│   ├── the gap matrix of file class, domain, harness and occupation
│   ├── customer search misses and repeated asks
│   ├── scouts over GitHub, package registries, skill and plugin marketplaces
│   │   and the protocol server registry
│   └── watchers over the release notes of harnesses, tools and standards
├── Rights
│   ├── copying allowed: the importer, with the licence file and notices
│   └── copying not allowed: an idea record, then an original rewrite
├── Producers from at least two model families
├── Deterministic pre-checks: parsers, the Agent Skills validator, scripts
│   against their own tests in a sandbox, secret and network scans, and the
│   malicious-skill regression set
├── Critique and repair by an agent that did not write the package
├── Review panel: three approvals from three families that did not produce it
├── Native loading sample: configured, loaded, used and verified
├── Daily catalogue release with notes a customer can read
└── Maintenance: re-verify on harness changes, merge near-duplicates,
    withdraw with reasons, rank by measured use
```

The rate is set by measurement, not by hope. Reaching 10,000 approved packages
in twenty days needs about 500 approvals a day; reaching 100,000 in a further
ninety days needs about 1,000 a day. The panel's measured throughput and error
gate (roadmap step S-6.63) decide the daily wave size, and every run declares a
ceiling on model calls and stops before it.

### Clear components, selectable engines and one index

Every functional component keeps one typed, versioned contract, and any number
of engines may implement it behind that contract. The design already exists in
[Engines behind fixed edges](../architecture/ENGINES-BEHIND-FIXED-EDGES.md) and
the slot catalogue `src/loop_engine/data/engine_slots.yaml`. Step S-6.84 writes
it into the development rules as one short rule and one standard, each rule with
a check.

```text
Functional component
├── Contract: typed request, result, errors, effects and version
├── Engines behind the contract
│   ├── Baltor-native engine
│   └── engine adapter around an outside project, pinned by revision and licence
├── Binding: function, subprocess, HTTP, protocol server, WebAssembly or container
├── Selection: pinned, preferred or automatic, with a recorded decision
├── Tests
│   ├── every engine alone against the shared contract test kit
│   ├── components in groups over their typed edges
│   └── customer journeys end to end
└── One generated index entry with its guide, owning folder and terms
```

An outside project is used through an engine adapter. The word wrapper stays
reserved for the layered harness wrappers of
[the harness wrapper design](../architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md),
so the two ideas do not blur.

### Agents that manage the system

The [reusable development workflows](../../artifacts/agent-workflows-2026-09-23/README.md)
review the state, grow the library, rediscover harnesses, sweep research and
news, and validate the plan. The roadmap's recurring reviews declare their
schedules and effect policies: reports and candidates only. A recurring job
never pushes, approves or publishes on its own. Step S-6.77 later runs these
jobs as Practitioner Loops through the canonical runtime.

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
