# Development tracker

Kind: generated view. Do not edit by hand. The only task authority is
[roadmap.yaml](roadmap.yaml); change it, then run
`PYTHONPATH=src:tools .venv/bin/python tools/build_development_tracker.py`.
Source fingerprint: `sha256:01d95e9b9bbfb464ac40f9baff633d5f5e114000f988a290ebcc39080a0e9b5d`.

## Where things stand

| Lane | Steps |
|---|---:|
| Being built now | 68 |
| Can start next | 15 |
| Waiting on earlier work | 134 |
| Blocked | 3 |
| Done | 49 |

## Ordered task checklist

Each subtask lives in its owning step in roadmap.yaml. A local check does not complete a task that requires publication.

Completed within their stated scope: 13 of 60 subtasks.

Next eligible subtask: S-6.215.11: Qualify and admit the new case groups

| Order | Task | State | Completion required | Next action or dependency |
|---:|---|---|---|---|
| 1 | [x] S-6.12.04: Separate three product cards from the introductory hero | live_qualified | live_qualified | Keep the three visible offerings consistent while the separate billing and hosted-service work proceeds. |
| 2 | [x] S-6.35.01: Release reviewed main and verify it live | published | published | Keep application deployment and catalogue publication from overlapping. |
| 3 | [x] S-6.215.01: Record the current live file baseline | offline_verified | offline_verified | Use this exact baseline for reconciliation. |
| 4 | [x] S-6.215.02: Qualify the retained API-contract population | offline_verified | offline_verified | Carry only the 31,459 qualified packages into admission. |
| 5 | [x] S-6.215.03: Admit the qualified contract batch | offline_verified | offline_verified | Build the admitted additions bundle. |
| 6 | [x] S-6.215.04: Build the additions bundle | offline_verified | offline_verified | Use bundle 26c50a60 in the preservation check. |
| 7 | [x] S-6.215.05: Check retrieval and grant preservation | offline_verified | offline_verified | Perform exact metadata and body reconciliation. |
| 8 | [x] S-6.215.06: Reconcile the complete release and its bodies | offline_verified | offline_verified | Use the exact completed proof for the next guarded publication after the prioritized website release. |
| 9 | [x] S-6.215.07: Publish the reconciled contract delta | published | published | Publish the next qualified delta against the release live at that time, with the publisher that stages objects as the service user. |
| 10 | [x] S-6.215.08: Verify the new catalogue as a customer | live_qualified | live_qualified | Repeat for each later publication with one new and one earlier package. |
| 11 | [x] S-6.215.09: Mirror the new bodies and refresh public counts | live_qualified | live_qualified | Mirror each later publication's new bodies after its customer check. |
| 12 | [x] S-6.215.10: Complete the repaired case-generation pilot | offline_verified | offline_verified | Qualify and globally deduplicate the completed pilot. |
| 13 | [ ] S-6.215.11: Qualify and admit the new case groups | building | offline_verified | Qualify the 379-group pilot separately, then combine only non-overlapping admitted material through the release owner. Use the larger campaign's cleared admission, not its initial 6,733-group folder. |
| 14 | [ ] S-6.215.12: Publish the qualified case delta | proposed | published | Waiting on S-6.215.11 |
| 15 | [ ] S-6.215.13: Measure and broaden production capacity | building | offline_verified | Integrate the retained-record repair into the release owner's next application release. Prepare a fresh bounded recovery with updated exclusions and enough disk headroom for generation, qualification and publication. Preserve the old failed journal and keep Claude's creative lane separate. |
| 16 | [ ] S-6.214.01: Define canonical source counting | ready | offline_verified | Write and test the source-counting rules in the existing source owner. |
| 17 | [ ] S-6.214.02: Build the source coverage census | ready | offline_verified | Waiting on S-6.214.01 |
| 18 | [ ] S-6.214.03: Normalize the supplied provider operations | building | offline_verified | Waiting on S-6.214.01 |
| 19 | [ ] S-6.214.04: Enforce shared quotas and collection costs | ready | offline_verified | Waiting on S-6.214.03 |
| 20 | [ ] S-6.214.05: Qualify source rights and privacy | ready | offline_verified | Waiting on S-6.214.02 |
| 21 | [ ] S-6.214.06: Run a hundred-source collection pilot | proposed | live_qualified | Waiting on S-6.214.03, S-6.214.04, S-6.214.05 |
| 22 | [ ] S-6.214.07: Expand to one thousand qualified sources | proposed | live_qualified | Waiting on S-6.214.06 |
| 23 | [ ] S-6.214.09: Produce useful source-backed feeds | ready | live_qualified | Waiting on S-6.214.06 |
| 24 | [ ] S-6.214.10: Save customer feed preferences per agent | proposed | live_qualified | Waiting on S-6.214.09 |
| 25 | [ ] S-6.214.11: Deliver and measure personalized feeds | proposed | live_qualified | Waiting on S-6.214.10 |
| 26 | [ ] S-6.207.01: Complete the approved SMB metadata inventory | blocked | offline_verified | Resolve the measured storage allocation before resuming. |
| 27 | [x] S-6.207.02: Extract the priority RapidAPI coding session | offline_verified | offline_verified | Use the exact chunks for substantive review and missing-artifact recovery. |
| 28 | [ ] S-6.207.03: Recover the missing registry artifacts | ready | offline_verified | Start with the two missing native databases and the missing discovery module. |
| 29 | [ ] S-6.207.04: Perform source-specific question reviews | building | offline_verified | Continue focused history review and turn verified gaps into tests and original implementations. |
| 30 | [ ] S-6.207.05: Convert approved findings into original candidates | proposed | offline_verified | Waiting on S-6.207.04 |
| 31 | [ ] S-6.218.01: Specify the hosted live-tool boundary | ready | offline_verified | Draft the narrow first hosted-tool contract and adversarial cases. |
| 32 | [ ] S-6.218.02: Qualify providers for customer-facing use | ready | offline_verified | Waiting on S-6.218.01 |
| 33 | [ ] S-6.218.03: Build tenant-bound credential leases | proposed | offline_verified | Waiting on S-6.218.01 |
| 34 | [ ] S-6.218.04: Add per-tenant budgets and upstream quota reservations | proposed | offline_verified | Waiting on S-6.218.02, S-6.218.03 |
| 35 | [ ] S-6.218.05: Implement scoped live invocation | proposed | offline_verified | Waiting on S-6.218.04 |
| 36 | [ ] S-6.218.06: Expose discovery and invocation through MCP and API | proposed | offline_verified | Waiting on S-6.218.05 |
| 37 | [ ] S-6.218.07: Verify customer isolation and abuse controls | proposed | live_qualified | Waiting on S-6.218.06 |
| 38 | [ ] S-6.218.08: Reconcile top-tier entitlements and pricing | proposed | live_qualified | Waiting on S-6.218.07 |
| 39 | [ ] S-6.218.09: Launch and monitor the qualified hosted-tool pilot | proposed | published | Waiting on S-6.218.08 |
| 40 | [ ] S-6.13.01: Qualify authenticated R2 file delivery | ready | live_qualified | Prepare a bounded delivery canary; keep Fly delivery until it passes. |
| 41 | [ ] S-6.13.02: Place bounded collectors and durable jobs on Cloudflare | proposed | live_qualified | Waiting on S-6.214.06 |
| 42 | [ ] S-6.13.03: Evaluate the customer authentication boundary | ready | offline_verified | Document the migration evidence needed and cost; do not replace login solely because DNS uses Cloudflare. |
| 43 | [ ] S-6.12.01: Add private-by-default customer submissions | ready | live_qualified | Implement a narrow customer upload flow before adding a public contribution CTA. |
| 44 | [ ] S-6.12.02: Add sharing and public-library submission controls | proposed | live_qualified | Waiting on S-6.12.01 |
| 45 | [ ] S-6.12.03: Reconcile the three offering cards and new-signup prices | building | live_qualified | Review and deploy compatible billing readers before an additive new-signup price migration; qualify the hosted upper tier before sale. |
| 46 | [ ] S-6.24.01: Prove one bounded overnight customer task | ready | live_qualified | Retain current provider holds; do not reset the earlier token ceiling. |
| 47 | [ ] S-6.24.02: Verify OpenCode and another harness against live Baltor | ready | live_qualified | Run the customer path on this PC without borrowing administrator access. |
| 48 | [ ] S-6.201.01: Recover the authorized TensorArt asset history | blocked | offline_verified | Resolve the missing target-account access without forwarding cookies to third parties. |
| 49 | [ ] S-6.201.02: Complete one editable creative project and revision | ready | offline_verified | Select a small end-to-end creative proof rather than expanding untested templates. |
| 50 | [ ] S-6.201.03: Produce a rights-cleared product demonstration | proposed | published | Waiting on S-6.201.02 |
| 51 | [ ] S-6.102.01: Package and test the ChatGPT and Codex plugin | building | offline_verified | Release the integration, then run tools/check_chatgpt_app_live.py with --expect-presentation and --screens as a fresh account, confirm the authorization server metadata advertises authorization_response_iss_parameter_supported, and keep the report with the release record. The remaining steps for each directory and client are in docs/guides/chatgpt-app.md. |
| 52 | [ ] S-6.102.02: Complete plugin review and release prerequisites | proposed | published | Waiting on S-6.102.01 |
| 53 | [ ] S-6.204.01: Measure onboarding and product use | ready | live_qualified | Use measured activation and usefulness to guide the next batch and marketing. |
| 54 | [ ] S-6.204.02: Prepare launch, funding and startup-credit material | ready | offline_verified | Prioritize the infrastructure already used and the next customer proof. |
| 55 | [ ] S-6.216.01: Expand useful SDG and competition-derived materials | ready | published | Choose unmet SDG jobs from measured coverage rather than multiplying labels. |
| 56 | [ ] S-6.67.01: Review the complete public page and design surface | ready | live_qualified | Run the owning browser checks for each visible release and verify the live result. |
| 57 | [ ] S-6.35.02: Publish a progress checkpoint after every completed subtask | building | offline_verified | Complete the first canonical subtask checklist and then advance it one result at a time. |
| 58 | [ ] S-6.217.01: Reconcile recent prompts and action history | building | offline_verified | Review prioritized recent chunks instead of treating extraction as full understanding. |
| 59 | [ ] S-6.215.14: Reach two million useful served files | proposed | published | Waiting on S-6.215.12, S-6.215.13 |
| 60 | [ ] S-6.214.08: Reach ten thousand active qualified sources | proposed | live_qualified | Waiting on S-6.214.07 |

## Subtask procedures and evidence

### S-6.12.04 Separate three product cards from the introductory hero

Owner step: S-6.12. State: live_qualified. Completion requires: live_qualified.

Acceptance: The homepage and pricing page show three visually distinct offerings outside the hero, with working actions and truthful current price and execution scope.

1. Keep the hero focused on the product and setup actions.
2. Give Agent Feeds, Harness Files and Overnight / AFK Work separate cards and setup paths.
3. Run responsive, theme, accessibility and full customer-journey checks; deploy reviewed main and verify every public hostname.

