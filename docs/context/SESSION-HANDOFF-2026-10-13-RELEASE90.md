# AgentFeeds launch and product direction

Kind: dated handoff, October 13, 2026. Follow
[AGENTS.md](../../AGENTS.md#commit-push-and-release-authority) for authority and
the [roadmap](../roadmap/roadmap.yaml) for current work. This record adds no
permission or competing work queue.

## Live result

AgentFeeds is live at `https://agentfeeds.si` and `https://www.agentfeeds.si`.
Its independent design, navigation and onboarding use the existing backend,
account and entitlement boundaries. Fly release 90 runs committed main
`6787552603b020d7b13ecc7fe6f80c7a83c7aaa0`; exact CI `38444338553` and guarded
deployment `38446304065` passed and the deployment gate is closed.

The site has 19 curated collections, 60 distinct source references, JSON,
RSS and Markdown delivery, and downloadable per-agent reading profiles.
These are not continuously collected articles, saved hosted feeds or an
activated reading schedule. `getagentfoundry.si` and `agentafk.si` were
verified in the registrar account but remain parked and unchanged.
The owner's subsequent status question also identified `dontbeameatproxy.si`
as an AgentFeeds funnel. Fresh account and DNS reads confirmed it is owned
but still parked, with no deployed campaign. It had been omitted from the
launch inventory; S-6.35.07 now owns that separate acquisition page.

All 414 AgentFeeds live checks passed over ordinary public DNS and verified
TLS, including 212 exact public responses, 122 conditional reads, 44 desktop
and phone page views, independent profiles and actual browser downloads.
Existing Baltor checks passed 456 independent assertions across ten hosts,
the 497-check offering matrix, all 3,281 edge files and the final fifty-read
pulse. Original failures and passing continuations remain separate in the
[release record](../../artifacts/architecture-audit-2026-09-19/pilot-release-90.json).
Live sign-up/email/payment journeys and actual fresh-harness task outcomes
were not re-executed on the new domain.

## DNS and rollback

The owner explicitly authorized DNS management and setting Cloudflare
nameservers. One registrar change selected `dana.ns.cloudflare.com` and
`nile.ns.cloudflare.com`. The free active zone has six DNS-only records,
including the preserved Fly certificate/ownership validation. AgentFeeds
serves directly from Fly; the existing Baltor Worker routes are unchanged.
Registry publication and recursive parking caches delayed ordinary reachability
after the application was ready. Do not repeat the completed DNS operation.

The application image is `sha256:7dd98fd2a54ecfa1aa4392e8d242525ec0f4b1b71d803d5a91a3f3bcf76a7b29`.
Rollback image 89 is `sha256:4a5feebb1ed8067c0cd2d98ca6d038850672e5e2b866c5559cc2a60865521e28`.
Restore the exact `/data/host-before-agentfeeds-20261013.json` first: image 89
rejects the new `brand_profiles` field. The release record binds hashes and
the edge rollback. That rollback withdraws AgentFeeds serving, so reconcile
its domain impact. Never replay the completed host, deployment or edge operators.

## Current owner priorities

Keep agents current without a human relaying newsletters or social posts.
Supply ready-to-use files, skills, harness configuration, working components
and qualified cloud tools. Support long-horizon overnight work with inexpensive
models, cloud supervision or fully hosted execution as each profile is qualified.
Token savings remain a longer-term measurement goal, not a launch gate.

AgentAFK owns the requested customized, self-learning queue: graph-based
tasks, dependencies, priorities and outcome feedback. Extend the existing
managed records, solution graphs and scheduler. Qualify replaceable ranking
engines against fixed rules before adoption, preserve dismissal and customer
preferences, and keep readiness and effect authority separate from ranking.
The [owner decisions](../architecture/OWNER-DECISIONS.md) and S-6.24.03 own
this direction. No adaptive customer queue is claimed live.

## Review and continuation

The private 72-hour audit covers retained local Codex, Claude Code and
OpenCode session records for October 10 to October 13. It found no Claude
conversation timestamps in that window despite recently modified older files.
Deleted or remote-only sessions and every historical tool-output byte are not
claimed reviewed. The workstation pointer identifies its complete scope and
private evidence; do not publish private transcripts or unrelated research.

The [Feeds deep dive](../research/AGENT-FEEDS-DEEP-DIVE-2026-10-13.md) separates
source discovery, permitted acquisition, normalization, decisions, delivery,
correction, retrieval and queue admission. Next work connects the existing
knowledge radar to one maintained decision feed, then saved customer delivery;
source counts and keyword rankings are not acceptance of that work.

The shared checkout's private lineage and concurrent staged OpenCode work
remain untouched. Release source is frozen in a clean detached checkout;
post-release records use a separate detached editor. The catalogue remains
1,560,856 distinct served files in 256,380 packages. Retained unpublished
candidates, creative portability and the two other standalone sites remain
separate work, not hidden launch accomplishments.
