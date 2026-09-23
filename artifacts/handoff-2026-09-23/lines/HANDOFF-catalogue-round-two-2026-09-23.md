# Handoff: second round of the starter catalogue review, September 23, 2026

Kind: dated handoff for one integration line, written by Claude Code (Claude
Opus 5.5) in session `81df4e9e`. It is a snapshot, not new authority. The
rules for committing, pushing and releasing are in the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md. The task authority stays
[roadmap.yaml](../roadmap/roadmap.yaml).

The line was worked in the detached worktree
`/home/username/.le-integration/round-two`, started from `main` at `243a8811`.
Nothing was pushed, deployed or published.

## What is done

1. The second round of independent review is restored into
   `examples/29_intelligence_service/starter-catalogue/reviews.json`. It was
   staged and never committed in the worktree of `release/catalogue-round-two`
   (`wf_2c5a17d0-bee-4`, HEAD `ade90f0`). The rows of its 74 items were taken
   byte for byte: each reviewer's decision and reason, the outcome, the rule,
   the approval reference, and the digest and size of the bytes the reviewers
   read. Round one's 49 rows are unchanged.
2. The review record is now `starter_catalogue_independent_review/v3`. It names
   each round of review: round one read the bodies at `81f341d` (anchored at
   `381efec`, 49 items), round two at `ade90f0` (anchored at `0cf19eb`, 74
   items). `tools/carry_catalogue_approvals.py` reads each round's bytes at that
   round's revision. `tools/build_host_catalogue_manifest.py` refuses a carried
   approval that names another round's bytes. Both tools refuse versions one
   and two.
3. The approved set grows from 43 to 114 items. 9 items stay rejected: the 6 of
   round one and 3 of round two, all three by reviewer three
   (`respond_to_a_leaked_credential`,
   `split_a_large_request_into_assignable_parts` and
   `turn_a_vague_request_into_a_testable_statement`).
4. The known defect of the earlier draft is repaired: its `REVIEW.md` bullet
   named the revision that holds round two's bytes, which the rule
   `source_references_are_pinned` refuses. The bullet now points at the revision
   `reviews.json` names. Known-wrong cases plant each round's revision in the
   sheet, one case for each round.
5. An independent reviewer (a separate agent that wrote none of this change)
   reviewed the restoration commit and found the record faithful and every
   approval within the rules. Its two blocking findings are repaired in the
   commit after it (see the list of commits).
6. The catalogue is anchored once, at `4be111ff`, the last commit before the
   anchor commit. No cited file changed since `565e133`. All 114 approvals
   carried; none was refused. The host release holds 114 items.
7. The homepage demonstration shows this anchor's three digests, and the
   homepage library count says 114. No other part of `index.html` changed.
8. A catalogue release bundle is built outside the repository (below).

Commits on this line, oldest first:

- `24abec3e` Restore the second round of the starter catalogue review.
- `4be111ff` Hold every reviewer's verdict to a named check and keep the README
  live count.
- The anchor commit that holds this file: anchor at `4be111f`, the three
  homepage digests, this handoff and the records index line.

## Approvals checked against the rules

For each of the 71 round two approvals, and again for all 114:

- all three named reviewers judged the item, and none objected;
- the reviewer records say no reviewer produced an item under review. The 74
  items were written by the `expand` agents of workflow `wf_ae05bc07-baf` on
  `pay/catalogue-expand` between 07:22 and 09:37 on September 21. The round two
  reviewers were the separate read-only `approve2` agents of workflow
  `wf_2c5a17d0-bee`, from 11:43 to 11:55;
- the digest each approval names is the sha256 of the body at the round's
  revision. The 74 bodies at `ade90f0` are byte for byte the bodies at
  `f89b720`, the checkout the reviewers state they read. Every carry proof shows
  that only the trailing anchor line differs, and only in the revision it names;
- every item declares `MIT`, which the host policy accepts.

No item failed, so none was left out on these grounds. The staged decisions
equal the three reviewers' own outputs in the workflow journal: 74 verdicts
from each, no mismatch.

## Checks run and their results

- Recovery: the staged diff equals the September 22 archive patch, apart from
  the abbreviated index hashes.
- `tools/test_starter_catalogue.py`, `test_the_committed_catalogue_passes_every_rule`,
  with the draft's bullet: failed on `source_references_are_pinned` ("REVIEW.md
  names revision 'ade90f0'"). With the repaired bullet: passed.
- Catalogue modules, on the restoration tree: `tools.test_starter_catalogue`,
  `tools.test_carry_catalogue_approvals`, `tools.test_build_host_catalogue_manifest`,
  `tools.test_build_catalogue_release_bundle`, `tools.test_homepage_demonstration`,
  `tools.test_catalogue_release_runbook` and `tools.test_fly_deployment`: 137
  tests OK. The independent reviewer ran the first five on `7b1e5acf`: 112
  tests OK.
- Removed-guard runs on `7b1e5acf` (the restoration commit before its message
  gained the attribution line; same tree as `24abec3e`): 10 of 10 mutants were
  caught by their named checks. Later, on the working tree:
  - the check that every named reviewer judged an approval (fails with its
    guard removed);
  - the refusal of an item with no row in the record (three errors with the
    coverage check removed).
