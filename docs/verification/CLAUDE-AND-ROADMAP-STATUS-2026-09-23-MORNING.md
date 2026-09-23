# Claude Code and roadmap status, September 23 morning

Kind: dated, read-only verification and recommendations for the existing
roadmap. This is not another task list or a release approval. The task
authority remains [roadmap.yaml](../roadmap/roadmap.yaml). Commit, push and
release decisions follow [AGENTS.md](../../AGENTS.md#commit-push-and-release-authority).

Observed at 12:46 UTC, September 23, 2026, with a final source inspection
afterwards. The source reviewed was the clean detached checkout at
`abcad4f8ce346e7d0759ccad703e0111574148a6`, which the GitHub main reference
also named. The shared checkout at `/home/username/loop-engine` was at
`385c6471e697a8665dd1b905be47fe9765e0fc4f`, 92 reachable commits behind
that revision. Reading its files as current source would give the wrong
answer about what Claude has shipped.

## What has reached customers

Claude has released substantial work since the earlier Codex audit. Fly
release 20 runs `f7c89465da6fec28c69afde3ddb2f6423068632a`. Current main adds
release records, the branch triage and roadmap updates; its difference from
the deployed revision contains no product source changes.

| Area | Observed evidence | Remaining qualification |
|---|---|---|
| Homepage and signed-in interface | Release 18 shipped the redesign with a full-width demonstration below the introduction and a phone invitation action in the first viewport. Release 20 adds Account and Sign out, an item usage table, and the address-splitting example. The release record reports 81 of 81 website checks on the three primary hostnames. | First-time visitor and complete native customer task journeys; final logo. The Fly hostname has the recorded 80 of 81 result. |
| Protocol | Both `2025-11-25` and `2026-07-28` are served, with the official protocol client exercised on live HTTPS. | Native client compatibility is a separate matrix; protocol library checks do not establish every named harness. |
| Catalogue publishing | Releases can reach the running service without an image deployment. The second catalogue release, `c824a1d2e222`, contains 43 items. | The releases so far change catalogue anchors, not library size. Multi-file admission, native materialization and customer settings remain separate gates. |
| Access isolation | Release 19 repaired the first catalogue-follow operation, which had granted all items to five accounts that should not receive them. Those accounts returned to empty fixed grants. | Preserve the failed activation evidence and include isolation on every later library release. |
| Customer access and payments | Invited accounts have sign-in and personal keys. Waiting list is enabled. Checkout and portal availability returned in release 16; earlier live sessions were proved without charging anyone. Public registration remains closed. | A complete eligible-customer onboarding and subscription lifecycle is not established by availability flags. Terms still await owner approval. |
| Scale | Store-backed catalogue releases, withdrawals, attributes and following grants are implemented. | The saved 100,000-item experiment still exceeds the current machine's practical memory, disk and swap-time limits. It is not evidence for a million-package service. |

Sources: [current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment),
[release 20 record](../../artifacts/architecture-audit-2026-09-19/pilot-release-18.json),
[release 20 catalogue check](../../artifacts/architecture-audit-2026-09-19/hosted-release20-catalogue.json),
and [catalogue activation record](../../artifacts/architecture-audit-2026-09-19/catalogue-release-activation-1.json).
This review read those saved live records; the parallel website audit makes
the new browser observations. It did not log in or alter a production record.

GitHub was read again during this audit:

- [CI run 35851011364](https://github.com/alisonjieli-png/loop-engine/actions/runs/35851011364)
  succeeded for `abcad4f8`.
- [CI run 35848892844](https://github.com/alisonjieli-png/loop-engine/actions/runs/35848892844)
  succeeded for the deployed `f7c89465`.
- [Fly workflow 35850578119](https://github.com/alisonjieli-png/loop-engine/actions/runs/35850578119)
  succeeded for that exact deployed revision. The pilot environment's
  `FLY_DEPLOY_ENABLED` value was `false`, last updated at 10:47:19 UTC.
- The later successful workflow called **Publish worker image** is not
  another Baltor website deployment. These are different service images.
- The failed CI run on `61d8b317` was followed by the explicit bare-URL
  Markdown repair in `abcad4f8` and its successful CI run. The failed run
  should remain in the history.

## Two findings to resolve before expanding approvals

### The phone item remains offered after the adverse measurement

The [data cleanup report](../../case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md)
finds that `normalize_phone_numbers` reduced the cheap model's score on the
declared synthetic phone population: 0.842 in each of three repetitions,
against 1.000, 0.974 and 1.000 without the material. It identifies missing
rules for trunk prefixes, international dialing prefixes and invalid lengths.

Release 20 correctly removed this item from the homepage demonstration.
However, the release 20 live catalogue record still returns it in search,
and the packaged manifest still approves it for `pilot-owner` with body
access. The current procedure is unchanged from the measured one. A diff of
the frozen body at `f90babc` against current main changes only this footer:
`Compiled from revision d893bba` becomes `Compiled from revision 565e133`.
The frozen body digest is
`b451b3663599c0971185feb21c5dd74e84145da5fad99580cfdd05067c209b63`;
the current digest is
`8f0ab269db267078c2f9b3f4671d8785a9e8a3dcce0fbdac578f6b2dacf255ef`.

Recommendation for S-6.45, S-6.47 and S-6.62: request independent adjudication
of a withdrawal or narrowed replacement, bind the decision to current bytes,
and use the existing durable withdrawal and catalogue release mechanism.
Test that pointer rollback cannot restore the withdrawn version. Keep the
measured failure as a regression case. This is evidence about a particular
model, harness and population; it does not establish universal harm.

### Earlier approvals conflict with the newer independent panel

The [branch triage](BRANCH-CONTENT-TRIAGE-2026-09-23.md) found a staged
second review round that could increase the starter approved set from 43 to
114 after review of the record and exact-byte carry. That is a real recovery
opportunity, but newer evidence must be reconciled before publication.

The unmerged library panel at `2424c34a` reviewed 30 previously undecided
starter items. It rejected all 30 under its three-family policy. Of those
30 identities, **29 are approved in the older staged round-two record** and
one is rejected there. For all 29, comparing the two actual bodies shows no
change except the explicit closing catalogue anchor, `0cf19eb` versus
`f29bddc`. The digests are different; this comparison does not carry an
approval or establish an exact-byte rejection of the current release.

The panel's substantive findings include an idempotency procedure that does
not prevent duplicate external effects, a rollback claim that exceeds its
schema-change procedure, and a process-local lock presented as sufficient
for multiple service copies. Reviewers also disagree on the effects rule.
These findings require adjudication rather than choosing the more favorable
review record.

Local evidence, not yet on main:

- Newer panel: `/home/username/.le-library/ls2/examples/29_intelligence_service/starter-catalogue/reviews-panel-2026-09-22.json`,
  SHA-256 `22f3fb23c41d93cca99ec76c648e9e6d3cb24cf2d201c71aa56670d45f2dab31`.
- Earlier staged round two:
  `/home/username/loop-engine/.claude/worktrees/wf_2c5a17d0-bee-4/examples/29_intelligence_service/starter-catalogue/reviews.json`,
  SHA-256 `043f92e36a4bde89b5d816c9dbcc31435a1a626c28f91f96c2c60c341497b9ef`.
- Reproduction: join the records on `identity`, select older
  `outcome == approved`, compare both files named by `body_path`, replacing
  only the literal sentence's anchor matching
  `Written for this catalogue at revision [a-f0-9]+.`. All 29 resulting byte
  strings match. Do not normalize arbitrary source references or text.

Recommendation for S-6.40 and S-6.63: make this overlap part of the
reconciliation before following triage step 6.1. Preserve both records,
resolve each substantive finding, and have independent reviewers decide the
exact successor package. Source-anchor carry alone cannot answer a newly
reported method defect.

## Useful Claude work exists outside main

These are observed commits and artifacts, not inferred work from agent names.
The process list showed Claude and Codex processes with their working
directory at the shared checkout; it does not reveal which task each process
is currently doing or whether it is waiting on a usage limit.

| Work | Location and exact observed tip | What exists and what does not |
|---|---|---|
| Outside ingestion, library package LS1 | `/home/username/.le-library/ls1`, `60929071e9d02124b309a03c36391b77133915a7` | Importer, pinned source/rights records, deduplication, staging, two recorded real runs, and later adversarial licence-reader repairs. Not merged into main or served. |
| Independent review, library package LS2 | `/home/username/.le-library/ls2`, `2424c34ad3e83cc4dd25509c4df6d0415be230d5` | Reviewer adapters, prechecks, ledgers, calibration, exact review records, real pilot and mutation checks. Not merged; pilot approves nothing. |
| Earlier consolidation | `/home/username/.le-consolidation/g2-website`, `44a4b42679babcf1ebb496be8b7c3fbd19c52d99` | 43 commits still absent from main. Campaign/benefit pages and several repairs need reconciliation with the newer design and contracts. |
| Next integration checkout | `/home/username/.le-integration/r21`, `abcad4f8` | Same revision as main at inspection, with only an untracked dependency link. Its name is not proof of another completed release. |
| Round-two approval recovery | Worktree named above | 121 dirty paths including staged review and derived catalogue changes. Preserve and review; do not copy the old generated release over the current one. |
| Incomplete intelligence-tree consolidation | `/home/username/.le-consolidation/g3-intelligence`, `28b7f033` | Ten dirty paths. The triage classifies the alternative top-level intelligence tree as obsolete, because it would duplicate the current authority. |

The worktree registry contained 109 worktrees; 49 local branches remained.
GitHub exposed only `main` and the frozen checkpoint branch. The historical
triage's count of 87 worktrees is therefore a dated observation. No worktree,
branch or dirty path was removed by this audit. The shared checkout had 43
dirty path entries and remains unsuitable for a blind reset or pull.

### What the real library pilots tell us

LS1's second run discovered 4,790 entries and staged 3,251 review-only
candidates: 596 skills, 445 instruction files and 2,210 connection packages.
It read 20 pinned repositories and the first 3,000 latest registry entries.
It held 511 skills that refer to bundled resources for the missing multi-file
contract. It recorded 187 outline model calls and an idempotent staging rerun.
These are candidate counts, not new customer packages. Later licence fixes
postdate the saved collection run, so their existence does not retroactively
qualify all staged material.

LS2's complete second attempt made 91 item calls and 32 calibration calls for
30 items. Fourteen items had both approvals and rejections; zero reached
approval. The reported review rate was 234.5 item verdicts per hour, or 164
including calibration, at about 33,600 tokens per item. The calibration had
only three planted defects and one control. One reviewer changed its verdict
on a planted defect across attempts; several rejected the benign control.
It therefore measures plumbing and this sample's outcomes, not a reliable
false-acceptance or false-rejection rate.

The saved arithmetic of approximately 43 hours and 336 million tokens for
10,000 reviews is a rate extrapolation, not an approved generation budget or
a prediction of 10,000 useful approved packages. Million-scale generation
should not multiply this process until yield, defects and reviewer error
are measured. Reuse and integrate these implementations; do not build a
second importer or review system in parallel.

## Roadmap corrections and the next discriminating evidence

The generated status is current to its YAML fingerprint, but several
sentences within the authoritative YAML lag the saved evidence. Update the
existing steps during integration; retain dated records unchanged.

| Existing step | Stale or incomplete current wording | Evidence to record and next useful work |
|---|---|---|
| S-6.29, D-18 | Earlier evidence says all five silent merge drops remain missing. | The newer triage finds all five present another way. Preserve the 43 outstanding consolidation commits and resolve the remaining branches. Recheck the actual source before restoring a second implementation. |
| S-6.34 | Next work still says to land the authority section. | The section is already in AGENTS.md. Continue entry-point reconciliation and the README audit. |
| S-6.30 and S-6.31 | Next work still starts with engine framework and adapter records. | Wave A records, slots, recipe catalogue and adapter contract are merged. Selection/adoption and the executor are still incomplete. Use the 34 findings in the wave A integration record to choose the next package. |
| S-6.42 | Evidence and next work still emphasize no-model tests; the integration record says model use waits for authority. | The one-call model-use record exists, with production successes for OpenCode and Claude cloud routes and Pi instruction/skill use, plus Codex and local context failures. No accepted task outcome follows from repeating a marker. Address the recorded native route and context problems instead of rerunning the same loading-only proof. |
| S-6.40 and S-6.63 | The panel's next action is to build and run the first 30-item pilot. | LS1 and LS2 already implement that locally, with zero panel approvals and the overlap conflict above. Integrate their reviewed fixes, reconcile criteria, and measure admission yield on repaired original packages. |
| S-6.35 | The release gate still ends before the entire named per-host suite. | Build the released-revision live-check runner already requested by this step; bind catalogue digests to the active catalogue release. Keep the known HEAD-root failure and all failed attempts. |
| S-6.62 | Publishing is implemented, while the first release adding items is pending. | Distinguish working hot publication from scale: qualify pagination, persistent index/storage engines, grant scope and account settings on realistic package distributions. |
| S-6.38, D-17 | Account keys and availability can look like a complete SaaS. | Qualify invited onboarding, client setup, actual use on a checked task, renewal/cancellation, export and deletion. Do not infer these from the homepage or checkout flag. |
| S-6.33, S-6.37 and D-10 | More marketing pages are proposed alongside older unmerged campaign pages. | Reuse the current access-state design. Blog work can publish engineering explanations or clearly labelled measurement reports; team content needs actual people and approved biographies. Avoid copying stale campaign tracking into the approved no-analytics privacy model. |

Source records:
[wave A integration](ENGINE-FRAMEWORK-WAVE-A-INTEGRATION-2026-09-23.md),
[one-call model use](HARNESS-MODEL-USE-ONE-CALL-2026-09-22.md),
[branch triage](BRANCH-CONTENT-TRIAGE-2026-09-23.md), and
[continuation status](../roadmap/CONTINUATION-STATUS.md).

The triage's catalogue-isolation prerequisite has already been satisfied by
release 19. Its read-only production check for obsolete billing customer
effect records remains unobserved in the records inspected here. That check
must record a count, including zero, rather than relying on the inference
that no customer used the older creation path. This audit did not access the
production database.

## Scope and limits

This audit read source, dated reports, selected worktree states, Git history,
GitHub branch references, workflow results and one non-secret deployment
variable. It reproduced the two body comparisons above. It did not rerun
model calls, read secret values, approve intelligence, mutate live accounts,
merge branches or deploy. Local unmerged pilots are reported as their saved
records describe them; their complete suites were not rerun in this audit.
The only authored file is this dated report. Other new files in the shared
review checkout belong to the parallel review tasks.
