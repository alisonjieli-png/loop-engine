# Competition for the first Loop Engine release

Kind: dated research report and proposed product assessment.
Date accessed for every external source below: September 19, 2026.
Local revision inspected: `48cc954322691e492aad69a465ba470a112730e7` on
`main`. Existing uncommitted work and concurrent research were preserved.
This report changes no product contract and authorizes no purchase, account
creation, deployment, publication, or live experiment.

The proposed subscription website, dashboard, payments, and authenticated
Model Context Protocol service enter an existing market. Tessl already
combines a skills registry with evaluation and private distribution. MCPize
documents the subscription, payment, application programming interface key,
quota, and server access path.
Apify sells reusable executable software through a marketplace. LangSmith
Context Hub distributes versioned instructions and skills to customer-run
harnesses. These are direct overlaps, not only memory products adjacent to a
future engine. The evidence for each appears below.

Loop Engine can still pursue a useful distinction: independently qualified
instructions, executable code, tools, and contracts whose exact identities
remain connected to task decomposition, client use, verification, and later
reuse. That is a proposed product advantage to demonstrate. The local review
does not establish an operated service or a fully connected implementation.

## Scope and evidence standard

The comparison covers 18 product surfaces. Smithery and Arcade are separate
surfaces under the same company according to their current announcement, so
the rows must not be counted as 18 independent companies. Sources are primary
vendor documentation, vendor product pages, or official repositories.
Nothing was installed, purchased, or benchmarked. Authentication, billing,
isolation, and evaluation behavior were not exercised against vendor accounts.
Pages were read through the web research tool, which can return indexed
representations. No immutable vendor-page snapshots or independently tested
release builds were saved. Current-looking documentation is not a guarantee
that every listed feature is available to every account.

The statuses mean:

- **Documented:** a primary source describes the capability and its interface
  or workflow. This is documentation evidence, not independently tested
  production behavior.
- **Partial:** a narrower capability is documented, or an important part of
  the combined property is missing from the inspected evidence.
- **Not documented:** the inspected sources do not describe the capability.
  This does not establish that the vendor lacks it.
- **Unverified:** the relevant source was inaccessible, ambiguous, or not
  sufficient to make a useful determination.

Runnable reuse means distributing an implementation or invoking a stored
implementation. It does not mean that an example code snippet is an admitted
executable capability. Evaluation means a described behavioral test or review.
Security scanning, publisher identity, successful builds, schema validation,
and task correctness are different properties. None alone establishes
independent qualification for a particular task and input region.

The [September 19 local review](../claude-session-review-2026-09-19/README.md)
is the source for Loop Engine's current integration gaps. The
[September 18 landscape](../../docs/research/COMPETITIVE-LANDSCAPE-AND-MONETIZATION-2026-09-18.md)
is historical research, not the source of current competitor statuses here.
Its binary absence cells and claims that no memory vendor executes code or
that no vendor sells reusable qualified capability are too broad. Its own
Letta row already described custom executable tools. The
[skill repository report](../../docs/research/SKILL-REPOSITORIES-AS-CONTEXT-INTELLIGENCE-2026-09-18.md)
also observed scripts inside several skill repositories. Skills must not be
treated as text-only by definition.

## Material and qualification comparison

The qualification column describes the specific evidence offered. It does
not rate quality or award a universal pass. A documented evaluation product
does not establish mandatory independent admission of every listed item.
Each product name links to its detailed evidence and limits below.