Evidence: Release 83 from 4a1f0879 passed exact CI and guarded deployment; gate closed. Local browser: 977 checks and 197 wrong controls. Live offering matrix: 483 checks. Independent ten-host review: 426 checks and twenty unchanged Terms comparisons. All 2,544 Cloudflare export files match exact bodies and headers. See pilot-release-83.json; earlier failed checks are retained.

Next: Keep the three visible offerings consistent while the separate billing and hosted-service work proceeds.

Comment: No third paid hosted service or new billing price is activated by a card layout.

### S-6.35.01 Release reviewed main and verify it live

Owner step: S-6.35. State: published. Completion requires: published.

Acceptance: The exact CI-passed revision is deployed through the guarded workflow, with the gate closed and rollback recorded.

1. Freeze the candidate and finish its owning checks and exact CI.
2. Dispatch the guarded deployment once and reconcile the remote result.
3. Close the deployment gate; record image, revision, rollback and all-host checks.

Evidence: Release 85 from c948a9aa: exact CI 37940684057, guarded deployment 37943750820, gate closed, image 4801fdb6ac7a, rollback release 84. Local suites on the exact tree: browser 977/977 with 197/197 wrong controls, offering 483/483, service smoke 766/766. All ten hosts pass the independent offering/Terms/health checks (426/426); Cloudflare export a5d9cd327dab matches all 2,556 files; route audit 67 pages, 277 views, 419 links, zero problems.

Next: Keep application deployment and catalogue publication from overlapping.

Comment: The fifty-read pulse passed with no slow response. Release 85 ships the clearer offer, three ways to connect and per-agent feeds; release 84 corrected the overnight copy. Application releases do not publish catalogue additions.

### S-6.215.01 Record the current live file baseline

Owner step: S-6.215. State: offline_verified. Completion requires: offline_verified.

Acceptance: Bind the live release, distinct-file count and current access policy before additions.

1. Read live health and the catalogue release identity.
2. Record distinct digests separately from placements and packages.
3. Preserve the current full metadata baseline and all body roots.

Evidence: Live catalogue 1694fb4a has 1,353,029 distinct files in 218,151 packages; 448 Public Good grants are preserved.

Next: Use this exact baseline for reconciliation.

Comment: Two million is the next milestone; ten million remains the longer-term target.

### S-6.215.02 Qualify the retained API-contract population

Owner step: S-6.215. State: offline_verified. Completion requires: offline_verified.

Acceptance: Every candidate has a recorded deterministic verdict and duplicate findings.

1. Run the qualification controls in a separate process.
2. Check all 31,474 exact candidate packages.
3. Retain refusals and record requested execution coverage separately.

Evidence: 31,459 qualified; 15 same-job duplicates withheld; zero unreadable. Forty known-wrong controls and 32 known-good rows passed.

Next: Carry only the 31,459 qualified packages into admission.

Comment: Static qualification does not mean every package ran against its upstream API.

### S-6.215.03 Admit the qualified contract batch

Owner step: S-6.215. State: offline_verified. Completion requires: offline_verified.

Acceptance: Admission binds exact bytes, current holds and prior reviewer rejections.

1. Read the current decision ledger and held-generator file.
2. Admit with the declared OpenAI producer family.
3. Check the admission report and retain the immutable output.

Evidence: 31,459 admitted with approval state qualified and independent review ongoing.

Next: Build the admitted additions bundle.

Comment: Admission is separate from publication.

### S-6.215.04 Build the additions bundle

Owner step: S-6.215. State: offline_verified. Completion requires: offline_verified.

Acceptance: Bundle metadata and payload digests agree with the admitted packages.

1. Use the native bundle builder and the existing accepted-licence policy.
2. Verify item count, exact files and bundle digest.
3. Keep the additions separate from the active release.

Evidence: 31,459 items; 266,677 file placements; bundle digest 26c50a607568b116ad12077958830ca168982f2f1915cb700a373db7532d27fc.

Next: Use bundle 26c50a60 in the preservation check.

Comment: Placements are not distinct new files.

### S-6.215.05 Check retrieval and grant preservation

Owner step: S-6.215. State: offline_verified. Completion requires: offline_verified.

Acceptance: No judged prior retrieval or supplied Public Good grant is lost.

1. Run the stored judged queries against the old and proposed catalogue.
2. Compare all previous item versions.
3. Calculate new digests and check the supplied access policy.

Evidence: 354 judged queries passed the conservative check; 218,151 prior items and 448 grants preserved; 120,036 new digests.

Next: Perform exact metadata and body reconciliation.

Comment: Coverage is the stated query population, not every possible query.

### S-6.215.06 Reconcile the complete release and its bodies

Owner step: S-6.215. State: offline_verified. Completion requires: offline_verified.

Acceptance: Produce a complete segmented baseline with unchanged prior versions and verified body references.

1. Run the native additive reconciler from committed source.
2. Preserve every previous body root and version.
3. Record the result digest and predicted release without activating it.

Evidence: Reconciliation completed from 609640a4: 249,610 items, all 1,353,029 baseline bodies verified, 120,036 new bodies. Bundle fac04d122bbed261c773023ad715f61d11f17ee243d9a7663e8f1710fc060a2c; proof d0caea32e34604dee5100ee197a1db13b503b9c3e713eb48d7ae0e28338cba1f. Not published.

Next: Use the exact completed proof for the next guarded publication after the prioritized website release.

Comment: Large outputs use the existing offload volume. The local memory cap was measured and raised from 10 to 14 GiB; no checks were removed.

### S-6.215.07 Publish the reconciled contract delta

Owner step: S-6.215. State: published. Completion requires: published.

Acceptance: The live pointer commits exactly the reconciled release without changing prior grants.

1. Recheck live baseline, deployment activity and publication ownership.
2. Run the existing guarded delta publisher once.
3. Reconcile an unknown outcome before retrying any effect.

Evidence: Live since October 9 07:46 UTC: release a4ba2053, content 7741e196, catalogue state revision 39, 249,610 packages and 1,473,065 distinct files (31,459 additions, 120,036 new bodies, 0 replaced or withdrawn). All 218,151 prior versions and 448 Public Good grants preserved. The first attempt stopped before activation because staged objects kept the workstation owner; an exact-stage ownership repair and a native recovery completed it.

Next: Publish the next qualified delta against the release live at that time, with the publisher that stages objects as the service user.

Comment: Record: artifacts/architecture-audit-2026-09-19/catalogue-api-contracts-2026-10-09.json. The publisher fix stages archive members as UID 65534 and ends the wait on a typed native error.

### S-6.215.08 Verify the new catalogue as a customer

Owner step: S-6.215. State: live_qualified. Completion requires: live_qualified.

Acceptance: Live counts and exact permitted downloads agree with the release, and previous access still works.

1. Read the live release and complete file population.
2. Search and download selected new and old packages with an ordinary account.
3. Check missing-body, denial, digest, usage and rollback behavior.

Evidence: After release 84, a non-staff account read the live population (249,610 packages, 1,473,065 distinct files, complete), then searched and downloaded one new a4ba2053 contract (9 exact files) and one October 6 data table (8 exact files). A wrong digest was refused 404 and an unauthenticated manifest request 401; usage rose by exactly 2 units in 29 requests with no retry. 526,935 files remain to the two-million milestone.

Next: Repeat for each later publication with one new and one earlier package.

Comment: Missing-body and rollback paths were not exercised. The shipped client sends only catalogue routes, so session and usage were read directly with the same credential.

### S-6.215.09 Mirror the new bodies and refresh public counts

Owner step: S-6.215. State: live_qualified. Completion requires: live_qualified.

Acceptance: New R2 objects match their digests and every published count reflects the active catalogue.

1. Mirror only the new approved body digests.
2. Verify readback and preserve private bucket access.
3. Refresh the existing edge export and check all product hosts.

Evidence: R2 delta complete October 9 10:38 UTC: 938 batches, 120,036 objects written and read back (GET 200 each), 223,812,995 bytes; an independent 32-object sample matched. R2 now covers all 1,473,065 bodies across three scopes. Cloudflare export 7d2c719ca8ab reads the live population; the homepage and library show 1,473,065 files and all ten hosts passed the release-84 checks.

Next: Mirror each later publication's new bodies after its customer check.

Comment: Mirroring does not switch authenticated body delivery to R2. The prepared operator's feed gate sent a query string the live feed refuses; it was corrected before running.

### S-6.215.10 Complete the repaired case-generation pilot

Owner step: S-6.215. State: offline_verified. Completion requires: offline_verified.

Acceptance: Every parent in the frozen pilot is processed with preserved lineage and bounded accounting.

1. Keep the original failed run unchanged.
2. Run the repaired generator from committed source.
3. Resume the successful bounded partial batch with unchanged whole-run limits.

Evidence: 381 of 381 parents processed; 1,686 case files, 379 groups and 2,999 distinct candidate payloads; zero model or provider calls.

Next: Qualify and globally deduplicate the completed pilot.

Comment: Candidate payloads include shared support files and parent schemas.

### S-6.215.11 Qualify and admit the new case groups

Owner step: S-6.215. State: building. Completion requires: offline_verified.

Acceptance: New groups pass native checks and do not repeat case jobs from any selected comparison population.

1. Compare case jobs and file digests with live, admitted and earlier pilot material.
2. Run the qualification controls and exact candidate checks.
3. Admit only qualified groups under the existing policy.

Evidence: October 9: the separate scalable campaign's completed prefix held 6,733 groups and 96,077 distinct payloads. All passed its original all-checks qualification. A new native duplicate pass compared both prior case populations and held 376 overlapping groups; 6,357 were admitted into a new cleared folder. Its byte-verified bundle contains 90,957 distinct payloads and 64,993 case jobs, with zero job overlap against those two populations. The held groups also retain 1,983 non-overlapping jobs for later regrouping. Prior execution evidence was reused, not rerun or relabelled as fresh execution. Publication remains separate.

Next: Qualify the 379-group pilot separately, then combine only non-overlapping admitted material through the release owner. Use the larger campaign's cleared admission, not its initial 6,733-group folder.

Comment: Do not count the failed and repaired copies twice.

### S-6.215.12 Publish the qualified case delta

Owner step: S-6.215. State: proposed. Completion requires: published.

Acceptance: Only net-new admitted case material is served and verified from the current release.

1. Build an additions bundle.
2. Repeat preservation, exact reconciliation and current-live preflight.
3. Publish and test ordinary customer retrieval.

Evidence: Not yet recorded.

Next: Use the release current at execution time.

Comment: An old baseline must not be replayed after another publication.

### S-6.215.13 Measure and broaden production capacity

Owner step: S-6.215. State: building. Completion requires: offline_verified.

Acceptance: A frozen production plan measures candidate yield, accepted yield, time, storage and cost across several useful file families.

1. Measure the completed batch rather than extrapolating from file placements.
2. Select licensed data tables, executable utilities, harness templates and editable creative materials.
3. Reuse unchanged implementations and allocate bounded cohorts with explicit stops.

