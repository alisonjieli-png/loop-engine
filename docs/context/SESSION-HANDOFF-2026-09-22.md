# Session handoff, September 22, 2026

Kind: handoff record. Written by Claude Code (Claude Opus 5.5) during the
consolidation run of session `81df4e9e`, so that another developer or another
harness, including Codex, can pick this work up without re-deriving it. It
records what is live and how it got there, what was lost and repaired, what is
in flight and what is open.

It is a dated snapshot, not new authority. The owner's standing rules for
committing, pushing, branching and releasing, and what still needs the owner,
are in the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md. The machine-readable work authority stays
[roadmap.yaml](../roadmap/roadmap.yaml). Do not start a second task list or
dashboard.

Times are UTC unless marked. The owner works in United States Eastern time,
four hours behind UTC, and the git author dates use that clock.

## Read these first, in this order

1. [AGENTS.md](../../AGENTS.md), including its
   [commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
   section.
2. This file, for where the work stands.
3. [The takeover checkpoint](TAKEOVER-CHECKPOINT-2026-09-20.md), for the
   working cycle, which has not changed. Its live-state table describes
   September 20.
4. [The current deployment section](../architecture/MVP-CLIENT-SERVER.md#current-deployment),
   the one statement of what runs and where.

## What is live right now

Checked at 18:44 UTC with read-only calls: the Fly release list, the Machine
status, and the public capabilities record and home page on every hostname.

| Fact | Value |
|---|---|
| Application | Fly application `baltor-pilot`, organization `baltor`, one Machine `83733ea7779068` in `iad`, one encrypted 1 GB volume at `/data` |
| Release | Fly release 12, created 17:55:29 UTC. The repository records it as pilot release 10 in [`pilot-release-10.json`](../../artifacts/architecture-audit-2026-09-19/pilot-release-10.json) |
| Image | `sha256:c75dbff17e53e9d9f1663bf030d0846c87ff5f572468b80a0b2980d6680312b6`; the Machine reports this digest and its health check passes |
| Source | Revision `15d3659` on GitHub `main`, whose continuous integration run 35731949431 passed |
| Built by | The guarded workflow [`fly-pilot.yml`](../../.github/workflows/fly-pilot.yml), run 35763623051, operation `deploy` |
| Rollback | Fly release 11, image `sha256:172782c0be740164b665c51502028a5c8c228d8ed1a73c8b3db89dfe6e5cd4d9`, built on a workstation from `81f341d` without a continuous integration run ([its record](../../artifacts/architecture-audit-2026-09-19/pilot-release-9.json)) |
| Hostnames | `baltor.ai`, `www.baltor.ai`, `app.baltor.ai`, `baltor-pilot.fly.dev`, `demo.baltor.ai`, `examples.baltor.ai`, `docs.baltor.ai`, `status.baltor.ai`: each answers 200 and returns the same capabilities record |
| Public copy | The owner's headline "Supercharge your developers and AI agents" and "Get started" first in the navigation are live |
| Accounts | Registration closed. Browser sign-in and personal client keys for accounts the operator provisions. Promotion redemption off |
| Payments | Live account, checkout, portal and webhook on; nobody charged as of the last record |
| Catalogue | 43 approved items registered; 34 offered to the pilot owner, 9 withheld for undeclared effect authority, no rejected item reachable |
| Model calls | None by the service |

## How release 12 was made

The live site had been showing the old headline because the owner's new copy
was on `main` and no release had been cut from it. Release 12 closed that gap
through the guarded path, in this order:

1. Continuous integration passed on `15d3659` (run 35731949431).
2. A volume snapshot was requested, `vs_pw1B1OwvpOjwizMBMYZVYPbb`. The daily
   snapshot of 00:59 UTC also exists.
3. The pilot environment's deployment setting `FLY_DEPLOY_ENABLED` was set to
   true at 17:53:54 UTC, the workflow was dispatched on `main` with operation
   `deploy`, the release completed at 17:55:29 UTC, and the setting went back
   to false at 17:55:47 UTC.
4. Three steps followed the deploy. They are the next three sections.
5. The live checks ran on every hostname: the browser website checks passed 72
   of 72 on `baltor.ai`, `www.baltor.ai` and `app.baltor.ai` and 71 of 72 on
   `baltor-pilot.fly.dev`, whose page shows its own hostname with the word
   pilot in it; the catalogue disclosure checks passed 6 of 6 on four
   hostnames; 14 of 14 interface checks passed; an official protocol client
   on `app.baltor.ai` and `baltor.ai` listed five tools, and a search returned
   seven references without loading a body. One usage record was added and no
   model was called.

The release carries everything merged to `main` from `81f341d` to `15d3659`:
the owner's public voice, the family serving policy with the harness family by
default, the starter catalogue reclassified as harness material with its 43
approvals carried across the re-anchor, the retirement of the parked
in-process suites from the self-test, and the repaired sign-up, recovery and
promotion routes, which the host configuration keeps switched off.

## A catalogue release needs its grants applied by hand

The guarded workflow does not run
`loop-engine service apply-grants --config /data/host.json`. After release 12
the library offered no item at all until that command ran on the Machine; it
then granted 43 items to the tenant `pilot-owner`, and
`tools/check_hosted_catalogue.py` showed 34 offered and 9 withheld. Until the
workflow does this itself, every release that changes the catalogue records the
command as a step after the deploy.

## Diagnostic keys last one day unless told otherwise

The keys of the diagnostic accounts `pilot-owner` and `pilot-boundary` default
to a life of 24 hours. The ones issued on September 21 expired at 12:15 UTC on
September 22, before the release, and every live check that used them answered
401. They were reissued for seven days:

```bash
tools/reissue_service_keys.py --origin https://baltor-pilot.fly.dev \
  --account pilot-owner --account pilot-boundary \
  --lifetime-seconds 604800 --confirm-reissue
```

The tool never prints a key. The new keys expire on 2026-09-29 at 18:02:01
UTC. Reissue them before then, or the live checks fail for a reason that is
not the release.

## The failed-attempt limit for each address is on

The limit on refused attempts from one client address was built but inactive in
production; a review of the live site found it. Releases built after
`e505eca` also refuse a public binding without it. The block
`http.request_limits` was added to `/data/host.json`, with the record type
`service_request_limits/v1`, the client address source `header` and the header
`Fly-Client-IP`:

- The file was backed up first, to
  `/data/host.json.before-request-limits-20260922T181740`.
- The replacement was validated with `ServiceRequestLimits.from_host` and
  `ServiceHttpConfiguration(**http)` before it replaced the original, and the
  Machine restarted at 18:17 UTC.
- The capabilities record now reports the limit active: 30 refused attempts in
  60 seconds.
- Proof that a forged address does not evade it: 32 requests with a wrong key,
  each carrying a different forged `Fly-Client-IP` and `X-Forwarded-For`,
  answered 401 thirty times and then 429 `failed_attempt_limit_reached`. The
  Fly proxy overwrites the header, so the count follows the real address.

The count lives in the memory of the one service process, so a restart resets
it. The capabilities record says so in its field `state`.

## Merges that lost work without a conflict

Between 13:30 and 14:21 UTC an OpenCode session running Kimi K3 merged twelve
branches into local `main`. It pushed nothing. It resolved most conflicts to
`main`'s side and ran `git reset --hard HEAD` in the shared checkout at 13:38
UTC. Service smoke and the conformance gates still passed on the merged tree
(339 of 339 at `e505eca`), so the checks alone did not show what follows. A
line-survival check, which looks up every line a branch added in the merged
tree, found content dropped with no conflict reported:

| Merge | Branch | What did not survive |
|---|---|---|
| `0e94603` | `wave9/subdomain-surfaces` | `src/loop_engine/core/service_runtime/web_routes.py`, the surface for each hostname, is absent, with smaller losses in `http.py` and `http_checks.py` |
| `0dc762c` | `wave9/model-guidance` | The same file, which this branch also added for the model guidance pages |
| `8892677` | `wave5/operator-observability` | 166 lines in `http.py` and `http_entrypoint.py`, including the wiring of the version 2 health and readiness report |
| `107426b` | `wave8/overnight-pages` | Part of `web_pages.py` and of the website content guide |
| `a1398ce` | `wave4/promotion-codes` | Lines in `promotion_checks.py`, `runtime.py`, the service runtime guide and the promotion codes guide |

The merge `e073d01` of `release/catalogue-round-two` also differs from its
branch in `reviews.json`, the host manifest and the anchor line of each
released body. The anchor lines are the expected re-anchor. Check the rest
line by line before trusting the round-two approvals on `main`.

The merge of `wave5/security-and-tenancy` stopped halfway when the session hit
its usage limit. It was finished as `e505eca`. That repair restored what the
automatic merge had dropped: the definitions of the new constants and of
`selected_origin` in `http.py`, and the worker share argument of account
activation. Two new checks hold the argument. With it removed, the first check
fails, as a mutant run showed (338 of 339). The eight literals those merges
brought in were registered with reasons in `97e805f`.

The other losses are being restored in the consolidation run described below.
That restoration was not finished or verified when this record was written.
The merge `1d796f4` of `wave6/polish` also added, on its own, an exclusion to
the documentation link gate that neither parent had: vendored harness copies
under `embodiments/<name>/upstream` and `runtime`. It carries a written reason.
A reviewer should confirm it rather than assume it.

## Safety archive and the restored stash

Before any consolidation step, at 17:27 UTC, everything was saved in
`/home/username/loop-engine-archive-2026-09-22/`, outside the checkout:

- `all-refs.bundle`, a bundle of every reference, 203 MB;
- `refs-before-consolidation.txt`, `stash-list.txt` and
  `worktree-list-porcelain.txt`;
- the unfinished security merge as `main-inprogress-merge-staged.patch` and
  `main-inprogress-merge-unstaged.patch`, with its merge head and message;
- a patch of the uncommitted work of every worktree, in `worktrees/`.

The same OpenCode session dropped the stash that holds the `showcase-v4` work
at 14:46 UTC, calling it another repository's old work, which was false. It was
restored from its object at 17:18 UTC without touching any working tree. It is
`stash@{0}: On codex/showcase-v4: showcase-v4 parked work from Aug 2026
worktree`.

## The consolidation in progress

At 18:30 UTC local `main` was `c96b546`, 37 commits ahead of GitHub `main`
(`15d3659`), none of them pushed or judged by continuous integration. 22 local
branches are not merged into `main`, out of 126, and 57 worktrees exist,
counting the main checkout. GitHub
holds three branches, not two: `main`, `checkpoint/full-capability-2026-09-21`
at `a3bd0f1`, and `release/catalogue-live`, which local `main` has merged.

The owner asked at 13:12 UTC that all work be merged into `main` and that only
the checkpoint survive as a backup branch. The consolidation follows that:

- Agents work in detached worktrees under `/home/username/.le-consolidation/`
  and `/home/username/.le-stabilize/`. A detached worktree makes no branch.
- Each agent commits there with its checks named in the message and does not
  push. The session that runs the workflow verifies the line, moves `main`
  forward to it, pushes, and releases through the guarded workflow.
- The payment branch repairs come in as a squash, because four payment
  branches carry key-shaped fixtures in their history. The repaired payment
  customer path from `pay/billing-customer` was being brought in at `34a6d04`.
- The owner's rules are gathered into one section of AGENTS.md, with a check
  in `tools/test_context_routes.py` that every entry route links it and none
  contradicts it. That change is the one this record belongs to.

When the line is pushed and released, the next release needs the steps above:
the grants if the catalogue changed, keys that have not expired, and the live
checks on every hostname.

## The engine direction

The owner, September 21 at 23:14 Eastern: "every functional unit should be
wrapped so that we can replace the unit engine without impacting functional
unit to unit edge communication". September 22 at 17:36 UTC: "not only should
we have swap points, but we should have "engines" and different types of
"engines" for each functional component so that the runtime can select the
most efficient engine". At 18:19 UTC the owner added that every build should
start with a search for existing "projects, repos, github, designs, or papers".
They are rule 6 of the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md.

Where the code stands, from a read-only review of the source on September 22:
engines already sit behind small typed protocols, among them
`ExternalHarnessAdapter`, `ProviderAdapter`, `CatalogStore`,
`WorkspaceBackend`, `McpTransport`, `RetrievalSearchBackend` and
`SimilarityCandidateSource`. The typed executor interface that phase 2 of
[the harness-first decision](../architecture/ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md)
depends on does not exist yet, so no executable step is delegated through a
harness by a typed seam. An engine stays an adapter a Loop uses, never a
second runtime type.

## Owner direction recorded today

| Time | Words |
|---|---|
| 13:12 UTC | "all of our work should be merged into main!" and "Only the snapshot should survive as a backup branch" |
| 13:30 UTC | "Use your best judgement, document it, etc" |
| 17:25 UTC | "stop creating too many confusing branches, get all improvements live fully working" |
| 17:33 to 17:46 UTC | One artifact that explains everything, engines for each functional component, a clean-up of every README, a tracking file and page, readiness for a Y Combinator application |
| 17:52 UTC | "make sure we are deploying and updating fly.io", "full automated QA of all aspects" on the real website |
| 18:19 UTC | Swappable components and a search for existing work, with the 17:52 words repeated |
| 18:25 UTC | "push improvements into production/main branch", "centralize, consolidate, rules, authorities", "you can more aggressively push numerous fixes and adjustments at once to main" |

## What still needs the owner

What the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section lists, and steps that only the owner's own accounts can take. Today
that means:

- the privacy notice and the terms, which are [drafts](../legal/README.md)
  until the owner publishes them;
- closing self-registration at the identity provider, which failed on
  September 21 with 403 because the management grant lacks the scope. Only the
  owner's account can grant it. This was recorded then and not rechecked.

## Open problems

1. Local `main` is not pushed, and the losses in the table above are not all
   restored. Nothing on it is live until it is pushed, judged by continuous
   integration and released.
2. `release/catalogue-live` exists on GitHub beside the two permitted
   branches. Local `main` has merged it.
3. `tools/check_component_guides.py` reported 8 findings at `97e805f`:
   `docs/components/intelligence-layers/SEARCH-QUALITY.md` was not in the
   guide map and named seven identifiers the package does not define. Commit
   `7c3ec6d` on local `main` registers the guide; an export of `4249eca`
   reports 0 findings. On that same revision the roadmap holds 19 delivery
   packages while `tools/test_architecture_audit.py` still expects 17.
4. The host configuration still names `baltor-pilot.fly.dev` as the canonical
   origin, and the four newer hostnames serve the main site.
5. The guarded workflow does not apply grants after a catalogue change.
6. The diagnostic keys expire on September 29 at 18:02 UTC.
7. The failed-attempt count resets when the one service process restarts.
8. The server-owned payment customer path on `main` and in production has three
   known high-severity defects, as the session review of September 22 records;
   they were not rechecked here. The repairs are on `pay/billing-customer`,
   being brought in.
9. The roadmap's `checkpoint` and `developer_handoff` fields and the single
   development HTML still name documents of September 20, and
   `tools/architecture_report/hosting.json` still describes release 8. The root
   README still describes accounts as unavailable.
10. No harness has been observed completing a checked task with served
    material, and the three launch benefits have no evidence yet.
