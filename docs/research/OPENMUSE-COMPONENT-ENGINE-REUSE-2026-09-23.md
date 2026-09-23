# OpenMuse: reusable components, service coupling and Baltor integration

Research checked September 23, 2026. Exact source:
`CopilotKit/openmuse` commit `bb7ce4e1c6e523bf282a655c63621e3ed9e75150`.
This report is research for the existing roadmap, not a second implementation
plan or a claim that these engines have been installed in Baltor.

## Decision

Use OpenMuse as concrete prior art for visible ongoing work, effect-bound review,
durable task coordination and narrowly injected backend transports. The best
first reuse is its interaction and lifecycle patterns behind Baltor's existing
typed boundaries. An optional AG-UI presentation adapter is worth a contained
experiment. Importing its entire personal-agent application would introduce a
second task runtime, storage schema and identity system, which conflicts with
our architecture.

OpenMuse is an MIT-licensed personal-agent alpha with a private root package
version of 0.1.0. The inspected source uses CopilotKit runtime 1.70.1 and AG-UI
client/core 0.0.59. The GitHub latest-release URL redirected to the release list;
this report pins the commit rather than claiming a verified release tag.
[Package](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/package.json),
[license](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/LICENSE).

## A current dependency that older descriptions miss

The September 23 commit requires a server-side `CPK_INTELLIGENCE_API_KEY` in
**every API mode, including sample mode**. Both `readConfig()` and the app's
startup precondition enforce it; the app constructs `CopilotKitIntelligence`.
Older indexed descriptions saying that the sample app needs no Intelligence
key are stale for this commit. Our isolated checks confirmed missing-key refusal
and construction with a synthetic, unvalidated key; no service connection ran.
[Configuration](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/apps/server/src/config.ts),
[app construction](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/apps/server/src/app.ts#L24-L46).

Intelligence supplies conversation persistence/replay through the CopilotKit
runtime. It is separately configured and not bundled under the application's
MIT license. The current source does not offer a configuration switch that
restores a wholly local, key-free API mode. Replacing that behavior would be an
explicit implementation change. A model-free scripted sample still avoids a
model provider; it does not remove the Intelligence dependency.
[Rich Threads](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/docs/RICH-THREADS.md).

For Baltor, qualify data routing, outage behavior, export, retention and service
cost before adopting this persistence path. Keep model-provider credentials,
CopilotKit project identity, customer login, and browser-worker credentials as
different authorities. No purchase or third-party service activation was made
for this research.

## Architecture mapping

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
OpenMuse patterns usable behind existing Loop-owned work
├── Presentation
│   ├── Conversation and rich artifact cards
│   ├── Activity, input requests and action review
│   └── Browser takeover and saved action records
├── Execution coordination
│   ├── Lease-based task claiming and fencing
│   ├── Checkpoints, pause/cancel and recovery
│   └── Uncertain-effect reconciliation
└── External adapters
    ├── Authenticated protocol transport
    ├── Browser and computer capabilities
    └── Tool/result schemas and explicit unavailable states
```

| Function | Existing Baltor owner | Reuse and own-engine direction |
| --- | --- | --- |
| Task status and event presentation | Existing web/API and Run History boundaries | Add a versioned AG-UI projection engine and retain a Baltor-native view over the same authoritative records |
| Durable work coordination | Existing Loop execution and persistence components | Adapt lease/fencing tests; keep our run IDs, budgets and state transitions rather than importing `AgentTask` as a new runtime |
| External-effect review | Existing permission, approval and effect boundaries | Reuse content/account/version binding concepts through a typed decision adapter; retain the canonical approval record |
| Native tools and functions | Existing selected capability and executor edges | Wrap a useful function behind typed request/result/error records with declared effects and a Baltor variant where useful |
| Browser or computer backend | Existing qualified execution/browser capability | Optional backend engine with explicit limits and identity; keep task authority at the caller |
| Conversation persistence | Existing store edge, if required by the chosen UI | Evaluate a CopilotKit adapter independently from native storage; do not make the UI vendor a second task authority |

An upstream TypeScript function can be adapted through a bounded subprocess or
service when importing it is unsuitable for our Python runtime. Choose the
containment from its effects and dependencies. Source reuse alone does not
qualify it as interchangeable: every engine and Baltor variant must pass the
same contract population, including refusal and partial-failure cases.

## Durable-task ideas worth adapting

The worker stores status, lease identity and expiration, claims eligible work
with database compare-and-swap, renews leases, and checks identity at checkpoints.
Pause/cancel invalidate the lease and abort local work. Its store implements
compare-and-swap with a conditional SQL update. These are concrete patterns for
preventing a stale worker from publishing a final result after another worker
takes ownership.
[Worker](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/apps/server/src/engine/worker.ts),
[store](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/apps/server/src/db.ts).

Do not equate a lease with exactly-once external effects. A worker can lose its
lease after sending an irreversible request. Baltor needs a separate dispatch
identity, recorded outcome and reconciliation state. The same distinction is
visible in OpenMuse: interrupted executing actions become `outcome_unknown`,
and retries of linked unsuccessful actions are blocked pending reconciliation.

The existing worker scans task records and takes up to three eligible records
per tick. This is useful small-deployment code, not evidence for a million-task
scheduler. PGlite is an embedded local option; a separately running task worker
requires PostgreSQL plus shared data/secrets. The upstream documentation requests
one API instance. No throughput or hostile multi-tenant qualification follows
from the database type.

Suggested Baltor conformance cases: two claimants race for one run; expired lease
is recovered; stale worker cannot checkpoint; pause arrives during a tool call;
provider returns after cancellation; restart occurs after dispatch but before
action-record persistence; retries preserve cumulative budgets. Keep success defined
by the owning Loop's acceptance condition, not a worker's status string.

## Action review is separate from intelligence approval

`ActionService` creates a proposal containing the account/connection, exact
parsed input, optional target/version and a digest. Decisions check the digest,
expiration, connection identity and eligible task state before claiming the
action. This is useful source for **one execution's external-effect review**.
It does not implement Baltor's independent admission of reusable intelligence,
producer/reviewer separation, or catalogue release policy.
[Action service](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/apps/server/src/actions.ts).

Adapt its preview pattern: show destination/account, operation, exact data,
impact and expiry, then keep a durable action record. Apply such interaction only when
the effect actually requires review under the user's existing authority. Reading
public evidence or generating a reversible candidate should not acquire a new
approval prompt merely because the template has review screens.

Useful tests distinguish approval of one body from a later changed body, one
account from a reconnected account, a denied proposal from a retry, and a
completed provider operation from a connection timeout. The exact approval
contract remains ours, including existing standing user authorization.

## Tools, remote agents and generated-tool limits

The model-task implementation builds an explicit tool set using Zod schemas and
CopilotKit `defineTool`. It serializes task tool operations, checks the current
lease, persists selected operation results, and stops further operations after
the task is waiting or finished. The built-in model run sets sixteen steps,
zero SDK retries and a five-minute timeout. These are bounded controls, but are
not a strict total-token budget or complete model-cost ledger.
[Model task](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/apps/server/src/engine/model.ts).

Its AG-UI chat route can instantiate an `HttpAgent` with a configured remote URL
and bearer token. That does not make every internal workflow use that remote
agent: the task service still routes document, monitor and finance jobs to
specific handlers and remaining delegated work to `executeModelTask`. A remote
chat backend is therefore not a drop-in replacement for every durable task
handler. Backend selection and service endpoint semantics need separate typed
bindings in Baltor.
[Agent route](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/apps/server/src/agent.ts),
[task dispatch](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/apps/server/src/engine/service.ts#L642-L738).

**A managed registry of generated tools is roadmap work.** The repository does
not supply a proven 100,000-package admission/search/materialization system.
The product page's discussion of learning and proposed skills refers to the
separately configured Intelligence service; it must not be counted as an
implemented open-source tool-generation pipeline in this repository.
[Roadmap](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/ROADMAP.md),
[product page](https://www.copilotkit.ai/openmuse).

For our original package campaign, retain the current exact-file factory,
frozen generation plans, producer identity, independent review and catalogue
stores. Borrow UI cards for proposal status, tests, compatibility, rejection
reasons and release history. Do not treat an application tool list or an AG-UI
event as package provenance or approval.

## A useful existing adapter example: OpenBot

The OpenBot adapter accepts an injected authenticated transport, has explicit
disabled/not-configured states, validates responses, and classifies uncertain
mutating outcomes. It does not call global `fetch`. Its documentation pins a
specific upstream contract and says the integration is not live. It also
distinguishes an Intelligence runtime URL from a direct AG-UI SSE endpoint.
[Adapter](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/packages/backends/src/openbot.ts),
[integration boundary](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/docs/OPENBOT-INTEGRATION.md).

Our no-network fixtures confirmed: disabled makes no transport call; a mutating
500 response is uncertain without a retry; a malformed successful mutation
response is also uncertain; a snapshot error is treated differently; and the
runtime descriptor identifies the Intelligence transport. Those are valuable
adapter behaviors. They do not prove real authentication or an OpenBot round
trip. An endpoint's localhost address is resolved on its executing machine;
neither a phone nor Baltor's hosted API can assume it means the customer's local
model server.

## UI/UX and product opportunities

OpenMuse separates the chat composer, ongoing server tasks, activity, reviews
and saved artifacts. A stop control keeps its location and retains the draft.
Queued follow-ups remain visible; stopping a chat pauses that queue while
delegated server work has separate controls. Rich cards reference saved objects
rather than embedding stale signed URLs. The user can take over the same browser
session. These are specific interaction ideas worth testing in Baltor.
[Interaction design](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/docs/EXPERIENCE.md).

Our application should expose a task's current focused step, selected package,
model, budget, reason for waiting and accepted result. Keep a compact activity
panel available on demand instead of forcing a large example-workflow sidebar
into the homepage. On package details, show inspectable files and tested client
profiles, then an exact installation preview. An action record should say whether
material was retrieved, placed, discovered or used; each is independently useful.

Conversation convenience must not imply durability: OpenMuse's unsent follow-up
queue lives in the open app; its delegated tasks live on the server. Baltor should
make the same distinction explicit, especially for overnight local-model work.
Show which computer must remain running and what can resume after a restart.

## Deployment and standards boundaries

OpenMuse's session system issues sessions for `local-user`; live mode authenticates
with one shared access key. This is a stated one-owner deployment model, not a
multi-tenant SaaS account system. Its optional Docker computer is nonroot,
network-disabled and resource-limited, with a persistent workspace volume. The
separate Chromium worker uses application-level public-network checks. The
upstream security document explicitly declines hostile-tenant isolation and
notes that Playwright disables Chromium's internal sandbox by default.
[Authentication](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/apps/server/src/auth.ts),
[security boundary](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/SECURITY.md).

AG-UI supplies an event vocabulary for agent/frontend interaction, including
message, tool and state events. It does not define a harness working-directory
package format, guarantee server execution permissions, or make an MCP server
available to a worker. A2A task exchange, MCP tools/resources, ACP harness
sessions and AG-UI presentation remain separate adapters with separately
qualified capabilities.
[AG-UI overview](https://docs.ag-ui.com/introduction),
[events](https://docs.ag-ui.com/concepts/events),
[our interfaces research](HARNESS-PACKAGE-STANDARDS-AND-INTERFACES-2026-09-23.md).

## Evidence, adoption gate and next concrete experiment

The [evidence inventory](../../artifacts/openmuse-component-reuse-2026-09-23/source-inventory.json)
records commit, source hashes and read-only scope. Seven isolated source checks
ran with no network, credentials, application startup, database, Docker, browser
or model. No upstream test suite was rerun. The project's September 16
verification report describes its own controlled tests and clearly leaves live
model, Google, Intelligence and some device acceptance open. Those historical
author results are not our independent validation of September 23 HEAD.
[Upstream verification](https://github.com/CopilotKit/openmuse/blob/bb7ce4e1c6e523bf282a655c63621e3ed9e75150/docs/VERIFICATION.md).

The smallest useful experiment is a frontend adapter over one existing Baltor
run: display a frozen task plan, stream its observed steps, request required
input, show one candidate artifact, and render the independent acceptance result.
Use synthetic records first; keep pause/cancel and approval decisions on the
existing service edges. Compare it with a Baltor-native rendering of identical
events. Test stale events, duplicate delivery, reconnect, unavailable service,
expired artifact links and a forbidden cross-customer task ID before a live pilot.

This preserves the owner's integration pattern: typed/versioned component,
qualified external engine, useful Baltor variant, and measured selection. It
does not require adopting the whole OpenMuse deployment or making a managed
conversation service mandatory for every Baltor customer.
