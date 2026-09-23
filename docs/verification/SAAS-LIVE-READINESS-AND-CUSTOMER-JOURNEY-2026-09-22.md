# SaaS live readiness and customer journey, September 22, 2026

Kind: read-only verification record. The public HTTP probes ran on September
23, 2026, at about 03:10–03:19 UTC, still September 22 in United States
Eastern time. They used unauthenticated GET and HEAD requests. No waiting list
request, account action, download, payment, model call or provider mutation was
made. This report distinguishes current public observations from earlier
authenticated evidence and from work still required.

## Source and release identity

At the time of the probes, GitHub `main` was `a51ac96378ce63cd4504499ea865a22e78168fec`.
Its [continuous integration run](https://github.com/alisonjieli-png/loop-engine/actions/runs/35805955473)
passed. The [guarded Fly deployment run](https://github.com/alisonjieli-png/loop-engine/actions/runs/35807183861)
completed successfully at 01:41 UTC, pushed image digest
`sha256:b5d2c5914dca1014f9d10275e55e45174ec82fe12e8dcb341df57fc71beb30bc`,
passed the service readiness gate and applied the packaged catalogue grants
on Machine `83733ea7779068`. Those are workflow observations. The Fly command
on this workstation had no access token, so this audit did not independently
read the current Machine image, Fly release number or rollback image.

After the public probes, a separate operator
[Fly release 15 record](../../artifacts/architecture-audit-2026-09-19/pilot-release-13.json)
was committed. It reports the Machine image and rollback digest, the host
record version migration, 73 of 73 browser checks on three main hostnames,
72 of 73 on the Fly hostname, six of six catalogue checks with 34 items
offered and nine withheld, and 19 of 19 hosted service checks. Those checks
were not rerun by this audit. The
[current deployment map](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
now records Fly release 15 and its rollback target. The initial workstation
Fly command still lacked an access token, so this audit itself did not read
the Machine.

The unauthenticated home page on all eight configured hostnames returned 200
and the same 79,892-byte HTML body, SHA-256
`a667c727280b4f7473571f5716cf9f52da81354fd02515bf83e23892abe2e90e`.
That is exactly the digest of the `a51ac963` packaged
[`index.html`](../../src/loop_engine/core/service_runtime/web_assets/index.html)
after its `{{SERVICE_NAME}}` placeholder is replaced with `Baltor`. The
capabilities and health responses also had identical digests across
`baltor.ai`, `www.baltor.ai`, `app.baltor.ai`, `baltor-pilot.fly.dev`,
`demo.baltor.ai`, `examples.baltor.ai`, `docs.baltor.ai` and
`status.baltor.ai`. Each [health response](https://app.baltor.ai/api/v1/health)
reported `service_health/v2`, `alive=true`, `ready=true`,
`readiness_checked=true`, all required checks passed, and
`deployed_provider_qualification=false`. Health establishes that dependencies
answered during the check, not that a customer completed a task.

Later local commits, including `4795276` for the owner's 100,000-file
direction and `38d5bcc` for the Fly release 15 record, are not called
deployed by the public body-digest comparison. The matched deployed HTML
still binds to `a51ac963`.

## Customer journey observed and still open

| Step | Evidence and current state | Next proof |
|---|---|---|
| Visit and request access | `GET /`, `/signup`, `/waitlist`, `/pricing`, `/privacy`, `/account`, `/connect` and `/app` returned 200 on `app.baltor.ai`. The [capabilities response](https://app.baltor.ai/api/v1/capabilities) reports `waitlist_available=true`, `registration_available=false` and `access_profile=operator_provisioned`. The served [page script](../../src/loop_engine/core/service_runtime/web_assets/service.js) reveals the waiting list form when that record says it is open. This audit did not submit the form or read its stored result. | Follow [D-18-T03](../roadmap/roadmap.yaml): a first-time visitor submits once, sees confirmation, and an operator can read the exact request. |
| Confirm an account and sign in | The public [identity configuration](https://app.baltor.ai/api/v1/account/identity) reports `email_signup_enabled=false`, `signup_available=false`, `recovery_available=false` and `session_persistence=page_memory`. The [private beta procedure](../guides/private-beta-operations.md) describes operator creation and binding; it explicitly says that no one had observed a first sign-in against a service with account creation closed at the time of that record. Current sign-in was not retested here. | Follow [D-17-T03](../roadmap/roadmap.yaml): an invited person outside engineering confirms control of the mailbox, signs in, and completes the journey without help; refuse an uninvited and disabled account. |
| Make a client key | Live capabilities report `client_access_available=true`, and the served [account page](../../src/loop_engine/core/service_runtime/web_assets/index.html) has issue, list and revoke controls. Earlier authenticated pilot evidence and the [setup guide](../guides/service-getting-set-up.md) support this path for prepared accounts. This audit used no account credential. | In the invited-person drill, create a personal key, connect a client, revoke it and observe the next request refused. |
| Search, download and review usage | The previous [release record](../../artifacts/architecture-audit-2026-09-19/pilot-release-10.json) recorded seven references from an official protocol client, without loading a body. The later [release 15 record](../../artifacts/architecture-audit-2026-09-19/pilot-release-13.json) reports 43 registered items, 34 offered to the pilot owner and nine withheld for undeclared effects, plus one metered digest-verified body read in its 19 hosted service checks. This audit made no authenticated search, body read or usage read itself. | In [D-17-T03 and T04](../roadmap/roadmap.yaml), record the invited person's offered, fetched, digest-verified and metered facts separately. |
| Load and use a file in a harness | The [independent-instance experiment](../research/HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md) loaded local selected files in Codex, OpenCode, Claude Code and Pi without a model turn. It explicitly separates loaded from used. There is no recorded customer path from a live download through native placement to an accepted step. | Follow [D-17-T04](../roadmap/roadmap.yaml): the native client itself records the selected release bytes loaded and used; a check accepts the step result. |
| Subscribe and manage billing | Live capabilities report `checkout=false`, `portal=false`, `webhook=true` and `discount_code=false`. The earlier [live payments record](../../artifacts/architecture-audit-2026-09-19/live-payments-enabled-1.json) proves live Stripe checkout and portal **session creation**, with no money moved. It names the missing customer binding, charge, webhook-to-entitlement and self-service journey. `GET /api/v1/billing/plans` without a credential returned 401, as expected. | With a test customer under the approved billing procedure, prove checkout, webhook, entitlement, customer portal and loss of paid access after cancellation before enabling paid self-service. |
| Manage data and get help | The account page has identity, keys, usage and a billing availability panel. Export and self-service deletion are future [S-6.38](../roadmap/roadmap.yaml) work. `/privacy` returned 200 and serves the [owner-approved notice](../legal/PRIVACY-NOTICE.md); `/terms` and `/support` returned 404. The [beta terms](../legal/README.md) are a draft awaiting owner approval. The privacy notice gives a postal address and points non-personal questions to the public issue tracker. | Prove the account lifecycle, tenant-safe export and deletion; obtain the owner's terms decision before publishing terms or opening paid access. |

The public root and `/signup` returned 404 to `HEAD` while their `GET`
requests returned 200. The demo, examples, docs and status hostnames served
the same home page bytes as the main host, so their named surfaces are not
present in this release. These are distinct [S-6.33](../roadmap/roadmap.yaml)
website findings, not failures of the public GET health check.

## Library population and 100,000-file boundary

The current packaged
[`host-release/manifest.json`](../../examples/29_intelligence_service/starter-catalogue/host-release/manifest.json)
has exactly 43 items and 43 distinct `body_path` values. Every path ends in
`.md`; every reference has `kind=skill`, `family=harness`, and
`source_layer=harness_local`. The references total 119,724 body bytes. This
counts the packaged release, not every candidate in the repository, and the
new deployment workflow used this packaged manifest. No live search result
was used in this audit to recheck the 34-item tenant offer count.
An exact pass over all 43 packaged bodies found **zero files named
`SKILL.md` and zero bodies beginning with Agent Skills frontmatter**.
They are retrievable Markdown guidance; their `kind=skill` metadata does
not by itself establish native Agent Skill discovery in Codex, Claude Code,
OpenCode or Pi. A qualified adapter could explicitly load or render selected
bodies, but that has to be measured as a separate customer step.

The owner now defines harness intelligence as **any file that a harness picks
up from its working directory or step configuration**, including instruction
files such as `AGENTS.md` and `CODEX.md`, skills with scripts and assets, tools
and reusable code, subagent and command definitions, hooks, plugin
declarations and protocol server configurations. The 43 single Markdown
bodies do not yet prove mixed-file or multi-file package serving. The current
[S-6.40](../roadmap/roadmap.yaml) gate requires the first 10,000 and then
100,000 distinct approved packages, with a public count derived only from
active releases and exact-byte independent review records. Files, logical
packages and rendered variants need separate counts. A capacity claim also
needs measured indexing, search, grants, storage and download behavior at the
intended population; the current host is one Machine with one SQLite database
and a 1 GB volume, as the [deployment map](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
records.

## Release gate that remains

The latest guarded workflow now applies grants automatically. It checks
service readiness before and after that step, but it does not run the full
hosted website, catalogue, service and protocol suites on every hostname or
write a release record with the running image and rollback digest. That is
the smallest remaining operational [D-18-T01 and S-6.35](../roadmap/roadmap.yaml)
gate. The required negative control removes the grant step and must make the
catalogue check fail. Until these checks, the successful deployment and
matching public HTML are stronger than a source-only claim but narrower than
a fully functioning SaaS customer journey.