Evidence: October 9: 19 of 92 ranges completed before a private diagnostic record reached 22,313 JSON values while using only 424,336 of its 4 MiB allowance. The decoder incorrectly shared the served-file 20,000-value limit. The repair has a separate bounded control-record traversal profile and preserves served limits. A fresh committed-source pilot at 059e5659 completes the formerly failing parent with three cases, 15 distinct payloads and unchanged inputs; it is not admitted or published. Construction findings now separate missing baseline members from unavailable probe candidates; a fixed 64-parent comparison retains all 496 case jobs. Larger recovery is not running while publication consumes the constrained disk headroom.

Next: Integrate the retained-record repair into the release owner's next application release. Prepare a fresh bounded recovery with updated exclusions and enough disk headroom for generation, qualification and publication. Preserve the old failed journal and keep Claude's creative lane separate.

Comment: Common-word and parameter combinations are research dimensions, not automatically useful files.

### S-6.214.01 Define canonical source counting

Owner step: S-6.214. State: ready. Completion requires: offline_verified.

Acceptance: An independently maintained upstream collection has one source identity regardless of provider, alias or query.

1. Specify canonical repository, feed, channel, dataset-collection and benchmark-stream identities.
2. Separate source, item, API operation, adapter and generated feed.
3. Define discovered, accessible, rights-checked, scheduled, fresh and feed-contributing counts.

Evidence: Not yet recorded.

Next: Write and test the source-counting rules in the existing source owner.

Comment: Ten thousand queries, API listings or credential aliases are not ten thousand working sources.

### S-6.214.02 Build the source coverage census

Owner step: S-6.214. State: ready. Completion requires: offline_verified.

Acceptance: One reproducible census accounts for the existing registries, collected leads and coverage gaps.

1. Read the current source registries and private lead stores.
2. Normalize aliases and underlying-source relationships.
3. Report each qualification and freshness stage without inventing a baseline.

Evidence: Not yet recorded.

Next: Measure the current denominator before claiming progress toward 10,000 sources.

Comment: Existing active-source coverage has not yet been reconciled across all collectors.

### S-6.214.03 Normalize the supplied provider operations

Owner step: S-6.214. State: building. Completion requires: offline_verified.

Acceptance: Every selected operation has a typed request, normalized result, host binding, effects and observed qualification state.

1. Map provider examples to existing query and source engine slots.
2. Retain successful probes and every refused or unknown outcome.
3. Add positive and known-wrong parser and destination tests before selection.

Evidence: Twenty-nine operation examples are classified; twelve bounded probes returned six usable responses and six held outcomes.

Next: Start with the six latest-key products that returned usable data.

Comment: A stored key or HTTP 200 is not full adapter qualification.

### S-6.214.04 Enforce shared quotas and collection costs

Owner step: S-6.214. State: ready. Completion requires: offline_verified.

Acceptance: Internal collection respects product/account allowances across all keys and workers.

1. Bind quota buckets to provider product and subscription.
2. Reserve requests before dispatch and retain unknown outcomes.
3. Set cadence, concurrency, timeout, retry and byte ceilings from observed limits.

Evidence: Not yet recorded.

Next: Use the smallest applicable product quota, not the marketplace-wide header.

Comment: Multiple RapidAPI application keys share account-wide subscription usage.

### S-6.214.05 Qualify source rights and privacy

Owner step: S-6.214. State: ready. Completion requires: offline_verified.

Acceptance: Each selected source has a recorded allowed use, retention policy and redistribution boundary.

1. Check provider and underlying-source terms for the intended use.
2. Quarantine account-sale ads, deceptive engagement services, duplicates and deprecated listings.
3. Keep private contact enrichment and unqualified media reuse out of public output.

Evidence: Not yet recorded.

Next: Begin with public repositories, publisher feeds, permitted job/company metadata and licensed data.

Comment: Marketplace ratings and compliance claims are not independent evidence.

### S-6.214.06 Run a hundred-source collection pilot

Owner step: S-6.214. State: proposed. Completion requires: live_qualified.

Acceptance: One hundred canonical sources have successful bounded collection, traceable observations and monitored failures.

1. Choose a diverse source population with declared refresh cadence.
2. Run and checkpoint bounded collection through existing owners.
3. Test stale, empty, changed, denied and unavailable sources.

Evidence: Not yet recorded.

Next: Publish the measured coverage and failure population before expansion.

Comment: An empty valid response can be observed; it is not evidence of useful feed output.

### S-6.214.07 Expand to one thousand qualified sources

Owner step: S-6.214. State: proposed. Completion requires: live_qualified.

Acceptance: One thousand canonical sources meet the recorded access, rights, freshness and collection criteria.

1. Expand by measured cohorts and source families.
2. Reuse snapshots and source identities across customers.
3. Hold failing providers without retry storms or credential-based quota multiplication.

Evidence: Not yet recorded.

Next: Advance only within the declared infrastructure and provider allowances.

Comment: The source census owns the count.

### S-6.214.09 Produce useful source-backed feeds

Owner step: S-6.214. State: ready. Completion requires: live_qualified.

Acceptance: Published feed items have original useful content, citations, dates, scope and a supported output format.

1. Separate observations from original synthesis and recommendations.
2. Generate JSON Feed, RSS and Markdown through the same owning record.
3. Check rights, freshness, duplicates, broken references and unsupported claims before publication.

Evidence: Not yet recorded.

Next: Qualify a small number of topic feeds before multiplying them.

Comment: A list of URLs is not automatically a decision brief.

### S-6.214.10 Save customer feed preferences per agent

Owner step: S-6.214. State: proposed. Completion requires: live_qualified.

Acceptance: Two customers and two agents can create, change and revoke isolated feed definitions.

1. Store topics, source allowlists, exclusions, cadence, format and agent assignment through existing account records.
2. Expose scoped setup through the website and MCP/API.
3. Test cross-account access, cursor isolation, edits, export and revocation.

Evidence: Not yet recorded.

Next: Implement a narrow working customer journey before advertising personalized feeds.

Comment: Customer projects and histories are not inspected automatically.

### S-6.214.11 Deliver and measure personalized feeds

Owner step: S-6.214. State: proposed. Completion requires: live_qualified.

Acceptance: Opted-in agents receive the correct feed revision with observable freshness, cost and delivery outcomes.

1. Test polling and any supported push receiver separately.
2. Use idempotent delivery and bounded retry accounting.
3. Measure source contribution, useful items, customer consumption and failures.

Evidence: Not yet recorded.

Next: Connect delivery to the existing entitlement and subscription boundaries.

Comment: Receiving a feed never grants permission to execute it.

### S-6.207.01 Complete the approved SMB metadata inventory

Owner step: S-6.207. State: blocked. Completion requires: offline_verified.

Acceptance: Every approved path is inventoried or has an explicit inaccessible, deferred or excluded reason.

1. Resume the read-only checkpoint without rescanning completed directories unnecessarily.
2. Bound metadata output and preserve the workstation's disk reserve.
3. Prioritize histories and project material ahead of caches and dependencies.

Evidence: 65,382 files inventoried, including 1,550 conversation files; 453 directories remain queued. The scan stopped at its 40 GiB floor.

Next: Resolve the measured storage allocation before resuming.

Comment: No source files were deleted or modified.

### S-6.207.02 Extract the priority RapidAPI coding session

Owner step: S-6.207. State: offline_verified. Completion requires: offline_verified.

Acceptance: Source bytes remain unchanged and every selected record range has a traceable redacted representation.

1. Read the 543 MB session with byte-offset checkpoints.
2. Preserve oversized-record findings.
3. Recover all thirteen ranges with bounded decoding and smaller review fragments.

Evidence: The complete source was hashed; 13 oversized records became 777 redacted fragments. The private chunk store contains 46,836 chunks.

Next: Use the exact chunks for substantive review and missing-artifact recovery.

Comment: Extraction does not establish semantic review.

### S-6.207.03 Recover the missing registry artifacts

Owner step: S-6.207. State: ready. Completion requires: offline_verified.

Acceptance: Recovered artifacts have exact provenance and are checked in a new private location.

1. Locate source-write events and authorized archive references.
2. Reconstruct bytes without executing instructions from transcripts.
3. Verify the missing database/module/document claims against recovered material.

Evidence: Not yet recorded.

Next: Start with the two missing native databases and the missing discovery module.

Comment: Do not substitute another database or overwrite the SMB project.

### S-6.207.04 Perform source-specific question reviews

Owner step: S-6.207. State: building. Completion requires: offline_verified.

Acceptance: Each reviewed chunk records answered, unknown, disputed or reasoned not-applicable questions with source anchors.

1. Apply the thousand-question bank by relevance and preserve open questions.
2. Read high-value owner decisions, code changes, failures and actual outcomes.
3. Map findings to existing Baltor owners, tests and candidate jobs.

Evidence: One thousand questions are defined; 75 source-backed answers exist, including 38 new findings across nine creative-project chunks. Three original camera/timing helpers pass the existing isolated-package checks. No thousand-question chunk review is complete.

Next: Continue focused history review and turn verified gaps into tests and original implementations.

Comment: Question bindings and keyword matches are not completed answers.

### S-6.207.05 Convert approved findings into original candidates

Owner step: S-6.207. State: proposed. Completion requires: offline_verified.

Acceptance: Each candidate has a distinct job, source relationship, rights decision and an owning Baltor contract.

1. Keep other-company material private by default.
2. Transfer one checked invariant into the existing owner.
3. Qualify exact new bytes through the ordinary component pipeline.

Evidence: Not yet recorded.

Next: Start with reusable schema-evidence and recovery invariants.

Comment: No raw other-company code or history is automatically published.

### S-6.218.01 Specify the hosted live-tool boundary

Owner step: S-6.218. State: ready. Completion requires: offline_verified.

Acceptance: Internal research, customer execution, file delivery and feed delivery remain distinct services and permissions.

1. Define discover, describe, invoke, status and cancel contracts over existing runtime owners.
2. Bind every operation to an exact version, engine, declared effect and audience.
3. Separate customer BYOK funding from any explicitly approved service-funded allowance.

Evidence: Not yet recorded.

Next: Draft the narrow first hosted-tool contract and adversarial cases.

Comment: An API provider is an engine; an endpoint listing is not a qualified customer tool.

### S-6.218.02 Qualify providers for customer-facing use

Owner step: S-6.218. State: ready. Completion requires: offline_verified.

Acceptance: Every exposed operation has working request/response evidence and permitted downstream use.

1. Check the provider contract, underlying data rights and any proxy/resale restrictions.
2. Test the declared endpoint and normalize explicit failures.
3. Hold deprecated, misleading, nonfunctional and unqualified offerings.

Evidence: Not yet recorded.

Next: Prioritize search, public company/job information and other bounded read-only tools.

Comment: Do not use account-sale or fake-engagement listings as tools.

### S-6.218.03 Build tenant-bound credential leases

Owner step: S-6.218. State: proposed. Completion requires: offline_verified.

Acceptance: One customer's tool can never resolve another customer's or an internal operator's credential.

1. Use the existing secret and credential-lease owners.
2. Bind provider, account, allowed operation, expiry and funding source.
3. Test logging, cross-tenant references, redirects and wrong-host failures.