- Full continuous integration set on `7b1e5acf`
  (`ci-run-wt.sh`, PY_OVERRIDE set to the `.venv-mcp2` interpreter):
  - exit 0: guard, markdown lint, retired language, embodiment lab,
    conformance, hardcoding audit, real-browser workspace check, component
    guides, tools suite, examples and qualification lab.
  - self-test: exit 1, 3217 of 3219 checks. The two failures were
    `a_request_in_flight_finishes_on_the_view_it_started_with` and
    `core.mcp_sdk_transport_self_test_completed` (TimeoutError), with a machine
    load average near 50 on 16 cores. Rerun alone on the same tree:
    `catalogue_serving_checks` 17 of 17 and `mcp_sdk_transport` 7 of 7.
    Neither check reads the starter catalogue.
- Anchor commit, on its tree before commit: the carry command and the manifest
  builder in check mode report nothing to change, and the catalogue modules
  pass (counts in the anchor commit message).

## Known failures and open points

- The full continuous integration set has not run on the anchor commit. It ran
  on the restoration commit only. Its two self-test failures pass on a
  targeted rerun, but a full run on the final commit is still owed.
- `docs/architecture/MVP-CLIENT-SERVER.md` (Current deployment) and `README.md`
  still say 43 items, because 43 is what the live service serves. Change both
  when the 114-item release is published and recorded.
- The homepage count says 114. Its check holds it to the packaged manifest, not
  to the live store, so deploy this homepage only with or after the 114-item
  catalogue release.
- The branch triage (hazard 5) asks that two review criteria an earlier
  single-reviewer panel disputed be settled before round two's items are
  published: whether a closing Source section may name this repository's paths
  and symbols, and whether a step that calls a model or a package registry must
  declare a network effect.
- The round two reviewers recorded limitations that the record does not carry,
  as round one did not: a backwards sentence in step 5 of
  `review_untrusted_input_for_injection`, effects declared narrowly on the
  credential items, `choose_a_smaller_model_for_a_bounded_decision` as the
  weakest approval, and a check gap in
  `rehearse_a_migration_on_a_copy_of_real_data`. They did not withhold
  approval.
- Not taken from the round two worktree: its manifest generator, container
  check and host release, which implemented the withholding rule that main's
  carry tool replaced.
- Not done: the catalogue release guards `295115e1` and `dabfa806` and the
  hosted check guard `46b454aa` of merge plan step 6.1. The roadmap was not
  edited, because a concurrent session holds uncommitted roadmap edits.
- Suggestions from the independent review that were not done: known-wrong
  cases for the round date, the full `reviewed_bodies_revision` and the
  non-empty folder in `review_rounds`; the manifest and bundle builders could
  run the history carry check before writing; version three allows one round
  for each item, so resubmitting a repaired rejection needs a rule for keeping
  its earlier verdict; `tools/check_fly_service_container.py` does not list
  `tools/carry_catalogue_approvals.py` among its source files.

## Commands to continue

Run the full continuous integration set on the anchor commit:

```bash
PY_OVERRIDE=/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python \
  bash /tmp/claude-1000/-home-username-loop-engine/81df4e9e-adbc-4fcf-9636-2fadc680611e/scratchpad/ci-run-wt.sh FULL_ANCHOR_COMMIT
```

The catalogue checks alone, from the repository root:

```bash
PYTHONPATH=src:tools python -m unittest tools.test_starter_catalogue \
  tools.test_carry_catalogue_approvals tools.test_build_host_catalogue_manifest \
  tools.test_build_catalogue_release_bundle tools.test_homepage_demonstration
```

The bundle, built from the anchored catalogue:

- folder `/home/username/baltor-bundles/round-two-4be111f`
- 114 items, 114 files, 294,220 bytes
- bundle digest
  `7f82235475f4e19b3288f0949bda7b87b11fe1273d235b08e54b50143c7383ea`
- archive `/home/username/baltor-bundles/round-two-4be111f.tar`, sha256
  `fd585512317e5ba3aa6f3bc8a50afca35dfc7d326319fb3d5ec3a9656b6ccc41`

Publishing follows steps 3 to 9 of the catalogue release procedure in
[the launch setup runbook](../guides/launch-setup-runbook.md): upload the
archive, check its digest on the Machine, unpack it as the service user, then
publish:

```bash
flyctl machine exec MACHINE "AS_SERVICE loop-engine service publish-catalogue --config /data/host.json --bundle /data/incoming/round-two-4be111f --expected-bundle-digest 7f82235475f4e19b3288f0949bda7b87b11fe1273d235b08e54b50143c7383ea" --app baltor-pilot --json
```

## Effects made

- No live or external effect: nothing was pushed, deployed, published or
  uploaded, and no model or network call was made.
- Local files outside the repository:
  - patches and the staged record in
    `/home/username/.le-safety/catalogue-round-two-20260923/` (with
    `SHA256SUMS`);
  - the bundle folder and archive in `/home/username/baltor-bundles/`;
  - scratch files in `/home/username/.le-ci-tmp/round-two/`.
- Detached worktrees created:
  - `/home/username/.le-integration/round-two` (this line);
  - `/home/username/.le-ci-tmp/round-two-review` and
    `/home/username/.le-ci-tmp/round-two-mutants` (review and removed-guard
    runs, both clean);
  - `/home/username/.le-ci-export/7b1e5acf3e1e49891ae906fe9074eefa76de9d30`
    (the continuous integration export).
