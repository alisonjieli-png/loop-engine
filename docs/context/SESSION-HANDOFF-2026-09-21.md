# Session handoff, September 21, 2026

Kind: handoff record. Written by Claude Code so that another developer or
another harness, including Codex Astra, can pick this work up without
re-deriving it. It records what is true, what is running, what is owed and
what is deliberately not done.

It is a dated snapshot, not new authority. The machine-readable work
authority stays [roadmap.yaml](../roadmap/roadmap.yaml). The owner's
standing direction stays [CLAUDE.md](../../CLAUDE.md) and
[AGENTS.md](../../AGENTS.md). Do not start a second task list or dashboard;
add to this file and to the roadmap.

## Read these first, in this order

1. [CLAUDE.md](../../CLAUDE.md) for the owner's authority and its limits.
2. [AGENTS.md](../../AGENTS.md) for the repository rules.
3. This file for where the work stands.
4. [The takeover checkpoint](TAKEOVER-CHECKPOINT-2026-09-20.md) for the
   working cycle, which has not changed.

## What is live right now

The deployed service is the Fly application `baltor-pilot` in the `iad`
region, one machine, one encrypted volume of 1 GB at `/data`.

| Fact | Value |
|---|---|
| Hostnames answering | `app.baltor.ai`, `baltor.ai`, `www.baltor.ai`, `baltor-pilot.fly.dev` |
| Subdomains added today, certificates issuing | `demo.baltor.ai`, `examples.baltor.ai`, `docs.baltor.ai` |
| Items served | 34 with no declared effect authority, 43 when the caller declares `reads_fs`, `writes_fs`, `network` and `spawns_process` |
| Account creation | Closed. The capabilities record reports `registration_available` false |
| Payments | Live account `acct_1UHZ972IF9bCskLc`, checkout and portal proven, nobody charged |
| Protocol | Model Context Protocol `2025-11-25` over Streamable HTTP, five tools |

Observed evidence, each with its own dated record under `docs/evidence/`:

- [The paid path](../evidence/live-service-path-2026-09-21.md): discover,
  list, manifest, download and usage all answered 200; the downloaded body's
  digest equalled the digest its manifest named; one download recorded
  exactly one unit.
- [The connection journey](../evidence/customer-connection-journey-2026-09-21.md):
  the Claude Code recipe fetched from the live site, followed to the letter,
  `claude mcp list` reporting the server and the one remaining step.
- [One real local model call](../evidence/local-model-call-2026-09-21.md):
  `qwen2.5-coder:7b` over a real socket, 87.28 seconds cold and 0.71 warm.

## The catalogue, and the one number that matters

123 candidate items exist. Two independent review rounds have judged every
one of them, three reviewers each, an item approved only when every reviewer
approves it.

| Round | Items | Approved | Rejected |
|---|---:|---:|---:|
| One | 49 | 43 | 6 |
| Two | 74 | 71 | 3 |
| Total | 123 | 114 | 9 |

**43 are deployed. 71 are approved and not yet deployed.** Closing that gap
is the single highest-value piece of work outstanding, and a workflow is
running for it on the branches `release/carry-approvals` and
`release/all-approved`.

## The defect that blocks a green build, and why it is not simply fixed

Continuous integration is red on `main`. Three checks fail:
`test_the_committed_catalogue_passes_every_rule`,
`test_the_pinned_digests_are_read_from_the_tree_and_not_from_the_record` and
`test_the_anchor_tool_refuses_a_revision_whose_cited_bytes_differ`.

The cause is correct behaviour, not a flake. Each catalogue body cites the
source files it was written against, pinned at a revision. An unrelated
change edited `src/loop_engine/core/service_runtime/http_entrypoint.py`, so
the pin at revision `0cf19eb` no longer names the bytes the catalogue uses.

Running the anchor tool with `--write` fixes those three checks. It also
rewrites one line in all 123 bodies, the trailing
`Compiled from revision <short>` line, which changes every body's digest.
Every row of `reviews.json` binds its approval to a `body_digest`. So the
obvious fix silently invalidates 114 independent approvals in order to
change a provenance citation.

Both easy answers are wrong. Leaving the build red is wrong. Throwing away
114 reviews because a citation line changed is also wrong, because no
reviewer's judgement was about that line.

**The fix being built:** an approval carries across a re-anchor only when the
sole difference between the approved bytes and the new bytes is that anchor
line, and only when that line differs only in the revision it names. Any
other difference anywhere returns the item to candidate state with a
recorded reason. A carried approval is recorded as carried, not as freshly
reviewed, keeping the original reviewers and the original digest beside the
new one.

If you inherit this and the workflow did not finish, that is the design to
build. Do not re-anchor without carrying, and do not weaken the three
checks.

## Work in flight

Roughly 30 agents were running when this was written, across these tracks.
Each works in its own git worktree on its own branch and commits there;
none of them push.