Evidence: Not yet recorded.

Next: Keep secret values out of model context, manifests and responses.

Comment: A customer's BYOK call must never fall back to an internal key silently.

### S-6.218.04 Add per-tenant budgets and upstream quota reservations

Owner step: S-6.218. State: proposed. Completion requires: offline_verified.

Acceptance: Every accepted invocation fits both customer allowance and shared upstream capacity.

1. Reserve the maximum declared cost/request allocation before dispatch.
2. Record actual usage separately from estimates and unknown outcomes.
3. Test concurrent exhaustion, duplicate request IDs, cancellation and circuit breakers.

Evidence: Not yet recorded.

Next: Define capped allowances before pricing service-funded calls.

Comment: A flat subscription must not create unlimited upstream spend.

### S-6.218.05 Implement scoped live invocation

Owner step: S-6.218. State: proposed. Completion requires: offline_verified.

Acceptance: The gateway invokes only qualified operation IDs through declared engines and records bounded results.

1. Validate schema, tenant, entitlement, permission and destination before effects.
2. Use explicit idempotency and unknown-outcome reconciliation.
3. Keep native execution, remote reads and external mutations separate.

Evidence: Not yet recorded.

Next: Start with one read-only tool and its complete conformance kit.

Comment: No arbitrary URL proxy, cookie forwarding or broad network authority.

### S-6.218.06 Expose discovery and invocation through MCP and API

Owner step: S-6.218. State: proposed. Completion requires: offline_verified.

Acceptance: A customer harness discovers relevant tools without loading thousands of definitions into context.

1. Expose small capability cards and exact descriptions on demand.
2. Bind invocations to the selected contract/version.
3. Verify annotations, authorization and error behavior through the actual MCP transport.

Evidence: Not yet recorded.

Next: Reuse the existing hosted MCP/API owner.

Comment: Existing library and staff tools do not already provide this capability.

### S-6.218.07 Verify customer isolation and abuse controls

Owner step: S-6.218. State: proposed. Completion requires: live_qualified.

Acceptance: Two customer accounts pass positive and hostile cross-tenant tests with complete cost accounting.

1. Exercise wrong credentials, replay, oversized payloads and private-network targets.
2. Test provider outage, stale rights and subscription expiry.
3. Run a real task from a supported harness with an ordinary customer account.

Evidence: Not yet recorded.

Next: Keep the tool disabled for public sale until this journey passes.

Comment: No independent security certification is claimed by these tests.

### S-6.218.08 Reconcile top-tier entitlements and pricing

Owner step: S-6.218. State: proposed. Completion requires: live_qualified.

Acceptance: Checkout, permissions, displayed limits and the delivered service agree without changing existing subscriptions.

1. Measure unit economics for the qualified provider set.
2. Separate BYOK access from any capped included credits.
3. Apply the approved pricing process and preserve existing rates and grants.

Evidence: Not yet recorded.

Next: Keep the $49.99 target conditional on a workable delivered scope.

Comment: Model tokens and unlimited third-party calls are not included by implication.

### S-6.218.09 Launch and monitor the qualified hosted-tool pilot

Owner step: S-6.218. State: proposed. Completion requires: published.

Acceptance: Customers can use the advertised scope, inspect usage and stop or revoke access.

1. Release through the guarded main workflow.
2. Check every advertised customer path live.
3. Publish actual supported capabilities and monitor failure, cost and withdrawal conditions.

Evidence: Not yet recorded.

Next: Expand provider engines only after the pilot is measured.

Comment: The highest-tier idea is a development target, not an available sales feature.

### S-6.13.01 Qualify authenticated R2 file delivery

Owner step: S-6.13. State: ready. Completion requires: live_qualified.

Acceptance: R2 delivery preserves exact bytes, customer authorization, revocation and download accounting.

1. Keep the existing private mirror and source body-store contract.
2. Test authorized, denied, missing, corrupt and partial reads.
3. Measure latency and cost, then exercise rollback before selecting the engine.

Evidence: Not yet recorded.

Next: Prepare a bounded delivery canary; keep Fly delivery until it passes.

Comment: Mirrored bodies are not evidence that R2 already serves customer downloads.

### S-6.13.02 Place bounded collectors and durable jobs on Cloudflare

Owner step: S-6.13. State: proposed. Completion requires: live_qualified.

Acceptance: A selected acquisition or coordination workload passes its contract and failure tests within the approved infrastructure allowance.

1. Choose a workload from measurement and existing engine slots.
2. Use Workers with the appropriate queue or durable-work owner.
3. Test duplicate delivery, retries, checkpoint recovery, observability and rollback.

Evidence: Not yet recorded.

Next: Start with one collector or job coordinator, not a fleet of unmeasured workers.

Comment: Keep custom retrieval and authoritative records on Fly until a replacement is qualified.

### S-6.13.03 Evaluate the customer authentication boundary

Owner step: S-6.13. State: ready. Completion requires: offline_verified.

Acceptance: The decision distinguishes customer identity, internal access protection and bot checks.

1. Record the current Supabase customer identity and email-first account flow.
2. Compare a Cloudflare-compatible customer auth implementation with the current provider.
3. Test ownership, password choice, recovery, sessions, OAuth and existing-account migration before a cutover.

Evidence: Not yet recorded.

Next: Document the migration evidence needed and cost; do not replace login solely because DNS uses Cloudflare.

Comment: Cloudflare Access and Turnstile must not be mistaken for an already implemented customer sign-up service.

### S-6.12.01 Add private-by-default customer submissions

Owner step: S-6.12. State: ready. Completion requires: live_qualified.

Acceptance: An ordinary customer can submit a bounded skill, tool or file with explicit ownership and an isolated audience.

1. Reuse account identity, managed records and existing content storage.
2. Declare content type, source, rights, size and exact digest.
3. Test two-account isolation, malformed files, secrets and inert storage.

Evidence: Not yet recorded.

Next: Implement a narrow customer upload flow before adding a public contribution CTA.

Comment: The current Dot work log is staff-only and is not a customer private library.

### S-6.12.02 Add sharing and public-library submission controls

Owner step: S-6.12. State: proposed. Completion requires: live_qualified.

Acceptance: Private storage, selected-recipient sharing and public-review submission have separate explicit permissions.

1. Bind audience changes to exact content versions and consent.
2. Require a usable licence and rights declaration for public submission.
3. Test revocation, link leakage, cross-tenant metadata and the admission boundary.

Evidence: Not yet recorded.

Next: Keep uploads private unless the owner deliberately selects another audience.

Comment: Uploading never publishes, executes or sends a file to a model by itself.

### S-6.12.03 Reconcile the three offering cards and new-signup prices

Owner step: S-6.12. State: building. Completion requires: live_qualified.

Acceptance: Displayed scope, checkout, entitlement and delivered behavior agree without repricing existing subscriptions.

1. Use the latest Feeds instruction: $4.99 per month, free through December 31, 2026 Eastern with explicit paid opt-in.
2. Keep the $29.99 library and $49.99 upper-tier targets separate from current $29 checkout.
3. Release a purchase card only when its promised capability and billing journey pass.

Evidence: Release 83 serves three distinct cards with pricing outside the hero. The live matrix passes 483 checks and independent review passes 426 across ten hosts. Current $29 checkout is unchanged; local overnight tools are included during Preview, not sold as hosted supervision. The prepared additive-policy migration requires compatible readers before activation and does not rewrite paid grants.

Next: Review and deploy compatible billing readers before an additive new-signup price migration; qualify the hosted upper tier before sale.

Comment: Earlier $14.99 Feeds design remains historical; no existing paid rate or free grant is changed by this checklist.

### S-6.24.01 Prove one bounded overnight customer task

Owner step: S-6.24. State: ready. Completion requires: live_qualified.

Acceptance: A supported customer harness completes useful work with checkpoints, declared model access and complete usage accounting.

1. Select a frozen task and a no-extra-material baseline.
2. Use an authorized provider route with a verified allowance and explicit ceiling.
3. Test interruption, unknown outcomes, cancellation and the morning report.

Evidence: Not yet recorded.

Next: Retain current provider holds; do not reset the earlier token ceiling.

Comment: Local Preview tooling is available; hosted supervision and measured task benefit are separate.

### S-6.24.02 Verify OpenCode and another harness against live Baltor

Owner step: S-6.24. State: ready. Completion requires: live_qualified.

Acceptance: Ordinary customer connections retrieve exact material and complete a task in supported native harnesses.

1. Use a non-admin customer account and a clean setup.
2. Run discovery, selection, download and actual use.
3. Capture errors, denied operations, revisions, complete costs and cleanup.

Evidence: Not yet recorded.

Next: Run the customer path on this PC without borrowing administrator access.

Comment: A successful metadata request is not a completed harness task.

### S-6.201.01 Recover the authorized TensorArt asset history

Owner step: S-6.201. State: blocked. Completion requires: offline_verified.

Acceptance: A bounded export from the exact owner account includes available images and generation provenance with coverage limits.

1. Re-establish an account-bound read path through available browser or official export/API access.
2. Preserve prompts, model/version, seed, dimensions and asset checksums where available.
3. Keep assets private until their downstream use conditions are reviewed.

Evidence: The supplied key is stored. Browser connector access is unavailable; inspected local site sessions did not identify the target account.

Next: Resolve the missing target-account access without forwarding cookies to third parties.

Comment: No images or account history have been claimed downloaded.

### S-6.201.02 Complete one editable creative project and revision

Owner step: S-6.201. State: ready. Completion requires: offline_verified.

Acceptance: An attractive finished project survives a meaningful revision and clean reopen in a supported environment.

1. Choose one scoped scene, motion or interactive brief with measurable acceptance.
2. Reuse qualified native tools and record exact assets, versions and rights.
3. Render, revise and reopen; preserve failed attempts and source files.

Evidence: Not yet recorded.

Next: Select a small end-to-end creative proof rather than expanding untested templates.

Comment: Formats, asset counts and native loading do not establish a useful creative result.

### S-6.201.03 Produce a rights-cleared product demonstration

Owner step: S-6.201. State: proposed. Completion requires: published.

Acceptance: Marketing visuals show the actual supported workflow and do not imply an unmeasured benefit.

1. Create a reproducible screen recording or render from the accepted project.
2. Run any with/without comparison under matched conditions.
3. Check captions, claims, phone layout, sound and media rights before publishing.

Evidence: Not yet recorded.

Next: Use the accepted creative proof and recorded customer outcomes.

Comment: Preview clips are labelled as previews; no fabricated before/after result.

### S-6.102.01 Package and test the ChatGPT and Codex plugin

Owner step: S-6.102. State: building. Completion requires: offline_verified.

Acceptance: The package exposes only qualified MCP capabilities and passes an ordinary-user connection journey.

1. Reconcile the preserved plugin candidate with current official packaging requirements.
2. Test OAuth, scopes, tool descriptions, read/write annotations and optional UI.
3. Prepare support, privacy, terms and reviewer instructions without exposing operator tools.

