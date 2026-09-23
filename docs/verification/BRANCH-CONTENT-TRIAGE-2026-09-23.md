# Branch content triage and merge plan, September 23, 2026

Kind: dated verification record and plan for roadmap package D-18 ("Every
branch and worktree merged, silent merge losses restored"). Written by Claude
Code (Claude Opus 5.5) in session `81df4e9e`. It is a snapshot, not new
authority. The owner's rules for committing, pushing, branching and releasing
are in the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md, and the task authority stays
[roadmap.yaml](../roadmap/roadmap.yaml).

This run was narrowed to triage and planning. No restoration commit was made
to source code. The only commit of this run is this record and the records
index line that lists it.

## What was checked, and against what

| Name used below | Revision | What it is |
|---|---|---|
| main | `5414581` | Current `main`. Its source tree equals `381cc52` (the release 17 line); `5414581` only adds the release 17 records under `artifacts/architecture-audit-2026-09-19/` and edits `docs/architecture/MVP-CLIENT-SERVER.md`. Fly release 17 runs `381cc52`. |
| consolidation line | `44a4b42` | The tip of an earlier consolidation workflow (journal `wf_35c20c1d-5d9`), built on `main` at `97e805f`. Group g1 (payments and accounts) ends at `96fda82`; group g2 (website and documents) starts there and ends at `44a4b42`. Everything of g1 up to `1373c05` is already on main; `44a4b42` holds 43 commits (11 of them merges) that main does not, changing 103 files. |
| release 18 line | `a559dc34` | The website redesign (`607c3a4`) merged onto `5414581`, being prepared as release 18 in another session. |

Method:

- Line survival. For each branch, every line it added relative to its merge
  base was looked up at the same path in the target tree (a file that moved is
  matched to the file that holds most of its lines). Missing lines were counted
  against `381cc52` (same source as main), against `5414581` and against
  `44a4b42`. The September 23 audit (`/home/username/.le-safety/unmerged-branch-patches/`,
  run against `06b903d`) gave the same counts to within one line.
- Merge drops. Every line that a merge dropped and that was still absent at
  `06b903d` was looked up again in main.
- The consolidation journal: one result line per agent, with each item's
  reasoning, gates and open problems. Line numbers below count from 1.
- Trial merges with `git merge-tree`, which writes no file and moves no
  reference.
- Seven parallel groups read each branch against main, ran the owning checks
  on scratch trees, and wrote findings. Before the scope was narrowed, five of
  them had prepared ports in their own detached worktrees; those ports are
  listed as unreviewed, not merged.
- The full continuous integration set ran on `381cc52` before any change: all
  12 stages exit 0 (self-test 3206 of 3206, tools suite 836 tests OK,
  conformance all gates pass, real-browser workspace check 412 of 412 with 60
  of 60 removed-guard controls, component guides 0 findings, hardcoding audit
  with no new high finding, embodiment lab 106 OK, the 24 examples, Markdown
  lint 0 issues in 642 files, qualification lab, publish guard, retired
  language search).

## Summary

| Item | Consolidation line `44a4b42` | Main `5414581` | Classification |
|---|---|---|---|
| `pay/accounts` | present as squash `8a161e3` | yes, `8a161e3` | on main another way |
| `pay/billing-customer` | `34a6d04` | yes, `ceeb7fa` and `34a6d04` | on main another way; hazard 1 is live |
| `pay/billing-setup` | present as squash `a8dc540` | yes, `a8dc540` | on main another way |
| `pay/container-journey` | present as squash `1f42fd8` | yes, `1f42fd8` | on main another way |
| `pay/catalogue-release` | no | its release builder, another way | still needs work (two guards); its review record is obsolete as approvals |
| `pay/web-campaigns` | `14b522f`, `362d8d4`, `65a3e61`, `913f24b` | no | carried by the consolidation line |
| `wave2/campaign-pages` | `805c0c3`, `3c5324b`, `f83a005` | no | carried by the consolidation line |
| `worktree-wf_ac2dc435-f2e-18` | same tip as `wave2/campaign-pages`; its unfinished merge in `e7734bb` | no | carried by the consolidation line |
| `wave2/intelligence-organization` | no | the approval parts, another way | obsolete |
| `worktree-wf_ac2dc435-f2e-15` | no | the approval and withdrawal parts, another way | obsolete |
| `wave2/waitlist` | squash `8a0b872` | yes, `8a0b872` | on main another way |
| `worktree-wf_ac2dc435-f2e-14` | squash `8a0b872` | yes, `8a0b872` | on main another way |
| `wave3/green-ci` | no | two of its parts, another way | still needs work |
| `wave6/documentation-content` | its status guard, another way, in `685fdd3` | its payment lines, another way | still needs work |
| `wave6/harness-component-intelligence` | no | the placement parts, another way | still needs work |
| `wave7/occupation-axis` | no | no | still needs work |
| `worktree-wf_163570aa-59d-5` | `bb66fe2` | no | carried by the consolidation line |
| `worktree-wf_163570aa-59d-7` | `053dc48`; its uncommitted repair in `685fdd3`, `4a06423`, `5576d37` | its 47 lines, another way | carried by the consolidation line |
| `worktree-wf_ac2dc435-f2e-12` | `77b5da5` | no | carried by the consolidation line |
| `worktree-wf_ac2dc435-f2e-16` | `e967090`, `4aa2ee6` | no | carried by the consolidation line |
| Merge drop: `web_routes.py` never on main (`0dc762c`, `0e94603`) | not applicable | yes, in `web_pages.py` | on main another way |
| Merge drop at `8892677` (`http.py`, `http_entrypoint.py`) | not applicable | yes, restored on September 22 in another form | on main another way |
| Merge drop at `107426b` (`web_pages.py`, `http.py`, guide) | not applicable | yes | on main another way |
| Merge drop at `e505eca` (`request_limit_checks.py`, `http.py`) | not applicable | yes, a stronger check | on main another way |
| Merge drops of `pay/web-landing`, `pay/web-message`, `pay/web-accounts` | not applicable | yes; the trial words are retired | on main another way; the trial wording is obsolete |

Counts: of the 20 branches, 7 are carried by the consolidation line and not
yet on main, 6 are on main another way, 2 are obsolete, and 5 still need
work. All five recorded merge drops are on main another way. "Still needs
work" never means that main is wrong today; it means content main lacks and
should get.

The largest item found is outside the 20 branches: a second round of
independent review, staged but never committed in the
`release/catalogue-round-two` worktree, approves 71 of the 74 starter items
that main's review record leaves without a verdict (merge plan step 6).

## The consolidation line

What it carries that main does not (all in `44a4b42`):

- g1, two commits: `f77b475` adds the five missing routes and two
  `/.well-known` addresses to the route table of
  `docs/components/service-runtime/README.md`; `96fda82` records the payments
  and accounts line in the September 21 handoff and adds
  `artifacts/architecture-audit-2026-09-19/payments-and-accounts-removed-guards-1.json`
  (nine removed-guard runs, all detected).
- g2: the campaign pages (`805c0c3`, `3c5324b`, `f83a005`, `e7734bb`), the
  benefit pages and page comparison (`14b522f`, `362d8d4`, `65a3e61`,
  `913f24b`), the nomenclature repair (`e967090`, `4aa2ee6`), the hosting
  repair (`77b5da5`), the overnight guide repair (`bb66fe2`), the usage
  documentation repair (`053dc48`, `685fdd3`, `4a06423`, `5576d37`) and the
  verifier's fixes (`9687745`, `52f56a6`). Its gates at `44a4b42` (journal
  line 16): service smoke 444 of 444, self-test 2604 of 2604, conformance all
  gates pass, hardcoding audit with no new high finding; the real-browser
  check passed 472 of 472 with 65 of 65 controls at `913f24b`, the last commit
  that changed a page. Its tools suite had 3
  failures and 1 error that already existed at its start; main fixed the
  component guide one in `7c3ec6d`, and the anchor ones clear with the
  re-anchor below.
