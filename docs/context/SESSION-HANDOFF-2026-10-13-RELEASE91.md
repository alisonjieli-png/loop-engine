# Standalone websites for review

Kind: dated handoff, October 13, 2026. Follow
[AGENTS.md](../../AGENTS.md#commit-push-and-release-authority) for authority and
the [roadmap](../roadmap/roadmap.yaml) for current work. This record adds no
permission or competing work queue.

## Application and verification state

Fly release 91 runs committed main
`b500149c5cfdebc2ee1bf5ee05b5fba4b7052ec2`, image
`sha256:34f939fa7cdceb200063a74ed5a01747d5e9a1f9bfd9eea3534d56e54f944a13`.
Exact CI `38461710945` passed twenty jobs. Guarded deployment `38463481427`
succeeded and the deployment gate is closed. Fly records the release's
creation at 20:34:40 UTC on October 13, not the workflow completion time.

All selected websites are live and available for public review. The six new
origins passed 1,814 functional assertions and 1,556 exact-source GET checks
through ordinary public DNS and verified TLS. Their certificates are ready.
The strict aggregate is false because four secondary browser-body measurements
failed. Public availability is established; a completely passing measurement
run is not. The exact limits and retained attempts are recorded below.

## Website scope

AgentFoundry at `getagentfoundry.si` and `www.getagentfoundry.si` has its own
component discovery, public examples, account pages and connection guide.
It reuses the shared catalogue, identity, authorization and MCP service.
The 376 public component examples show actual packaged metadata and recorded
renders. Public Good search reads the shared collection. Paid checkout is
not offered on this standalone site; its billing return path remains
unqualified. Existing account access and subscriptions are unchanged.

AgentAFK at `agentafk.si` and `www.agentafk.si` is a browser-local Preview.
Its task arrangement and downloadable run material do not execute work in
the cloud, install a supervisor or enable learned prioritization. Account
and provider-effect routes are refused on this public-only presentation.
The requested adaptive task graph and outcome-based queue remain work under
S-6.24.03, with dependency readiness and customer authority enforced separately.

The Don't be a meat proxy campaign at `dontbeameatproxy.si` and
`www.dontbeameatproxy.si` sends visitors to AgentFeeds collections and its
reading-profile builder. It is an acquisition site, not a fourth product.
It has no account or execution controls and makes no claim that curated
references are continuously maintained personalized research.

AgentFeeds remains at `agentfeeds.si` and `www.agentfeeds.si`. Baltor keeps
the combined product presentation. All four standalone domains share the
existing backend while retaining separate presentation and navigation.
Common operator and approved legal text are preserved.

## DNS and rollback

The owner requested parallel launch work and explicitly authorized DNS and
Cloudflare nameserver management. Three separate registrar transitions set
`dana.ns.cloudflare.com` and `nile.ns.cloudflare.com`. Each new free zone
contains six DNS-only records. The six new certificates are ready. Existing
registrar records remain preserved; no paid zone, advertising purchase or
new application or database was created. Each new apex CNAME targets
`yj0ooj6.baltor-pilot.fly.dev`; each `www` CNAME targets its apex. The six
certificates add at most $0.60 a month. The release record includes the three
zone identities. Do not replay these completed operations.

All standalone sites serve directly from Fly. The existing nine Baltor hosts
retain the Cloudflare Worker and dynamic origin mode `all`; the technical
Fly hostname remains the fallback. Export
`f69adc4be69749a8e9e8f080dbebadd6ff607cbd94af862941c5a98feb86c9b7`
passed all 3,281 exact public-file checks. Its 89,426,338 public-file bytes
exclude the extra control-index asset. Worker deployment
`a6df5253-910d-4bef-abf4-775193cb3341` uses version
`7a20ffdf-62e2-43c0-9df1-12e1131fba56`; the nine Worker routes are unchanged.

Rollback image 90 is
`sha256:7dd98fd2a54ecfa1aa4392e8d242525ec0f4b1b71d803d5a91a3f3bcf76a7b29`.
Before starting it, restore `/data/host-before-standalone-sites-20261013.json`
with SHA-256
`33bb6e2bd929741bbc9a081a8b03d80b45e76415d7a365899e834b7031d7b64d`.
Its brand parser rejects the new brand values. The staged host hash is
`ed23fffd71d4a48cf8c09f4cf239695fe7cf105278ef25be8a78d29e9a140cb6`.
Only the host/origin allowlists and brand profiles changed; both AgentFeeds
profiles, other settings, file owner and mode are preserved.

This rollback keeps AgentFeeds but withdraws the three new presentations.
Reconcile their domain and customer impact before selecting it. The
[release record](../../artifacts/architecture-audit-2026-09-19/pilot-release-91.json)
binds the exact image, host backup, Worker rollback and retained attempts.
Never repeat a staging, deployment or edge operation whose outcome is unknown.

## Checks and remaining work

The exact source passed 3,949 self-tests, 1,003 workspace browser checks and
197 negative controls, 128 AgentFeeds browser checks, and the new campaign,
AgentFoundry and AgentAFK browser populations of 101, 110 and 86. Focused
checks passed 67 cases plus 26 follow-ups; conformance passed 32 gates and
documentation passed 58 checks. A clean installed wheel rendered all 858
selected responses. Regenerating all owned views produced identical bytes.
These local checks include fixtures; they are not live customer sign-ins.

AgentFeeds passed all 414 live checks with 348 API requests and no errors.
The existing ten-host matrix passed 456 assertions over 68 desktop/phone
views. The complete offering matrix passed 497 checks. The final pulse
passed fifty reads with no problems or slow reads; registration was available
and identity-provider health returned 200.

The final new-site run completed all six origins with 1,814 passing functional
assertions and no failed assertions. It made 1,656 API requests and 912 browser
requests. Its strict aggregate remains false for four Chrome DevTools body
accounting errors: one identity configuration response and one halftone-preview
response on each Foundry hostname. The 29,446,706 accounted bytes are partial.
Network-idle waits and complete measurement drains did not resolve those four
errors. No further retry was made.

Versions 2 and 3 of the checker buffer the actual same-origin Public Good GET
response unchanged to measure it. Their browser rendering and live metadata
checks do not establish native streaming behavior for that endpoint. AgentAFK
report parsing used a labelled fixture, not a claimed customer worker run.
No real sign-up, email, sign-in, checkout, model call or worker dispatch ran.

All three new-site attempts remain preserved: the first stopped after 876
passing assertions; the second and third completed all 1,814 but retained
secondary accounting errors. Offering attempt 1 retained a 104/105 navigation
timeout result; the second complete run passed. Existing-host attempt 1
retained 393/395 with transport failures; its complete successor passed.
The first pulse retained a health transport failure and a slow health read;
the second full pulse passed. No original report was rewritten.

The failed first conformance, source-scan, browser-startup and
AgentAFK phone-table checks remain in the private evidence beside their
passing successors. A later browser run passed with shorter temporary paths;
that observation does not establish the precise cause of the earlier Chrome
failure. No failed report was relabelled as a successful run.

The catalogue remains 1,560,856 distinct served files in 256,380 packages,
state revision 41. This release publishes no catalogue increment, changes no
price or subscription, and makes no model call. The guarded workflow's
existing grant reconciliation ran as part of the normal deployment.

The next product work is still useful maintained feeds, portable component
retrieval and revision, and bounded long-horizon execution. Token-savings
proof is not a launch gate. Website availability does not complete those
customer outcomes or the adaptive AgentAFK queue.

S-6.35.07 is live-qualified for the campaign's public funnel scope. S-6.35.06
stays building for real authenticated/acquisition outcomes and the remaining
instrumentation qualification. That state does not mean any selected website
is still waiting to launch.

The deployment source remains frozen. This record is prepared in a separate
detached editor; the workstation pointer names the active release session
and its private evidence. Preserve the shared checkout's private lineage
and all concurrent OpenCode and creative work.