Evidence: October 9, 2026: the October 5 work (8f1d6228, e68648f5, c3ee59b3 and two uncommitted edits) is on main, rebased with every superseded hunk recorded in its commits. OAuth client registration admits the documented callbacks of Claude, Cursor on the web, VS Code and Codex and any loopback port, and RFC 9207 issuer identification is advertised; the tests and gates are in docs/guides/chatgpt-app.md. The live proof of October 5, before the release that serves the presentation, passed 23 of 23 checks.

Next: Release the integration, then run tools/check_chatgpt_app_live.py with --expect-presentation and --screens as a fresh account, confirm the authorization server metadata advertises authorization_response_iss_parameter_supported, and keep the report with the release record. The remaining steps for each directory and client are in docs/guides/chatgpt-app.md.

Comment: Directory approval and discovery are external outcomes, not guaranteed engineering dates.

### S-6.102.02 Complete plugin review and release prerequisites

Owner step: S-6.102. State: proposed. Completion requires: published.

Acceptance: The exact submitted package is approved and deliberately published under the correct verified identity.

1. Check publishing organization/project and owner-completed identity requirements.
2. Submit only the tested supported scope with complete review material.
3. Record automated findings, review outcome and actual directory availability.

Evidence: Not yet recorded.

Next: Prepare everything engineering can do; personal identity verification remains with the owner.

Comment: No marketplace submission has been represented as complete.

### S-6.204.01 Measure onboarding and product use

Owner step: S-6.204. State: ready. Completion requires: live_qualified.

Acceptance: Activation, successful retrieval/use, retention, cost and support metrics come from actual service records.

1. Define a small funnel from sign-up to a useful customer result.
2. Instrument allowed aggregate events without leaking submitted content.
3. Run controlled journeys and inspect the resulting counts.

Evidence: Not yet recorded.

Next: Use measured activation and usefulness to guide the next batch and marketing.

Comment: Catalogue size alone is not product-market-fit evidence.

### S-6.204.02 Prepare launch, funding and startup-credit material

Owner step: S-6.204. State: ready. Completion requires: offline_verified.

Acceptance: Launch and funding material has current facts, source-backed credit eligibility and post-credit operating costs.

1. Build a concise demo, one-pager and evidence-backed deck.
2. Compare relevant startup programmes using their current primary terms.
3. Prepare founder-only applications and separate credits from sustainable unit economics.

Evidence: Not yet recorded.

Next: Prioritize the infrastructure already used and the next customer proof.

Comment: No advertising spend, personal verification, bank details or founder-account submission is automated.

### S-6.216.01 Expand useful SDG and competition-derived materials

Owner step: S-6.216. State: ready. Completion requires: published.

Acceptance: New Public Good material has a distinct useful job, clear rights, ordinary admission and working no-plan retrieval.

1. Use the existing Kaggle metadata connection and other permitted primary sources.
2. Build original small data, validation, accessibility or research tools with source and scope.
3. Qualify, publish and explicitly grant exact package versions through the existing Public Good policy.

Evidence: Not yet recorded.

Next: Choose unmet SDG jobs from measured coverage rather than multiplying labels.

Comment: The live 448 grants and 1,128 useful Public Good files remain a separate verified baseline.

### S-6.67.01 Review the complete public page and design surface

Owner step: S-6.67. State: ready. Completion requires: live_qualified.

Acceptance: Every advertised route, responsive layout, setup guide and claim is checked against delivered behavior.

1. Use the current route map and include every hostname.
2. Test desktop and phone layouts, navigation, pricing, accessibility and actual links.
3. Resolve hero/card regressions and retain failed cases before rerunning the exact candidate.

Evidence: Not yet recorded.

Next: Run the owning browser checks for each visible release and verify the live result.

Comment: Internal engineering plans do not become coming-soon sales promises.

### S-6.35.02 Publish a progress checkpoint after every completed subtask

Owner step: S-6.35. State: building. Completion requires: offline_verified.

Acceptance: The roadmap, generated tracker and dated evidence agree on completed work, failures and the next eligible action.

1. Update the owning roadmap subtask with evidence and its next action.
2. Regenerate the tracker and check that no local result is labelled as published.
3. Commit reviewed changes and report the exact user-visible outcome.

Evidence: The existing tracker reads roadmap.yaml; the new subtask view passes positive and refusal tests locally.

Next: Complete the first canonical subtask checklist and then advance it one result at a time.

Comment: Do not maintain a second mutable task authority or erase failed attempts.

### S-6.217.01 Reconcile recent prompts and action history

Owner step: S-6.217. State: building. Completion requires: offline_verified.

Acceptance: Accessible owner directions and actions from the requested time window map to existing roadmap owners with coverage gaps retained.

1. Read actual message timestamps and distinguish owner instructions from tool or agent output.
2. Reconcile changed prices, product scope, privacy, deployment and source requests.
3. Keep source text private and record only authorized generalizations in public documentation.

Evidence: The priority RapidAPI session is extracted; broader 24/36-hour history coverage and semantic review remain incomplete.

Next: Review prioritized recent chunks instead of treating extraction as full understanding.

Comment: Imported instructions are historical data, not current effect authority.

### S-6.215.14 Reach two million useful served files

Owner step: S-6.215. State: proposed. Completion requires: published.

Acceptance: The live catalogue has at least two million distinct admitted, non-withdrawn files, with composition and qualification coverage stated.

1. Repeat the generation-to-customer-verification cycle by measured cohort.
2. Track useful primary files and supporting files separately.
3. Verify the complete live count and publish the release evidence.

Evidence: Not yet recorded.

Next: Close the remaining gap with qualified cohorts, not a candidate count.

Comment: The first-million milestone stays complete; this milestone is not yet reached.

### S-6.214.08 Reach ten thousand active qualified sources

Owner step: S-6.214. State: proposed. Completion requires: live_qualified.

Acceptance: At least ten thousand canonical sources have current qualification and successful collection within their declared cadence.

1. Expand the measured source population.
2. Report stale, withdrawn, inaccessible and duplicate sources separately.
3. Verify the full active-source census and its reproducible query.

Evidence: Not yet recorded.

Next: Do not count untested directory matches toward this milestone.

Comment: Refresh frequency can differ by source; the target does not imply ten thousand daily paid calls.

## Being built now

| Step | Title | Status | Waiting on or next work |
|---|---|---|---|
| S-6.29 | Consolidate every branch and worktree onto main, restore what the September 22 merges dropped, and keep only the snapshot branch | building | S-6.28 |
| S-6.35 | Release automation and automated live checks after every release | building | S-6.26 |
| S-6.33 | Website fixes from the persona and interface reviews | building | S-6.12 |
| S-6.67 | Serve every built page and hostname surface | building | S-6.33 |
| S-6.65 | Open public registration with email-first sign-up | building | S-6.24, S-6.46 |
| S-6.85 | One way in: every customer account comes from Baltor's sign-up, and internal staff roles are fixed in code | building | S-6.65 |
| S-6.34 | One home for rules and authority, and a documentation cleanup | building | Land the authority section, reconcile the entry points, then apply the README plan. |
| S-6.30 | Engines behind fixed edges: the shared engine framework | building | S-6.28 |
| S-6.31 | The harness executor slot: delegate each step to a standard harness | building | S-6.30 |
| S-6.42 | Harness landscape: forks of Pi and OpenCode, and independent instances in every supported harness | building | S-6.31 |
| S-6.69 | The package factory: 10,000, then 100,000 approved packages, then 100 to 1,000 more each day | building | S-6.40, S-6.63, S-6.62 |
| S-6.197 | One unattended daily job from the day's approvals to a checked live catalogue release, with automatic rollback | building | S-6.62, S-6.119 |
| S-6.199 | Publish after one screen, then let feedback withdraw: the four-question screening review, automatic Community publication, a report button, nightly rescans, upstream checks and withdrawal rules | building | S-6.197, S-6.62 |
| S-6.203 | 10,000 packages served: measured at 1,000, 5,000 and 10,000, paged listing, one indexable page per item with sitemap entries | building | S-6.62, S-6.184, S-6.199 |
| S-6.205 | Library composition: every kind a harness picks up in every export, code read by the reviewer at Community, and the mix recorded per release | building | S-6.197 |
| S-6.206 | Step function tags: each served item carries the kinds of step it supports (acting, analysis, building, operating, planning, reasoning, research, reviewing, verification, writing), filterable in search and shown on the pages | building | S-6.62, S-6.205 |
| S-6.207 | The owner's own volumes as seed material: a read-only inventory with provenance classes, seed records per project, and generated harness files reviewed and published under the owner's authorship declaration | building | S-6.40, S-6.197, S-6.205 |
| S-6.200 | Continuous integration in 12 minutes or less, and fewer failed pushes: sharded self-test, cached environment, a records-only lane and a pre-push hook that runs the preflight | building | S-6.180 |
| S-6.201 | A page or a demo from one typed record, live on its own hostname within an hour: the page generator, the demo generator and hostname automation | building | S-6.67, S-6.62 |
| S-6.204 | The weekly number: visitors, accounts, paying subscribers and served packages, read from the service's own records and published to staff | building | S-6.120, S-6.6 |
| S-6.210 | Every owner request tracked: one ledger row per request with its steps and live state, checked against the roadmap and reported daily | building | S-6.76 |
| S-6.211 | User Feedback Intelligence on the hosted service: a rating of each download, requests for material and search gap counts, read by staff and turned into generation ideas | building | S-6.199, S-6.120 |
| S-6.212 | Unlinked public changelog, feature list and todo pages generated from the release records and the roadmap | building | S-6.67, S-6.35 |
| S-6.214 | Daily distillations: new papers, skills, plugins, protocol servers, services and repositories, each served as a summary page, RSS, JSON and downloadable components | building | S-6.213, S-6.81, S-6.197 |
| S-6.215 | Ten million served component files across useful code, data, native assets and maintained feeds, with qualified supply and complete delivery | building | S-6.40, S-6.213 |
| S-6.81 | Source scouts: search tools for skills, plugins, protocol servers and harness files | building | S-6.40, S-6.76 |
| S-6.216 | Account-required Public Good collection, header-linked browsing and 1,000 useful components across all SDGs | building | S-6.40, S-6.81, S-6.199 |
| S-6.217 | Library candidates from the owner's Dot direction: review and persona packs, rubrics, briefs, templates and worked examples, one per distinct job | building | S-6.215, S-6.216 |
| S-6.63 | An independent review panel of several model families | building | S-6.45 |
| S-6.119 | Community and Verified library tiers from the review panel, written as reviewed catalogue folders for release | building | S-6.63, S-6.40 |
| S-6.62 | Catalogue releases and library settings with good defaults | building | S-6.40 |
| S-6.37 | Demonstrations, case studies and benchmarks with and without Baltor, each on its own subdomain | building | S-6.33 |
| S-6.36 | Y Combinator application package, fact-checked | building | S-6.34 |
| S-6.4 | Bind the provisioning catalogue to durable records and tenant disclosure authority | building | Connect authoritative qualification adapters for every intelligence layer and templates; add restore checks without treating host attestation as independent qualification. |
| S-6.13 | Prepare portable deployment definitions and procedures for every hosting family | building |  |
| S-6.1 | Confine the complete provisioning write set | building |  |
| S-6.2 | Make unresolved guardrail decisions stop dependent effects | building |  |
| S-6.3 | Repair model-call occurrence identity, retention, and training persistence | building |  |
| S-6.26 | Remove unused pre-launch compatibility while retaining versioned handshakes | building |  |
| S-6.27 | Close independently reproduced contract and data-integrity defects | building | Metadata disclosure now binds the initial grant revision and revalidates it at completion. Revocation, replacement and entitlement changes refuse in local tests, and removing the guard is detected. Preserve the original  |
| S-6.28 | Streamline the main line to harness intelligence and delegate every step to a harness | building | Phase 2 moves execution behind the HarnessProcessSpec delegation contract; after the suite retirement at ea59df0, one executable step through a harness is phase 2's gate, not an in-process run, and a delegation claim met |
| S-6.5 | Expose provisioning through a versioned Model Context Protocol service | building | S-6.4 |
| S-6.6 | Persist usage and telemetry with acknowledgments and reconciliation | building | S-6.4 |
| S-6.21 | Connect payment lifecycle to durable subscription entitlements | building | S-6.4 |
| S-6.7 | Wire public solving to the declared provisioning dependencies | building | S-6.1, S-6.2, S-6.4 |
| S-6.12 | Build the website, subscriber dashboard, and operator workflows | building | S-6.5, S-6.6, S-6.21 |
| S-6.24 | Deliver client, authentication, endpoint-based model and native-harness onboarding | building | S-6.5, S-6.9, S-6.12 |
| S-6.15 | Deploy an authorized pilot and qualify its real request path | building | S-6.14 |
| S-6.120 | Staff tools: a staff protocol endpoint and admin routes for accounts, credits, messages, sign-up links, activity and catalogue releases | building | S-6.85 |
| S-6.184 | A library page anyone can open: Verified item cards, counts by kind and tier, one full sample and the release and withdrawal log, with downloads kept behind an account | building | S-6.39, S-6.67 |
| S-6.182 | The whole first journey on baltor.ai: the public base address, the emailed link, the published connection address and a check on every release | building | S-6.65, S-6.35 |
| S-6.177 | Every Baltor client asks with version 2 of the provisioning request, so an item a search offers is never refused on download | building | S-6.63 |
| S-6.25 | Expand the system map to every source file with explicit evidence limits | building |  |
| S-6.18 | Reorganize coherent code families and update current callers | building | S-6.1, S-6.2, S-6.3 |
| S-6.22 | Maintain sourced competitor, prior-art, funding, and strategic-path research | building | Review each changed or inaccessible source from a new source-watch report before editing a claim; keep the roadmap as the only task state. |
| S-6.77 | Maintenance as Practitioner Loops that stage candidates for independent review | building | S-6.76, S-6.41 |
| S-6.100 | Decision stations around the build step: typed judgments with swappable engines, measured | building | S-6.30, S-6.31 |
| S-6.180 | The browser suite runs every night on main and reports a failure without gating a deploy | building | S-6.177 |
| S-6.198 | Red-team the typed decision engines with the modern slavery scenarios: a request-screening station, every engine scored on the same five requests, and a showcase page | building | S-6.94, S-6.63 |
| S-1.4 | Evaluation product command over a frozen suite | building |  |
| S-1.7 | Runnable prompt and harness optimization command | building | S-1.4 |
| S-2.15 | Noise injection and explorative optimization over the evaluation product | building | S-1.7 |
| S-2.4 | Node grid over typed input parameters with separate counts | building | S-1.7 |
| S-3.1 | Offline convergence run over a grid with deterministic graders | building | S-2.4 |
| S-4.2 | Service software with tenants, keys, and metering | building |  |
| S-4.3 | Packaging tiers and pricing draft | building | S-4.2 |
| S-4.4 | Deployment to the owner's cloud account | building | S-4.2 |
| S-4.5 | Billing with metered usage | building | S-4.4 |