- The g3 group (intelligence and catalogue) and the final gates never ran
  (journal lines 17 to 21). A partial g3 attempt left
  `/home/username/.le-consolidation/g3-intelligence` at `28b7f03`, a merge of
  `wave2/intelligence-organization` onto `44a4b42`, with staged and
  uncommitted changes. This record classifies that content as obsolete.

A trial merge of `44a4b42` into main conflicts in 16 files, and into the
release 18 line in 17 (the same 16 and `tools/check_hosted_website.mjs`):
`docs/architecture/MVP-CLIENT-SERVER.md`,
`docs/guides/service-serving-and-connections.md`,
`docs/roadmap/CONTINUATION-STATUS.md`, `src/loop_engine/ARCHITECTURE-MAP.md`,
`src/loop_engine/architecture_conformance.json`,
`src/loop_engine/architecture_map.py`, `service_runtime/http.py`,
`service_runtime/http_checks.py`, `service_runtime/provisioning.py`,
`web_assets/index.html`, `web_assets/service.js`, `service_runtime/web_pages.py`,
`tools/check_service_documentation.py`, `tools/check_service_workspace.mjs`,
`tools/test_architecture_audit.py` and `tools/test_service_documentation.py`.
`docs/roadmap/roadmap.yaml` merges cleanly: main already renumbered the
waiting list package to D-24, the line adds D-10-T06 and D-10-T07, and the
merged plan holds 24 packages and 111 verification cases (main has 109).

Among the 80 files the starter catalogue cites, the consolidation line changes
only `src/loop_engine/core/settings_loader.py` (a self-test added by
`bb66fe2`). The release 18 line changes none.

## The 20 branches

| Branch (tip) | Missing lines, main / line | Classification | Evidence |
|---|---|---|---|
| `pay/accounts` (`ce9036b`) | 13 / 21 | on main another way | Journal line 3: all 11 files the branch changed are byte-identical to the squash `8a161e3`. The 13 lines missing on main were all on main once and were rewritten later (`once_on_main` equals `missing` for every file). |
| `pay/billing-customer` (`43a2c28`) | 37 / 35 | on main another way | Journal line 3: `34a6d04` brought in the repairs from `5dbed97` onward; the three high defects (a truncated empty search read as no customer, a reconciliation window below the search lag, a wedge after a provider account change) each fail named checks when their repair is removed, and the removed-guard runs were repeated at `f77b475` (journal line 8). The missing `runtime.py` lines moved to `records.py`, two functions under new names (`billing_customer_request_differs_only_by_provider_account`, `billing_customer_search_can_show_the_previous_attempt`), to keep `runtime.py` under the size cap. On `381cc52` the Stripe session checks pass 121 of 121 and the runtime checks 45 of 45, including the named checks for the three defects. The repairs have removed-guard evidence and no second review. |
| `pay/billing-setup` (`9d61690`) | 44 / 44 | on main another way | Journal line 3: the tip matches the squash `a8dc540` except the key fixtures in `tools/test_setup_stripe_sandbox.py`, which were rewritten to join a prefix and a body because push protection refuses key-shaped strings. |
| `pay/container-journey` (`007cf9b`) | 10 / 4 | on main another way | Journal line 3: all three files are byte-identical to the squash `1f42fd8`; the missing lines were rewritten on main later. |
| `pay/catalogue-release` (`0e2ca9b`) | 4151 / 4151 | still needs work | Two guards of its release builder are missing on main; the rest is on main another way or obsolete. See the g3 section. |
| `pay/web-campaigns` (`c7cb3e2`) | 920 / 0 | carried by the consolidation line | An ancestor of `44a4b42`, merged as `14b522f`. Nobody reviewed the branch; the line's review found claims resting on parked modules, repaired in `65a3e61` and `913f24b`, and `362d8d4` added the rule that a missing measurement is not a limit. Needs work at the merge (hazard 2). |
| `wave2/campaign-pages` (`36d8bc7`) | 1001 / 0 | carried by the consolidation line | Merged as `805c0c3`; `3c5324b` removed the retired trial words and aligned the header and footer; `f83a005` kept `web_pages.py` free of service imports. Needs work at the merge (hazard 2). |
| `worktree-wf_ac2dc435-f2e-18` (`36d8bc7`) | 1001 / 0 | carried by the consolidation line | Same tip as `wave2/campaign-pages`. Its worktree holds an unfinished merge (267 paths, 5 in conflict); its own edits (published campaign names, sign-up refuses an unpublished name with `unknown_campaign`) are integrated in `e7734bb`; the rest was main's content already on the line (journal lines 11 and 16). |
| `wave2/intelligence-organization` (`046731d`) | 1865 / 1865 | obsolete | A new top-level `intelligence/` tree and a move of the starter catalogue. Main keeps the catalogue at `examples/29_intelligence_service/starter-catalogue`: `Dockerfile.service` line 21 copies its `host-release` into the image, 16 code and configuration files and three roadmap entries cite the path, and served material now lives in the body store with catalogue release records (`058e57b`). A manifest built from the tree would be a second source of truth beside `tools/build_host_catalogue_manifest.py`. |
| `worktree-wf_ac2dc435-f2e-15` (`38ab39c`) | 2458 / 2458 | obsolete | Contains `046731d`. Its approval rules exist on main another way (`reviews.json` version 2, `test_no_reviewer_produced_an_item_it_judged`; 63 builder and carry tests OK), and so does its withdrawal repair (`catalogue_withdrawal/v1`; `catalogue_release_checks` 50 of 50, including `a_withdrawn_item_is_not_served_after_a_rollback`). Its decision record says "accepted" for a tree main does not have, so restoring it would misstate the architecture. |
| `wave2/waitlist` (`16e1403`) | 197 / 175 | on main another way | Squashed with its repair branch as `8a0b872` (journal line 3). The missing lines are its `web_routes.py` (main serves `/waitlist` from `web_pages.WEB_ASSETS`, and the boundary check was ported as `_web_pages_boundary`) and its first source record, `service_waitlist_source/v1`, which is obsolete: main uses a keyed `service_waitlist_source/v2` and refuses the first version before any write (`a_first_version_source_record_is_refused_before_any_write`). |
| `worktree-wf_ac2dc435-f2e-14` (`6cd5cbc`) | 162 / 116 | on main another way | Same squash `8a0b872`. "Count nobody where no address source was declared" is on main (`waitlist.py` lines 122 and 399 to 400, `a_host_that_declared_no_address_source_names_no_address`), and so is erasure on request (`removing_an_entry_erases_the_address_and_the_note_from_the_stored_record`). |
| `wave3/green-ci` (`8d5bb00`) | 644 / 645 | still needs work | In no consolidation group. See "Other branches" below. |
| `wave6/documentation-content` (`240c127`) | 1778 / 1958 | still needs work | See the g3 section. |
| `wave6/harness-component-intelligence` (`825162d`) | 5055 / 5059 | still needs work | See the g3 section. |
| `wave7/occupation-axis` (`6bb1d77`) | 1654 / 1654 | still needs work | See the g3 section. |
| `worktree-wf_163570aa-59d-5` (`70168f3`) | 617 / 0 | carried by the consolidation line | Merged as `bb66fe2`; every file it touched is byte-identical at `44a4b42` except `custom_endpoint.py`, which also has main's later changes. The three defects it repairs are real on main: the guide's keyless `--compile-provider local_ollama` call is refused, `settings check` accepts `id: mistral` with `kind: custom`, and a run started from `--file` records `"task": ""`. Two gaps remain (see the merge plan). |
| `worktree-wf_163570aa-59d-7` (`664327f`) | 47 / 0 | carried by the consolidation line | The branch commit only merged `wave3/service-usage-docs`; `053dc48` merged it for ancestry. The 47 lines missing on main were all on main once and rewritten by `3b64ab4`, `ad4dbdc` and `3b82091`. Its uncommitted repair is in `685fdd3`, `4a06423` and `5576d37`: the defect it fixes is live on main, where reusing a `request_id` for another item answers 503 `meter_commit_unknown` on every repeat. |
| `worktree-wf_ac2dc435-f2e-12` (`ae4bb6b`) | 541 / 0 | carried by the consolidation line | Merged as `77b5da5`, which binds the Current deployment section to `live_service_record` in `tools/architecture_report/hosting.json`. That record names Fly release 11; main records release 17, and the line's own guard finds six disagreements with main's section, so the merge needs work. |
| `worktree-wf_ac2dc435-f2e-16` (`fef00c0`) | 318 / 0 | carried by the consolidation line | Merged as `e967090` with the uncommitted guide edit; `4aa2ee6` pins 18 packages and 93 cases. It adds the gate `retired_source_terms_in_package_source` and claims every page region; main's newer `view:privacy` is claimed by no surface on the line, so the merge needs work. |

