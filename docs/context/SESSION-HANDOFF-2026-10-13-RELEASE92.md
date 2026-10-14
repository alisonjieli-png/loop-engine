# AgentStudios public qualification and AgentBriefs local prototype

Kind: dated handoff, October 13, 2026. Follow
[AGENTS.md](../../AGENTS.md#commit-push-and-release-authority) for authority and
the [roadmap](../roadmap/roadmap.yaml) for current work. This record adds no
permission or competing work queue.

## Application and public verification state

Fly release 92 runs committed main
`b0e2c4cd7dd2b49c611abca478e78a7624b14704`, image
`sha256:aa73def135cddf3b27a45c39d8b37e0083b609ae922a2744cc8bb5e3449315ec`.
Exact CI `38493865609` passed twenty jobs. Guarded deployment `38494952598`
succeeded and the deployment gate is closed. Fly records the release's
creation at 01:21:13 UTC on October 14, still October 13 in the owner's
timezone.

Both `https://agentstudios.si` and `https://www.agentstudios.si` completed
ordinary public DNS and verified TLS readiness after the `.si` parent switched
to `dana.ns.cloudflare.com` and `nile.ns.cloudflare.com`. The one-shot
twenty-host public check completed all 20 origins and all 200 desktop and phone
views: 3,660 of 3,664 assertions passed, all 3,194 exact-source GET checks
passed, and all 20 identity-encoded HEAD checks passed.

Its strict aggregate remains false for two recorded reasons:
1. Four assertions on AgentStudios `/connect` checked `body.innerText()` for
   `https://agentstudios.si/mcp` and `https://www.agentstudios.si/mcp`, while
   `/connect` renders the own-domain MCP URL inside a `readonly` `<input>`
   element omitted by DOM `innerText`. A separate four-of-four read-only
   browser supplement verified `input[readonly]` `.inputValue()` on both
   origins at 1440 and 390 without rewriting the original report.
2. Sixteen Chrome DevTools `net::ERR_ABORTED` body-accounting events occurred
   on Foundry Public Good and AgentStudios streaming media routes.

The earlier eighteen-host attempt 1 report (164 of 200 views, 2,042 of 2,052
assertions, 1,702 of 1,702 exact GETs, nine compressed HEAD assumptions and
three Foundry `net::ERR_ABORTED` events while AgentStudios DNS was pending)
remains preserved alongside attempt 2 in the
[release 92 record](../../artifacts/architecture-audit-2026-09-19/pilot-release-92.json).

## AgentStudios scope and rollback

AgentStudios at `agentstudios.si` and `www.agentstudios.si` provides six
nonexclusive creative filters, public component examples, existing original
audio and video demonstrations, editable source downloads, Public Good search
and own-origin account and MCP setup over the shared backend. It keeps its own
navigation, assets, OAuth issuer and browser storage. Paid checkout is not
offered on this standalone site, and public availability does not establish
a hosted media editor, general generation service or completed customer
edit-and-reopen proof.

Cloudflare Worker `baltor-web-edge` serves export
`a031cd4dd6139851ac8bf4218d66ff1a03d6b0668efcf5a179eb5f237cf79a16` (`3,281`
public files, `89,430,691` bytes, deployment
`6231d769-3582-42c8-b648-1e9bc28e849a`, version
`4165d810-05a0-43a6-a41d-3bf70bcd29f7`) across the nine Baltor hosts. All ten
standalone `.si` hostnames serve HTTPS directly from Fly.

Rollback to image 91 (`sha256:34f939fa7cdceb200063a74ed5a01747d5e9a1f9bfd9eea3534d56e54f944a13`)
requires restoring `/data/host-before-agentstudios-sites-20261013.json` first,
with SHA-256 `ed23fffd71d4a48cf8c09f4cf239695fe7cf105278ef25be8a78d29e9a140cb6`.
The staged host digest is
`0acccc4af0e36252f3db9f2fb4ad3dad2a7c2edf66d73e22e2f22762bb5f5bc2`.
Do not replay completed Fly, Cloudflare, Namecheap or host-staging operations.

## AgentBriefs local review prototype and frontend integration map

The [website integration map](../architecture/BRAND-FRONTEND-BACKEND-INTEGRATION.md)
binds every selected website (`baltor.ai`, `agentfeeds.si`,
`getagentfoundry.si`, `agentafk.si`, `dontbeameatproxy.si`, `agentstudios.si`
and proposed `agentbriefs.si`) to its shared backend owners and remaining
acceptance gates.

The local-only AgentBriefs review frontend in
`design/prototypes/agentbriefs/` provides five interactive views (`Overview`,
`Company Profile`, `Opportunity Queue`, `Brief Detail` and `Decision Memory`),
explicitly synthetic company fixtures, threshold controls, escaped local notes
and memory-only reset controls. It makes zero outbound network requests,
refuses secret-shaped input, and includes no live upload, signup, OAuth or
payment flow.

An initial independent browser check passed 50 of 53 assertions and caught
three horizontal overflow cases on 80-character and 600-character unspaced
strings at 390px and 1440px. After repairing the CSS wrapping rules while
preserving the first failed report, the prototype passed all 124 producer
browser checks, all 53 independent browser checks, and the changed-scope
hardcoding audit with zero new high findings. `agentbriefs.si` remains a
selected name and local prototype, not a verified or launched production
domain.
