# Session handoff, September 25, 2026

Kind: dated handoff. It follows the
[September 24 session handoff](SESSION-HANDOFF-2026-09-24.md), whose text stays
as it was. The [roadmap](../roadmap/roadmap.yaml) remains the task authority,
and the owner's standing rules are in the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md.

## What the owner asked for on September 25

- "put some on pause and do step by step actions and improvements, and
  deployments because we keep running out of our 5 hours limit and then
  having to restart many things again", and the owner was frustrated that the
  interface improvements were still not live.
- "For releases you may want to adjust the logic, to be more flexible,
  reasonable, and human oriented tests rather than something too strict".
- "You should have it do retries on ollama and tactical daily, not a
  permanent block".
- Earlier the same night: improve the pipeline so it generates more harness
  working directory files, now that Tactical is back.

## What is live

| Release | When (UTC) | What a person sees | Record |
|---|---|---|---|
| Fly release 26 | 08:46 | Mostly work behind the site: the component standard, decision stations, review engines with the two-family quorum, the licensed import, library tiers. The homepage filler line is gone. | [pilot-release-26.json](../../artifacts/architecture-audit-2026-09-19/pilot-release-26.json) |
| Host change on release 26 | 09:04 | Every customer account follows the catalogue release, so a published catalogue release reaches all customers without a redeploy. Isolation passed 19 of 19. | [release 27 evidence](../../artifacts/release-27-2026-09-25/README.md) |
| Fly release 27 | 10:24 | The new hero with one step's working directory and three demonstrations; each hostname's own page; demonstration, status, examples, case study and /for pages; retired phrases gone; eight persona fixes; the deck; the protocol server directory at /directory. | [pilot-release-27.json](../../artifacts/architecture-audit-2026-09-19/pilot-release-27.json) |

Release 27 was decided by the new check of what a person sees: no problem on
41 pages at desktop and phone width, in light and dark, on 8 hostnames and 83
links. The customer's search and download passed 8 of 8 and the service 19 of
19. The detailed wording rules passed 215 of 215 as advice.

## How releases work now

```text
Release
├── Lines push green slices to main at any time; there is no freeze file
├── The deploy workflow takes -f revision=<sha>: any main revision whose CI passed
│   └── It refuses a revision that left main or is not on it yet
├── Two checks decide whether a release stays
│   ├── tools/check_live_site_for_people.mjs: every page opens with its heading,
│   │   no script error, no sideways scroll on a phone, links work, both themes
│   └── the customer's search and download, and the service isolation check
└── Advice only: the detailed wording rules and the address sweep
```

The live check script is `/home/username/baltor-private/tools/live_checks.sh`,
outside the repository. Run every test suite with `TMPDIR` under
`$HOME/.le-ci-tmp`. `/tmp` is over its quota, and on September 25 it turned 37
of 45 release 26 failures into false errors.

## What stopped, and why

Around 06:00 Eastern every subagent and workflow agent stopped with "You've
hit your weekly limit · resets Oct 1, 1pm (America/New_York)". Resume nothing
before then. The registry
`/home/username/baltor-private/wrap-up/registry.json` records where each line
stopped and marks it paused. The two recovery and research crons are off. The
hourly release train still runs and stops after one line when main has not
moved.

## Next, in order

1. **Release 28.** The tree `/home/username/.le-release28-20260925` holds:
   - persona fix 9 (62163b00): every connection entry shows the address the
     service publishes;
   - the overnight page now says the per-step harness is "built to" run;
   - a plain answer to the team account question.

   Still to add:
   - the models and can-I-run directory: its line was mid-rebase onto main
     when it stopped;
   - the stack starters, which rebase after the models line;
   - removal of the pricing card's "Available now" badge, a status tag the
     owner retired.
2. **The first Community catalogue release.** The bundle is built:
   - `~/baltor-bundles/community-release-1`, digest `4e0484b7…`, 93 items:
     42 Verified and 51 Community;
   - the phone item is withdrawn.

   Blocker: the HTTP path never offers Community items. The account's
   library setting is not wired into provisioning and retrieval requests, and
   the Community items declare reading files, which clients do not grant
   today. The review line was writing that change in
   `/home/username/.le-release-community-20260925` when it stopped. Publish
   only after that code is live, then check retrieval as a customer.
3. **The generation pipeline workflow.** Its script now includes the owner's
   daily retry rule for the Ollama and Tactical lanes. All four stages
   stopped at the limit; resume them with the same script.
4. **Held lines.** The engine selector and the staff tools were held out of
   release 26 (37 new high hardcoding findings, and the staff tools' change
   to `http_entrypoint.py` broke the pinned starter sources). They go in a
   release of their own.
5. **Moving `http.public_base_url` to `https://baltor.ai`.** The persona line's
   runbook is at `/home/username/.le-persona-fixes-tmp/runbook-public-base-url.md`.
   It needs the identity provider's redirect settings first. Engineering's
   access to those settings is refused, so this waits for the owner's
   optional provider sign-in.

## Records from the night

- 250-persona review: 37 of 41 agents finished. The pack is at
  `/home/username/baltor-private/review-2026-09-24/REVIEW-PACK.md`.
  Synthesis and the YC and go-to-market implementation stages did not run.
- Four research records reached main: harness engineering sources (steps
  S-6.165 to S-6.176), the agent stack mapping, community and chat
  distribution, and publishing into Baltor.
- Affiliate research: 145 services checked, 30 pay cash. It waits in
  `/home/username/.le-affiliate-research-20260924` (ea56a5c9, 35f6bbb9).
- All five of the owner's media repositories now carry the MIT licence.
- The owner action pages were refreshed. Six are marked resolved; the others
  ask only for what the owner alone can do: identity, tax and payout details,
  personal sign-ins, posts, hardware and submissions.
