# Development checkpoint: September 20, 2026

Kind: working-tree handoff and evidence snapshot. This document does not grant
authority, close release gates or replace the machine-readable roadmap.

The [main development HTML](../../artifacts/architecture-audit-2026-09-19/loop-engine-system-map.html)
remains the single owner-facing document. It embeds this checkpoint, the setup
runbook, architecture, feature comparisons, worklist and source inventory.
The [Fable 5.1 handoff](FABLE-5-1-HANDOFF-2026-09-20.md) is also embedded there.
The latest update records Fly release 7, the working app hostname and the
Cloudflare nameserver change. No source commit or push accompanies it.

## Current outcome

The private Baltor pilot is deployed and usable. It is not a completed paid
product. All eight broad launch gates remain open because their full customer
journeys require more than the component and hosted checks completed here.

| Surface | Address or state |
|---|---|
| Public website | <https://baltor-pilot.fly.dev/> |
| Architecture and task example | <https://baltor-pilot.fly.dev/how-it-works> |
| Guided client connection | <https://baltor-pilot.fly.dev/connect> |
| First retrieval example | <https://baltor-pilot.fly.dev/examples> |
| Access and data boundaries | <https://baltor-pilot.fly.dev/security> |
| Email-free sign-in | <https://baltor-pilot.fly.dev/login> |
| Administrator dashboard | <https://baltor-pilot.fly.dev/admin> |
| Intelligence protocol endpoint | <https://baltor-pilot.fly.dev/mcp> |
| Custom hostnames | <https://baltor.ai/>, <https://www.baltor.ai/> and <https://app.baltor.ai/> each have a valid certificate and pass 45 hosted website checks. Cloudflare is active; some public DNS caches still retain older answers. |
| Source | Branch `main`, base revision `48cc954322691e492aad69a465ba470a112730e7`, with substantial uncommitted work. No source commit or push was performed in this delivery. |

The deployed image is
`registry.fly.io/baltor-pilot@sha256:0dd8a0e539c775c1898cf98f239b1c780e104b88c164ec7631c993c4cfe5d0e1`.
The runtime source identity is
`65010363f3092095404e9c7f1b14677c95c11fbb288f2d3e09a1e690e2918d2e`.
The full check report explains the files covered by that identity.

The running platform-specific image digest is
`sha256:7b45d327faba2e65829230e8ee4f91109207183b4575cdab08c545aae6af55e8`.
The September 20 website update retained the existing machine, region,
processor allocation, memory and persistent volume. No new model allowance,
public registration or live charging was enabled.

## Owner direction to preserve

The newest public-language direction is explicit: use Baltor, task, each
step, information, tools, models and results on the homepage and How it works.
Do not use Loop, Loop node, Loop Engine or runtime taxonomies on those pages
or in their shared footer. Preserve the canonical names and complete
definitions in technical documentation and GitHub. A documentation subdomain
is a future hosting choice, not an existing address.

The [launch benefit guide](../guides/launch-benefits-and-evidence.md) records
three draft themes: overnight work with local models, fewer tokens spent on
repetition, and useful expertise for each step. They are product directions,
not measured claims. Local inference, overnight recovery, complete token
accounting and independent context-use comparisons are explicit proof work.
Do not promise completion by morning, significant savings or always-correct
context selection before that evidence exists.

Lead the homepage with reusable solutions and useful work, not deployment
location, a context-layer category or unexplained runtime terminology.
The current headline is: "Turn complex problems into reusable solutions."
Agents, harnesses and prompt cycles belong in technical explanations when
they help the reader understand the implementation.

The five customer problems are excessive context, unnecessarily expensive
models, missing domain expertise, regeneration of existing code and repeated
mistakes. Position model selection, context sizing, tool choice, code reuse
and evaluation as parts of one work process. Retain reusable components and
complete solutions as the intended output, not merely a larger prompt.

The owner wants less effort spent assembling separate optimization systems.
Do not turn that direction into an unsupported promise that no specialists
are needed, that every configuration is optimal or that performance improves
every day. Improvements require measured outcomes and independent acceptance.

Light mode is the website default, including on systems configured for dark
appearance. Dark mode remains an explicit option. Benefits belong on the
homepage; client/server responsibilities and precise runtime definitions
belong on How it works and in the technical documentation.

