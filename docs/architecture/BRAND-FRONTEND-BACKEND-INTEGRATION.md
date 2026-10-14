# Website frontends and shared backend integration

Kind: implementation map and acceptance plan. The owner requires every selected
website to have its own frontend and an explicit backend integration plan.
The [current deployment](MVP-CLIENT-SERVER.md#current-deployment) owns live
revision, hostname and verification facts. The [roadmap](../roadmap/roadmap.yaml)
owns task status. A prototype or a live landing page does not establish a
complete service.

## Frontend coverage

| Offering and domain | Frontend and implemented connection | Remaining integration and customer proof | Roadmap owner |
| --- | --- | --- | --- |
| Baltor, `baltor.ai` | Combined catalogue, feeds, component and local overnight surfaces. Existing account, entitlement, retrieval, MCP and billing boundaries. | Complete the ordinary native harness journey: connect, find, retrieve, use, revise and recover. Keep each paid capability distinct from previews. | S-6.12, S-6.35 |
| AgentFeeds, `agentfeeds.si` | Independent live renderer, collection directory, browser-local saved selections and reading-profile downloads. Own-origin account and MCP presentation over shared service records. | Connect maintained source observations, freshness and applicability evidence to authorized personalized subscriptions. Qualify newsletter intake before advertising an active mailbox, and qualify scheduled delivery rather than treating a local saved choice as a subscription. | S-6.35.06, S-6.214 |
| AgentFoundry, `getagentfoundry.si` | Independent live renderer, 376 public examples, Public Good search, account access and own-origin MCP setup. | Qualify installed native starter kits and dependency/runtime checks, retrieval, actual use and a meaningful revision. Source-checkout kit tools are not an installed hosted builder. Standalone payment returns remain held. | S-6.35.06, S-6.12, S-6.215 |
| AgentAFK, `agentafk.si` | Independent live browser-local Preview and task preparation. Public-only transport; no account, MCP or provider-effect routes. | Bind an authorized task to the canonical queue/history and approved execution profile; enforce dependencies, priorities, leases, fencing, budgets, cancellation and recovery before hosted execution. Evaluate learned ranking against a baseline before promotion. | S-6.35.06, S-6.24 |
| Don't be a meat proxy, `dontbeameatproxy.si` | Independent live acquisition funnel pointing to AgentFeeds. Public-only transport. | Check every call to action and its destination. Keep campaign measurement within approved aggregate tracking; no new account database, subscription service or private visitor profile. | S-6.35.07 |
| AgentStudios, `agentstudios.si` | Independent creative renderer deployed in release 92 and qualified over ordinary public DNS and verified TLS on both `agentstudios.si` and `www.agentstudios.si`: six nonexclusive media filters, public examples, original audio/video demonstrations, editable source download, Public Good search and own-origin account/MCP presentation. | Qualify actual selection, retrieval, edit and clean reopen, and resolve the retained `/connect` `innerText` selector and CDP stream-accounting instrumentation limits. Qualify larger media delivery separately; current examples do not establish a general browser editor or hosted rendering service. | S-6.35.08, S-6.201, S-6.215 |
| AgentBriefs, `agentbriefs.si` | Selected executive offering with a reviewed local-only prototype in `design/prototypes/agentbriefs/` (124 producer and 53 independent browser checks, zero outbound requests). No production brand profile or verified domain ownership. | Private company context, qualified research, evidence assessment, optional approved experiments, thresholded delivery and decision follow-up. First prove one complete decision family and verify domain ownership before opening a hosted intake. | S-6.35.09 |

The six standalone domain names also need independently tested `www` handling.
AgentMedia is the retired placeholder for AgentStudios. AgentComputer is a
capability direction within AgentAFK, not another selected website. No additional
domain purchase or service is implied by this map.

## Shared systems and deliberate separation

Brand, product, plan, account, model access and effect authority are different
identities. A brand selects presentation, not a second service or additional
permissions. The existing [service component](../components/service-runtime/README.md#host-specific-website-presentation)
owns these boundaries.

| Boundary | Shared owner | What remains separate |
| --- | --- | --- |
| HTTP presentation | `service_runtime/http.py`, `brand_profiles.py`, `brand_pages.py` | Exact admitted Host/Origin, renderer, assets, navigation, errors and customer wording. Unknown hosts and cross-brand asset fallthrough are refused. |
| Accounts and browser access | Existing account service, account policy and durable tenant stores | Origin-local browser state, explicit return addresses, tenant authorization and consent. Shared backend does not mean a cross-domain cookie. |
| Harness connection | Existing OAuth authorization and MCP service | Each account-enabled origin has its own issuer, resource and callback validation. A token from one issuer is not silently accepted by another. |
| Catalogue and downloads | Provisioning, retrieval, catalogue releases and `catalogue_body_store/v1` | Current grants, scopes, withdrawals, use permissions and usage accounting. A public preview grants no private package access. |
| Payment | Existing billing records, customer bindings and Stripe session adapter | Qualified product/return policy and truthful common operator. Standalone checkout/portal creation remains refused; no duplicate customer or charge is created for a new brand. |
| Research and source intake | Existing managed research, feed source contracts and qualification owners | Tenant-private inputs, source rights, retention, consent and provenance. Raw newsletters and chat logs are untrusted material, not execution instructions. |
| Execution and scheduling | Canonical Loop execution, task/history, model gateway and sandbox owners | Explicit task authority, customer model access, permitted data recipients, resource limits and supported placement. A frontend click or opportunity score grants none of these by itself. |
| Feedback and improvement | Managed records, Run History and feedback | Tenant visibility, original evidence, failed attempts, independent acceptance and rollback. Decisions and realized outcomes are not overwritten by later model opinions. |
| Internal operations | Existing staff access, qualification, release and configuration owners | Operator tools, secrets, private candidates and raw session exports never become public because a brand reuses the backend. |

The application still shares failure and capacity risks. Keep common request
and email ceilings authoritative. Where execution paths are enabled, retain
their worker and model ceilings; allocate and measure demand per offering
without accidentally multiplying total authority. Add isolated
execution or independently scaled delivery only when evidence justifies it.

## Screen-to-service acceptance plan

Every new screen needs its data owner, typed request/result and refusal states
identified before wiring. Use the existing contracts rather than inventing
unimplemented URL names in a frontend.

| Customer action | Integration path | Required proof before calling it working |
| --- | --- | --- |
| Browse, filter and preview a component or asset | Existing public catalogue metadata and exact packaged previews; authenticated search uses `service_retrieval_request/v2`. | Real search/pagination, correct empty/error states, current authorization, withdrawn item refusal and no cross-brand chrome. |
| Connect a harness and retrieve source | Own-origin MCP/OAuth; `service_provisioning_request/v1` and existing versioned results. | Supported native client, correct PKCE/resource/callback handling, exact bytes, use permissions, usage accounting, revoked access and clean recovery. |
| Save feed preferences and receive useful updates | Keep existing local selections labeled local. Future account subscriptions belong to managed records and qualified intake/delivery. | Explicit persistence mode, ownership, source dates, duplicate suppression, fresh/failed/stale states, unsubscribe and a real authorized delivery. |
| Edit media or run a task | Deliver qualified native material first; use a separately approved execution profile when requested. | Real native use, revision and clean reopen; declared filesystem/network/model effects; no automatic production deployment or model funding. |
| Import company context for AgentBriefs | Future tenant-scoped managed record operations with explicit import/synchronization consent. | Size/type/path limits, escaped rendering, provenance, tenant isolation, correction/export/deletion policy and no secret transmission through examples. |
| Investigate and receive an executive brief | Existing research and typed decisions compose with task/evaluation/acceptance; notifications have their own delivery authority. | Useful and withheld controls; source-backed analysis distinct from a PoC; baseline, actual attempts and limits for experiments; separate estimated and realized benefit. |
| Review outcomes and improve recommendations | Versioned feedback linked to original brief and run records. | Accepted/rejected/snoozed decisions, correction history, consented outcome follow-up, failure analysis and evaluated preference changes. No self-approval of published intelligence. |
| Upgrade or manage a subscription | Existing billing customer and entitlement owners, after exact brand return policy qualifies. | Approved success/cancel/portal URLs, no open redirects, webhook reconciliation, duplicate-click recovery and no cross-brand grant loss. Test without an engineering live charge. |

## Engine and deployment portability

The complete operational classification remains:

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

Every discrete cognitive or act step Loop node retains the
[complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation).
Screens, passive files, service adapters and media frames are not new Loop
runtimes. The four persistent intelligence layers and temporary Runtime Memory
keep their canonical meanings; a company's Decision Memory is a product view.

```text
Independent frontend
└── Existing typed, versioned service edge
    └── Qualified engine adapter
        ├── Implementation language and build identity
        ├── Runtime and invocation protocol
        ├── Enforced isolation, authority and resource envelope
        └── Compatible deployment location and recovery policy
```

The [portability standard](../standards/LANGUAGES-AND-COMPONENTS.md#implementation-and-deployment-portability)
owns migration gates. An engine may move from Python to Rust, from in-process
to a supervised process, or to another approved host without changing the
frontend contract only after compatibility and authority checks pass. These
are separate changes, not automatic consequences of containerization.

First compare the existing catalogue search engine, the same engine behind
a persistent process boundary and a Rust candidate behind that same boundary.
Use the same immutable index, queries, filters, result semantics and resource
limits. Include startup, serialization, tail latency, working memory, failures
and maintenance cost. Preserve the current engine and rollback. No percentage
speed or hosting saving is established by a no-op native executable.

## Delivery sequence and common release gate

1. Preserve the existing public websites and complete AgentStudios public
   qualification. Record functional results separately from transport-accounting
   limitations; do not erase failed attempts.
2. Give AgentBriefs a reviewable local frontend with explicitly synthetic
   examples and memory-only controls. Do not accept private company uploads,
   signups or payments through an unwired prototype.
3. Close the ordinary native customer journey and then bind one complete
   value-producing path for each offering. Prefer a real small workflow to
   disconnected controls for unimplemented features.
4. Qualify newsletter intake, maintained feeds, portable execution and larger
   media under their existing owners. Keep provider activation distinct from
   source implementation and UI deployment.
5. Measure the selected engine alternatives before migrating production or
   splitting more services. Compare total operating cost as well as runtime.

Every production brand addition must pass exact Host/Origin and cross-tenant
negative controls, desktop/phone and keyboard checks, packaged asset checks,
real error states, native downloads and applicable account/MCP journeys.
Verify TLS and ordinary public DNS, title/metadata, links, no unintended brand
navigation, approved legal disclosure and all existing hostnames after the
guarded release. Preserve configuration-aware rollback. Passing the homepage
does not waive an unfinished account, execution, payment or delivery gate.