## Can start next

| Step | Title | Status | Waiting on or next work |
|---|---|---|---|
| S-6.44 | Harness Working Directory Compiler and native package compatibility | proposed | Extend the existing compiler and ClientLayoutProfile to carry activation, dependencies, entry points, reload behavior and exact native checks for executable packages. Preserve bytes, declared file modes and authority; qu |
| S-6.76 | Reusable development workflows and recurring reviews with declared effect policies | ready | Choose a scheduler that can run the workflows against this machine (a timer that starts a headless harness, or a hosted routine for read-only jobs) and record the first scheduled runs. |
| S-6.153 | Community spaces: the Discord layout applied from a spec by a one-time setup app, declared bot credentials, ordinary member checks and a measures log | proposed | Declare the three credential references, write the setup tool against a recorded dry run of the spec, and hand the owner the account steps in the private kit. |
| S-6.157 | Research watch sources for the chat platforms | proposed | Add the four sources and raise the limits, with tests. |
| S-2.10 | Intelligence access contract and no-direct-edit conformance rule | proposed |  |
| S-2.18 | Relayer each declared boundary package from core one boundary at a time | proposed |  |
| S-2.19 | Move the specifications at the docs root into their kind folders with redirect stubs | proposed |  |
| S-2.2 | Harness instance provisioning manifest verified against loaded files | proposed |  |
| S-2.23 | Cluster placement decision, one pod per node against a worker pool that hosts many nodes | ready |  |
| S-2.26 | Orphan recovery and shared model residency | proposed |  |
| S-2.29 | Harness capability profile with a confirmation that the instance loaded what it was given | proposed |  |
| S-3.7 | Mirror the name families in core into folders, one tranche at a time | ready |  |
| S-4.10 | Cost reservation ledger before work, reconciled after | proposed |  |
| S-4.13 | First release hosts serving and deterministic work, not customer harnesses | ready |  |
| S-5.3 | Career research | proposed |  |

## Waiting on earlier work