The missing-line counts against main use the September 23 method at `381cc52`;
the counts against the consolidation line do not match moved files, so a
branch the line squashed shows the lines the squash rewrote.

## The five recorded merge drops

The September 22 handoff lists five merges that dropped branch lines. Each
was looked up again in main, and main's owning check was run on an export of
`381cc52` (`http_checks.self_test()` 565 of 565).

| Merge drop | What was dropped | Classification | What replaced it on main |
|---|---|---|---|
| `web_routes.py`, dropped at `0dc762c` (`wave9/model-guidance`) and `0e94603` (`wave9/subdomain-surfaces`) | The file itself; 22 and 24 of its lines never arrived anywhere | on main another way | `web_routes.py` was a third design of the page table move. `web_pages.py` holds the same table (with more rows: `/privacy`, `/waitlist`, `/assets/catalogue-browser.js`), the serve function and the missing page (lines 27, 77 and 92). The lines that never arrived are the docstrings and names (`serve_web_asset`, `web_asset_bytes`) of that design. Checks: `an_address_the_router_answers_is_reachable_over_a_real_socket`, `the_route_table_names_every_address_the_router_answers`, `served_address_table_does_not_import_the_transport_application`. |
| `8892677` (`wave5/operator-observability`) | 40 lines of `http.py`, 3 of `http_entrypoint.py`, 2 of `forbidden_paths.json` | on main another way | Restored on September 22 in another form: `readiness_report` and `readiness_deadline_report` (`service_health/v2`, `observability.py` lines 501 and 563), `_record_failure` (`http.py` line 779) called for protocol tool refusals, `failures` in `SERVICE_COMMANDS`, `observability_policy`. Checks: `a_running_service_answers_the_measured_health_question`, `a_health_measurement_that_misses_the_deadline_answers_503_not_ready`, `a_protocol_tool_refusal_carries_a_reference_the_operator_finds`, `the_failures_command_answers_through_the_service_entry_point`. |
| `107426b` (`wave8/overnight-pages`) | 24 lines of `web_pages.py`, 3 of `http.py`, 3 of the website guide | on main another way | Main keeps the page headers in the transport (`http._page_headers`, line 1258) and the bytes in `web_pages.served_asset` (line 77); the guide names `web_pages.py`. |
| `e505eca` (`wave5/security-and-tenancy`, recorded on five more branches) | 12 plus 2 lines of `request_limit_checks.py`, 6 comment lines of `http.py` | on main another way | The overlap check now holds inside the worker slot at `authenticator.host_key` and asserts more: every slot answers 401, four extra answers are 503 `service_busy`, then a 429 (`attempts_already_inside_authentication_finish_and_the_worker_slots_bound_them`, `request_limit_checks.py` line 648). The comments are doc comments at `http.py` lines 71 to 78. |
| `pay/web-landing` (72 lines), `pay/web-message` (54), `pay/web-accounts` (12) | The September 21 homepage and pricing copy, the trial captions, two style guide rows, a catalogue browser group name | on main another way; the trial wording is obsolete | The owner's later headline and copy, the `waiting` and `invitation_only` states (`service.js` lines 34 to 67) and wider checks replaced them. "Private pilot", "Request access" and "invited beta users" are retired words that `no_customer_page_describes_the_product_as_a_trial` refuses. The catalogue browser group was renamed to "Files for your development tools" on September 22 (`catalogue-browser.js` line 23). |

The other merge drops the audit recorded are also on main another way:
the starter catalogue test constants and query note of `beta/catalogue-r2`
(`de59092`), the review rules of `release/catalogue-round-two` (`e073d01`,
now `starter_catalogue_independent_review/v2` with `_judged`), the wrong-method
check of `wave10/status-page` (`0dc762c`, reworded in
`account_email_checks.py` lines 542 to 553), the network allowance and
self-test lines of `wave4/promotion-codes`, `wave5/operator-observability`,
`wave5/search-quality` and `wave8/overnight-runnable` (present with other
wrapping), the import line of `wave5/security-and-tenancy`
(`capacity_checks.py` line 26), and the documentation link condition of
`wave6/polish` (`conformance_report.py` line 111). The September 22 handoff
asked a reviewer to confirm the exclusion that the merge `1d796f4` added to the
documentation link gate. It is confirmed: `.gitignore` lines 74 to 78 ignore
`embodiments/*/runtime/` and `embodiments/*/upstream/`, the vendored copies of
other harnesses; no file under them is tracked; the main checkout holds
thousands of their Markdown files (1654 under `embodiments/hermes_agent/runtime`
alone); and in a clean export the folders do not exist, so the exclusion
changes nothing in continuous integration.

## The g3 intelligence items

The consolidation workflow never ran this group. Each item is classified
against main.

### pay/catalogue-release