| Branch | What it is | State when written |
|---|---|---|
| `release/carry-approvals`, `release/all-approved` | Carry approvals across the re-anchor, then deploy every approved item | Running. Highest value |
| `wave4/public-voice` | The owner's headline, the phrase "harness and agent optimized operation", removing "pilot" and "beta" from every page | Running |
| `wave4/promotion-codes` | Paid access by redeeming a code, without Stripe | Build done |
| `wave8/overnight-pages` | Dedicated pages for solving overnight with a local model and with Ollama | Running |
| `wave5/search-quality` | Name the search's matching mode and measure what it returns | Build done |
| `wave5/security-and-tenancy` | Adversarial tenancy and authority attack | Running |
| `wave5/operator-observability` | Find out what went wrong in production without guessing | Running |
| `wave5/component-documentation` | Make component guides match the source | Build done |
| `wave6/harness-component-intelligence` | Skills, plugins and protocol servers as Code Intelligence | Build done |
| `wave6/documentation-content` | Serve the Documentation view from one versioned index | Build done |
| `wave6/polish` | Say what happened and what to do next in every refusal | Build done |
| `wave2/waitlist` | Email waiting list, operator review, invitation with a discount | Build done |
| `wave2/campaign-pages`, `pay/web-campaigns` | Dedicated landing pages for advertising | Build done |
| `wave2/intelligence-organization` | Where intelligence files live and how a new one is added | Build done |
| `wave7/occupation-tables`, `wave7/occupation-axis` | Load the real occupation tables; make role, company, country and language a search axis | Running |
| `pay/web-browse` | Browsing the intelligence layers for signed-in users | Running |
| `wave3/green-ci` | Make continuous integration green and keep it that way | Running |

Branches whose work is already on `main` but which still carry merge
commits: `pay/accounts`, `pay/billing-customer`, `pay/billing-setup`,
`pay/container-journey`, `pay/web-message`. Four of those carry revisions
whose test fixtures wrote whole payment keys, so they were squash merged and
must stay squash merged. Merging them normally reintroduces blobs the
repository host rejects.

## Owner direction recorded today

Added to the rules today, with the owner's own words:

- **Puffery is allowed.** Evaluative and aspirational marketing words need
  no evidence. A number nobody measured, a comparison to a named product, a
  guarantee, an invented customer, or a capability the product lacks are
  statements of fact and need evidence. The test is in the
  [product style guide](../guides/product-style-guide.md).
- **The public positioning phrase is "harness and agent optimized
  operation".** An agent retired it as jargon; that was wrong, because the
  buyer is a developer who uses the word. It goes back on the homepage,
  written out in full.
- **Ship what is approved.** Approved and undeployed is not shipped.
- **Never tell the owner to rotate, revoke or re-create a credential.**

## Open defects worth an inheritor's attention

1. **The search has no relevance floor.** It returns the best ranked items
   whatever their score, and marks no hit as a poor match, so it answers a
   question it has no material for. Measured and recorded as gap three in
   [the layer coverage record](../../artifacts/intelligence-layer-coverage-2026-09-21/README.md).
   `wave5/search-quality` is on it.
2. **Two of the four intelligence layers ship empty.** Context Intelligence
   441 items, Code Intelligence 81, Runtime History and Solution
   Intelligence 0, User Feedback Intelligence 0 on a fresh installation. The
   search reports both as unqueried, so nothing is hidden; what is missing
   is material.
3. **An unsupported protocol version is refused without naming the versions
   that work.** The refusal is typed and correct and does not silently
   downgrade. It just does not tell the client what to do next.
4. **The service is one machine with one attached volume.** It cannot
   survive the loss of its host. A volume attaches to one machine and the
   durable store lives on it, so a second machine is not a configuration
   change.
5. **`http.py` is 814 lines against an 800 line convention.** No gate
   enforces it. The split, moving `WEB_ASSETS` and the static branch into a
   new module, was deferred because three agents held that file.

## What the owner still has to do personally

Only what engineering genuinely cannot. As of today:

- Two bracketed placeholders in the pitch deck: their background and the
  moment they hit this problem, and their contact details.
- Nothing else is waiting on them. Account creation, payments, the domain
  and the providers are all engineering work and are either done or in
  flight.

## How to continue

Follow the cycle in [the takeover checkpoint](TAKEOVER-CHECKPOINT-2026-09-20.md).
In short: write the check for the known-wrong case before the repair, record
state in the roadmap, save every report under a new name, release only from
a committed revision whose checks passed, and deploy by image digest keeping
the previous image for rollback.

Two practical notes from today. The machine runs about 16 cores and was at a
load average near 45 with thirty agents; commands are slow and slowness is
not failure. The root disk was at 90 percent, and agent worktrees under
`.claude/worktrees/` are worth pruning when their workflow has finished.