| Step | Title | Status | Waiting on or next work |
|---|---|---|---|
| S-6.68 | Support, status and incident response for paying customers | proposed | S-6.35 |
| S-6.46 | Close the dated deadlines and small gaps before inviting users | proposed | S-6.35 |
| S-6.39 | Search access policy: protect the library from scraping, with a free quota to start | proposed | S-6.32 |
| S-6.38 | A familiar customer dashboard with the full account lifecycle | proposed | S-6.33 |
| S-6.66 | Self-serve paid onboarding with a verified first load in the customer's harness | proposed | S-6.65, S-6.21, S-6.48 |
| S-6.48 | Setup paths for every kind of customer, with seeded starter files | proposed | S-6.42 |
| S-6.55 | Persona reviews after every release | proposed | S-6.33 |
| S-6.49 | Subscription plugins for Hermes Agent and OpenClaw | proposed | S-6.44 |
| S-6.50 | Baltor forks of OpenCode and Pi | proposed | S-6.42 |
| S-6.61 | One place for the customer's credentials and connections, with scoped access for every step | proposed | S-6.31 |
| S-6.32 | Hosted search as an engine slot with the measured policy and a relevance floor | proposed | S-6.30 |
| S-6.52 | More retrieval engines behind the search slot | proposed | S-6.32 |
| S-6.60 | A layer before every model call that decides one model or several | proposed | S-6.30 |
| S-6.40 | Grow the library: original package factory first, scheduled source ingestion later | proposed | S-6.30 |
| S-6.209 | Occupation, industry, level, language and geography tags on every served file, searchable in the signed-in dashboard | proposed | S-6.206, S-6.40 |
| S-6.202 | Quickstarts that are checked every night: one copy-paste setup per harness on Get set up, each run against the live endpoint | proposed | S-6.24, S-6.182 |
| S-6.213 | The product as a harness file: a first-party Baltor skill any harness installs to search and fetch from the library, plus a daily public library snapshot from each catalogue release | proposed | S-6.202, S-6.212, S-6.197 |
| S-6.70 | Serve 100,000 packages: pass the capacity probe with paged listing and an indexed search | proposed | S-6.62, S-6.32 |
| S-6.83 | Maintain 100,000 packages: re-verification, near-duplicates, deprecation and withdrawal | proposed | S-6.69, S-6.51 |
| S-6.64 | Independently authored alternatives to restricted-source ideas | proposed | S-6.63 |
| S-6.54 | Data-work intelligence packs as text and as tested code | proposed | S-6.40 |
| S-6.53 | Generate intelligence along the occupation grid | proposed | S-6.40 |
| S-6.45 | Make served files safe to trust: a malicious-skill regression set, exact licences and a bill of materials | proposed | S-6.40 |
| S-6.41 | Customer activity history and separately consented harness run records | proposed | S-6.31 |
| S-6.51 | Learn from retrieval: wrong context, repeated asks and items fetched together | proposed | S-6.41 |
| S-6.58 | Choose the model and the decision method for each step | proposed | S-6.31 |
| S-6.56 | Landing pages and demonstration pages by role | proposed | S-6.37 |
| S-6.47 | Measure each item against a no-skill arm and a raw-source arm before claiming a benefit | proposed | S-6.37 |
| S-6.59 | Go-to-market: early, useful replies under popular posts, approved by a person | proposed | S-6.36 |
| S-6.57 | A scale plan from one machine to many services | proposed | S-6.35 |
| S-6.78 | A release train for the service, the catalogue, client recipes and plugins, and the local engine | proposed | S-6.35, S-6.62 |
| S-6.79 | Feature flags and staged rollout through versioned host configuration | proposed | S-6.78 |
| S-6.8 | Connect credential leases and resource admission to harness lifetime | proposed | S-6.7 |
| S-6.10 | Publish qualified starter packages and prove client retrieval | proposed | S-6.4, S-6.5 |
| S-6.9 | Qualify actual instruction and capability use in native harnesses | proposed | S-6.5, S-6.7, S-6.8 |
| S-6.20 | Complete the classification-grid generation and improvement pipeline | proposed | S-6.3, S-6.7, S-6.10 |
| S-6.11 | Publish solutions and verify standalone reuse on fresh inputs | proposed | S-6.9, S-6.20 |
| S-6.23 | Exercise every required internal component through its actual owning entry point | proposed | S-6.3, S-6.7, S-6.8, S-6.9, S-6.20, S-6.11 |
| S-6.14 | Qualify the release candidate on the exact exported tree | proposed | S-6.4, S-6.5, S-6.6, S-6.10, S-6.12, S-6.13, S-6.21, S-6.23, S-6.24, S-6.26, S-6.27 |
| S-6.16 | Activate approved paid access and publish the release decision | proposed | S-6.6, S-6.15, S-6.21 |
| S-6.194 | A trust section and the web basics a reviewer checks first: CAA, DMARC reports, subprocessors, a dated list of what does not exist yet and a continuity answer | proposed | S-6.33 |
| S-6.192 | One privacy notice and terms revision for a paid service, drafted by engineering and approved by the owner before it is published | proposed | S-6.65 |
| S-6.190 | Supply-chain trust for served material: a working disclosure route, a published threat model, signed catalogue releases verified before writing, and scan results per item | proposed | S-6.45, S-6.62 |
| S-6.186 | Design partners and one weekly number: outside developers and teams through a finished task of their own, counted without tracking people | proposed | S-6.66, S-6.120 |
| S-6.183 | Distribution outside baltor.ai: pinned releases, the protocol registry and an OpenAI plugin | proposed | S-6.67 |
| S-6.181 | One truth on every public surface: a claims register that feeds a dated evidence page, each harness's recorded state beside its name, and a check over the website, the README, the deck and the capabilities record | proposed | S-6.33 |
| S-6.218 | Tenant-scoped hosted live tools for customer harnesses, with qualified provider engines and explicit funding | proposed | S-6.24, S-6.214 |
| S-6.19 | Continue flexible composition and controlled improvement research | proposed | S-6.3, S-6.20, S-6.14 |
| S-6.84 | Write the functional component standard into the development rules, with a check for each rule | proposed | S-6.30, S-6.34 |
| S-6.71 | One generated component index with a drift check | proposed | S-6.30, S-6.34 |
| S-6.72 | Contract test kits: every engine alone, components in groups, the system end to end | proposed | S-6.30, S-6.71 |
| S-6.73 | One topic and decision index, with a term conflict check | proposed | S-6.34, S-6.71 |
| S-6.74 | Pinned, preferred and automatic engine selection at every slot | proposed | S-6.30 |
| S-6.75 | An upstream engine and a Baltor-native engine for every adopted outside project | proposed | S-6.74, S-6.72 |
| S-6.80 | Keep every Harness File Profile current with a verified weekly refresh | proposed | S-6.44, S-6.76 |
| S-6.82 | News and release watchers that turn changes into component work | proposed | S-6.81 |
| S-6.86 | Task decomposition as a functional component with several engines | proposed | S-6.30, S-6.74 |
| S-6.87 | Step graph expansion: steps between steps, substeps, breadth, depth and advanced steps | proposed | S-6.86 |
| S-6.88 | Machine learning tools in the harness working directory, and when to use or train them | proposed | S-6.44, S-6.69 |
| S-6.90 | Side project: an entry to the Kaggle Gemma 4 Developer Agent competition and paper track | proposed | S-6.44 |
| S-6.91 | A step that lacks a tool reports a typed capability need, and search runs before any build | proposed | S-6.31, S-6.32 |
| S-6.92 | The tool authoring step: a candidate tool with its own tests, held-out tests from another Loop, and a typed repair summary | proposed | S-6.91, S-6.63 |
| S-6.93 | The step tool menu: a small, stable, permitted and relevant tool set for each step, with an abstention answer | proposed | S-6.32, S-6.44, S-6.61 |
| S-6.94 | Tool run contracts: duration class, timeout, heartbeat, polling, cancellation and idempotency, with task handles for long tools | proposed | S-6.61 |
| S-6.95 | Tool reliability and quarantine from recorded outcomes, with history kept | proposed | S-6.41, S-6.83 |
| S-6.96 | Failure fingerprints and known fixes, and a changed approach when a fingerprint repeats | proposed | S-6.41 |
| S-6.97 | The decision outcome review: tool decisions joined to their later outcomes and scored by an independent evaluator | proposed | S-6.41, S-6.58 |
| S-6.98 | Consented run traces as training and evaluation examples | proposed | S-6.41 |
| S-6.110 | Replayable showcase run records: step working directories, trajectories in the Agent Trajectory Interchange Format, and a cost and time ledger | proposed | S-6.37, S-6.44 |
| S-6.111 | The owner's publications index on papers.baltor.ai and the showcase hostnames, each serving its own page | proposed | S-6.67, S-6.110 |
| S-6.112 | DueCare rebuilt per step, with and without Baltor, on DueCare's own scorer and judges | proposed | S-6.110 |
| S-6.113 | The 2025 red-team finding tracked on current models, and the safety framework's checks repaired | proposed | S-6.110 |
| S-6.114 | Recreate and reuse: the owner's small tools rebuilt from their READMEs by small models, checked by the original tests | proposed | S-6.110, S-6.44 |
| S-6.115 | Configuration search on the owner's entity resolution pipeline, scored by an exact metric | proposed | S-6.110 |
| S-6.116 | media.baltor.ai: seeded short videos from the owner's media tools, made step by step | proposed | S-6.110, S-6.111 |
| S-6.117 | Original first-party media packages from the owner's MIT tools, through the independent review | proposed | S-6.40, S-6.63 |
| S-6.118 | Baltor's own social posts, made step by step and approved by a person | proposed | S-6.59, S-6.116 |
| S-6.140 | Author namespaces and a publish scope that a download key never carries | proposed | S-6.85 |
| S-6.141 | Submission intake: staged by form, interface or command line, confirmed by a signed-in person, kept where nothing serves it | proposed | S-6.140, S-6.62 |
| S-6.142 | Automated checks on every submission on a worker, and the same deterministic checks on the author's machine | proposed | S-6.141, S-6.40, S-6.45 |
| S-6.143 | A package's own tests in an offline sandbox on a worker that holds no Baltor secret | proposed | S-6.142 |
| S-6.144 | Independent review of submissions into the Community tier, never by the author or a declared model family | proposed | S-6.143, S-6.63 |
| S-6.145 | Versions, deprecation, yanking, withdrawal, reports, quarantine and takedown | proposed | S-6.144, S-6.83 |
| S-6.146 | Author pages, package pages and the publishing dashboard | proposed | S-6.145, S-6.67 |
| S-6.147 | Contributor terms and the privacy notice addition, published with the feature | proposed | S-6.141 |
| S-6.148 | Provenance for submitted packages: verified source links, trusted publishing and a signed publish record | proposed | S-6.144 |
| S-6.149 | A public recipe search: at most three Verified, body-free recipe cards per query, and public recipe pages, inside the search allowance | proposed | S-6.39 |
| S-6.150 | Recipe Rescue core: a chat request channel slot, a request gate and a deterministic recipe card answer, behind a host setting that is off | proposed | S-6.149 |
| S-6.151 | Recipe Rescue on Telegram: guest mode in any chat and an ephemeral /recipe command in the owned group | proposed | S-6.150, S-6.153 |
| S-6.152 | Recipe Rescue on Discord: a user-installed and server-installed app with /recipe and a message command, private answers first | proposed | S-6.150, S-6.153 |
| S-6.154 | Solution cards: consented write-ups of solved community threads on Baltor's own pages | proposed | S-6.153 |
| S-6.155 | Unmet recipe requests become consented demand records that feed the package factory | proposed | S-6.150, S-6.40 |
| S-6.156 | Nothing is sold inside chat apps until the Telegram Stars and Discord Premium Apps flows are qualified | proposed | S-6.151, S-6.152 |
| S-6.160 | Reproducible step materialization (experiment E01): every placement engine proves byte, mode, identity, home-folder and repeatability fidelity, with Microsoft APM as the first upstream engine | proposed | S-6.44, S-6.75 |
| S-6.161 | Installed, listed, loaded, used and useful (experiment E02): native skill placement measured against no material and forced inclusion | proposed | S-6.160, S-6.47 |
| S-6.162 | Reuse versus repeated model work (experiment E03): verified code packages against model-written code and a deterministic run | proposed | S-6.161, S-6.54 |
| S-6.163 | A lifecycle watch for every outside engine candidate: archival, licence change, acquisition and discontinuation hold its selection | proposed | S-6.22, S-6.74 |
| S-6.164 | Original harness packages from the agent stack research, through independent review | proposed | S-6.69, S-6.63 |
| S-6.165 | Token accounting by billing class, dated prices and price-weighted cost per accepted step | proposed | S-6.6, S-6.41 |
| S-6.166 | Cache-stable step files: shared material first, the step's own assignment last, and no volatile values before the shared part ends | proposed | S-6.44, S-6.165 |
| S-6.167 | The step proxy as an independent recorder and live limiter: an append-only exchange log written before forwarding, live call and token limits, and preserved reasoning items | proposed | S-6.61 |
| S-6.168 | Step reach controls: no secret reachable from a step, built-in tools counted in the step menu, deny-by-default egress and a data policy at each tool call | proposed | S-6.61, S-6.93 |
| S-6.169 | Failure records with the interaction edge, the fault side and the repair owner, labelled at the earliest unrecovered failure | proposed | S-6.96 |
| S-6.170 | A compaction policy slot with native, drop-only, model summary and fresh-restart engines, checked for instruction survival | proposed | S-6.31, S-6.165 |
| S-6.171 | A typed-decision provisioning engine that decides which skills, tools and context files the next step receives | proposed | S-6.58, S-6.93 |
| S-6.172 | Regularized selection for improvement Loops: an edit budget, a noise floor, a cost rule, a leakage review before evaluation and pruning | proposed | S-6.63, S-6.77 |
| S-6.173 | A harness efficiency benchmark with and without Baltor on the HarnessTax method, cheap models first | proposed | S-6.31, S-6.110, S-6.165 |
| S-6.174 | An evidence section on the efficiency page: outside evidence with its population and limits, and Baltor numbers only from run records | proposed | S-6.33 |
| S-6.175 | A harness engineering package family: ten candidates with their licence basis, review criteria and regression cases for published items | proposed | S-6.45, S-6.63, S-6.69 |
| S-6.176 | Baltor harness defaults for the Baltor forks and the step executor: file offload, asynchronous tools, constrained output with a capability check and a progress bound | proposed | S-6.50, S-6.94, S-6.165 |
| S-6.195 | Payable outside the United States: Managed Payments requested on every checkout, sandbox renewals with addresses abroad, and one pricing answer from that evidence | proposed | S-6.21 |
| S-6.193 | Identity controls: a second factor for every staff role, then OAuth for the protocol endpoint | proposed | S-6.120, S-6.5 |
| S-6.191 | The Team plan, built and checked before it is sold | proposed | S-6.38, S-6.120 |
| S-6.189 | Generation hygiene: certificate checks on every generation lane, a repository hygiene check, and a published note on how generated candidates are screened | proposed | S-6.63 |
| S-6.188 | Company pages: About, Work with us and Press from public facts, with the block that names who runs Baltor held until the owner decides | proposed | S-6.67 |
| S-6.187 | How Baltor is built with AI coding agents: a public statement, and a review by a second model family before a change to identity, billing, access or deployment code is pushed | proposed | S-6.34 |
| S-6.185 | A pre-registered with-and-without study on an outside population: SkillsBench v1.1 with no material, the raw skill, Baltor's selection allowed to add nothing, the forced bundle and the oracle | proposed | S-6.47, S-6.32 |
| S-6.179 | Candidates come from planned ideas, not from a mechanical grid of data types, tasks and domains | proposed | S-6.40 |
| S-2.11 | Search characteristics sidecar and hybrid retrieval over two adapters | proposed | S-2.10 |
| S-2.21 | Browser harness adapter with an element table reader and independent outcome verification | proposed | S-2.2 |
| S-2.25 | Execution profile per workload class instead of one shape for every node | proposed | S-2.23 |
| S-2.27 | Skill pack importer from public repositories into candidate Context Intelligence | proposed | S-2.10 |
| S-2.3 | Iterative publication with consumer output digests | proposed | S-2.2 |
| S-2.30 | Portable capability package, written and read in the published plugin layout | proposed | S-2.2 |
| S-2.31 | Provisioning set record, separating what was offered, fetched, exposed to the model, used, and verified | proposed | S-2.2 |
| S-2.8 | Middleware and wrapper abstractions for microservice hosting | proposed | S-2.2 |
| S-3.2 | Live convergence run on an authorized Ollama Cloud route | proposed | S-3.1 |
| S-3.3 | Adversarial validation of claimed improvements | proposed | S-3.2 |
| S-3.4 | Runnable optimizer proof on the live suite | proposed | S-3.2 |
| S-4.14 | Measure occupancy and egress from one instrumented deployment before choosing a host | ready | S-4.13 |
| S-4.15 | Honest units for a release the customer executes | ready | S-4.13 |
| S-4.16 | Define the deployment in the repository, not in a console | ready | S-4.13 |
| S-4.8 | Cloud capacity within a client budget, quotas, and spin-up policy | proposed | S-2.23, S-4.2 |
| S-4.9 | Administrator surfaces for system and client administrators | proposed | S-4.8 |