A parallel design of the release step, written on September 21 before main
settled on its own. Main's replacement is `tools/build_host_catalogue_manifest.py`
(the host release from the review record), `tools/carry_catalogue_approvals.py`,
`tools/build_catalogue_release_bundle.py` and the catalogue releases the
service serves from its store without a redeploy (`058e57b`, `0f5c458`,
`b91cbe3`), switched on live on September 23 as `5414581` records.

| Content | Classification | Evidence |
|---|---|---|
| `tools/build_catalogue_release.py`: a release folder built only from approved items, with a coverage, a verdict, a body and a licence refusal, and a `--verify` mode an operator runs before a service reads the folder | on main another way | The manifest builder refuses a rejected or unjudged item, a body whose digest or size changed and a licence the host policy does not accept (`test_the_generator_refuses_an_item_a_reviewer_rejected`, `test_a_body_changed_after_its_digest_was_computed_is_refused`, `test_the_generator_refuses_a_licence_the_host_policy_does_not_accept`), and it checks the committed folder when run without `--write`. The service refuses a body whose digest differs when it loads the manifest (`artifact_digest_mismatch`) and verifies every body of a catalogue release before it serves it. |
| The engine's licence policy refusal reported under its own code (`822884c`) | still needs work | Recorded by the author of prepared port `295115e1` on `381cc52`: main's builder stops with an untyped `ServiceRuntimeError` and exit status 1, the status of a stale folder, for `--accept-license unknown` or `" MIT"`. Prepared port `295115e1` reports `invalid_license_policy` and exits 2; five cases fail with the refusal unwrapped. |
| Refusing to empty a release folder the builder did not write (`6ebcadc`, `19bac22`) | still needs work | Recorded by the author of prepared port `dabfa806` on a copy of the catalogue at `381cc52`: `--output` naming the catalogue folder with `--write` removed `reviews.json`, `items.json`, the specifications and all 123 candidate bodies, and reported "written" with exit status 0. Prepared port `dabfa806` refuses such a folder (`unsafe_release_folder`, `unexpected_release_file`) before it removes anything; five checks fail with the guard removed. |
| `release/reviews.json`: one verdict for each of the 123 items, by one of three reviewers who each took 41 items, on the bytes at `0cf19eb` (79 approve, 44 reject) | obsolete as approvals | Main approves an item only when every named reviewer approves it, and `test_every_judged_candidate_is_judged_by_every_named_reviewer` holds that. One verdict per item cannot meet the rule. It records one open question, under hazards. |
| `release/approvals.json`, `host-manifest.json`, `starter-identities.json` and the copied bodies | obsolete | Written by the replaced tool. Main's `host-release/` and its catalogue releases are the served set, and grants replace the starter identity list. |

### wave2/intelligence-organization and worktree-wf_ac2dc435-f2e-15

Obsolete, as the table says. Nothing needs porting. In detail: the tree, the
move and a second manifest builder are not wanted; the approval separate from
the item, bound to the body digest and never given by the producer, is on main
in `reviews.json` version 2; only approved items reach a manifest and a digest
mismatch is refused (`test_the_generator_refuses_an_item_a_reviewer_rejected`,
`test_a_body_changed_after_its_digest_was_computed_is_refused`,
`load_host_manifest` raising `artifact_digest_mismatch`); a withdrawal
withdraws (`catalogue_withdrawal/v1` with its removed-guard controls); every
body is declared by a record and every item is a candidate
(`tools/test_starter_catalogue.py`). The branch bytes stay in the bundle
`/home/username/.le-safety/local-branches-20260923T012120.bundle` and the
audit patches.

### wave6/harness-component-intelligence

| Content | Classification | Evidence |
|---|---|---|
| A body effect scan: a harness item whose body runs a command, opens a remote address or reads a credential it does not declare is refused | still needs work | Absent on main and on the line. Main's only effect rule reads roles, not bytes (`catalogue_bundle.effect_refusal`). The scan flags none of the 123 starter bodies, so the 43 approved items build unchanged. |
| `pure` declared beside another effect refused on a harness item | still needs work | Code facets and engine records refuse it (`pure_excludes_other_effects`); `HarnessIntelligenceItem` does not. |
| 25 candidate bodies (hooks, skill folders, commands, subagent definitions, protocol servers, configuration profiles, plugins) | still needs work | Original MIT text with no approvals; main's candidate batches hold other kinds. The branch's own review sheet says none would pass independent review today, so they can only land as candidates. |
| The effect check when the service loads its manifest (`load_host_manifest`, 33 lines of `http_entrypoint.py`) | still needs work, website line | After the digest check at line 325 and before `catalogue.register(item)`: refuse a body that is not UTF-8 text (`item_body_not_text`), then refuse with `item_effects_not_declared` when `effects_refusal(item, text)` is not empty. Known-wrong case: the branch's `TheServiceRefusesABodyThatCarriesMoreThanItDeclares` at `825162d`. |
| A typed component shape (`harness_component_spec/v1`, six more item kinds, an item reference version 2, its reader) | on main another way | Main places each file of a package by one of 13 roles (`catalogue_packages.FILE_ROLES`) and a client layout profile (`tools/install_selected_material.py`); an install path on each item would be a second placement authority. Four facts it held have no home yet (requirement versions, protocol transport and revision, the settings keys a merge writes, the page and date a format was read); they belong to roadmap step S-6.44. |
| The tree records, the collection's `refresh.py`, `specifications.json`, the uncommitted worktree changes (typed kinds and allowlist entries) | obsolete | They serve the typed shape and the tree, which are not restored. The archive patch keeps the bytes. |

### wave7/occupation-axis

Still needs work. It makes role (O*NET-SOC codes), organization kind, country
and language four typed, validated search fields, which roadmap step S-6.53
asks for ("Search can be scoped by role, seniority, country and language";
seniority is not covered). Main has only open, unchecked tags for these
(`core/intelligence_tagging.py`), so nothing replaced it. Found in the branch:
its two hardcoding allowlist entries never applied (wrong classification);
its O*NET notice lacks the trademark sentence and names Loop Engine where the
O*NET load names Baltor; its statement that ESCO states no licence is out of
date (the O*NET load found the ESCO terms on September 21: Commission Decision
2011/833/EU). It also claims `harness_intelligence_item/v2`, which the harness
component work claims for another meaning.

The O*NET 31.0 load, uncommitted in the `wave7/occupation-tables` worktree
and in the September 22 archive, is related and also still needs work. It
repairs a real licence gap (main records "CC BY 4.0" for O*NET but no seed
carries the notice the licence requires), adds 54,269 job titles, column
checks against the file header and a verbatim sample. Verified read-only: all
file digests and counts match its record, and its self-test passes 20 of 20
on an export of main. Open: it grows `seeded_generation.py` to 1237 lines,
over the 800-line cap; that module's suite is parked on main (roadmap S-6.28),
so its checks would not run; and its record claims 180,758 staged seeds while
the store on disk holds 148,476 records with an interrupted-write journal and
no staging report, so that claim must be corrected before it lands.

### wave6/documentation-content