SenseLab informed the bright presentation and short connection sequence.
Stripe's documentation informed the proposed client-specific setup guidance,
authentication distinctions and revocation instructions. Do not copy vendor
claims, testimonials, pricing or graphical assets into Baltor.
[SenseLab](https://www.sense-lab.ai/), [Stripe connection documentation](https://docs.stripe.com/mcp).

## Implemented and observed

| Work | Evidence and boundary |
|---|---|
| Benefit-led public site | Five problem statements, four intelligence layers, a reusable-workflow illustration and an interactive task-context example. Illustrations make no model calls. |
| Tenant access | Server-bound token identity, scope checks, revocation and disclosure grants over the existing catalogue authority. |
| Administrator test access | Email-free owner sign-in; create, label, inspect and revoke test tokens. Twenty active tokens by default, 24-hour default expiry and seven-day maximum. Limits are configured on the host. |
| Search and delivery | Authorized metadata search, exact reference selection, digest-checked UTF-8 body delivery and durable idempotent usage records. |
| Guided connection | Versioned Codex and OpenCode 1.x configuration recipes, secret references instead of embedded keys, a real browser protocol handshake and tool discovery, and explicit error states. |
| Native client connection | OpenCode 1.17.9 connected to the deployed service without starting a model turn or fetching a file body. Other configured servers were disabled for the command only; permanent client settings were unchanged. |
| Website comparison | Nineteen known original competitors, four adjacent references and Baltor reviewed as signed-out pages. The main HTML includes a filterable page matrix and scoped design/messaging notes. |
| Review-only intelligence | Twelve records, four persistent layers and ten content families, staged through the existing atomic catalogue contract. Normal search excludes all twelve. No publication or independent qualification is implied. |
| Hosting | One Fly Machine in `iad`, one shared processor, 2 GB memory, one encrypted 1 GB persistent volume. No automatic horizontal scaling. |
| Private recovery exercise | A real deployed SQLite backup, configuration and declared artifact files were restored into a network-isolated local container. Authentication, revoked records, exact bodies and request idempotency survived restart. |
| Supabase preparation | Project `qfzxmjznlwiopgvfgtsw` is healthy in `us-east-1`; database, storage and key access are prepared. Authentication-settings management is refused by the current grant. Runtime integration is not qualified. |
| Stripe preparation | The selected Baltor sandbox `acct_1UHZ9KCCxLfArYED` responds to the stored runtime test credential. Checkout, customer bootstrap and webhook qualification remain unfinished. |

The hosted catalogue contains a small host-attested diagnostic Context
Intelligence example. It is not an independently qualified commercial
catalogue across all four layers. The current search combines SQLite text
search with optional character-hash similarity, not a learned semantic model.

The public website does not expose internal source inventories, private
backups or operator administration credentials. Its administrator token has
service access-management authority, not unrestricted host, model or cloud
authority. Test tokens cannot delegate administration or billing management.
Tokens for one tenant share that tenant's grants and usage; they are not
separate private customer workspaces.

## Deployed account code and remaining integration

| Work | Current observation | Remaining check |
|---|---|---|
| Browser identity and account creation | Deployed adapter validates signed identity and current user information, creates a server-owned tenant binding and records token revocation. | Live configuration and real signup, recovery, self-service client credentials, transient provider failures and abuse limits are not qualified. |
| Browser integration | Email forms, dependency notices and a pinned same-origin Supabase browser library are deployed. Local browser regression passes 120 checks. | These local fixtures do not prove real confirmation mail or recovery. |
| Architecture conformance | Reviewed exact identity and loopback-test registrations pass the existing conformance checks. | Preserve the permission checks and exact boundaries in later changes. Earlier failing reports remain unchanged. |
| Public explanation | The deployed How it works page uses steps, selected information and checked results. Technical definitions remain in documentation. | Preserve plain-language public copy and exact technical definitions while completing customer workflows. |
| Planning and handoff | Sixteen delivery packages expand existing work into 128 actions and eighty verification cases, with owning code paths, acceptance dependencies, negative controls and rollback procedures. Three benefit drafts name their evidence requirements. | Planning coverage does not close a launch gate or authorize model calls. |

The account code is deployed but not enabled for public registration.
The private pilot still uses host-key
authentication, SQLite and files on its Fly volume. Its live capabilities
disable public registration, checkout, the billing portal and webhooks.
The current search is not learned semantic retrieval.

The [plain-language browser report](../../artifacts/architecture-audit-2026-09-19/plain-language-handoff-browser-2.json)
records those 120 checks. The first attempt is retained: its route-specific
check found the technical reference on the example page instead of in
documentation. The reference was moved to the correct page, not removed.
Local component checks also pass 104 HTTP checks and 31 durable-runtime
checks. They use provider fixtures and do not qualify real email or billing.
The [focused handoff capture](../../artifacts/architecture-audit-2026-09-19/handoff-focused-checks-1.json)
binds those component results to an unchanged package identity and preserves
the earlier failing conformance output. Planning and architecture-report
checks pass 37 tests. Documentation lint and 125 local file-link checks pass.

## Provider connections and domain cutover

Read-only checks confirmed homepage, login, connection, health and capability
responses from the existing Fly deployment. Stripe's account read returned
the newly approved Baltor sandbox, `acct_1UHZ9KCCxLfArYED`. Resend management
initialization succeeded. The sender `auth.baltor.ai` has since been created,
its exact records installed in Cloudflare and verification requested.
Cloudflare's new write grant created the Free `baltor.ai` zone. Supabase's public
authentication settings responded with email confirmation enabled.

These observations establish access and current configuration only. They do
not establish subscription processing, DNS cutover, sender verification,
customer confirmation or complete task execution. Resend's first management
callback expired; the subsequent callback succeeded. Do not restart the
successful connection without a new observed failure.

The original read-only Cloudflare grant refused zone creation. An incorrect
follow-up request used `zone.edit` and `dns.edit`; those scope names were
rejected. The corrected `zone.write` and `dns.write` request was approved,
and actual zone and record writes succeeded. The failed requests remain part
of the work record rather than being described as account problems.

Namecheap authorization works. Its read-back confirms custom nameservers
`dana.ns.cloudflare.com` and `nile.ns.cloudflare.com`. The owner confirms no
existing email or forwarding. Fourteen records are installed in Cloudflare,
including exact Resend sender records and Fly certificate verification.
The root and www records replace the registrar parking destinations.
The `.ai` registry now publishes the Cloudflare delegation and Cloudflare
reports the zone active. Some public resolvers still return cached older
answers. Do not repeat the nameserver write.
The [cutover record](../../artifacts/architecture-audit-2026-09-19/domain-cutover-progress-1.json)
preserves the old delegation, partial writes and transient failure. The
[later verification](../../artifacts/architecture-audit-2026-09-19/domain-cutover-verification-2.json)
records activation, working hostnames and remaining sender-verification limits.

The app hostname passes 45 hosted website checks after the registrar change.
One earlier HTTPS probe failed to connect; subsequent ordinary and
direct-address checks succeeded. No uninterrupted-availability claim is made.
Root and www certificates are issued and both hostnames pass all 45 hosted
website checks. Cloudflare is the DNS provider; its proxy and web firewall
are not enabled by this DNS-only setup.
The host configuration accepts only the four exact public origins plus its
local health host. Its prior configuration is backed up privately on the
same volume. Canonical protocol and account redirects still use the Fly origin.

Supabase management
access previously refused authentication-settings operations. The owner
confirmed the Fly Site URL and exact `/auth/callback` redirect in Supabase;
engineering has not independently read them back. Its attempted dynamic
client registration rejected authentication-settings scopes. Request an
appropriate grant, not the same unsuccessful flow or a manual settings task.

## Credential reuse for Claude Code

The credential handoff contains six project-local connections in
Claude Code 2.1.271. Resend, Cloudflare, Supabase, Stripe test, Fly and
Namecheap report Connected through Claude Code's checks. Thirteen named credential
references are reusable from the same workstation keyring. The existing
GitHub command-line authentication also works. No model session was started.
See the [credential handoff guide](../guides/developer-credential-handoff.md).
The private export contains references and helper commands, not plaintext
secrets; it does not create any missing provider permission.

Namecheap uses Claude Code's native authorization store and refresh mechanism.
The Cloudflare helper selects the newly approved write grant and refuses a
grant without the required scopes. Twenty-three local credential checks pass.

## Release 7 verification

| Check population | Result | Report |
|---|---|---|
| Complete offline package suite | 5,938 of 5,938 passed; 15 optional checks not tested; source unchanged | [Package checks](../../artifacts/architecture-audit-2026-09-19/verification-deployment-account-code-1.json) |
| Focused launch integration | 284 of 284 passed; five removed-guard controls detected | [Focused checks](../../artifacts/architecture-audit-2026-09-19/deployment-account-launch-slice-1.json) |
| Local browser journeys | 120 of 120 passed | [Browser checks](../../artifacts/architecture-audit-2026-09-19/deployment-account-browser-1.json) |
| Clean service image | Seven container checks and 104 installed service checks passed | [Container checks](../../artifacts/architecture-audit-2026-09-19/deployment-account-container-1.json) |
| Deployed public website | 45 of 45 passed; served assets match tested source | [Hosted browser checks](../../artifacts/architecture-audit-2026-09-19/hosted-account-code-2.json) |
| Deployed service and protocol | 16 of 16 passed | [Service checks](../../artifacts/architecture-audit-2026-09-19/hosted-account-service-1.json) |
| Deployed administrator lifecycle | 12 of 12 passed; temporary test token revoked | [Administrator checks](../../artifacts/architecture-audit-2026-09-19/hosted-account-admin-1.json) |
| App hostname after registrar update and host restart | 45 of 45 passed | [Custom hostname checks](../../artifacts/architecture-audit-2026-09-19/hosted-custom-domain-cutover-1.json) |
| Root hostname | 45 of 45 passed | [Root website checks](../../artifacts/architecture-audit-2026-09-19/hosted-root-domain-1.json) |
| www hostname | 45 of 45 passed | [www website checks](../../artifacts/architecture-audit-2026-09-19/hosted-www-domain-1.json) |

The first hosted copy check used an old phrase and failed. Its repaired
assertion also rejects a deliberately wrong secret destination. That failed
report remains available. A new encrypted-volume snapshot exists, but its
existence is not a new restore test. None of these checks establishes real
customer email delivery, subscription processing or complete task execution.

## Previous deployment checks

These reports belong to the earlier frozen image. Later account and website
edits make the full-package result stale for the current working tree. Keep
the original results and failures; collect new reports for changed source.

| Check population | Result | Report |
|---|---|---|
| Complete offline package suite | 5,914 of 5,914 passed; 15 optional checks not tested; source unchanged | [Package checks](../../artifacts/architecture-audit-2026-09-19/verification-website-journey-2.json) |
| Focused launch integration | 266 of 266 passed; five removed-guard controls detected | [Focused checks](../../artifacts/architecture-audit-2026-09-19/website-journey-launch-slice-2.json) |
| Local browser journeys | 114 of 114 passed, including protocol responses, configuration-loading races, authenticated cancellation, narrow layouts, keyboard controls and 200-percent text | [Browser checks](../../artifacts/architecture-audit-2026-09-19/guided-connection-browser-7.json) |
| Clean service image | Seven container checks and 86 service checks passed | [Container checks](../../artifacts/architecture-audit-2026-09-19/website-journey-container-2.json) |
| Deployed public website | 42 of 42 passed; served assets match tested source | [Hosted browser checks](../../artifacts/architecture-audit-2026-09-19/hosted-website-journey-1.json) |
| Deployed service and protocol | 16 of 16 passed | [Hosted service checks](../../artifacts/architecture-audit-2026-09-19/hosted-service-attempt-7.json) |
| Deployed administrator lifecycle | 12 of 12 passed; temporary test token revoked | [Administrator checks](../../artifacts/architecture-audit-2026-09-19/hosted-administrator-attempt-5.json) |
| Native client discovery | OpenCode 1.17.9 reports a real connection; no model turn or native material-loading claim | [Native connection](../../artifacts/architecture-audit-2026-09-19/native-opencode-connection-2.json) |
| Prior deployment backup restored locally | 15 of 15 passed on that earlier image; temporary container and volume removed | [Restore checks](../../artifacts/architecture-audit-2026-09-19/pilot-backup-restore-2.json) |

These are separate populations, not one customer-success benchmark. No real
model calls were authorized by this checkpoint. No live customer charges were
enabled. Full native harness loading, useful task completion and a paid
customer journey are not established by these counts.

Preserve failures. Earlier full-suite captures became stale when page source
changed during execution. An enlarged-text browser check found four overflow
cases before the wrapping repair. The first restore attempt omitted Docker's
interactive input flag, so its restore process received no archive input;
the failure was reproduced with harmless empty data before correcting the
test runner. The original reports remain beside their successful successors.

This cycle also retains the failed browser check that assumed a JSON-only
protocol response, two enlarged-text layout failures and a reproduced race
where sign-in cancelled public setup data. The repaired reader accepts bounded
event-stream replies and checks response identities. Public configuration
loading no longer shares cancellation with credential-bound requests; signing
out still aborts authenticated work. A report-browser check caught missing
serialization of the new comparison and candidate sections before final handoff.

The retained backup is private, permission-restricted and excluded from Git.
It is not separately encrypted by the restore tool. This test does not
establish scheduled off-site retention, regional recovery or a recovery-time
guarantee. A production restore must reconcile later credential revocations
and external payment state before admitting traffic.

## Measured latency and review population

The [post-deployment latency report](../../artifacts/architecture-audit-2026-09-19/service-latency-2.json)
retains 84 serial requests, twelve per profile, with no failed requests.
Nearest-rank percentiles include successful cold and reused-connection samples;
the report also separates reused connections. Failed requests would remain in
the denominator and raw observations, not disappear from the report.

| Profile | Median milliseconds | 95th-percentile milliseconds |
|---|---:|---:|
| Homepage request | 64.5 | 199.7 |
| Permitted catalogue metadata | 56.9 | 183.0 |
| Lexical retrieval | 62.3 | 133.2 |
| Character-similarity hybrid retrieval | 57.0 | 161.4 |

These measurements are from the development workstation to the Fly pilot in
`iad`. They include network round trip and client handling, not isolated server
processing. The catalogue is a small diagnostic population. They do not
establish production capacity, global latency, an availability guarantee or
semantic retrieval quality. The first run remains as
[latency attempt one](../../artifacts/architecture-audit-2026-09-19/service-latency-1.json);
differences between runs are not attributed to the website change.

The hosted browser record measured one navigation per route. Load events
ranged from about 145 to 296 milliseconds across five routes. These are
headless laboratory observations, not field Core Web Vitals, a percentile
estimate or complete authenticated-interaction timing.

The [candidate export](../../artifacts/architecture-audit-2026-09-19/candidate-intelligence-2.json)
and [staging report](../../artifacts/architecture-audit-2026-09-19/candidate-intelligence-staging-2.json)
preserve twelve acknowledged records. Six belong to Context Intelligence, two
to Code Intelligence, two to Runtime History and Solution Intelligence, and
two to User Feedback Intelligence. They cover ten content families. The
history records reference actual checks; the feedback records summarize
previously recorded owner direction rather than invented user outcomes.

All twelve title-derived review probes found the intended record among the
first three references with zero model calls. Normal search returned no
candidates. These are mechanism checks, not held-out retrieval relevance or
task-success evidence. Code cards remain source references, not executable
packages. Source digests must be checked again before review because living
repository documents can change after staging.
Record versions bind search labels and layer placement as well as payload and
source identities. A metadata-only change advances the record version without
pretending its body bytes changed. The corresponding test rejects a control
that removes metadata from the version binding. The first staging export is
preserved as an earlier attempt, not combined with this population.

## Ambiguities resolved in this cycle

| Owner wording | Working resolution | Boundary |
|---|---|---|
| Six or more intelligence layers | Expand useful content families across the four canonical persistent layers | No new runtime type or persistent layer was introduced. |
| Superior to every competitor | Compare scoped customer journeys and close measurable gaps | No blanket superiority, customer-conversion or competitor-performance claim. |
| Continuously improve | Preserve observations, failures and next work in the existing roadmap | No unbounded model spending, external mutations or automatic candidate promotion. |
| Connect a harness | Separate configuration, connection, discovery, retrieval, native loading and task benefit | OpenCode connection passes; full native material use remains unqualified. |

The [website review](../research/WEBSITE-JOURNEY-REVIEW-2026-09-20.md) explains
the comparison scope and proposed go-to-market sequence. Its raw observations
are research inputs, not product authority or proof of customer adoption.

## Delivery sequence after this checkpoint

The authoritative task states remain in
[roadmap.yaml](../roadmap/roadmap.yaml). This table prioritizes implementation;
it is not a second editable task store or a claim that the steps are finished.

| Priority | Existing work | Complete when |
|---|---|---|
| 1 | D-01: source and account-boundary review | Preserve the reviewed conformance repair, review account security and keep exact-source test evidence current. |
| 2 | D-02 through D-04: domain, email, accounts and sandbox subscriptions | An ordinary user confirms an account, obtains scoped client access, uses test checkout and loses access when revoked. |
| 3 | D-05 and D-06: cloud records, retrieval and selected material | Real storage preserves tenant isolation and exact bytes; the supported native client demonstrably loads the selected files. |
| 4 | D-07 through D-09: long-running work, reusable output and benefit measurements | A declared local-model profile survives interruption; reviewed solutions run on fresh inputs; matched trials measure quality, tokens and context usefulness. Model calls need separate authority. |
| 5 | D-10 and D-11: customer experience and release | Plain-language pages and the complete supported journey pass exact-source checks, recovery and release review. No elapsed deadline creates readiness. |
| Ongoing | D-12: engine choices and controlled improvement | Research and adapters stay replaceable and candidate-only where required, independent of paid-release or runtime authority. |

The packages are planning detail inside the existing roadmap. They do not
create a second task-state store. Acceptance dependencies do not prevent
independent local implementation while an external grant is unavailable.

Useful independent work while account integration is pending includes native
layout compilation, client configuration templates, compatibility refusal
tests, current-contract cleanup and an isolated PostgreSQL adapter test suite.
Do not create another orchestration framework, credential store or runtime
class to make these integrations easier.

The first proof of the core product should follow one useful task through
retrieval, a scoped assignment, actual execution, independent checking and
reuse on changed inputs. Another diagram or fixture count cannot replace it.

## Owner actions still required

Fly, Stripe and Supabase accounts exist. Do not ask the owner to create them
again. The selected infrastructure allowance is 50 United States dollars per
month and up to 10 dollars for setup. These are operator limits, not provider
billing caps. Model spending remains zero and live customer charges remain off.

1. Cloudflare and Namecheap authorization are complete. No manual zone,
   record or nameserver task remains. Engineering verifies propagation.
2. Approve exact Supabase authentication-settings management access when
   requested. Database, storage and key access already work. Do not repeat
   the owner-confirmed Site URL and redirect changes.
3. Supply controlled recipient labels when email testing is ready, plus
   genuinely owner-only privacy, support and public-pricing decisions.
4. Approve a bounded model-call allowance or provide a customer-controlled
   qualification run when native task and overnight tests are ready.

Resend management and Stripe runtime sandbox credentials are prepared.
Engineering owns sender creation, DNS and mail setup under proper grants,
test products, private storage, callbacks, webhooks and delivery checks.
No routine account-creation request remains for those prepared services.

Engineering owns implementation, configurations, callback addresses, test
products, deployment and technical choices within the declared scope. Owner
tasks should be limited to account consent, private access, business policy
and genuinely external decisions.

## Handoff to Claude Code or another developer

Read [AGENTS.md](../../AGENTS.md), [ASTRA.md](../../ASTRA.md) and the relevant
component guide. Recheck live state and source identity; this is a snapshot,
not permission to reuse historical authority. Keep the repository name,
Python import and command as Loop Engine. Baltor is the public brand.

Do not replace, reset, format or commit the entire dirty tree. Resolve
ownership of overlapping paths first. No source publication is implied by a
successful direct image deployment. The GitHub pilot workflow remains disabled
until the reviewed source and deployment files are published together.

The website lives in `core/service_runtime/web_assets`. Public HTTP routing
and configured branding live in `core/service_runtime/http.py`. Administrator
policy is in `core/service_runtime/access.py`; it uses the existing catalogue.
The main HTML is generated by `tools/architecture_audit.py`, not maintained
by directly editing the generated file. See the
[launch setup runbook](../guides/launch-setup-runbook.md) for private credential
references and the administrator copy command. Never copy operator keys into
customer harness environments.

Use focused checks during iteration. Freeze the package before its full test
capture so a simultaneous content edit does not invalidate that expensive
run. Browser and report commands require new output paths; retain earlier
attempts rather than overwriting evidence. Regenerate status after editing
the roadmap, then rebuild and check the main HTML.

```bash
PYTHONPATH=src .venv/bin/python -m loop_engine service smoke
node tools/check_service_workspace.mjs artifacts/architecture-audit-2026-09-19/NEW-browser-report.json
PYTHONPATH=src:tools .venv/bin/python tools/build_continuation_status.py
PYTHONPATH=src:tools .venv/bin/python tools/architecture_audit.py
```

Replace `NEW-browser-report.json` with an unused attempt name. Hosted checks
that mint tokens or read metered bodies require their explicit command-line
authority flags. The public-site checker is read-only. Do not repeat bootstrap
administrator creation when the credential is already in the system keyring.

The [endpoint migration design](../architecture/SERVICE-IDENTITY-ENDPOINTS-AND-MIGRATION.md)
records trusted service discovery, domain changes and multi-endpoint policy.
Those mechanisms are proposed. Do not add replicas of the current SQLite
service, silently follow credential-bearing redirects or replay an uncertain
external action on a different endpoint.
