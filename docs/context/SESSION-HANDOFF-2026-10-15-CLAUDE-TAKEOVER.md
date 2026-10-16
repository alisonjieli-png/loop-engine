# Claude takeover, monitor repairs and history review

Kind: dated handoff, October 15, 2026. Follow
[AGENTS.md](../../AGENTS.md#commit-push-and-release-authority) for authority and
the [roadmap](../roadmap/roadmap.yaml) for current work. This record adds no
permission or competing work queue. Application release 93 remains live; no
application deployment, catalogue publication or price change was started.

## Why this session took over

Gemini Antigravity and the Gemini 4 models ran out of quota. The owner made
Claude responsible for continuing adjustments, deployments, edits, end-to-end
testing, feeds and harness component files. At the start, no Codex session had
written for four hours; the Codex takeover record stays authoritative for
release 93. Separate sessions keep working on the social_videos project, which
this session did not edit. The shared checkout stays dirty and far behind
public `main`; it was neither reset nor pushed.

## Changes on `main`

| Commit | Change | Checks |
| --- | --- | --- |
| `54f6f4b9` | The live pulse now requires the release 93 permanent redirect from `www.baltor.ai` to the same apex path for the public pages the service forwards, and still requires Get started and the API to answer on the `www` origin. | Every scheduled pulse had failed since release 93 on exactly those two pages. Four known-wrong controls fail as they should, a test holds the forwarded list to the service rule, CI passed and a dispatched pulse passed all 50 rows. |
| `20e05aea` | The temp reaper keeps Python environments, folders marked `.keep-in-place` and folders a running process works in. Coldness uses the newest top-level entry, and `REAPER_DRY_RUN=1` reports without changing anything. | It could move the gate environment to the external disk whenever the root disk was at least 92 percent full. A dry run kept `venv312` protected. CI passed. Cron now runs the copy in the auto-updated main checkout. |
| `583337c2` | Research watch sends the workflow's own read-only token to `api.github.com` only, reports a spent limit as `rate_limited`, and follows three moved sources. | 13 of 50 sources had failed: ten GitHub rate limits, two moved pages and one domain that no longer resolves. A dispatched run read all 50 sources with authenticated GitHub requests. |

## Live change outside the release path

Antigravity had deployed an internal systems portal at `systems.baltor.ai` on
October 14 as its own Cloudflare Worker, outside the guarded workflow and
without access control. It served generated projections and pass labels. The
owner had asked for an internal reference without non-live systems. This
session uploaded one new version of the same Worker that requires HTTP sign-in
on every path, after an intent record and before any other change. Readback
passed 27 of 27 checks: requests without sign-in or with a wrong password
answer 401, and the stored credential answers 200. The earlier version stays
available for rollback. Deleting the Worker, its route or its DNS record needs
the owner. S-6.35.11 still owns the rebuild as a staff-only page of verified
live facts, recorded in this repository.

## Preserved work

The shared checkout's unique work was saved without changing the checkout: a
bundle of its three local-only commits, a patch of 347 staged paths, an archive
of the untracked files, its status and digests. The staged research is
attributed to OpenCode sessions of October 6 to 7 and 12 to 13 and has not been
reviewed for adoption.

## History review and owner-intent measurement

A private review read every Loop Engine session of the Ollama-driven OpenCode
lane (August 26 to October 13), the Codex lane (September 4 to October 15) and
the Antigravity lane (October 13 to 15), and rechecked 30 consequential claims
against this repository and the live sites. A separate measurement collected
the owner's prompts from all four harness histories, separated pasted material
from the owner's own words, split prompts into asks and labelled them into
directions, with desire weighted by emphasis and recency and completion taken
from the reviewers' judgments. Raw prompts, digests and reports stay private.
The findings that change engineering practice:

- A producer's "verified" is a claim. Unsupported claims and invented numbers
  were the largest problem class; independent review caught the large ones.
- Silence drove repeated prompts in every lane. Report briefly after each
  prompt and each release.
- Count only served, admitted files, and name the stage of every count.
- Save a list or bundle before any deletion of files or provider resources,
  not only before git resets.

## Open work and dates

- Public Good access grants expire on October 31 and November 1 UTC. Renew
  eligible unchanged versions through the guarded policy path before then.
- A private model endpoint's host appears in public files, and three clients
  disable TLS verification for it. Remove the host from current files and
  restore verification with the pinned certificate; published history stays.
- 341,902 reconciled catalogue files are unpublished; the live count is
  1,560,856.
- The twenty-host browser matrix still records 21 canceled metadata fetches
  (S-6.35.06, S-6.35.08).
- The deployment allowance record says 50 United States dollars a month; the
  owner's October 5 words in [Cloudflare hosting](../architecture/CLOUDFLARE-HOSTING-2026-10-05.md)
  allow up to 100. Spending authority stays with the owner, so 50 stands until
  the owner records the change in AGENTS.md.