| Content | Classification | Evidence |
|---|---|---|
| The website Documentation view: a versioned index, built pages, the build and check tools, the served index and pages | still needs work, website line | Absent on main and on the line; main's `/docs` view is written by hand in `index.html`. On main the addresses belong in `web_pages.py`, and the release 18 redesign decides how the view renders. |
| The refusal status guard in `tools/check_service_documentation.py` | carried by the consolidation line another way | `685fdd3` holds its own guard (`_status_map`). On main nothing checks the 61 documented status rows. |
| Three customer pages (your account, usage and what you pay for, what Baltor is) | still needs work | Absent on both lines. Written against September 21; read against main, several statements no longer held (served items are the harness family, the order of the download checks, `access:manage`, the waiting list, retired words) and were corrected in a prepared port. They are customer copy and need an independent review. |
| Lines of payment and journey files | on main another way | Brought in by the branch's merge of main at `e146e56`, then rewritten on main by `34a6d04` and `3c6e66c`. |

## Other branches and work outside the branches

### wave3/green-ci

In no consolidation group. Absent from main and from the line.

| Part | Classification | Evidence |
|---|---|---|
| Five workflow guards (ripgrep exit 2 read as success, an empty diagram extraction, an unwatched Studio readiness wait, an installation proof that ran nothing, an empty benchmark record list) and their new test file | still needs work | `refuse_language`, `render_diagram`, `STUDIO_READY` and `report["total"] > 0` occur 0 times in `.github/workflows/ci.yml` on both lines; `tools/test_continuous_integration_workflow.py` is absent. |
| Population guards in four checks that pass on an empty collection | still needs work | Mutants: an empty match list, gate list, launch gate list or probe list each fail the restored check. |
| Tests for the Fly storage target step | still needs work | The step in `.github/workflows/fly-pilot.yml` was repaired in `e63f614`, and nothing runs it. |
| Anchor tool refusals: a shallow checkout named as such, a drift refusal that names the repair command, a review sheet report | still needs work | `require_revision_present` and `review_sheet_work` occur 0 times in `refresh.py`. |
| An explicit release of the held session creation instead of a fixed two second hold | still needs work | The fixed hold caused a Python 3.11 self-test failure (run 35607750980); `release.wait(2)` is still in `stripe_session_transport_checks.py`. |
| The publish paragraph of the packaging guide | still needs work | Main's guide says the image is built "on every push to main"; `publish-image.yml` publishes only for a trusted successful continuous integration run on the current head. |
| Full-history checkout of the suite job; the evidence link | on main another way | `09e68726` set `fetch-depth: 0` and removed the forward link. |
| Two anchor commits (`37b4a89`, `8d5bb00`) | obsolete | The catalogue was anchored seven more times since, now to `40fce69`. |

### Uncommitted work in worktrees

Each of these was compared with the archive
`/home/username/loop-engine-archive-2026-09-22/worktrees/`: the tracked
changes hash the same and the untracked file counts are equal, so nothing is
lost if the worktree goes. None of it is on main or on the line unless said.

| Worktree (branch) | Content | Classification |
|---|---|---|
| `wf_ac2dc435-f2e-18` (`worktree-wf_ac2dc435-f2e-18`) | unfinished merge | carried by the consolidation line in `e7734bb` |
| `wf_163570aa-59d-7` (`worktree-wf_163570aa-59d-7`) | the usage documentation repair | carried by the consolidation line in `685fdd3` |
| `wf_ac2dc435-f2e-16` (`worktree-wf_ac2dc435-f2e-16`) | developer language guide edit | carried by the consolidation line in `e967090` |
| `wf_a4d66b9e-235-1` (`wave7/occupation-tables`) | the O*NET 31.0 load | still needs work (g3 section) |
| `wf_bce6c2d4-baf-1` (`wave6/harness-component-intelligence`) | typed component kinds, allowlist entries | obsolete |
| `wf_eb5e10dc-951-1` (`wave10/machine-fit`) | `loop-engine machine-fit`: reads the machine and advises a building and a deciding setup | still needs work: it matches the hardware picker of roadmap D-21 and its own self-tests pass on an export of main, but it was never reviewed, `machine_reading.py` is 834 lines (over the cap) and the patch no longer applies; its page is website work |
| `wf_cb91ffac-592-2` (`wave9/subdomain-surfaces`) | the surface map for each hostname (`WebSurfaceMap`, `service_web_surface_map/v1`) and three page tools | still needs work, website line; this is the per-hostname surface work, which never reached a commit; the checker its builder names does not exist |
| `wf_cb91ffac-592-1` (`wave9/model-guidance`) | three model guidance pages and their checks module | still needs work, website line; 4 of its own 17 checks fail on its own tip, so it was unfinished; it overlaps the suggested models surface |
| `wf_90f15b07-bb7-1` (`wave8/overnight-pages`) | two overnight views and a guide draft | views: still needs work, website line; guide: reconciled by the overnight group (merge plan step 4) |
| `wf_eb5e10dc-951-2` (`wave10/status-page`) | `service_runtime/status.py` | still needs work, website line, only with its route: alone it is a module no request reaches, and its `health()` would be a second producer of `service_health/v2` in another shape |
| `wf_bce6c2d4-baf-3` (`wave6/polish`) | wording for 14 refusal codes and next actions for `loop-engine report` refusals | still needs work: adapted on an export of main, refusals self-test 3 of 3 and its own self-test 2 of 2; drop the `forbidden` entry, which repeats the 403 wording; visitors see this wording, so it lands with the website line |
| `wf_90f15b07-bb7-2` (`wave8/overnight-runnable`) | two constants with no caller | on main another way (`97e805f` registered the literals) |
| `wf_2c5a17d0-bee-4` (`release/catalogue-round-two`) | a staged second round of review: the same three reviewers who approved main's 43 items judged the other 74 at `0cf19eb` and approved 71 under the same unanimous rule (the record totals 123 reviewed, 114 approved, 9 rejected), with a host release of those 71 items (before the carry tool existed, its generator withheld round one's 43, whose bytes had moved with the anchor; main later carried those 43) | still needs work, and the largest gain found: it was never committed (`git log --all -S` finds no trace), so main's record still names 74 items without a verdict and serves 43. The branch commit and its merge `e073d01` carry only round one. For all 74 items the only difference between the bytes the reviewers read and today's body is the anchor line, so main's own carry rule carries the 71 approvals. |
| `wf_059b60f1-136-4` (`release/catalogue-live`) | a guard in `tools/check_hosted_catalogue.py` that sends a keyring key to another hostname only when both answer with the same public capabilities record, and four release 9 check files | still needs work: prepared port `46b454aa` (six tests; the keyring is opened in both command checks when the guard is removed) |
| `wf_17b40c64-552-1` (`release/carry-approvals`) | an anchor pass from `7ed4e85` to `add9b7c` | obsolete: anchored seven more times since, now to `40fce69` |
| `wf_582812c1-fbf-2`, `wf_a9500b52-cd6-1` | a regenerated `architecture_conformance.json` only | obsolete |

### Detached lines with commits not on main

| Worktree | Commits not on main | State |
|---|---|---|
| `.le-consolidation/g1-payments`, `.le-consolidation/g2-website` | `f77b475`, `96fda82`; then the g2 line to `44a4b42` | the consolidation line; merge plan step 2 |
| `.le-consolidation/g3-intelligence` | `28b7f03` and uncommitted changes | a partial g3 attempt; obsolete (the intelligence tree) |
| `.le-wave3/landing-redesign`, `.le-integration/r18` | `607c3a4` and its release 18 merge `a559dc34` | in flight in another session |
| `.le-library/ls1`, `ls1-verify`, `ls2` | library ingestion work | in flight in another session; not triaged here |
| `.le-wave3/model-use-test` | `1e99817` | on main another way: every content line is on main |
| `.le-stabilize/r2-release` | `4e6a228`, a merge of main | on main another way: its two document lines were on main and were rewritten |