## Blocked

| Step | Title | Status | Waiting on or next work |
|---|---|---|---|
| S-6.178 | Two other model families review the first catalogue, whose September 21 approvals do not show them | blocked | S-6.63, S-6.177 |
| S-3.5 | Unseen tasks on an authorized frontier model and Kaggle export | blocked | S-3.3 |
| S-4.6 | Package index publication | blocked | the owner's package index account |

## Launch gates

| Gate | Met | Steps |
|---|---|---|
| A visitor can subscribe, use the dashboard, connect a client, and manage access | no | S-6.12, S-6.21 |
| An authenticated client retrieves qualified material with durable accounting | no | S-6.4, S-6.5, S-6.6 |
| The declared starter catalogue is qualified, versioned, and retrievable by supported clients | no | S-6.10 |
| Task graphs, atomic harness assignments, every intelligence layer, templates, and existing internal capability paths are connected and tested | no | S-6.1, S-6.2, S-6.3, S-6.7, S-6.8, S-6.9, S-6.20, S-6.11, S-6.23 |
| A new user can install, authenticate, configure a provider, and use the supported harness architecture | no | S-6.24 |
| Tenant operations, restart, restore, upgrade, and rollback are exercised | no | S-6.12, S-6.13, S-6.14 |
| The chosen authorized hosting target passes the same acceptance suite | no | S-6.15 |
| Approved pricing and payment integration reconcile with durable usage | no | S-6.16 |

## Delivery packages

| Package | Title | Stage | Steps done |
|---|---|---|---:|
| D-01 | Freeze the handoff and repair release blockers | initial_service | 1 of 3 |
| D-02 | Finish domain and authentication email | initial_service | 0 of 3 |
| D-03 | Connect customer accounts and client access | initial_service | 0 of 3 |
| D-04 | Complete sandbox subscriptions | initial_service | 0 of 3 |
| D-05 | Connect cloud records, files and retrieval | initial_service | 0 of 3 |
| D-06 | Prove selected material reaches each step | core_proof | 0 of 4 |
| D-07 | Qualify overnight local work and recovery | core_proof | 0 of 4 |
| D-08 | Build useful expertise and reusable outputs | core_proof | 0 of 4 |
| D-09 | Measure token savings and context usefulness | core_proof | 0 of 4 |
| D-10 | Simplify the website and finish customer journeys | initial_service | 0 of 3 |
| D-11 | Exercise operations and make the release decision | public_launch | 0 of 5 |
| D-12 | Continue interchangeable engines and governed improvement | continued_improvement | 0 of 4 |
| D-13 | Qualify execution and service security boundaries | core_proof | 0 of 4 |
| D-14 | Operate intelligence ingestion, review and withdrawal | core_proof | 0 of 5 |
| D-15 | Operate reliability, telemetry and customer data lifecycle | public_launch | 0 of 5 |
| D-16 | Qualify installation, distribution and compatibility | public_launch | 0 of 6 |
| D-17 | Open a private beta for invited users | initial_service | 0 of 6 |
| D-18 | Ship the September 22 review: one main line, live checks and launch readiness | initial_service | 0 of 9 |
| D-19 | Engines behind fixed edges for every functional component | continued_improvement | 0 of 9 |
| D-20 | Meet the open standards and make served files safe to trust | initial_service | 1 of 5 |
| D-21 | Meet customers in the harness they already use | initial_service | 0 of 4 |
| D-22 | Learn from every request and grow the library by occupation and data work | continued_improvement | 0 of 8 |
| D-23 | Show, review, reach and scale | initial_service | 0 of 5 |
| D-24 | Take requests for access and invite one person from them | initial_service | 0 of 3 |
| D-25 | Go fully live: open registration and self-serve paid onboarding | public_launch | 2 of 17 |
| D-26 | Reach 10,000 and then 100,000 approved harness packages, then add 100 to 1,000 a day | public_launch | 2 of 23 |
| D-27 | Clear components: one index, contract test kits and one home for every topic and term | continued_improvement | 0 of 4 |
| D-28 | Selectable engines at every slot, with a Baltor-native engine beside every adopted project | continued_improvement | 0 of 9 |
| D-29 | Agents that manage and improve the system | continued_improvement | 0 of 6 |
| D-30 | A release train for upgrades, features, packages and engines | public_launch | 0 of 4 |

## Only the owner can do these

| Action | Title | Phase |
|---|---|---|
| OWNER-01 | Private pilot limits are recorded | prepared |
| OWNER-02 | Fly account and private pilot are prepared | prepared |
| OWNER-03 | Close the identity provider's back-door sign-up so that Baltor registration can open to everyone | now |
| OWNER-04 | Engineering prepares private intelligence storage | engineering |
| OWNER-05 | Stripe sandbox credentials are prepared | engineering |
| OWNER-06 | Domain and registrar access are prepared | engineering |
| OWNER-07 | Existing credentials are privately stored | prepared |
| OWNER-08 | Engineering chose the first client and leaves the model to the customer | engineering |
| OWNER-09 | Choose optional decision engines and fallback order | optional |
| OWNER-10 | Engineering compiles the starter catalogue and independent reviewers approve each item | engineering |
| OWNER-11 | Read the drafted privacy notice and terms before live charging | before_charging |
| OWNER-12 | Resend management is authorized; engineering completes email | engineering |
| OWNER-13 | Engineering applies exact hosted settings | engineering |
| OWNER-14 | Invite real people when you choose; engineering has tested the journey in containers | after_endpoint |
| OWNER-15 | Activate the live Stripe account and say go | prepared |
| OWNER-16 | Give the legal entity name and a contact address, and approve the terms and privacy text | before_public |
| OWNER-17 | Grant a model-call budget for measuring the launch benefits | optional |
| OWNER-18 | Choose the paid identity and email plans, which take hosting above the recorded allowance | before_public |
| OWNER-19 | Name who approves and posts replies, and from which accounts | optional |

## Done (49 steps)

- S-6.43: Speak the current protocol revision: negotiate the 2026-07-28 Model Context Protocol beside 2025-11-25 (live_qualified)
- S-6.89: Superadmin user management and the first 10 accounts free each month (live_qualified)
- S-6.99: Sign-up links a superadmin sends through Baltor's own sign-up, and a confirmation page that waits for its settings (offline_verified)
- S-6.102: A free public directory of MCP servers and agent APIs at /directory (offline_verified)
- S-6.101: A public directory of models, endpoints and local runtimes, with a can-I-run hardware check, at /models, /endpoints and /can-i-run (offline_verified)
- S-6.196: The review panel reads imported packages: a reader for the imported layout, criteria written for imported material, calibration controls and a yield pilot (live_qualified)
- S-6.208: One component library with combined kind counts, source and review details, and no customer-facing review classes (live_qualified)
- S-6.17: Maintain one continuation plan and regenerate its status artifact (offline_verified)
- S-6.121: The deck at deck.baltor.ai: every number from a saved record, the hostname root, and the slides only the owner can supply (offline_verified)
- S-0.5: Text conformance, standalone export, example 26, export command (published)
- S-1.1: Temporal fact graph in Context Intelligence (published)
- S-1.10: Detection and correction node family with confidence (offline_verified)
- S-1.11: Job-description-seeded intelligence pipeline and first seeds (offline_verified)
- S-1.12: Adversarial validation and audit of every matrix feature (offline_verified)
- S-1.2: Memory versioning with history, diff, and rollback (published)
- S-1.3: Shared memory scopes with writer identity (published)
- S-1.5: Operation cost records wired into invocations and calls (published)
- S-1.6: Model-versus-not decision record per operation (published)
- S-1.8: Specialist training from learnable call records (published)
- S-1.9: Feature matrix regeneration with evidence links (offline_verified)
- S-2.1: Step efficiency review record with a deterministic judge (published)
- S-2.12: Component interface and intelligence flow documentation with inconsistencies (offline_verified)
- S-2.13: Typed-decision model route (a Jev-class judge) behind the model call boundary (offline_verified)
- S-2.14: Feature component breakdown with the four intelligence layers as areas (offline_verified)
- S-2.17: Records index and folder charters (offline_verified)
- S-2.20: Typed action decisions over an element table (offline_verified)
- S-2.22: Local resource detection and a supervisor for harness instances (offline_verified)
- S-2.24: Hibernation protocol, capacity reservation, and progress-aware stalls (offline_verified)
- S-2.28: One instruction file per harness instance, in the name every harness reads (offline_verified)
- S-2.32: Harness Intelligence, one catalogue of what a harness instance can be given (offline_verified)
- S-2.33: A run searches all four intelligence layers rather than one (offline_verified)
- S-2.34: External service capabilities, recorded without their credentials (offline_verified)
- S-2.35: Tag dimensions for intelligence, so it can be found and its gaps named (offline_verified)
- S-2.36: One authentication shared across every harness instance, by lease (offline_verified)
- S-2.37: One atomic node provisioned into one harness folder (offline_verified)
- S-2.38: A queue of exact capability gaps, each one precise enough to build against (offline_verified)
- S-2.39: Guardrails as records a run carries, evaluated at declared points (offline_verified)
- S-2.40: A spawned node's folder is filled before the node starts (offline_verified)
- S-2.41: Keep what a run's model calls can teach, without keeping what must not be kept (offline_verified)
- S-2.5: Versioned training data store and heuristic adoption policy (published)
- S-2.6: Dimension inventory at every level (offline_verified)
- S-2.7: Prompt element and response-style dimensions as grid axes (offline_verified)
- S-2.9: Intelligence storage analysis and measurement (offline_verified)
- S-4.1: Worker image, Kubernetes manifests, placement policy (offline_verified)
- S-4.11: A usable total token ceiling, or an honest refusal that names what it needs (offline_verified)
- S-4.12: The first paid surface serves what goes into a harness instance (offline_verified)
- S-4.7: Worker image publication to the GitHub Container Registry (published)
- S-5.1: Branding record (offline_verified)
- S-5.2: Business paths record (offline_verified)