| Product | Main reusable material and execution location | Runnable reuse | Qualification evidence |
|---|---|---|---|
| [Tessl](#tessl) | Versioned skills, plugins, and library context installed into coding agents. | Partial: skills can contain scripts; the documented emphasis is agent context. | Documented: reviews, security scans, and tasks run with and without the skill. Scenario evaluation can be skipped at publication. |
| [Vercel skills.sh](#vercel-skillssh) | Skill folders installed into the customer's harness. | Documented: the skill format includes executable scripts and resources. | Partial: security audit results; no guarantee of item quality or safety. |
| [Smithery](#smithery) | Server releases, downloadable server bundles, remote tools, and prompt-based skill records. | Documented: server implementations and tool invocation. | Partial: verification and quality-score fields exist; their full correctness and independent-review criteria were not established. |
| [Glama](#glama) | Server discovery, tool schemas, hosted servers, and a gateway. | Documented: install or host reusable servers. | Partial: license detection, security scans, health checks, and indexing. These are not task-acceptance evidence. |
| [PulseMCP](#pulsemcp) | Curated server metadata, versions, authentication details, and tool descriptions. | Partial: references to executable packages and endpoints, rather than a general code-body catalog. | Not documented: independent task qualification in the sub-registry interface. |
| [Docker Model Context Protocol Catalog](#docker-model-context-protocol-catalog) | Server containers and custom catalogs, primarily run in the customer's environment. | Documented: containerized server implementations. | Partial: publisher review, provenance, software bill of materials, and signatures for Docker-built servers; no general task correctness claim established. |
| [Composio](#composio) | Versioned toolkits and custom servers invoked through managed sessions or a gateway. | Documented: executable actions with input and output schemas. | Not documented: an independent task-qualification gate for every reusable action. |
| [Arcade](#arcade) | Custom Python tools, hosted servers, and federated tool gateways. | Documented: reusable code and remote execution. | Documented: evaluation suites test model tool selection and argument accuracy. This is narrower than acceptance of the user's final result. |
| [Pipedream Connect](#pipedream-connect) | Reusable actions, triggers, and workflows, normally executed on Pipedream. | Documented: a source-backed action registry and custom requests. | Unverified: qualification rules for the complete action population were not established. |
| [Apify](#apify) | Actor implementations packaged into container builds and invoked remotely. | Documented: marketplace software reused by applications and agents. | Partial: build identity and publishing requirements; independent semantic acceptance of every Actor was not established. |
| [MCPize](#mcpize) | Hosted servers sold through subscription plans or per-call payments. | Documented: executable server deployments. | Partial: functional quality standards and moderation; the terms explicitly do not require review of every listing. |
| [Context7](#context7) | Version-specific documentation and code snippets delivered to the customer's agent. | Partial: code as context, rather than an independently qualified callable implementation. | Partial: injection screening and repository trust signals, not a demonstrated task acceptance gate. |
| [Letta](#letta) | Stateful agents, skills, and stored source-code tools. | Documented: tools store source code, schemas, and package requirements. | Not documented: an independent candidate-to-qualified lifecycle for every reusable tool. |
| [Mem0](#mem0) | Persistent memory and, in the Python open source edition, procedural task knowledge. | Not documented: executable capability storage and admission in the inspected memory interface. | Not documented: independent qualification of each stored procedure. |
| [Zep and Graphiti](#zep-and-graphiti) | Temporal memory graphs, source episodes, and retrieved context. | Not documented: executable capability reuse in the inspected memory product. | Not documented: automatic independent qualification; source review state is supplied by the application. |
| [Supermemory](#supermemory) | Memory, documents, code as indexed content, and a memory-backed filesystem. | Not documented: admission and reuse of code as a qualified executable artifact. | Not documented: independent task qualification of retrieved material. |
| [Braintrust](#braintrust) | Reusable hosted or locally downloaded tools, prompts, scorers, and workflows. | Documented: typed code functions, exact version pinning, and local reuse. | Documented: evaluation and scoring infrastructure. A mandatory separate approver for every function was not established. |
| [LangSmith Context Hub and Deep Agents](#langsmith-context-hub-and-deep-agents) | Versioned instructions, skills, file bundles, and an adjacent graph and subagent framework. | Partial: file bundles and agent tooling, rather than a demonstrated universal qualified code catalog. | Documented: evaluation tooling and review workflows. Public prompts are explicitly unverified. |

## Distribution and commercial comparison

Authenticated paid access below means a documented paid platform or service
with machine authentication. It does not mean the platform lets an arbitrary
creator sell a particular skill. Creator-defined paid distribution is directly
documented for MCPize and Apify. Other rows must not be read as evidence of
creator payouts or a resale marketplace.

Private/team scope includes a protected catalog, private project, or scoped
memory store. The evidence notes identify which one. Version/provenance is
partial when only versions, mutable history, source links, or dependency
metadata are documented, without a complete immutable source-to-delivery
chain. Metering refers to measured billable usage, not just a request limit.

| Product | Authenticated paid access | Private/team scope | Version/provenance | Metering | Model Context Protocol or programming interface |
|---|---|---|---|---|---|
| Tessl | Documented | Documented | Partial | Documented | Documented |
| Vercel skills.sh | Partial | Partial | Partial | Not documented | Documented |
| Smithery | Unverified | Partial | Partial | Partial | Documented |
| Glama | Partial | Documented | Partial | Partial | Documented |
| PulseMCP | Documented | Partial | Documented | Not documented | Documented |
| Docker Model Context Protocol Catalog | Partial | Documented | Documented | Not documented | Documented |
| Composio | Documented | Documented | Partial | Documented | Documented |
| Arcade | Documented | Documented | Partial | Documented | Documented |
| Pipedream Connect | Documented | Partial | Partial | Documented | Documented |
| Apify | Documented | Documented | Documented | Documented | Documented |
| MCPize | Documented | Not documented | Partial | Documented | Documented |
| Context7 | Documented | Documented | Partial | Documented | Documented |
| Letta | Documented | Documented | Partial | Documented | Documented |
| Mem0 | Documented | Documented | Unverified | Documented | Documented |
| Zep and Graphiti | Documented | Documented | Partial | Documented | Documented |
| Supermemory | Documented | Documented | Partial | Documented | Documented |
| Braintrust | Documented | Documented | Partial | Documented | Documented |
| LangSmith Context Hub and Deep Agents | Documented | Documented | Documented | Documented | Documented |

## Primary evidence and limits

### Tessl

Tessl is a direct comparison for paid harness intelligence. Its registry
describes versioned skills, quality reviews, impact evaluations, and security
scanning. Its distribution guide documents private workspace membership,
private search, pinned installation, archiving, and usage statistics.
[Registry](https://tessl.io/registry),
[private distribution and versions](https://docs.tessl.io/distribute/distributing-via-registry).

Scenario evaluations compare agent task performance with and without a skill.
The same guide permits `tessl tile publish --skip-evals`. That is a concrete
reason to distinguish evaluation availability from compulsory independent
admission. Public docs also use both older tile commands and newer plugin
commands; the exact installed client compatibility was not tested.
[Scenario evaluation](https://docs.tessl.io/evaluate/evaluate-skill-quality-using-scenarios).

The pricing page shows Team at $100 per month with 5,000 credits. Publishing
and installing are free; reviews, evaluations, and agent runs consume credits.
The homepage says some enterprise policy and audit features are rolling out,
while pricing lists them as enterprise features. Treat exact availability as
unverified. The documented Model Context Protocol integration is a local
standard input and output server, not proof of an equivalent remote endpoint.
[Pricing](https://tessl.io/pricing), [homepage](https://tessl.io/),
[Model Context Protocol tools](https://docs.tessl.io/reference/mcp-tools).

### Vercel skills.sh

The registry and installer distribute Agent Skills. The format explicitly
allows scripts, references, and assets. Audit pages aggregate security
assessments; the documentation does not promise universal safety or quality.
[Documentation](https://www.skills.sh/docs),
[audit results](https://www.skills.sh/audits),
[Agent Skills specification](https://agentskills.io/specification).

Packs can contain private source files and belong to a Vercel team, but packs
are unlisted and can be installed without authentication by anyone with the
URL. This is not a protected private catalog. The catalog programming
interface separately documents project-scoped identity tokens and request
limits. No paid pack-entitlement or creator-billing workflow was established.
[Pack access rules](https://www.skills.sh/docs/packs),
[programming interface](https://www.skills.sh/docs/api).

### Smithery

Smithery documents server publication, release records, source metadata,
downloadable server bundles, skill search, and machine tokens. Its skill
response includes a prompt, source repository, quality score, and verification
flag. Those fields do not explain a full independent task-qualification
procedure. Server release history is more explicit than skill version
pinning in the inspected interface.
[Interface index](https://smithery.ai/docs/llms.txt),
[skill response](https://smithery.ai/docs/api-reference/skills/get-a-skill),
[release response](https://smithery.ai/docs/api-reference/servers/get-a-release).

Token scoping governs connections and operations. A server's `unlisted`
field does not by itself establish restricted body access. The pricing page
did not expose a current rate card. Smithery's announcement says it is now
part of Arcade; no transition of account terms was tested.
[Token scope](https://smithery.ai/docs/use/token-scoping),
[server visibility](https://smithery.ai/docs/api-reference/servers/update-a-server),
[pricing page](https://smithery.ai/pricing),
[company announcement](https://www.arcade.dev/blog/smithery-joins-arcade/).

### Glama

Glama documents license, security, and health checks during indexing. Its
gateway provides credential handling, per-tool access switches, shared
workspace logs, and usage analytics. Full request and response payloads are
logged by default according to the questions page. That privacy choice is
material when comparing it with a service that only delivers code or skills.
[Checks and gateway behavior](https://glama.ai/mcp/faq),
[gateway](https://glama.ai/mcp/gateway).

The directory interface requires bearer authentication, returns server and
connector records, and distinguishes private hosted instances. Its data
license requires attribution and offers commercial exceptions. Current
subscription pricing redirected to sign-up, so this report does not infer
unit rates or claim a particular paid catalog plan.
[Directory interface and data license](https://glama.ai/mcp/reference),
[pricing access limit](https://glama.ai/pricing).

### PulseMCP

PulseMCP's sub-registry is a close comparison for selling curated intelligence
about external services. It documents an application programming interface key
plus tenant identifier,
tenant-specific curated entries, upstream source identity, per-server version
lookup, and premium authentication and tool metadata. It is a read-only
aggregation interface; it does not accept direct server publication.

This supports commercial metadata distribution. It does not establish a
private customer code store, billed request units, or task qualification of
the referenced implementation. The public interface provides a useful
example of preserving publisher data separately from registry enrichment.
[Sub-registry interface](https://www.pulsemcp.com/api/docs/v0.1).

### Docker Model Context Protocol Catalog

Docker documents versioned server images with provenance and software bill of
materials metadata, plus digital signatures for Docker-built servers. Users
can create catalogs containing private images and distribute them through an
Open Container Initiative registry. A custom catalog also limits the gateway's
dynamic discovery scope. The catalog is marked beta.

These are significant code distribution and supply-chain controls. They do
not establish that every server satisfies an independently evaluated task
contract. The inspected catalog pages do not describe charging a subscriber
for a particular qualified skill or metering that subscriber's tool calls.
[Catalog scope](https://docs.docker.com/ai/mcp-catalog-and-toolkit/catalog/),
[custom catalogs and gateway](https://docs.docker.com/ai/mcp-catalog-and-toolkit/cli/).

### Composio

Composio exposes reusable executable actions with input and output schemas,
connected-account authentication, and explicit toolkit versions. Custom
servers become project-scoped toolkits whose schemas are synchronized and
versioned. The customer can retain its own agent while Composio invokes tools.
[Tool contracts](https://docs.composio.dev/reference/api-reference/tools),
[custom server boundary](https://docs.composio.dev/docs/extending-sessions/custom-mcp).

Current new-customer pricing documents a $29 monthly Pro plan, included
credit, measured tool calls, separate add-ons, and spending controls. Search
meta-tools are free. The page distinguishes new sign-ups from older plans;
old prices should not be carried forward. The gateway also advertises team
access policies and logs, but its automatic repair claims were not exercised.
[Current pricing](https://landing.composio.dev/pricing?cta_placement=content-sidebar-secondary),
[gateway product](https://composio.dev/mcp-gateway).

### Arcade

Arcade combines authentication, custom code tools, server hosting, a gateway,
and organization governance. Its evaluation suites test tool choice and
arguments against expected calls. This is a real qualification mechanism,
although a correct tool call does not establish a correct final deliverable.
[Product](https://www.arcade.dev/product/),
[evaluation suite](https://docs.arcade.dev/en/build/create-tools/evaluate-tools/create-evaluation-suite).

Current pricing shows Team at $25 per month plus $0.10 per authentication
event and $0.01 per tool call. Enterprise lists private registry access.
Older blog posts describe other pricing structures, so use the current
pricing page for this dated comparison. No paid tool execution was tested.
[Pricing](https://www.arcade.dev/pricing/),
[organization operation](https://docs.arcade.dev/en/operate).

### Pipedream Connect

Pipedream offers an action and trigger registry, managed user authentication,
custom authenticated requests, workflows, and a Model Context Protocol server.
The customer retains its application or agent. Production access is paid;
the overview describes development mode as free. Project and external-user
scope are documented, but the precise private custom-catalog rules were not
established in this review.
[Connect overview](https://pipedream.com/docs/connect).

Its usage interface returns time-window totals separated into action,
proxy, and source-event credits. That is stronger metering evidence than a
dashboard screenshot. The pricing page did not render a rate card through
the research tool, so no current price is asserted.
[Usage records](https://pipedream.com/docs/connect/api-reference/list-usage-records),
[pricing access limit](https://pipedream.com/pricing).

### Apify

Apify is a direct counterexample to treating reusable executable software as
an unsold category. Its Store monetizes Actor implementations through events
and platform usage. Customers can use these from their own applications and
agent harnesses, while Apify runs the implementation. This differs from
delivering all implementation bytes for local execution.
[Monetization](https://docs.apify.com/actors/publishing/monetize),
[consumer charging rules](https://docs.apify.com/actors/running/actors-in-store).

Builds snapshot source and settings into container images with unique build
numbers. Private Actor access requires authentication. The public plan page
shows Starter at $19 per month plus usage. Some documentation still describes
legacy rental Actors while new monetization pages emphasize events and
usage; do not conflate legacy consumption with a new publishing option.
[Build identity](https://docs.apify.com/actors/development/builds-and-runs/builds),
[private access](https://docs.apify.com/api/v2/act-get),
[pricing](https://apify.com/pricing).

The hosted Model Context Protocol server supports authorization and structured
result schemas, and excludes full-permission and rental Actors. Those
exclusions are a concrete governed selection boundary, although they are not
proof of an independently correct result.
[Model Context Protocol server and exclusions](https://docs.apify.com/integrations/mcp).

### MCPize

MCPize describes almost the exact commercial access sequence proposed for the
first release: a creator sets plans in a dashboard, a buyer uses Stripe
Checkout, the buyer receives a subscription-bound application programming
interface key, and a gateway
counts usage and enforces quotas. Per-call payments are an additional option.
This is documentation of the product, not independently verified payment
processing or an assertion of actual sales.
[Monetization workflow](https://mcpize.com/docs/monetization).

The platform advertises deployment history and rollback. Its public command
line repository separates publisher secrets from subscriber credentials.
Marketplace terms set functional quality requirements but state that review
of every listing is not required. Private team catalogs and cryptographically
bound independent task reports were not established.
[Platform](https://mcpize.com/platform),
[official command line repository](https://github.com/mcpize/cli),
[review limits](https://mcpize.com/terms).

### Context7

Context7 serves library documentation and snippets through an authenticated
programming interface and Model Context Protocol integration. It documents
version-specific library identifiers, private repository indexing, teamspace
policies, and usage metrics. It is a strong substitute for a product whose
main value is better library context, but snippets are not qualified executable
implementations.
[Interface](https://context7.com/docs/api-guide),
[team controls](https://context7.com/context7-for-teams).

Pricing shows Pro at $10 per seat monthly, included calls, paid overages, and
separate private-source parsing charges. The page describes injection
screening and repository trust scores. Those are useful admission signals,
not evidence of task correctness. The “unlimited calls” label means paid
overages are available, not that every call is included in the seat price.
[Plans and screening](https://context7.com/plans),
[usage breakdown](https://context7.com/docs/howto/usage).

### Letta

Letta's tool interface stores source code, argument schemas, dependency
requirements, creator and updater identities, a project identifier, and an
approval requirement. It also supports tool search. This is a decisive
counterexample to saying all memory-oriented platforms only keep prose.
Mutable tool updates and dependency versions are not by themselves an
immutable qualified-release record.
[Tool interface](https://docs.letta.com/api/typescript/resources/tools),
[stored tool contract](https://docs.letta.com/api/typescript/resources/tools/methods/upsert).

The current developer plan is $20 per month plus active-agent, model, and
server-side tool execution usage. Teams can share agents with access controls.
Letta is also an agent harness, so its overall product is broader than the
first Loop Engine serving release. A mandatory independent approval process
for reusable code was not established.
[Pricing and execution units](https://docs.letta.com/pricing),
[product scope](https://docs.letta.com/).

### Mem0

Mem0's current memory-type page makes an important edition distinction:
procedural memory is implemented in the Python open source interface, but
not the hosted `MemoryClient` or TypeScript interface. It stores task
knowledge, rather than documenting an executable package-admission path.
The page also separates entity scope from named memory types.
[Memory-type implementation limits](https://docs.mem0.ai/core-concepts/memory-types).

The hosted product documents authenticated memory operations, organizations,
projects, and Model Context Protocol access. Its plans meter add and retrieval
requests. This is relevant competition for context and user guidance, but the
inspected sources do not establish immutable qualified code releases.
[Hosted quickstart](https://docs.mem0.ai/platform/quickstart),
[organization interface](https://docs.mem0.ai/api-reference/organization/create-org),
[pricing](https://mem0.ai/pricing).

### Zep and Graphiti

The commercial comparison here is Zep; Graphiti is its adjacent open source
graph technology, not evidence that every Zep feature is available in the
open source package. Current Zep documentation describes temporal context,
project/user/graph isolation, source episode metadata, and agent access
policies. The security guide explicitly assigns source validation and
authenticated end-user binding to the calling application.
[Current concepts](https://help.getzep.com/),
[source and access responsibilities](https://help.getzep.com/v3/memory-security).

Zep also documents a Memory Model Context Protocol Server. Pricing meters
episode size and some webhook activity while retrieval and storage are
unmetered. Temporal history and provenance are relevant overlaps, but are
different from a tested executable release lifecycle.
[Memory server](https://help.getzep.com/memory-mcp-server),
[current pricing units](https://www.getzep.com/pricing/).

### Supermemory

Supermemory documents indexed code as well as documents, a memory-backed
filesystem, shared spaces, container-scoped keys, and a remote authenticated
Model Context Protocol server. These are more than isolated prose notes, but
the inspected documentation does not establish independent admission and
execution of retrieved code as reusable capability.
[Product and boundaries](https://supermemory.ai/product/).

Pricing separates ingestion, retrieval, and operations, and the changelog
records scoped credentials, per-key usage, revocation, and billing corrections.
Those operational details are useful requirements for Loop Engine's service.
They remain vendor-described behavior; no isolation or restart experiment was
performed here.
[Pricing](https://supermemory.ai/pricing/),
[interface and operational changes](https://supermemory.ai/changelog/api/).

### Braintrust

Braintrust hosts reusable prompts, general-purpose code tools, scorers, and
workflows. The function guide shows typed parameters and returns,
direct remote invocation, sandbox execution, and tracing. Functions are
automatically versioned. Customers can pin a version or download a specific
version into their codebase to run locally. This is a direct counterexample
to describing evaluation vendors as unable to reuse executable code, including
reuse in the customer's environment.
[Reusable functions, versioning, and local download](https://www.braintrust.dev/docs/deploy/functions),
[authenticated function interface](https://www.braintrust.dev/docs/api-reference/functions/create-function).

Pricing documents projects, permission controls, version environments,
processed data, scores, model credits, and retention. Pro is listed at $249
monthly. The inspected material establishes evaluation and deployment
mechanisms, not a mandatory separate approver for every function or a general
creator-paid marketplace.
[Platform pricing and controls](https://www.braintrust.dev/pricing).

### LangSmith Context Hub and Deep Agents

Context Hub stores `AGENTS.md`, skills, policies, and file bundles, supports
commits and deployment tags, and pulls pinned material to a customer's local
harness. It also supplies persistent context to Deep Agents. This overlaps
directly with the first serving release, beyond conventional prompt storage.
[Context Hub announcement and workflow](https://www.langchain.com/blog/introducing-context-hub).

Deep Agents documents planning, task decomposition, specialized subagents,
persistent memory, filesystem permissions, and approval interrupts. Graph and
subproblem composition therefore cannot be claimed as unique to Loop Engine.
The intended distinction would have to be the exact contracts, independent
qualification, and observed behavior of Loop Engine's complete process.
[Deep Agents capabilities](https://docs.langchain.com/oss/javascript/deepagents/overview).

LangSmith offers prompt ownership, environment promotion, evaluation, and paid
usage. Its public prompt documentation explicitly calls community prompts
unverified. Review and deployment tooling must not be mistaken for universal
qualified content. The wider paid platform also includes hosted execution,
so its full price cannot be compared directly with a material-only service.
[Prompt controls and public-content limit](https://docs.langchain.com/langsmith/manage-prompts),
[pricing](https://www.langchain.com/pricing).

## What this changes for Loop Engine

Observed competition already supplies the main commercial plumbing and many
of the planned individual features. A website, a payment page, authenticated
material lookup, versioned skills, private team access, reusable tools, and
evaluations each have direct precedents. Combining these remains useful, but
feature presence alone does not establish an advantage.

The canonical engine remains in scope. Serving material to customer-run
harnesses is the public release boundary, not a decision to reduce the engine
to a file marketplace. Internal task decomposition into graphs, subgraphs,
and atomic solutioning assignments must still connect to qualification,
verification, and reusable solutions where applicable. This research did not
test those internal paths. The local review identifies concrete gaps in
provisioning, tenant disclosure, qualification, metering, telemetry, and the
public solve dependency construction.

The four persistent intelligence layers remain Context Intelligence, Code
Intelligence, Runtime History and Solution Intelligence, and User Feedback
Intelligence. Harness Intelligence references and external-service records
must not be marketed as completed additional canonical layers. A larger
classification vocabulary is not evidence of better delivered outcomes.

### Proposed first-release differentiation

1. Sell a maintained, narrowly scoped collection with inspectable task
   evidence. Each admitted version should state source identity, license,
   dependencies, input and output contracts, declared effects, applicable
   inputs, evaluator identity, failures, and known limits. Attach the evidence
   to the exact bytes delivered. Use the existing code-asset, skill-admission,
   and reusable-capability authorities named in the
   [contract index](../../docs/contracts/README.md).
2. Make the boundary between candidate inspection and normal use observable.
   A high ranking, a scan result, payment, or a good self-test must not activate
   a candidate. Demonstrate a separate qualification process and a versioned
   promotion decision. Tessl's optional evaluation and marketplace moderation
   show why this must be a precise claim, not a generic “verified” badge.
3. Prove portability on customer-run harnesses. Demonstrate reference search,
   authorized selection, exact material delivery, loaded-version confirmation,
   client-side execution authority, and independent task verification. A
   generated instruction file alone does not prove that the harness used it.
4. Preserve the complete engine mechanism behind the release. Demonstrate
   task decomposition, typed connections, scoped atomic assignments,
   independently verified outputs, and a later assignment that consumes the
   exact admitted implementation. Customer-facing graph editing can be a
   separate product decision; internal integration is still required.
5. Make evidence export and privacy part of the product. Distinguish
   server-observed delivery from client-reported loading, execution, and
   outcomes. Retain only approved metadata unless a user explicitly permits
   content retention. A customer's positive report must not silently become
   independent verification or active training data.
6. Start with a comprehensible subscription and declared usage allowance.
   Price maintained access and team controls, with any costly qualification
   service charged separately. Charging for avoided model calls requires a
   defensible counterfactual that the current service has not measured.
   Preserve the existing direction that outcome reporting is not metered.
   No specific price is proposed here because willingness to pay has not been
   measured.

### Evidence that would discriminate the product

These are proposed acceptance checks, not experiments performed in this
report. Any live model or hosted qualification run still needs its declared
authority.

| Claim | Discriminating acceptance evidence |
|---|---|
| Paid access serves only entitled qualified material. | Two tenants, a revoked entitlement, a candidate item, and a changed body all take their intended refusal paths through the real transport. Restart preserves the correct decisions and usage records. |
| A delivered version is the evaluated version. | The client rejects altered bytes and incompatible dependencies. Records join qualification, delivery, actual loading, execution, and verification by exact identities. |
| Reuse improves an assignment. | A frozen fresh task population compares the same harness and model with no supplied material, the instruction material, and the admitted executable implementation. Report failures, denominator, physical model calls, complete or incomplete token accounting, time, and unknown costs. |
| The internal engine is fully connected. | Start at the public task boundary, observe the actual graph and subassignments, verify their typed dependencies and authority, then observe independent acceptance and later exact reuse. A helper fixture or static import closure is insufficient. |
| Billing is durable and understandable. | Acknowledged metering survives restart, retries do not create unintended duplicate charges, and an unknown write is not reported as a successful charge. A visible usage record reconciles to the served material. |
| Revocation has an honest scope. | New protected fetches or invocations stop after revocation. Document the client's use-time recheck policy and acknowledge that already downloaded bytes cannot be recalled from the customer's machine. |

No current evidence here supports a claim that Loop Engine is the only
platform combining memory, executable tools, evaluation, or decomposition.
No acquisition interest, company revenue, customer demand, or measured
performance advantage was inferred. The useful next claim is narrower: a
specific customer task can retrieve a specific admitted version, use it under
declared authority, and produce an independently verified result with a complete
record. That claim should be demonstrated before it becomes product copy.