### Prepared ports from this run, unreviewed

Before the scope was narrowed, groups committed ports in their own detached
worktrees under `/home/username/.le-integration/`. They are not on main and
not in the plan unless a step names them. Each needs an independent review.

| Worktree | Commits | What they are |
|---|---|---|
| `restore-d18-ci-audit-names` | `13456bc`, `7c9bd67`, `a2d51ef`, `99012e4`, `49a129d` | the `wave3/green-ci` restoration, each commit message with its checks and mutant results; plus an uncommitted duplicate of `e967090` (discard) and a draft binding of the Current deployment section to the newest release record |
| `restore-d18-intel-tree` | `a490d81`, `2589d3a` | the body effect scan, wired into both release builders and the bundle reader (self-test 3212 of 3212, five mutants caught), and the 25 harness component candidates as artifacts (9 tests, four mutants caught) |
| `restore-d18-docs` | `bf3afdc`, `ca62214` | a refusal status guard (the same purpose as `685fdd3`'s; keep one) and the three customer pages; plus `docs/uncommitted-meter-refusal-port.patch` in the triage folder, which resolves `685fdd3`'s `provisioning.py` hunk against main |
| `restore-d18-overnight` | `cab477d`, `06ed63d`, `880371e` | source changes that duplicate `bb66fe2` (do not take), two tools tests that `44a4b42` lacks (take), and an uncommitted guide reconciliation with `tools/test_overnight_guide_commands.py` |
| `restore-d18-occupation` | none; an uncommitted draft | the occupation axis adapted to main's family field, leaving the hosted wire record unchanged (16 of 16 mutants caught) |
| `restore-d18-catalogue-pay` | `295115e1`, `dabfa806`, `46b454aa`, `781b76c9` | the two release builder guards, the hosted catalogue check guard, and `f77b475` with a new check that the route table names every address in `API_ROUTES` and the protocol path exactly once (the table rows duplicate the consolidation line; the check does not); plus an uncommitted draft of review record version three, which names each round and the bytes its reviewers read and carries all 114 approvals (none refused) |

The triage folder `/home/username/.le-ci-tmp/d18-triage/` keeps every
group's findings, the line survival data and the saved patches.

## Hazards

1. Version one billing customer records. The payment line accepts only
   `service_billing_customer_effect/v2` and refuses version one with
   `unsupported_or_corrupt_record`; no operation migrates or retires a version
   one record. This reader is not waiting for a merge: `34a6d04` reached main
   before Fly release 13 (`pilot-release-11.json`, revision `9cdf99e`), so it
   has been live since release 13. Fly releases 11 and 12, and main from
   `ceeb7fa` until `34a6d04`, wrote version one. An unbound account with a
   version one record cannot reach checkout, and a bound one cannot be
   released. No record in the repository shows that the production store
   was read for version one records: main's guides describe the refusal, and
   only the consolidation line's handoff section (`96fda82`) names the read as
   a precondition. Only Fly releases 11 and 12 can have written one. Six
   accounts exist (`baltor-admin`, `billing-check`, `billing-check-2`,
   `billing-check-3`, `pilot-boundary`, `pilot-owner`); the three
   `billing-check` accounts are the likely holders. Nobody has subscribed and
   the live checkout proof ran on Fly release 10, whose image writes no
   creation record, so none may exist, but that is inferred, not observed. No
   operation that retires a version one record exists yet.
2. The campaign pages need the release 18 access states. The consolidation
   line's `service.js` labels the access action "Create your account"
   (`/signup`) or "Join the waiting list" (`/signup#waiting-list`) and keeps a
   true or false payment state. The redesign `607c3a4` uses "Get started"
   (`/connect`) or "Request an invitation" (`/waitlist`), adds the start panel
   states and the named payment states `open`, `invitation_only` and
   `closed`. Both use `data-access-state` with an inner `data-access-label` element, so
   the campaign and benefit pages can follow the redesign once their markup,
   their route titles and the browser checks that name the old labels and
   addresses are updated. Two more constraints hold before they are served:
   one call to action per page (roadmap S-6.33; every drafted campaign page
   has two), and the owner-approved privacy notice, which lists what the
   service keeps and says the site runs no analytics or tracking scripts.
   Storing a campaign name with an account, or the page comparison record
   `baltor.page-comparison` in the visitor's browser, needs the owner's
   revision of the notice first. Until then the pages ship without
   attribution and with the stable version only.
3. The starter catalogue anchor. The catalogue pins the bytes of 80 cited
   files at `40fce69`. `bb66fe2` changes `settings_loader.py` (cited by
   `validate_input_at_the_boundary_and_refuse_early.md`, an item without a
   verdict); the harness component and occupation work change
   `harness_intelligence.py`. Until the catalogue is anchored again, three
   `tools/test_starter_catalogue.py` tests fail on
   `cited_source_bytes_are_the_pinned_bytes`.
4. Publishing a catalogue release. Since 06:20 UTC on September 23 the live
   service serves its catalogue from the store, and the activation record
   (`artifacts/architecture-audit-2026-09-19/catalogue-release-activation-1.json`)
   says no new item may be published until the grant isolation fix is
   released: five non-owner accounts follow the active release, and a new
   item would reach them. A re-anchored catalogue changes the digest of every
   body, so publish it as a new catalogue release only after that fix.
5. An unsettled review criterion. The earlier panel of `pay/catalogue-release`
   (one reviewer for each item, bytes at `0cf19eb`) rejected 16 of the 43
   items main serves today, most for naming the producing repository's source
   paths and symbols in a closing Source section. Its own reviewers disputed
   that criterion (`no_internals_disclosure`) and never settled it, and it
   also disputed whether a step that calls a model or a package registry must
   declare a network effect. The served bodies still carry the Source section.
   That panel is not part of main's decision rule, so its verdicts change
   nothing, but the review process should settle both criteria before the
   next review round, and before round two's 71 items are published.
6. Smaller hazards the consolidation authors recorded: `http_checks.py` was
   799 lines on the line, one under the cap; the benefit pages and homepage
   benefits 02, 03 and 06 rest partly on parked modules (the line repaired the
   pages, not the homepage); nobody reviewed `pay/web-campaigns`, and the
   repairs of `f2e-12`, `f2e-16`, `59d-5` and `59d-7` were not reviewed a
   second time; the payment repairs and the waiting list repair have only
   removed-guard evidence and no second review.

## Merge plan, in order

Every step runs in a new detached worktree, makes no branch, and ends with the
checks named. A merge also gets a line survival check: every line the merged
side added must be present in the result or have a recorded replacement
(roadmap D-18-T02).

0. Now, before any merge, read the production store for
   `service_billing_customer_effect/v1` records (hazard 1). A read-only
   check is prepared and was tested on a local copy, not in production:
   `/home/username/.le-ci-tmp/d18-triage/catalogue-pay/v1check/check.py`. It
   opens the store through the engine's own reader with writes switched off,
   prints only counts by record version and the account identifiers that are
   not on version two, and prints no provider identifier. Copy it to the
   Machine and run it as the service user against `/data/host.json`. Record
   the count in the handoff and the next release record. If any account has
   a version one record, a host operation that retires it (keeping it as
   evidence) must be built and qualified before that account can check out;
   it is a production data change, recorded before it is made.
1. Let release 18 (`a559dc34`, the redesign) reach main first. The rest of
   this plan is written against main after release 18.
2. Merge the consolidation line `44a4b42` into main with a merge commit
   (`--no-ff`, no squash: the line's key scan found no key-shaped string in
   225 blobs). Resolve the 17 conflicted files by these rules:
   - Regenerate, never hand-merge: `ARCHITECTURE-MAP.md`,
     `architecture_conformance.json`, `CONTINUATION-STATUS.md`,
     `DEVELOPMENT-TRACKER.md` and `development-tracker.json`. Take the union
     of module lists in `architecture_map.py`.
   - `tools/test_architecture_audit.py`: keep main's version, which compares
     with the roadmap, and drop `4aa2ee6`'s fixed pins. The merged plan has 24
     packages and 111 cases.
   - `index.html` and `service.js`: take the redesign. Add the four `/for/`
     campaign pages and the four benefit views with the redesign's
     `data-access-state` markup, access labels and payment states (hazard 2).
     Keep `campaigns.js` (the page comparison) out of the served table until
     the owner has decided on the privacy notice. The campaign field of
     sign-up (`e7734bb`) reaches nobody while account creation is closed, but
     the release that opens sign-up needs the same decision first.
   - `web_pages.py`: the union of the `WEB_ASSETS` rows. `http.py`: keep
     main's file and add only `685fdd3`'s 409 for `usage_identity_conflict`
     and its `intelligence_search` annotations on main's schema (which now has
     `filters`). `http_checks.py`: resolve against main's split (`72eb867`,
     `2d8bc9f`) and stay under 800 lines.
   - `service_runtime/provisioning.py`: apply `685fdd3`'s meter wrapper to
     main's view-based constructor (`058e57b`), with the saved
     `uncommitted-meter-refusal-port.patch`; its two named checks and two
     mutants were run on main's tree.
   - `tools/check_service_documentation.py` and its test: one reader of
     `web_pages.py`, main's named command tuples and privacy test, and a
     protocol version guard that reads both served version tuples in
     `http.py`.
   - `docs/guides/service-serving-and-connections.md` and
     `service-troubleshooting.md`: keep main's two-version text, add the
     `usage_identity_conflict` rows, give `counted` its three published
     entries, and replace the sentence that says the deployed pilot lacks
     `failed_attempts_per_address`, which is false since September 22.
   - `docs/architecture/MVP-CLIENT-SERVER.md` and
     `tools/architecture_report/hosting.json`: keep main's Current deployment
     rows. Either refresh `live_service_record` from the newest release record
     and adapt the two patterns of `77b5da5`, or bind the section to the
     newest release record instead (a draft of this in
     `restore-d18-ci-audit-names` reports 0 disagreements on `5414581`). Add a
     known-wrong case that names an older release.
   - Both `terminology.yaml` copies: claim `view:privacy`, and every region the
     redesign adds, under a surface, so that
     `page_region_claimed_by_no_surface` stays at 0.
   - `tools/check_service_workspace.mjs` and `check_hosted_website.mjs`: the
     union, with the campaign and benefit checks naming the redesign's labels
     and addresses; add `web_pages.py` to the checked source digests.

   Checks: the full continuous integration set, service smoke, the line
   survival check for all 43 commits, and the real-browser check with its
   removed-guard controls.
3. Right after step 2, the consolidation line's own follow-ups:
   - Overnight: take the two tools tests of `06ed63d` and `880371e`
     (`tools/test_compile_provider_keys.py`, three tests of
     `tools/test_solve_cli_checkpoint.py`), which make continuous integration
     run the keyless and checkpoint checks that stay parked in
     `solve_cli_checks.py`. Do not take the source changes of `cab477d`,
     `06ed63d` or `880371e`; `bb66fe2` carries them.
   - Documentation: keep one refusal status guard. `685fdd3`'s is on the
     line; `bf3afdc` differs in one rule, because it refuses a page that
     promises a status for a code the service never raises (such as
     `item_license_unknown`), where `685fdd3` reads that code as the default
     400. Decide which reading is right, keep that guard and add the other's
     extra known-wrong cases. Then rebase `ca62214`, rename its
     `ITEM_IDENTITY` placeholder (the new credential variable guard refuses
     it) and have the three pages reviewed independently.
   - The service runtime guide: take the completeness check of `781b76c9`
     (`tools/test_service_runtime_guide_addresses.py`, every address in
     `API_ROUTES` and the protocol path named exactly once). The rows
     themselves arrive with `f77b475`. Any route the website work adds then
     needs a row, and the check names it until it has one.
4. The overnight guide: apply the reconciled guide from
   `restore-d18-overnight` with `tools/test_overnight_guide_commands.py` and
   the `parse_command()` extraction. On `44a4b42` the printed settings
   allocate 32768 output tokens inside a 32768-token context window, so the
   gateway's preflight refuses every request (`context_window_preflight_refused`)
   and the guide's sample result cannot come from that file; the
   reconciliation allocates 4096. The new test must fail on the old guide and
   pass on the new one.
5. `wave3/green-ci`: review and cherry-pick `13456bc`, `7c9bd67`, `a2d51ef`,
   `99012e4` and `49a129d`. They share three files with other steps:
   `tools/test_architecture_audit.py` (three lines, also resolved in step 2),
   and `refresh.py` and `tools/test_starter_catalogue.py`, which the re-anchor
   of step 7 uses, so this step goes before step 7. It does not depend on
   step 2 and can go first.
6. The g3 items, in this order:
   1. The catalogue release guards and round two. Review and cherry-pick
      `295115e1` and `dabfa806`, and `46b454aa` for the hosted catalogue
      check. Then restore the second round of review from the
      `release/catalogue-round-two` worktree: a review record that names each
      round and the bytes its reviewers read (the draft
      `starter_catalogue_independent_review/v3` in `restore-d18-catalogue-pay`),
      with every round two approval carried from the bytes at `0cf19eb` by
      `tools/carry_catalogue_approvals.py`, and the host release rebuilt. The
      draft reports 114 approved, all by carry, none refused, and every
      recorded digest matches the bytes its round read (round one at
      `81f341d`, round two at `ade90f0`). It has one known defect: its
      REVIEW.md bullet names revision `ade90f0`, which the rule
      `source_references_are_pinned` refuses; reword it, since `reviews.json`
      names the revision. Until this step lands, the round two verdicts exist
      only as staged blobs in that worktree's index and in the September 22
      archive patch, not in any commit. A new record
      version means the older release refuses it, as the pre-launch version
      policy requires. This step moves the approved set from 43 to 114 items,
      so the record change needs an independent review of its own, and the
      new items reach the live service only through a catalogue release after
      the grant isolation fix (hazard 4).
   2. The harness component effect scan: review `a490d81` with care for the
      live publish path, then cherry-pick it and `2589d3a` (candidates only).
      Give the website line the `load_host_manifest` note above.
   3. The O*NET 31.0 load: split `seeded_generation.py` under 800 lines,
      decide and record whether its suite is collected on main again (the
      triage recommends it, because roadmap S-6.53 needs the licence notice
      checks to run where the library grows), add a loader test (count mode
      writes nothing; a database path inside the repository is refused), and
      correct the staging claim. Edit `roadmap.yaml` last: a concurrent
      session has uncommitted roadmap edits.
   4. One `harness_intelligence_item/v2` for both the component and the
      scope work: an optional `component` and an optional `scope`, at least
      one, one reader, and an item with neither stays version one with
      unchanged bytes. Split `harness_intelligence.py` under 800 lines.
   5. The occupation axis from the reviewed draft on top of step 6.4, with
      the O*NET notice of step 6.3 and the corrected ESCO text. The hosted
      scope (`service_provisioning_request/v2`) is later website work.
7. Anchor the starter catalogue once, after the last change to a cited file
   (`settings_loader.py` from step 2, `harness_intelligence.py` from step 6),
   with the procedure in `examples/29_intelligence_service/starter-catalogue/REVIEW.md`:
   `refresh.py --anchor <full sha> --write`;
   `tools/carry_catalogue_approvals.py --catalogue examples/29_intelligence_service/starter-catalogue --carried-at <date> --write`,
   where every approval in the record must carry and none may be refused
   (43 today, 114 after step 6);
   `tools/build_host_catalogue_manifest.py ... --write`; and the REVIEW.md
   anchor sentences, including the authoring paragraph, which must name the
   new revision and describe each newly changed cited file. The three anchor
   tests must pass again. Publish the re-anchored catalogue as a live release
   only after the grant isolation fix (hazard 4).
8. Run the full continuous integration set on the final commit, read every
   log, then release through the guarded workflow and run the live checks on
   every hostname, as the commit, push and release authority says.
9. Website follow-ups for the agent that owns the website files, after
   release 18: the Documentation view (served through `web_pages.py`, index
   rebuilt to list the three pages), the per-hostname surface map, one set of
   model guidance pages, the status page with its route and one producer of
   `service_health/v2`, the overnight views, the refusal wording of
   `wave6/polish`, and the machine-fit page. The non-website part of
   machine-fit (move `local_fit.py` into `core`, split `machine_reading.py`,
   register the modules, declare the loopback network and `nvidia-smi`
   allowances) can land on its own first.

## Branches and worktrees that can go

Deleting a branch loses nothing that the bundle
`/home/username/.le-safety/local-branches-20260923T012120.bundle` does not
keep, and every uncommitted worktree change matches the September 22 archive.
A worktree must be removed before its branch can be deleted. Nothing was
deleted in this run.

| When | Branches (worktrees) |
|---|---|
| Now: merged into main, and every drop is on main another way | `pay/web-landing` (`wf_ae05bc07-baf-17`), `pay/web-message` (`wf_0f37f5f3-d6b-2`), `pay/web-accounts` (`wf_ae05bc07-baf-38`), `pay/web-browse` (`wf_ae05bc07-baf-26`), `wave4/public-voice` (`wf_582812c1-fbf-1`), `wave5/security-and-tenancy` (`wf_e52d4cd0-8b0-1`), `wave5/operator-observability` (`wf_e52d4cd0-8b0-3`), `wave5/search-quality` (`wf_e52d4cd0-8b0-2`), `wave5/component-documentation` (`wf_e52d4cd0-8b0-4`), `wave2/hosting-truth` (`wf_ac2dc435-f2e-5`), `wave2/intelligence-coverage` (`wf_ac2dc435-f2e-4`), `wave2/nomenclature` (`wf_ac2dc435-f2e-6`), `wave3/overnight-local` (`wf_163570aa-59d-2`), `wave3/service-usage-docs` (`wf_163570aa-59d-3`), `wave9/model-guidance` and `wave9/subdomain-surfaces` and `wave8/overnight-pages` and `wave10/status-page` (branches only; keep their worktrees until their uncommitted drafts are restored or the archive is accepted as their copy), `wave7/occupation-tables` (branch only; the O*NET load lives in its worktree), `wave10/machine-fit` (branch only, same reason), `wave8/overnight-runnable`, `wave4/promotion-codes`, `wave6/polish` (branch only; its worktree holds the refusal wording), `release/catalogue-live` (branch only; its worktree change is prepared port `46b454aa`), `release/carry-approvals` (`wf_17b40c64-552-1`), `release/catalogue-round-two` (branch only; keep its worktree, which holds the round two review, until step 6 lands or the archive is accepted as its copy), `worktree-wf_ac2dc435-f2e-10` (`wf_ac2dc435-f2e-10`) |
| Now: on main another way through the g1 squashes | `pay/accounts` (`wf_ae05bc07-baf-23`), `pay/billing-customer` (`wf_a9500b52-cd6-1`), `pay/billing-setup` (no worktree), `pay/container-journey` (`wf_ae05bc07-baf-21`), `wave2/waitlist` (`wf_ac2dc435-f2e-2`), `worktree-wf_ac2dc435-f2e-14` (`wf_ac2dc435-f2e-14`) |
| Now: obsolete | `wave2/intelligence-organization` (`wf_ac2dc435-f2e-3`), `worktree-wf_ac2dc435-f2e-15` (`wf_ac2dc435-f2e-15`) |
| After step 2 reaches main | `wave2/campaign-pages` (`wf_ac2dc435-f2e-1`), `worktree-wf_ac2dc435-f2e-18` (`wf_ac2dc435-f2e-18`), `pay/web-campaigns` (`wf6-campaigns`), `worktree-wf_163570aa-59d-5`, `worktree-wf_163570aa-59d-7`, `worktree-wf_ac2dc435-f2e-12`, `worktree-wf_ac2dc435-f2e-16`, each with its worktree |
| After step 5 | `wave3/green-ci` (`wf_163570aa-59d-1`) |
| After step 6 | `pay/catalogue-release` (`wf_ae05bc07-baf-18`), `wave6/harness-component-intelligence` (`wf_bce6c2d4-baf-1`), `wave7/occupation-axis` (`wf_a4d66b9e-235-2`), `wave6/documentation-content` (`wf_bce6c2d4-baf-2`, once the website owner has taken the Documentation view from the bundle) |

The `.le-consolidation` and `restore-d18-*` worktrees can go once their
commits are on main or declined.

## Limits

- Observed: the line survival counts, the trial merges, the journal entries,
  the base continuous integration run on `381cc52`, and the checks each group
  names in its findings, run on scratch trees.
- Not observed: the production store (hazard 1), the release 18 line after its
  merge, and any merged tree of the plan. The plan's conflict resolutions are
  written from the trial merge and the findings, not from a finished merge.
- The prepared ports and drafts were checked by their authors only. None has
  had an independent review.
- The catalogue and payment group's findings arrived after the first version
  of this record and confirmed its classification; they added the read-only
  check, the account list, the draft's known defect and the payment check
  counts.
- The missing-line counts against the consolidation line match exact paths
  only, so they overstate what a squash rewrote; the counts against main also
  match moved files.
