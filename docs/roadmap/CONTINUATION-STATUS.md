# Continuation status

Kind: generated planning artifact.

Source: `roadmap.yaml`. Regenerate with
`python tools/build_continuation_status.py`; `--check` rejects a stale view.

Plan fingerprint: `a5cc2fce5c5f660283699caddd21b781b7e377045730209168295fd21d635312`.

Started: 2026-09-19T14:12:54Z. Historical target: 2026-09-20T14:12:54Z. This is not a release forecast.

A subscription website and dashboard with payments, all intelligence layers and templates served through one authenticated service, and a verified internal graph-to-harness architecture; customers run their harnesses.

[Execution plan](CONTINUATION-AND-LAUNCH.md) | [Hosting procedures](../guides/hosting-and-deployment-procedures.md) | [Owner checklist](../guides/launch-owner-checklist.md) | [Style guide](../guides/product-style-guide.md)

## Next eligible work

- Launch: none currently ready; review dependencies and authority.
- Improvement: S-6.76: Reusable development workflows and recurring reviews with declared effect policies.

## Work in progress

These steps are already being built. They are not completed dependencies or permission to deploy.

| Step | Current evidence | Next local work |
|---|---|---|
| S-6.29 | September 22: every ref and every dirty worktree archived in ~/loop-engine-archive-2026-09-22; the open security merge finished with its two silent losses restored and two new checks; silent losses of five earlier merges measured; consolidation running in detached worktrees. September 23: GitHub keeps only main and the checkpoint branch; release/catalogue-live was fully in main, bundled and deleted. Of 124 local branches, 77 merged ones were deleted after a verified bundle (local-branches-20260923T012120.bundle); 20 hold content missing from main (patches and missing-line lists in /home/username/.le-safety/unmerged-branch-patches/), and the five merge drops the September 22 handoff records are still missing on main. A triage and restoration pass is running; 87 worktrees use 682 GB, of which 25 are candidates for removal. September 23, 06:50 Eastern: the triage of every branch and merge drop that never reached main, with an ordered merge plan, is docs/verification/BRANCH-CONTENT-TRIAGE-2026-09-23.md. It starts with a read-only count of version 1 billing customer effect records in the live store, then merges the consolidation line 44a4b42 with named conflict rules, then the intelligence items the consolidation run never reached. | Follow the triage report's merge plan in order, each step in a detached worktree with a line survival check and the full checks, starting with the read-only billing record count. |
| S-6.35 | September 22: release 12 needed a manual apply-grants and a key reissue; the failed-attempt limit was switched on in the host file and proven against a forged address. The guarded workflow now applies the packaged grants on the one Machine after the deploy, through the Machines API exec call as the service user, requires exit code zero and exactly one grant record, and repeats the readiness check; tools/test_fly_deployment.py fails when the step is removed, moved, pointed at any Machine or stripped of either gate. Both container drills state the client address source, and the Fly container check requires the image to refuse a host file without it. Locally, an image of this work together with the restored measured health record passed the Fly container check 18 of 18 and the client journey drill 34 of 34; without that restore each fails its health check. No release has run the grant step yet. September 22, 21:41 Eastern (01:41 UTC September 23): Fly release 15 from GitHub main a51ac96, built by the guarded workflow run 35807183861 after continuous integration run 35805955473 passed; deploy switch off at 01:41:14 UTC. Every workflow step passed, including the readiness poll and the grant step on the Machine. Live checks afterwards: health version 2 alive and ready; website 73 of 73 on baltor.ai, www and app and 72 of 73 on the fly.dev address (the known host-name check); catalogue 6 of 6 with 34 offered and 9 withheld until effects are declared; HEAD / still 404. September 23, 01:28 Eastern (05:28 UTC): Fly release 16 from main 06b903d, image sha256:0fa11f15..., guarded workflow run 35822425444 after CI run 35821280608; grants and the new billing policy step passed on the Machine; switch off 05:28:57 UTC. Live: every hostname the same capabilities; health ready with billing_policy_current and retention_sweep_current; website 74 of 74 on baltor.ai, www and app, 73 of 74 on the fly.dev address; catalogue 6 of 6; hosted service 19 of 19; waiting list recorded, refused a repeat, erased. Record pilot-release-14.json. September 23, 02:10 Eastern (06:10 UTC): Fly release 17 from main 381cc52, image sha256:cd593bc4..., run 35825420925 after CI run 35824162536, every step passed; switch off 06:11:22 UTC. Live: health ready with catalogue_view_current; website 74 of 74 (73 on fly.dev); catalogue 6 of 6; hosted service 19 of 19; waiting list recorded, refused a repeat, erased. Record pilot-release-15.json. Both first runs of the live checks failed for environmental reasons and are kept beside their successors: release 16's used the shared main checkout's older tools and the phone item's release 15 digest (a catalogue anchor rewrites every body's anchor line, so every digest changes), and release 17's worktree lacked the .venv link the protocol client runs from. | Move the live check sequence into a repository tool that runs from the released revision, reads each item digest from that revision's packaged manifest and links its own environment, and have the guarded workflow or a follow-up job run it on every configured hostname; keep a check that HEAD on the public root succeeds. |
| S-6.33 | September 22: five persona testers and an interface review on the live site; no persona would sign up or pay; ten ranked fixes with exact copy and code locations. A local homepage repair removed the right-hand example workflow and put working steps first. The named old-layout check failed before repair; the local browser suite then passed 318 of 318 checks and 33 removed-guard controls. The changed page has not been deployed. September 22 late evening, the owner: "we need a more advanced demo, more improved landing page, there is too much white, no clear seperations or off white or best practices or horizontal breaks seperating sections, etc also get started and join the waiting list are redundant". The redesign started in the detached worktree /home/username/.le-wave3/landing-redesign. The privacy notice went live at /privacy in Fly release 15; a store removal operation and retention sweeps are being built so its retention sentences hold. September 23: a redesign built from the design canvas (607c3a4): one invitation action per access state, the fresh harness per step in the opening message, the demonstration below it at full width, a 65 pixel phone header with a keyboard menu, the primary action at 451 to 503 pixels on a 390 by 844 screen, the invitation email field in the first phone viewport, AA contrast on seven pages in both themes, and a placeholder summit mark as header and page icon; browser suite 472 of 472 with 66 of 66 controls. Codex's live and draft reviews (docs/verification) supplied the measured targets. Logo rounds three and four are on the design canvas; the owner will pick the final mark. September 23: the redesign reached the live service in Fly release 18 (519c82af, 04:52 Eastern): website checks 81 of 81 on baltor.ai, www and app, and the homepage's connection example names `https://baltor.ai/mcp`. Fly release 20 (f7c89465, 06:47 Eastern) added the signed-in header (Account and Sign out), moved the homepage demonstration from the phone item the data cleanup study found harmful to split_address_lines_into_components with a check that refuses any item a recorded measurement found harmful, and shows usage as a table; browser suite 495 of 495 with 76 of 76 controls; live website 81 of 81. September 23 (morning, owner directions recorded in docs/context/SESSION-HANDOFF-2026-09-23.md): a 141-row inventory of everything the redesign cut or never shipped (docs/verification/WEBSITE-CUT-INVENTORY-2026-09-23.md); a design review of release 17 against live release 20 with 457 screenshots and measured padding (docs/verification/WEBSITE-DESIGN-REVIEW-2026-09-23.md); a device sweep of 18 sizes and page depth on the live site (artifacts/handoff-2026-09-23/website-audit/); a live probe (docs/verification/HANDOFF-SITE-UAT-2026-09-23.md). Merged: release 21 (terms at /terms, the traced logo), the restored header and four-group footer, a sticky header, Get set up at /setup with /connect as an alias, the waiting-list page, and /get-started served. Saved as patches under artifacts/handoff-2026-09-23/patches/: the email-first sign-up with the Get started funnel, the documentation pages, the use-case pages with status and the hostname map. September 23 Codex takeover: the owner removed the homepage category pill. Local repair removes it, replaces the absolute drift claim with a design aim, adds cache validators and content-versioned direct asset references, supports HEAD, and raises the bounded Fly proxy allowance to 128 while retaining eight API workers and one machine. Fifteen owning tests, 551 browser checks and 91 removed-guard controls pass; independent review found no scoped blocker. The Python 3.11 review-configuration import failure from GitHub was reproduced and repaired with 48 tests. See docs/verification/HOMEPAGE-BADGE-AND-ASSET-DELIVERY-2026-09-23.md. These repairs await exact-tree integration checks and live verification. September23 at16:29UTC: checked main1920296c deployed through guarded workflow35888814908, exact image sha256:4c82835554d45d22efa6a56753da2039a51e34278f1e6e5c3408524984b56857. The homepage pill is absent. All eight hostnames returned200 and identical capabilities; required health checks pass, catalogue6/6 and authenticated service19/19. Four simultaneous website suites found no styling errors; three passed98/98 and the technical Fly hostname had one wording-check false positive from its own URL. The checker successor masks only the exact service origin and still refuses an adjacent retired marketing claim. Four live assets returned correct SHA256 ETags,304 responses and matching empty HEAD responses; sixteen requests at concurrency4 all returned200. Registration stays closed pending the secure signup flow. Previous release20 image is retained for rollback. Follow-up consolidated documentation candidate has six page bodies, seven rewritten source guides, strict index/body validation, 551 existing browser checks and81 dedicated documentation checks passing locally. It is not yet deployed. All four additional live hostnames passed99/99 browser checks after release21; the technical hostname successor also passed99/99. | Follow the ordered work of docs/context/SESSION-HANDOFF-2026-09-23.md: merge the saved patches (sign-up and funnel, documentation pages, use-case pages), land the design standards with tools/test_website_site_map.py and tools/check_website_layout.mjs switched on in CI, apply the homepage polish patch and the scroll budgets (first screen holds the h1, lead and action; 64 px band padding; homepage under 4,000 px at 1440 wide; no dark bands), then per-page crawler titles and descriptions, robots.txt, a sitemap, a www redirect, HEAD on every page and long caching for versioned files; release and run the device lab and acceptance tests on the live site. |
| S-6.67 | September 23, 2026, the owner: "We need to get all of the pages that we built fully working and fully live, there is no point in building a page if we can't show it." Live release 21 answered 404 for /models, /use-cases, /status, robots.txt and sitemap.xml, and five hostnames served the same homepage (checked September 23 at about 14:40 Eastern). | Land the documentation pages from the Codex consolidation, write the use-case and status views from the saved patch, generate robots.txt and sitemap.xml from the typed site map, then switch tools/check_website_site_map.py on in continuous integration. |
| S-6.65 | September 23, 2026, the owner: "I have approved the terms, you can open it". The identity probe of September 23 found that the provider's public sign-up keeps the first password, so activation waits for OWNER-03. Codex integrated the email-first flow, switched off, in its consolidation of September 23. | After OWNER-03, stage the secrets, switch registration_enabled and email_signup_enabled on in the host configuration, release, and run the live sign-up journey with a fresh address and the negative controls. |
| S-6.34 | September 22: a README audit of 259 entry points (keep 173, update 72, archive 8, merge 5, remove 1) and a register of 128 owner directions, nine recorded nowhere. | Land the authority section, reconcile the entry points, then apply the README plan. |
| S-6.30 | September 22: three independent designs, a judge synthesis and prior-art research (standard-library entry points for discovery, exact sign tests for evidence, deterministic hash bucketing for side-by-side samples). September 23: wave A of the engine framework (F1 engine records, F2 the catalogue of 45 engine slots, F11 live dependency guards, X1 the harness recipe catalogue, X2 the step executor adapter contract) was integrated at a557586 with no line lost, merged into main in 5c188ab and released in Fly release 17. Self-test 3,206 of 3,206 on the release line. The integrator's 34 open problems, deduplicated, are in docs/verification/ENGINE-FRAMEWORK-WAVE-A-INTEGRATION-2026-09-23.md. September 23: an ecosystem edge map (docs/research/ECOSYSTEM-EDGE-MAP-2026-09-23.md) places each reusable project and standard behind a slot of src/loop_engine/data/engine_slots.yaml, with trials here: FastMCP 4.0.5 exposed and ran a destructive endpoint by default and narrowed only with an allowlist plus a final exclude rule; DBOS 3.0.0 re-ran an interrupted external action unless reconciled by a stable key; the Agent Skills validator rejects Baltor's underscore identities and a version field. It proposes three slots (step_attempt_durability, interaction_stream, release_inventory_export) and one new kind (configuration compiler under material_install_layout), and corrects the outside map: OpenMuse at bb7ce4e requires CopilotKit Intelligence in every mode. September 23 Codex research: docs/research/FUNCTIONAL-ENGINE-WRAPPING-RESEARCH-AND-IMPROVEMENTS-2026-09-23.md reviews functional engine wrapping against current source and primary standards; proposes behavioral qualification, separate binding dimensions, state migration, explicit translation losses, and retry/cancellation ownership. Records and bounded adapters exist; this research does not implement a universal selector or activate new engines. | Complete shared selection and at-use binding using existing records; qualify semantic behavior and state transitions per docs/research/FUNCTIONAL-ENGINE-WRAPPING-RESEARCH-AND-IMPROVEMENTS-2026-09-23.md before adopting the framework in executor, compiler, search, email, store, model, identity and billing slots. |
| S-6.31 | September 22 research: the Agent Client Protocol Python library (Apache 2.0, Python 3.10 or newer) reaches about 39 agents; OpenCode supports it natively. September 23: wave A of the engine framework (F1 engine records, F2 the catalogue of 45 engine slots, F11 live dependency guards, X1 the harness recipe catalogue, X2 the step executor adapter contract) was integrated at a557586 with no line lost, merged into main in 5c188ab and released in Fly release 17. Self-test 3,206 of 3,206 on the release line. The integrator's 34 open problems, deduplicated, are in docs/verification/ENGINE-FRAMEWORK-WAVE-A-INTEGRATION-2026-09-23.md. | Implement the records and the first adapter after the framework package. |
| S-6.42 | September 22: owner direction; opencode 1.18.32, codex 0.155.1, pi and claude are installed on the workstation. ZCode is documented as an unqualified additional harness candidate at source revision 872ad960de7ec172591f7e1952f7849229f94521 in docs/research/ZCODE-AND-HARNESS-INTELLIGENCE-MARKET-REVIEW-2026-09-22.md; no native run was tested. September 22: Codex 0.155.1, OpenCode 1.18.32, Claude Code 2.1.280 and Pi 0.73.1 each started as a separate instance for one step with no model call and loaded only that step's material, once HOME was empty and each harness had its own configuration folder (docs/research/HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md). Loading is proven; use by a model is not. The fork review recommends thin forks whose Baltor behavior lives in a Pi package and an OpenCode plugin (docs/research/HARNESS-FORKS-2026-09-22.md). September 23: wave A of the engine framework (F1 engine records, F2 the catalogue of 45 engine slots, F11 live dependency guards, X1 the harness recipe catalogue, X2 the step executor adapter contract) was integrated at a557586 with no line lost, merged into main in 5c188ab and released in Fly release 17. Self-test 3,206 of 3,206 on the release line. The integrator's 34 open problems, deduplicated, are in docs/verification/ENGINE-FRAMEWORK-WAVE-A-INTEGRATION-2026-09-23.md. | Research the forks and run the independent-instance tests without model calls where possible. |
| S-6.69 | September 22, 2026: 10,000 is the first milestone and 100,000 the target. September 23, 2026, the owner: "aggressively get everything working with at least 100,000 harness component files" and "generate and maintain adding 100 to 1,000 more harness components per day". The milestone unit is a distinct approved package (decision of September 22); the files inside the packages are counted beside it. | Calibrate the three-family panel on the malicious and benign controls and measure its throughput, run wave 5 and the Codex twelve-package cohort through it, then size the daily waves to the measured capacity. |
| S-6.62 | September 22 evening: owner direction for 10,000 items, multi-model review, managed releases of new files, and user settings with good defaults. September 22 late evening, the owner: "how can we add harness intelligence files and have their attributes/searchable columns/details without having to redeploy the entire system". Engineering decided the design above; the build started the same night in the detached worktree /home/username/.le-wave3/catalogue-releases. September 22 late-night offline 100,000-row metadata probe: the synthetic manifest reached 122,071,567 bytes against the 2,000,000-byte host loader, the bare unpaged list reached 73,314,429 bytes against a 262,144-byte response ceiling, and current per-request Retriever build took 48.57 seconds and 2.10 GiB peak resident memory. No real bodies or active approvals were part of the fixture. See artifacts/hundredk-serving-probe-2026-09-22/README.md. September 23: built in 18337ff and released in Fly release 17: a content-addressed body store, releases with an active pointer and durable withdrawals, an attribute schema defined as data, search filters, grants that can follow the active release, five operator commands and a catalogue state marker that older images refuse. Locally at 100,000 items one Machine breaks on memory (a swap needs about 2 GB), disk, a 65 second swap and hybrid search speed. Switched on live at 06:17 to 06:21 UTC: the host file gained a catalogue section (backed up first), the first release ad440982... (43 items) was published from a bundle without a redeploy, and the source moved to the store; health, catalogue 6 of 6 and website 74 of 74 passed. The runbook's follow-catalogue-release --all-tenants step then gave all six accounts every item, including the isolation account pilot-boundary, and the hosted service check failed two isolation checks; the five non-owner accounts now deny every current item and the check passes 19 of 19. Record catalogue-release-activation-1.json. Fly release 16 and older refuse the host file now. September 23, 05:27 Eastern: Fly release 19 from 421f37ce (image sha256:23b00490...) shipped the isolation fix: stop-following-catalogue-release returns an account to a snapshot of what it receives now, --all-tenants moves only accounts that already receive every served item, and the runbook's first-time step follows only pilot-owner; 16 new checks with removed-guard controls, and a replay of the release 17 step that fails under the old rules. Live repair at 09:30 UTC: the five non-owner accounts returned to empty snapshots and the hosted service check passed 19 of 19. Then the second catalogue release c824a1d2... (43 items, anchored to 565e133) was published without a redeploy and served within a minute; website 81 of 81, catalogue 6 of 6 and hosted service 19 of 19 afterwards. Record pilot-release-17.json. | Publish the first release that adds new items (the library-scale importer's reviewed candidates once the independent review panel approves them); then the account library settings, pinning a release for search, paged listing, and the index-file and object-storage engines the 100,000 item measurement calls for. |
| S-6.36 | September 22: market analysis with dated competitor prices and a fact-checked draft in progress. | Finish the draft and the fact check; the owner adds personal background, contact details and equity facts. |
| S-6.4 | The SQLite-backed service persists tenants, key digests, subject bindings, exact grants, revocation and usage. The durable checkpoint records 153 owning and dependent checks and 11 detected mutants. Canonical all-layer qualification adapters and hosted database deployment remain open. | Connect authoritative qualification adapters for every intelligence layer and templates; add restore checks without treating host attestation as independent qualification. |
| S-6.13 | One tested service image runs on the existing Fly Machine and encrypted volume. A prior deployed backup passed 15 local restore checks. Release 7 carries the account code, switched off by host configuration. Releases one to seven were built on one workstation from an uncommitted working tree, so none can be rebuilt from the repository. Release 8 (2026-09-20) is the first built by the guarded workflow from a committed revision, e63f614, after its continuous integration run passed; 46 website checks pass on each of four hostnames and 16 service and protocol checks pass. The record is artifacts/architecture-audit-2026-09-19/pilot-release-8.json. Shared-state scaling, current-image rollback and other hosting profiles remain unqualified. | Continue the declared acceptance checks |
| S-6.1 | Path, link, overwrite, immutable authority, and guardrail repairs have owning and independent checks in artifacts/architecture-audit-2026-09-19/root-changes-independent-review.md; full frozen-tree integration pending. | Continue the declared acceptance checks |
| S-6.2 | Before-provisioning blocking and unresolved decisions refuse writes. Supplied unsupported enforcement points refuse; before-effect text is explicitly guidance only. Runtime audit records the public-path checks. | Continue the declared acceptance checks |
| S-6.3 | Unique model-step occurrence records, metadata privacy, accepted-incumbent labels, Unicode byte counts, and persisted product outcomes are tested. Capture currently counts model-step invocations, not every physical gateway attempt; complete physical-call capture remains open. | Continue the declared acceptance checks |
| S-6.26 | Current-only Code, references, graph/spec, product outcome, export, model-learning and test reports are implemented. The memory repository forwarder is removed. Loop definition, checkpoint, ontology, fingerprint, skill and other aliases remain inventoried work. | Continue the declared acceptance checks |
| S-6.27 | Runtime, storage, retrieval, export, test collection, and capability-dispatch repair reports are saved in artifacts/architecture-audit-2026-09-19/. Complete source qualification remains a separate release gate. | Metadata disclosure now binds the initial grant revision and revalidates it at completion. Revocation, replacement and entitlement changes refuse in local tests, and removing the guard is detected. Preserve the original counterexample; qualify hosted behavior and remaining defects separately. |
| S-6.28 | The family axis and its four known-wrong-case checks are on main (a3bd0f1, 6229/6229). Phase 1 landed at commit 6781c89 — the typed, versioned intelligence_family_policy record in the host configuration, harness-only by default, refusing a manifest item whose family the host has not declared before its body or licence is read, with the six named checks in core/service_runtime/http_boundary_checks.py including the removed-guard control. The four intelligence layer folders restate as open folders that serve the harness family and hold the others off (commit 88714c2). The self-test is at 2349/2349. The decision record docs/architecture/ADR-HARNESS-FIRST-SERVING-AND-EXECUTION.md holds the three-phase plan. The checkpoint branch is recorded at revision a3bd0f1. | Phase 2 moves execution behind the HarnessProcessSpec delegation contract; after the suite retirement at ea59df0, one executable step through a harness is phase 2's gate, not an in-process run, and a delegation claim met by the retired path is the known-wrong case. Phase 3 retires the in-process execution modules from main, leaving PARKED.md marker files that name the checkpoint branch and revision. |
| S-6.5 | The live pilot supports host-key Model Context Protocol access and OpenCode 1.17.9 discovery. Browser identity and account-activation code ships in Fly release 7 and is switched off by host configuration. Personal client keys are local only; they use an owner-bound record version that an older release refuses, shown by a rollback drill against the real release 7 image. Generic browser tokens remain invalid for the protocol resource audience. OAuth client consent and complete typed package serving remain unqualified. | Verify the installed command and package, a second supported client, and exact protocol refusal; qualify live authorization only after owner setup. |
| S-6.6 | Exact usage identity, atomic authority read sets, restart and unknown-commit reconciliation are implemented in core.service_runtime. HTTP and protocol retries share one durable usage acknowledgment. Complete telemetry retention, consent, export and collector-outage behavior remain open. | Exercise retention, tenant export and telemetry outage behavior with raw-content collection disabled; preserve unknown cost and commit outcomes. |
| S-6.21 | Checkout and portal creation have 52 local checks and 18 detected mutants; signed-event reconciliation has separate local checks. The newly approved Baltor sandbox acct_1UHZ9KCCxLfArYED is reachable with the runtime test credential. No real test checkout or webhook lifecycle has been completed; live charging stays disabled. September 22 at 21:20 Eastern: checkout and portal were unavailable since Fly release 13 because StripeSessionConfiguration.policy_definition() digests every field and commit 8a0b872 added allow_promotion_codes, so the stored policy digest (960b387a...) no longer matched the running one (710a3d5d...); only the one-time configure step writes that record. It was not re-applied by hand, because the public page would then say payment is open beside the waiting list; release 16 carries the command, the health check, the release step and an invitation-only public payment state together. September 23: Fly release 16 moved the payment session policy to service_billing_session_policy/v2 and re-applies it after the grants on every deploy; checkout and the customer portal report true again, and the public pricing view says Invitation only while account creation is closed. Release 15 reads only version 1, so a rollback to it turns checkout and the portal off rather than honouring a record it does not know. | Dashboard session routes have local browser checks. Complete periodic reconciliation, automatic customer bootstrap and qualified deployment, then exercise the owner's Stripe test account under explicit authority. |
| S-6.7 | Immutable digest-bound public provisioning configuration reaches scoped assignments; public solve has nine dedicated integration checks and fourteen provisioning mutants. Preparation does not establish native loading, full resource admission, or arbitrary completed task decomposition. | Continue the declared acceptance checks |
| S-6.12 | Fly release 7 includes account forms, browser identity validation, server-owned tenant activation and the plain-language website. Conformance passes. Local browser checks pass 120 cases; both the Fly origin and app.baltor.ai pass 45 hosted website checks. Provider account registration is not enabled or qualified. Real confirmation, recovery, self-service client tokens, billing and complete native task loading remain open. | Continue the declared acceptance checks |
| S-6.24 | Guided website setup provides secret-free Codex and OpenCode 1.x configuration, an actual protocol handshake and tool-list check, a first retrieval example and access/data boundaries. OpenCode 1.17.9 connected to the deployed pilot using a scoped key with no model turn and no permanent configuration change. This proves native connection and discovery only. Native material loading, model-backed task success, Kaggle access and the complete fresh-user journey remain open. See artifacts/architecture-audit-2026-09-19/native-opencode-connection-2.json. | Continue the declared acceptance checks |
| S-6.15 | The private diagnostic Fly pilot runs release 8, image sha256:a2d31be073025fcc4f6f0ad86ef743eeffbd36d8d65671855d7298260862ce0a, built from revision e63f614, and is healthy. Release 7, image sha256:7b45d327faba2e65829230e8ee4f91109207183b4575cdab08c545aae6af55e8, is kept for rollback. Public read-only status checks returned successful homepage, login, connection, health and capability responses. Live capabilities still disable public registration, checkout, portal and webhooks. Complete customer and native task journeys remain open. | Continue the declared acceptance checks |
| S-6.25 | artifacts/architecture-audit-2026-09-19/ contains the source graph, file coverage, component rows, review registers, and client/server diagrams. Structural enumeration is complete for its declared population; every-file semantic review is not claimed. | Continue the declared acceptance checks |
| S-6.18 | Practitioner runtime, Solution execution and export templates have separate modules. Typed decision contracts, provider mapping and gateway support now live under core/decisions with import-boundary tests. Website assets live inside service_runtime. The larger flat core still needs measured reorganization; no whole-repository cleanliness claim is made. | Continue the declared acceptance checks |
| S-6.22 | Three dated primary-source reports are delivered under artifacts/continuation-research-2026-09-19/. They cover eighteen adjacent product surfaces, prior-art families, funding programmes, and acquisition comparables. The September 22 ZCode review and docs/research/CROSS-FUNCTIONAL-HARNESS-AND-LAUNCH-REVIEW-2026-09-22.md add pinned harness sources, theory, current competing offers, stakeholder questions, a launch audit and proposed discriminating checks. Six further September 22 records in docs/research cover frontier harness positioning and Google context-state work, model-call strategy and disagreement, benchmark and showcase options, CodeGraph and Graphify alongside retrieval engines, library scale with paid acquisition readiness, and customer-side credential and endpoint delegation. They distinguish observed behavior from proposals and identify tests for Claude Code's build work. tools/refresh_research_sources.py made a bounded read-only check of ten primary sources with a new dated report. Ongoing research remains open; no outreach occurred. | Review each changed or inaccessible source from a new source-watch report before editing a claim; keep the roadmap as the only task state. |

## Release gates

A completed planning task, import, or published module does not establish a release gate.

| Gate | State | Required steps |
|---|---|---|
| A visitor can subscribe, use the dashboard, connect a client, and manage access | Not verified: required work remains | S-6.12, S-6.21 |
| An authenticated client retrieves qualified material with durable accounting | Not verified: required work remains | S-6.4, S-6.5, S-6.6 |
| The declared starter catalogue is qualified, versioned, and retrievable by supported clients | Not verified: required work remains | S-6.10 |
| Task graphs, atomic harness assignments, every intelligence layer, templates, and existing internal capability paths are connected and tested | Not verified: required work remains | S-6.1, S-6.2, S-6.3, S-6.7, S-6.8, S-6.9, S-6.20, S-6.11, S-6.23 |
| A new user can install, authenticate, configure a provider, and use the supported harness architecture | Not verified: required work remains | S-6.24 |
| Tenant operations, restart, restore, upgrade, and rollback are exercised | Not verified: required work remains | S-6.12, S-6.13, S-6.14 |
| The chosen authorized hosting target passes the same acceptance suite | Not verified: required work remains | S-6.15 |
| Approved pricing and payment integration reconcile with durable usage | Not verified: required work remains | S-6.16 |

## Delivery packages

These packages expand existing steps into implementation and verification work. They are not another status authority, runtime scheduler, permission grant, or completion percentage. Dependencies apply to acceptance; independent local work can proceed earlier.

### D-01: Freeze the handoff and repair release blockers

Owning steps: S-6.17, S-6.26, S-6.27. Acceptance dependencies: none.

Owning boundaries: `src/loop_engine/core/service_runtime/http_auth.py`; `src/loop_engine/forbidden_paths.json`; `tools/capture_architecture_checks.py`.

- Record the exact deployed image separately from the dirty working tree and preserve all unrelated changes.
- Preserve the reviewed exact identity network registrations and recheck conformance after further changes; earlier failures remain in their original reports.
- Review browser identity session lifetime, logout, duplicate account activation, provider outages, token audience and registration limits.
- Review browser dependency licenses and include all required distribution notices.
- Run focused checks and removed-guard controls before a frozen full-suite capture; do not reuse stale green reports.
- Record which files are being changed by each active developer and keep unrelated work outside the release batch.
- Bind each evidence artifact to the source, dependencies, host settings and exact test population it actually exercised.
- Classify a failed check as implementation, test or environment failure before repair; keep the original result and a discriminating control.

Complete when: The exact candidate tree passes its declared local checks and conformance, with all failed attempts and untested provider journeys retained.

Failure control: Removing audience validation, subject binding or network authority must fail a named check. Registering a module must not hide a real ungoverned call.

Authority: Local source and tests only. Deployment and publication require their own exact release decision.

Rollback or safe stop: Keep the deployed image and configuration until the replacement passes. Preserve failed source snapshots and never reset the shared worktree.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-01-T01 | source_review | Review changed files and concurrent work before a release batch. | Every changed behavior has an owning boundary and resolved edit ownership. | An unexplained dirty file cannot enter a publish command. |
| D-01-T02 | local_contract | Remove issuer, audience or subject binding from identity validation. | The corresponding negative authentication test fails. | A correctly signed token for another service must still be refused. |
| D-01-T03 | local_contract | Remove an exact network registration or introduce an ungoverned call. | Conformance detects the boundary change without a broad exception. | A loopback fixture does not authorize an external destination. |
| D-01-T04 | operational_drill | Change a package file while a full check capture runs. | The report records source drift and is not used for release. | A green subprocess exit alone cannot establish matching source. |
| D-01-T05 | source_review | Review transitive browser and server dependency notices. | The distributed image contains the notices for its pinned dependencies. | A top-level license alone does not satisfy a dependency with separate terms. |

### D-02: Finish domain and authentication email

Owning steps: S-6.12, S-6.15, S-6.24. Acceptance dependencies: none.

Owning boundaries: `docs/guides/launch-setup-runbook.md`; `tools/operator_credentials.py`; `src/loop_engine/core/service_runtime/browser_identity.py`.

- Reuse the created auth.baltor.ai sender, its exact records and the running verification request; confirm success before enabling authentication mail.
- Reuse the approved Cloudflare write grant and existing Free zone; verify activation and all records without recreating resources.
- Verify registry publication of the nameserver change already accepted by Namecheap. The owner confirms no existing mail or forwarding; preserve the old delegation in the rollback record.
- Configure the exact website record and certificate, then exact identity redirects and private sender settings under a permitted management connection.
- Test confirmation, recovery, expired and reused links, duplicate submissions, delivery failure and sender authentication with controlled recipients.
- Record authoritative and recursive DNS observations separately, including negative caching, DNSSEC state and certificate renewal.
- Add sender failure, suppression, bounce and complaint handling without storing raw account email content in general traces.
- Move canonical service and callback addresses only through an explicit migration that preserves accepted old connections until their retirement.

Complete when: The chosen hostname and sender work through the real customer path without disrupting existing website or mail behavior.

Failure control: A missing management permission, wrong host, unverified sender or unknown DNS-change outcome prevents a readiness claim and triggers reconciliation.

Authority: Existing pilot limits apply. Registrar and Cloudflare write access are authorized. Supabase authentication-settings access remains a separate permission gap; do not bypass refusals.

Rollback or safe stop: Keep the verified Fly origin available. Reconcile uncertain DNS writes before retrying and never restore obsolete mail records without review.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-02-T01 | real_provider | Read the registrar, registry and both authoritative DNS servers. | All identify the intended delegation and exact website and sender records. | A cached recursive answer cannot establish the registrar state. |
| D-02-T02 | real_provider | Verify all advertised hostnames with ordinary HTTPS clients. | Hostname validation succeeds and the served source matches the candidate image. | An insecure TLS bypass or pinned-address probe alone is insufficient. |
| D-02-T03 | end_to_end | Deliver confirmation and recovery messages to controlled recipients. | The intended recipient receives a valid, expiring link for the selected environment. | A verified sender domain alone is not proof of inbox delivery. |
| D-02-T04 | real_provider | Expire, reuse or change a confirmation or recovery link. | The provider and application refuse the changed or consumed authority. | A forged tenant claim or redirect cannot grant another account. |
| D-02-T05 | operational_drill | Interrupt sender or DNS configuration after a possible write. | Read-back establishes the outcome before another mutation. | Repeating an unknown write or silently changing providers fails the drill. |

### D-03: Connect customer accounts and client access

Owning steps: S-6.5, S-6.12, S-6.24. Acceptance dependencies: D-01, D-02.

Owning boundaries: `src/loop_engine/core/service_runtime/access.py`; `src/loop_engine/core/service_runtime/runtime.py`; `src/loop_engine/core/service_runtime/http_auth.py`; `src/loop_engine/core/service_runtime/web_assets/client-access.js`.

- Exercise the real identity provider with two ordinary test identities and server-owned tenant creation.
- Complete confirmation, password recovery, session expiry, logout and account-disable behavior without accepting editable tenant metadata.
- Add scoped self-service client credentials through the existing access boundary, with short lifetime, one-time display and revocation.
- Qualify native client authorization separately from browser sign-in; never accept a generic browser audience as the service resource audience.
- Test account switching, delayed responses, concurrent activation, request limits and two supported client implementations.
- Require a verified browser session for personal credential management; service tokens cannot mint more credentials or delegate billing and administration.
- Bind personal tokens to their issuing subject, account state, explicit scopes and expiry; cap active tokens and retained token history.
- Test logout during pending reads and writes, provider outages, account disablement and subject revocation without leaking stale results.

Complete when: A new customer signs in, obtains only permitted client access and loses that access when revoked, across browser and native clients.

Failure control: Cross-tenant requests, old sessions, anonymous identities, server keys in browsers and repeated activation cannot restore or expand authority.

Authority: Disposable test identities and exact selected project only. No opening public registration before delivery and abuse controls work.

Rollback or safe stop: Disable new account admission or personal token issuance independently. Keep existing revocation records and do not restore discarded secrets.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-03-T01 | end_to_end | Two verified customers create and revoke their own client credentials. | Each token authenticates only its server-assigned account and is shown once. | Supplying another tenant or using a service token to mint must fail. |
| D-03-T02 | local_contract | Race two requests against the last available token slot. | At most one credential commits under the tenant quota. | Removing the transaction guard must expose the excess issue. |
| D-03-T03 | local_contract | Lose the write acknowledgment and retry the same request identity. | The existing result reconciles without another key or recovered plaintext. | Changing scope or label under that identity must fail. |
| D-03-T04 | end_to_end | Sign out while a credential response is delayed. | Local data clears immediately and the late result cannot repopulate the page. | The test must hold a real response, not only clear a static form. |
| D-03-T05 | real_provider | Disable an account or revoke its mapped subject. | New management requests and linked client tokens lose authority within the declared revocation policy. | Browser logout alone must not be misreported as revoking all independent client tokens. |

### D-04: Complete sandbox subscriptions

Owning steps: S-6.21, S-6.12, S-6.16. Acceptance dependencies: D-01, D-03.

Owning boundaries: `src/loop_engine/core/service_runtime/billing.py`; `src/loop_engine/core/service_runtime/stripe_sessions.py`; `src/loop_engine/core/service_runtime/stripe_provider.py`.

- Bind all test operations to the approved Baltor sandbox account and privately stored runtime test credential.
- Create the test product, recurring Price and portal settings with idempotency and reconcile uncertain outcomes.
- Implement server-owned customer creation through the existing billing boundary; customers cannot choose another customer's identifier.
- Register the exact test webhook and separate signing-secret reference; complete periodic reconciliation and outage recovery.
- Exercise activation, failed payment, cancellation, reactivation, duplicate and reordered events, and access revocation in website and client requests.
- Separate customer creation, checkout session creation, subscription state and material entitlement, with durable identities for each effect.
- Handle multiple subscriptions, changed prices, trials, refunds and payment disputes through explicit owner-approved entitlement policy.
- Verify checkout return and cancellation destinations against configured origins; never accept a browser-supplied customer, Price or redirect.

Complete when: One complete real test-mode subscription lifecycle changes the same durable entitlement used by both transports.

Failure control: A checkout redirect, forged event, wrong account, old success event or lost response cannot grant access or create duplicate customer actions.

Authority: Test mode only. Public prices, terms and live customer charging remain owner decisions.

Rollback or safe stop: Keep live charging disabled. Preserve provider identifiers and reconcile payments before restoring an older application or entitlement projection.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-04-T01 | real_provider | Create a disposable customer and subscription in the selected Stripe sandbox. | Account identity and test mode match every stored provider object. | A different sandbox or live-mode response must be refused. |
| D-04-T02 | end_to_end | Complete test checkout, cancel and reactivate a subscription. | The same durable entitlement governs browser and client delivery. | A success redirect without verified provider state grants nothing. |
| D-04-T03 | local_contract | Deliver duplicate and reordered signed events. | Current provider state wins and every event identity remains traceable. | An older paid event cannot restore canceled access. |
| D-04-T04 | real_provider | Lose a customer or session creation response. | A durable idempotency identity prevents duplicate effects during reconciliation. | A new random request identity is not an acceptable automatic retry. |
| D-04-T05 | operational_drill | Pause webhook processing and resume with periodic reconciliation. | Missed changes are recovered without expanding grants or discarding failures. | A healthy webhook endpoint with a stuck reconciliation queue fails readiness. |

### D-05: Connect cloud records, files and retrieval

Owning steps: S-6.4, S-6.5, S-6.6. Acceptance dependencies: D-01.

Owning boundaries: `src/loop_engine/catalog/protocol.py`; `src/loop_engine/catalog/stores/sqlite_store.py`; `src/loop_engine/core/service_runtime/storage.py`; `src/loop_engine/core/service_runtime/provisioning.py`.

- Implement PostgreSQL behind the existing catalogue transaction contract, including read-set guards and unknown-commit reconciliation.
- Create the private bucket under the existing project; map immutable references to exact bytes without a second source of truth.
- Add one versioned semantic embedding profile beside exact and lexical retrieval; separate filters, candidate generation, fusion and optional ranking.
- Preserve missing-feature and incompatible-embedding-space states, deletion, grant revocation and index rebuild behavior.
- Measure permission-filtered recall, search and delivery latency, cold starts, payload sizes and concurrency on a declared corpus.
- Define migration rehearsal, cutover, rollback and consistency checks before replacing the live SQLite authority.
- Keep index projections rebuildable and file objects immutable; record versions, deletion state and access decisions outside provider-owned indexes.
- Test object size limits, partial transfers, expiry, cache isolation and tampered bytes across inline, streamed and signed delivery.

Complete when: Two tenants retrieve only permitted exact revisions through real shared-state and storage adapters; search indexes can be rebuilt from authoritative records.

Failure control: Stale grants, cross-tenant caches, wrong digests, partial writes, leaked signed URLs and missing embedding features must refuse or remain explicitly unavailable.

Authority: Existing project and pilot allowance only. No extra search cluster or model embedding calls without exact authority.

Rollback or safe stop: Retain the authoritative source and a verified export. Stop writes during an unresolved cutover; do not run divergent stores as simultaneous authorities.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-05-T01 | local_contract | Run identical catalogue transactions against each supported store. | Read-set guards, unique ownership and commit acknowledgments preserve the same semantics. | An adapter without atomic batch support must refuse mutation. |
| D-05-T02 | real_provider | Store and fetch selected immutable objects in a private bucket. | Bytes and digests match and anonymous retrieval fails. | A public bucket or permanent bearer URL fails qualification. |
| D-05-T03 | end_to_end | Revoke a grant after search but before object delivery. | Delivery reauthorizes and refuses the stale selection. | A cached search result cannot preserve revoked access. |
| D-05-T04 | operational_drill | Rebuild the search projection and rehearse a store migration. | Counts, identities, grants and exact revisions reconcile before cutover. | An index match count alone cannot establish data completeness. |
| D-05-T05 | held_out_comparison | Compare retrieval on a frozen permission-scoped corpus. | Report recall, latency, payload size, exclusions and missing embedding features. | Character similarity cannot be labeled learned semantic retrieval. |

### D-06: Prove selected material reaches each step

Owning steps: S-6.1, S-6.2, S-6.7, S-6.9. Acceptance dependencies: D-01, D-05.

Owning boundaries: `src/loop_engine/core/node_provisioning.py`; `src/loop_engine/core/instance_instructions.py`; `src/loop_engine/core/harness_process.py`.

- Connect search, selection, authorized download and digest verification through the existing provisioner.
- Resolve required dependencies and compile a versioned native layout for one named client version.
- Record offered, selected, downloaded, placed, loaded and used material separately, including inherited user-level instructions and truncation.
- Compare useful material with withheld, changed and malicious material; preserve relevant limits across a permitted harness change.
- Run one complete task through independent verification and preserve the exact files and outputs consumed by each step.
- Resolve dependency closure, license state, executable effects and layout compatibility before writing a selected bundle.
- Give instructions, reusable material, writable outputs and host-owned authority separate filesystem scopes.
- Track inherited configuration, actual discovery, truncation and use independently from successful download and placement.

Complete when: A supported client demonstrably loads selected material and completes a checked task; file presence and connection success are insufficient.

Failure control: Disabled discovery, incompatible native versions, traversal, symbolic links, unexpected inherited instructions and missing required files must be detected.

Authority: Offline preparation can proceed now. Model-backed task proof needs an exact model-call allowance, including for local inference.

Rollback or safe stop: Keep exact prior bundles and outputs. Stop before execution if the compiled layout or permission boundary cannot be verified.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-06-T01 | end_to_end | Materialize an exact selected bundle into one supported native client. | Observed loading identifies every required revision and its declared native path. | A file existing on disk without loading evidence is not a pass. |
| D-06-T02 | local_contract | Try traversal, symbolic links, archive escapes and conflicting paths. | Preparation refuses before overwriting or exposing unrelated files. | A friendly filename cannot replace path confinement. |
| D-06-T03 | end_to_end | Compare useful material with withheld, changed and misleading material. | Independent checks distinguish actual use and task effect. | A model claiming it read the material is not sufficient evidence. |
| D-06-T04 | local_contract | Resolve a missing dependency or incompatible native layout. | The response names the unsupported requirement without silently dropping it. | A fallback cannot replace an exact contract with prose. |
| D-06-T05 | operational_drill | Interrupt preparation or change harness after a failed attempt. | The manifest, outputs and consumed authority remain bound and recoverable. | A new process cannot erase a previous effect or renew its budget. |

### D-07: Qualify overnight local work and recovery

Owning steps: S-6.8, S-6.9, S-6.24, S-6.13. Acceptance dependencies: D-01, D-06.

Owning boundaries: `src/loop_engine/core/local_resources.py`; `src/loop_engine/core/instance_hibernation.py`; `src/loop_engine/core/credential_leases.py`; `src/loop_engine/loop/delegation_runtime.py`.

- Connect an existing local model endpoint and one supported development tool; record hardware, model identity, context capacity and effective settings.
- Bind resource admission, scoped credential use and cancellation to the existing process lifetime owner.
- Compare fresh processes, retained workers and trust-group sandboxes; do not require a separate operating-system image for every step or assume Python for every tool.
- Persist work and remaining limits across process crash, machine restart, sleep, network loss and unavailable model service; uncertain effects require reconciliation.
- Test a declared overnight duration with multiple real task types, an independently checked result and a morning report that distinguishes complete, blocked and unfinished work.
- Set explicit maximum running processes, memory reservations, disk use, output growth and slow-consumer behavior for each supported execution profile.
- Keep external model serving separate from worker placement; accept user-operated endpoints without taking ownership of their model processes.
- Test operating-system-specific shutdown, signal handling and checkpoint restoration with the same declared task authority.

Complete when: A named local configuration performs bounded unattended work and resumes or stops honestly, without hidden cloud-model fallback or repeated external effects.

Failure control: Lost contact cannot free reserved capacity, a restart cannot reset the budget, and a failed verifier cannot be reported as overnight completion.

Authority: Model calls remain disabled until approved. Existing endpoints are user-operated; this does not authorize installing weights or launching model servers.

Rollback or safe stop: Stop new admissions, reconcile active effects and retain checked work. Resume only a supported checkpoint with the original remaining authority.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-07-T01 | end_to_end | Run the declared unattended duration on a real local endpoint. | The final report distinguishes accepted, provisional and unfinished work. | Local execution with hidden remote inference fails the local-model claim. |
| D-07-T02 | operational_drill | Restart after a process crash, machine sleep or network interruption. | Safe work resumes without duplicated effects or lost output identities. | A new attempt with reset time or token allowance fails. |
| D-07-T03 | local_contract | Cancel a worker that still owns descendants or reservations. | Capacity is released only after observed termination. | Sending a signal alone cannot count as stopped execution. |
| D-07-T04 | held_out_comparison | Compare fresh processes, warm workers and shared trust-group sandboxes. | Measure whole-task memory, startup, cost, cancellation and isolation. | A cheaper shared environment that leaks another task's files is ineligible. |
| D-07-T05 | real_provider | Lose an optional decision or model endpoint during work. | The configured refusal or authorized fallback is recorded distinctly. | No undeclared provider, model server or paid route is started. |

### D-08: Build useful expertise and reusable outputs

Owning steps: S-6.10, S-6.20, S-6.11, S-6.23. Acceptance dependencies: D-05, D-06.

Owning boundaries: `src/loop_engine/core/code_intelligence_assets.py`; `src/loop_engine/core/reusable_capability_flywheel.py`; `src/loop_engine/code_nodes/solution_export.py`.

- Select a small useful starter population across the four persistent intelligence layers, with licenses, provenance and coverage gaps recorded.
- Independently review the existing twelve candidate records; distinguish code reference cards from executable packages.
- Add expert methods, mistakes, constraints, code and example outputs where actual task coverage is missing, through existing catalogue writes.
- Exercise bounded generation, review, promotion, later-task retrieval and withdrawal; a generator cannot approve its own work.
- Export an accepted solution into a clean environment and run fresh inputs without the builder conversation or undeclared dependencies.
- Specify applicability, contraindications, version validity and dependency limits for each reusable item rather than promoting generic descriptions.
- Preserve rejected candidates and corrective findings so later retrieval can distinguish failure evidence from approved guidance.
- Bind consumer feedback to the exact item and output revision used; never overwrite a consumed result with a later improvement.

Complete when: Reviewed material helps a declared task population, and at least one accepted solution is independently reusable on changed inputs.

Failure control: A mislabeled generic file, incompatible dependency, changed source, unsupported license or builder-only test cannot qualify a package.

Authority: Distribution rights and independent review are required. No automatic promotion or bulk model generation under the zero-call allowance.

Rollback or safe stop: Withdraw a bad item by lifecycle state and keep its history. Restore an approved prior revision only after current rights and compatibility checks.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-08-T01 | source_review | Review the starter population across all four persistent layers. | Each item has a responsible source, rights, purpose and explicit qualification state. | A Markdown format or vector representation is not a new intelligence layer. |
| D-08-T02 | end_to_end | Use a reviewed item in a fresh task and export the result. | The consumer records the exact revision and independently checked outcome. | Retrieval rank or placement alone cannot establish benefit. |
| D-08-T03 | local_contract | Attempt to promote a producer's own generated candidate. | The separate review requirement prevents activation. | A high model confidence or passing producer test cannot waive review. |
| D-08-T04 | operational_drill | Withdraw an item after a license or correctness finding. | Future selection refuses it while previous consumption records remain intact. | Deleting history to hide an earlier bad result fails the record contract. |
| D-08-T05 | end_to_end | Run an exported solution on changed inputs in a clean environment. | Declared dependencies and checks suffice without the builder conversation. | Undeclared local files or cached credentials must not make the example pass. |

### D-09: Measure token savings and context usefulness

Owning steps: S-6.3, S-6.6, S-6.19, S-6.23. Acceptance dependencies: D-06, D-08.

Owning boundaries: `src/loop_engine/core/model_gateway.py`; `src/loop_engine/core/model_call_records.py`; `src/loop_engine/core/run_history.py`; `src/loop_engine/core/stage_evidence_records.py`.

- Capture each physical model attempt exactly once across retries, helpers and native sessions, with unknown usage kept unknown.
- Freeze matched tasks, evaluator, quality tolerance, model and non-treatment settings before measuring changes.
- Compare selected versus full, insufficient, expanded and misleading context, and code reuse versus generation where both meet the task.
- Report input, cached input, output, reasoning usage when available, cost, elapsed time, memory and failures separately; include retrieval and verification overhead.
- Use repeated trials and uncertainty estimates; record task-specific regressions, withheld cases and the exact limits of any public claim.
- Track retrieval, feature generation, model startup, context transfer, execution, retries and verification in the same route-cost accounting.
- Separate optimization search cost from later serving savings and report the workload needed to recover that investment.
- Predeclare quality floors and task-group regression limits; publish absolute outcomes and uncertainty as well as relative savings.

Complete when: A source-bound report can support or reject each launch benefit without changing the quality standard to make savings appear.

Failure control: Dropped failed calls, missing usage treated as zero, cheaper unfinished work, mismatched models and evaluation-set tuning invalidate the comparison.

Authority: No benchmark model calls are authorized by writing this plan. Telemetry defaults to structural records; content reuse requires separate consent.

Rollback or safe stop: Keep the prior qualified policy and raw observations. Reject unsupported claims rather than repairing the held-out benchmark from its own failures.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-09-T01 | held_out_comparison | Compare complete routes on frozen tasks and independently checked outputs. | Include useful outcomes, failures, confidence intervals and all charged work. | A lower bill caused by unfinished tasks fails the capability floor. |
| D-09-T02 | local_contract | Omit usage from one physical call or count a retry twice. | Accounting reports missing or duplicate evidence explicitly. | Unknown cost cannot become zero. |
| D-09-T03 | held_out_comparison | Vary selected, expanded, insufficient and misleading context. | Record both improvements and regressions by task group. | Minimum context is not assumed to be universally optimal. |
| D-09-T04 | source_review | Review a proposed public efficiency claim. | Its task population, source, model, harness, evaluator and limitations are traceable. | Borrowed vendor percentages do not become Baltor results. |
| D-09-T05 | operational_drill | Discover leakage between search tasks and evaluation tasks. | The affected result is invalidated and the frozen split remains unchanged. | A repaired candidate cannot reuse the same exposed holdout as independent proof. |

### D-10: Simplify the website and finish customer journeys

Owning steps: S-6.12, S-6.24, S-6.22. Acceptance dependencies: D-03, D-04.

Owning boundaries: `src/loop_engine/core/service_runtime/web_assets`; `docs/guides/product-style-guide.md`; `tools/check_service_workspace.mjs`.

- Use Baltor, task, step, model, tools and results on public pages; keep runtime names in technical documentation and GitHub.
- Keep How it works focused on the example and benefits, with a short honest pilot limitation instead of a runtime taxonomy.
- Complete sign-in, account, client setup, first successful retrieval, usage, access revocation, billing and clear failure states.
- Check keyboard navigation, small screens, enlarged text, loading races and expired sessions; test whether a new reader understands the page.
- Plan public documentation, examples and approved showcase subdomains without presenting an unconfigured docs hostname as live.
- Show connection, authentication, material loading, task success and subscription state as separate observable stages.
- Make one-time secrets, ambiguous outcomes, expired links, empty results and unavailable features understandable without support intervention.
- Compare public pages and setup journeys against the existing competitor matrix without copying claims or hiding current product limits.

Complete when: A new user can understand the product and complete the supported journey without knowing internal architecture terms or copying a secret into the wrong field.

Failure control: Hidden unfinished features, misleading benefit claims, missing error recovery and technical vocabulary leaking into public explanations fail the page review.

Authority: Copy can be improved independently. Public deployment must use a qualified exact source; no customer testimonials or performance numbers may be invented.

Rollback or safe stop: Retain the last qualified customer interface and feature flags. Disable an incomplete flow visibly instead of leaving a working-looking control.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-10-T01 | end_to_end | A new reader completes the declared account and client journey. | They can identify the next action without internal runtime vocabulary. | A static mock control or undocumented manual workaround fails. |
| D-10-T02 | local_contract | Display malicious labels, retrieved text and provider errors. | The page renders text without script execution or credential disclosure. | Unsafe HTML insertion must be detected. |
| D-10-T03 | end_to_end | Use keyboard-only navigation, narrow screens and enlarged text. | All required controls remain operable and readable. | A desktop screenshot alone cannot establish accessibility. |
| D-10-T04 | local_contract | Switch accounts while responses are delayed. | Late results cannot reveal or modify the previous account's state. | Clearing labels without aborting or invalidating requests fails. |
| D-10-T05 | source_review | Review homepage benefits, docs and showcase examples. | Every current claim has matching evidence or a clear qualification limit. | An illustrative task must not look like a recorded successful customer run. |

### D-11: Exercise operations and make the release decision

Owning steps: S-6.14, S-6.15, S-6.16, S-6.6, S-6.13. Acceptance dependencies: D-02, D-03, D-04, D-05, D-06, D-08, D-10, D-13, D-14, D-15, D-16.

Owning boundaries: `Dockerfile.service`; `fly.toml`; `.github/workflows/fly-pilot.yml`; `tools/check_pilot_backup_restore.py`.

- Freeze the exact source, image, database migration and host settings; run clean installation, full checks, examples and real customer journeys.
- Test backup, restored revocations, rollback, secret rotation, payment reconciliation, abuse limits, tenant deletion and retention.
- Establish alerts, support contact, incident ownership and a tested maintenance path; record single-machine availability limitations.
- Review security boundaries, dependencies, license obligations, privacy settings, terms, cancellation and public claims.
- Obtain the separate paid-release decision and publish only reviewed source under explicit commit and push authority.
- Define the supported pilot contract separately from optional research engines and later enterprise features.
- Require exact evidence for every release gate and an explicit owner decision for live charging and source publication.
- Rehearse a failed release with account and payment state changing during rollback, not only a clean image replacement.

Complete when: Every required launch gate has current reviewed evidence, a supported-customer scope and a rehearsed recovery path; otherwise remain a named private pilot.

Failure control: A health check, account connection, plan checkbox or old test count cannot stand in for the complete release record.

Authority: No live charges or source publication without owner approval. An overnight or savings claim additionally requires D-07 or D-09 respectively.

Rollback or safe stop: Pause admission and writes where necessary, restore a compatible image and reconcile newer revocations and payment state before serving protected material.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-11-T01 | operational_drill | Deploy and roll back a frozen candidate with matching settings. | The expected image, schema and configuration are observed after each transition. | A rollback that resurrects revoked access fails. |
| D-11-T02 | end_to_end | Complete the supported journey from a clean customer environment. | Account, client access, retrieval, execution, acceptance and revocation have actual evidence. | A collection of unrelated component checks cannot substitute. |
| D-11-T03 | source_review | Review all launch gates against their source identities. | Every required gate has current independent review or remains open. | A plan checkbox or an expired green report cannot approve release. |
| D-11-T04 | operational_drill | Restore while subscription or credential state changed after backup. | Fresh authority is reconciled before protected delivery resumes. | Restoring old database bytes alone is insufficient. |
| D-11-T05 | real_provider | Inspect the final selected accounts, region and charging mode. | They match approved limits and live charging remains separately authorized. | A configured test Price must never silently become a live offer. |

### D-12: Continue interchangeable engines and governed improvement

Owning steps: S-6.18, S-6.19, S-6.22, S-6.25. Acceptance dependencies: D-01.

Owning boundaries: `src/loop_engine/core/retrieval_backends.py`; `src/loop_engine/core/decisions`; `src/loop_engine/core/harness_semantic.py`; `src/loop_engine/core/harness_layering.py`.

- Review exact, hybrid and bounded agentic retrieval profiles behind the same reference-first interface; qualify challengers only for demonstrated gaps.
- Compare configured decision endpoints, including Jev, Circuit and a separately specified SemIf score adapter, without assuming confidence is calibrated.
- Keep SoL-Pi mechanisms optional within the existing harness boundary; compare whole-task quality, cost and omission failures before promotion.
- Compare direct requests, scripted browsers and native tool access under the same permission and outcome rules.
- Stage proposed routing, context and intelligence changes for independent replay and review, with rollback and the existing learned-adoption policy preserved.
- Record each engine's license, supported protocol, actual feature coverage, initialization cost and unavailable states in configuration.
- Compare configured preference with learned selection, keeping confidence calibration, downstream utility and factual verification distinct.
- Preserve one owner for retries, cancellation and cumulative budgets across nested wrappers and native harness controls.

Complete when: New engines replace implementations at existing typed boundaries without new runtimes, stores or silent authority changes; supported combinations have specific evidence.

Failure control: Incompatible handshakes, invented conversion rules, tenant-leaking learning, self-promotion and cheaper but lower-quality routes must not become defaults.

Authority: Research and offline adapters can proceed independently; provider experiments, automatic adoption and external outreach need their own authority.

Rollback or safe stop: Retain the last qualified engine profile and stop on unsupported semantics. Never invent protocol conversions or reset authority during fallback.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-12-T01 | local_contract | Negotiate versions, schemas and optional features at initialization. | The selected binding is explicit and checked again at use. | Equal vector dimensions or similar field names do not establish compatibility. |
| D-12-T02 | real_provider | Call an owner-configured decision endpoint with typed alternatives. | Actual provider output, uncertainty and usage remain distinct from verification. | No canned result is substituted for a failed call. |
| D-12-T03 | held_out_comparison | Evaluate a retrieval or harness challenger on matched tasks. | Whole-route quality, cost, startup and failure behavior determine eligibility. | A vendor benchmark or low token count alone cannot promote the engine. |
| D-12-T04 | local_contract | Race native and outer retries or cancellation. | One policy owns the transition and each physical call is counted once. | Nested wrappers cannot multiply attempts or duplicate an uncertain effect. |
| D-12-T05 | held_out_comparison | Promote and later roll back a candidate improvement. | Independent evidence, consent scope and the existing adoption threshold are enforced. | Production interactions cannot directly rewrite global policy. |

### D-13: Qualify execution and service security boundaries

Owning steps: S-6.8, S-6.9, S-6.14, S-6.24. Acceptance dependencies: D-01, D-03, D-06.

Owning boundaries: `src/loop_engine/core/action_fence.py`; `src/loop_engine/loop/effect_approval.py`; `src/loop_engine/core/workspace_contracts.py`; `src/loop_engine/core/service_runtime/http.py`.

- Write a threat model for browser accounts, service tokens, retrieved material, plugins, local workers and operator infrastructure access.
- Separate trusted control state and credential brokers from model-editable workspaces and retrieved instructions.
- Test filesystem, archive, network, process and resource confinement for each supported isolation profile.
- Make prompt injection and malicious tool output tests cross the actual retrieval-to-execution path.
- Apply request limits, exact origins, redirect refusal and destination checks at the existing transport boundaries.
- Review package installation, executable dependencies and native user-level configuration before allowing a harness profile.
- Document credential rotation, account revocation and incident containment without exporting raw secrets.
- Keep unsupported sandbox, provider and protocol combinations unavailable instead of silently weakening isolation.

Complete when: The supported client and service profiles withstand declared adversarial cases without crossing tenant, workspace, credential or effect boundaries.

Failure control: Malicious retrieved instructions, a forged principal, a symbolic-link escape or a stale approval cannot expand authority.

Authority: Security fixtures and isolated local checks are permitted; no attack on unrelated infrastructure or unapproved external service is authorized.

Rollback or safe stop: Disable the affected capability or admission path while preserving evidence. Do not replace a failed sandbox with raw-host execution.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-13-T01 | end_to_end | Retrieve a malicious instruction or plugin candidate. | It remains untrusted and cannot acquire tools, secrets or network permission. | A label claiming approval must not alter authority. |
| D-13-T02 | local_contract | Forge tenant, subject, origin and permission fields. | Typed authentication and current grants refuse the request. | A signed token with editable tenant metadata still fails. |
| D-13-T03 | operational_drill | Cancel untrusted code with descendants and open handles. | Owned processes stop and unrelated work remains intact. | Killing by a shared process name is not acceptable cleanup. |
| D-13-T04 | local_contract | Attempt path, archive, symlink and redirect escapes. | The exact boundary refuses before the effect. | Passing a harmless filename test is not a substitute for adversarial paths. |
| D-13-T05 | operational_drill | Contain a leaked test credential and restore service. | Revocation is durable, rotation is scoped and records contain no secret values. | A restored snapshot cannot reactivate the leaked credential. |

### D-14: Operate intelligence ingestion, review and withdrawal

Owning steps: S-6.4, S-6.10, S-6.11, S-6.20, S-6.23. Acceptance dependencies: D-05, D-06.

Owning boundaries: `tools/stage_intelligence_candidates.py`; `src/loop_engine/core/code_intelligence_assets.py`; `src/loop_engine/core/intelligence_layers.py`.

- Define the supported source formats, size limits, provenance fields and trust classifications for intake.
- Preserve immutable source revisions, license evidence and dependency identities before extraction or chunking.
- Stage imported and generated material through existing catalogue contracts with candidate-only lifecycle state.
- Keep prompts, skills, contracts, code packages and history distinct as content families within the four persistent layers.
- Route semantic review and executable verification to an independent process with a fixed subject digest.
- Track applicability, freshness, contradictions and withdrawal reasons without silently rewriting consumed history.
- Propagate deletion and revocation to indexes, caches and delivery while preserving legally permitted audit metadata.
- Build a useful starter population from real task gaps and measure coverage rather than the number of generated files.

Complete when: Every served starter item has traceable rights, exact bytes, an appropriate review basis and a tested withdrawal path.

Failure control: Leaked proprietary prompts, poisoned context, stale licenses and producer-approved executable packages must not enter the active catalogue.

Authority: Use owned or distributable material. Private customer content, model generation and publication require their separate authority and consent.

Rollback or safe stop: Withdraw affected revisions and invalidate projections. Keep immutable provenance and previous consumer bindings; do not edit historical outcomes.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-14-T01 | source_review | Admit representative prompts, skills, code and historical records. | Each has its correct layer, rights, source identity and qualification basis. | A public repository URL is not proof of redistribution permission. |
| D-14-T02 | local_contract | Ingest changed bytes under an existing immutable identity. | The mismatch refuses rather than replacing the active body. | Updating only a title cannot conceal a changed executable. |
| D-14-T03 | end_to_end | Review, activate, retrieve and withdraw one exact revision. | Each stage records a distinct authorized transition. | Successful execution cannot silently promote its producer's candidate. |
| D-14-T04 | operational_drill | Delete or revoke material after indexing and caching. | Future search and delivery respect the change within the declared window. | A stale cache cannot outlive the authorization contract. |
| D-14-T05 | held_out_comparison | Evaluate domain coverage on frozen tasks. | Report useful, missing, harmful and unused material separately. | Title-matching probes alone do not demonstrate intelligence quality. |

### D-15: Operate reliability, telemetry and customer data lifecycle

Owning steps: S-6.6, S-6.13, S-6.14, S-6.15, S-6.16. Acceptance dependencies: D-03, D-04, D-05.

Owning boundaries: `src/loop_engine/core/service_runtime`; `tools/measure_service_latency.py`; `tools/check_pilot_backup_restore.py`.

- Define availability, latency, recovery and data-loss objectives for the supported pilot without promising unmeasured guarantees.
- Measure cold and reused connections, simultaneous customers, large files and slow clients with failures retained.
- Add alerts for identity outages, failed delivery, reconciliation backlog, storage growth and exhausted capacity.
- Use structural telemetry by default and separate raw-content retention, embeddings and training reuse behind explicit settings and consent.
- Implement customer export, deletion, retention and backup-expiry procedures across records, files, indexes and logs.
- Rehearse private backups, restore, secret rotation and incident response using exact manifests and owner-selected limits.
- Split stateless serving, workers, indexes or storage onto separate resources only when measurements and consistency contracts justify it.
- Keep infrastructure budgets, model budgets and customer subscription entitlements separately enforced and observable.

Complete when: Operators can detect, diagnose and recover declared failures without leaking private content, reviving revoked access or exceeding approved resources.

Failure control: Missing telemetry is unknown, embeddings are not anonymous, alerts are not hard spending caps, and additional SQLite replicas are not a scaling strategy.

Authority: Remain within the existing infrastructure allowance. No new paid cluster, model experiment, retention policy or training reuse is approved by the plan.

Rollback or safe stop: Use a rehearsed degraded mode or maintenance response. Restore only compatible state and reconcile post-backup revocations before admission.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-15-T01 | operational_drill | Stop the service or one external dependency during requests. | Failures, recovery time and uncertain effects are recorded accurately. | A health endpoint alone cannot establish customer availability. |
| D-15-T02 | end_to_end | Load the declared corpus with concurrent, slow and canceled clients. | Latency, memory, errors and backpressure stay within the chosen profile. | Failed requests cannot be dropped from the denominator. |
| D-15-T03 | local_contract | Disable raw-content telemetry and inspect all exported records. | Credentials and disallowed content are absent; missing cost stays unknown. | Embedding vectors cannot be relabeled anonymous telemetry. |
| D-15-T04 | operational_drill | Export and delete a disposable customer's data. | Every configured store and projection follows the retention contract. | Deleting the primary row alone does not complete erasure. |
| D-15-T05 | operational_drill | Restore a backup with newer revocation and payment events. | The restored service refuses stale authority until reconciliation. | A successful archive extraction is not a complete restore test. |

### D-16: Qualify installation, distribution and compatibility

Owning steps: S-6.1, S-6.2, S-6.9, S-6.15, S-6.24, S-6.26. Acceptance dependencies: D-01, D-06, D-13.

Owning boundaries: `pyproject.toml`; `Dockerfile.service`; `examples/29_intelligence_service`; `src/loop_engine/core/harness_execution_contracts.py`.

- Choose and document the exact operating systems, Python versions, native clients and transport profiles supported by the pilot.
- Test clean installation and upgrade without relying on developer caches, user-level instructions or untracked packages.
- Keep model endpoints user-operated and credential references local; do not require installing a model server to connect an existing endpoint.
- Provide container and process profiles that separate dependency images, workers, workspaces and inference services.
- Pin distributed dependencies, retain notices and produce source and image identities that match the tested release.
- Verify protocol negotiation and explicit unsupported states across independently deployed client and server versions.
- Document uninstall, credential removal, workspace retention and rollback without broad filesystem deletion.
- Publish packages, source and images only after reviewed ownership and explicit release authority, keeping automatic deployment disabled until then.

Complete when: A new customer can install the supported profile, connect securely, run the documented task and recover or uninstall without hidden dependencies or data loss.

Failure control: An operator's warm cache, privileged shell, global model key or old unpublished interface cannot be required for a passing clean installation.

Authority: Local packaging and isolated checks are permitted. Public package publication, Git commits and pushes need their exact authority; model calls remain separately bounded.

Rollback or safe stop: Retain the prior qualified distribution and explicit data migration path. Never reset customer workspaces or reinstall incompatible versions silently.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-16-T01 | end_to_end | Install the supported package and client in a clean environment. | Only declared dependencies and credential references are needed. | A developer checkout on the import path must not make the test pass. |
| D-16-T02 | local_contract | Connect clients with missing features or incompatible versions. | Negotiation selects a qualified common profile or refuses explicitly. | Similar field names cannot trigger an invented conversion. |
| D-16-T03 | end_to_end | Run equivalent trusted work through process and container profiles. | Contracts and outcomes agree while isolation differences remain explicit. | One directory per task cannot be called a security sandbox. |
| D-16-T04 | source_review | Inspect the distributable image, dependency lock and notices. | They match the tested source and required licenses. | A newly downloaded unpinned executable invalidates the release identity. |
| D-16-T05 | operational_drill | Upgrade, roll back and uninstall with retained customer work. | Credentials and scoped state follow the documented lifecycle. | Recursive deletion of a broad home or workspace directory fails the procedure. |

### D-17: Open a private beta for invited users

Owning steps: S-6.5, S-6.10, S-6.12, S-6.15, S-6.24, S-6.28. Acceptance dependencies: D-01, D-03.

Owning boundaries: `.github/workflows/fly-pilot.yml`; `tools/check_rollback_key_version.py`; `src/loop_engine/core/service_runtime/browser_identity.py`; `src/loop_engine/core/service_runtime/http_entrypoint.py`; `src/loop_engine/core/service_runtime/web_assets/client-recipes.json`; `tools/stage_intelligence_candidates.py`; `tools/build_host_catalogue_manifest.py`; `tools/carry_catalogue_approvals.py`; `examples/29_intelligence_service/starter-catalogue/reviews.json`.

- Release only from a committed revision whose continuous integration run passed, through the guarded pilot workflow, so that the deployed image can always be rebuilt from the repository.
- Enable browser sign-in on the pilot for accounts that the operator prepared in advance, with public registration closed, and supply the identity provider's publishable key as a deployment secret reference.
- Give the operator one command that prepares an invited account and returns a single-use link for setting a password, so that an invitation does not depend on outgoing email.
- Let each invited person create, label, see and revoke personal client keys, and show copy-ready connection settings for OpenCode, Codex and Claude Code.
- Compile a starter catalogue of useful, skill-sized material from existing repository sources across the four persistent intelligence layers, refuse an item without a known licence, keep every item a candidate until the owner approves it, then publish the approved items with exact digests.
- Prove with one supported native client that selected material is downloaded, placed in that client's native layout and actually loaded, and record what the client received.
- Bound the cost of anonymous requests before inviting anyone: limit sign-in and activation attempts for each address and keep the pause between identity key reads.
- Run the invited-user journey with two people outside engineering, record every obstacle as roadmap work, and repeat the restore and rollback drills on the release that they used.

Complete when: An invited person signs in, creates a client key, connects a supported client, finds and downloads useful starter material, sees usage, and loses access when the operator disables the account. Every release comes from a committed revision and has a rehearsed rollback.

Failure control: An uninvited visitor, a disabled account, a key whose owner was disabled, an older release reading newer records, and a burst of forged sign-in tokens must all be refused without exhausting the service.

Authority: The private beta service has no public registration or live charges and makes no model calls. Engineering model calls use the completed OWNER-17 authority and its recorded ceiling. Candidate material is published only after the independent exact-byte approval delegated by the owner; the owner retains withdrawal authority. Provider changes use only the prepared connections.

Rollback or safe stop: Redeploy the previous release image by digest. Personal keys use a record version that the previous release refuses, so a rollback cannot honor a key whose owner was disabled. Remove browser sign-in from the host configuration to return to operator-issued keys.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-17-T01 | operational_drill | Deploy a release from a committed revision through the guarded workflow and compare the running image with the image built from that revision. | The running image digest equals the built digest and the revision's continuous integration run passed. | A working tree with uncommitted changes, or a revision whose checks failed, must be refused before anything is deployed. |
| D-17-T02 | operational_drill | Write service state with the new release, including a personal key whose owner is then disabled, and read it with the previous release image. | The previous release refuses the personal key and still accepts operator-issued keys. | State written without the record version change must be shown to be accepted, so the drill can detect the defect. |
| D-17-T03 | end_to_end | A person outside engineering completes sign-in, key creation, client connection, search, download and usage review on the deployed service. | Every step succeeds without help and the record names the release that served it. | An address that was not invited and a disabled account must both be refused at sign-in. |
| D-17-T04 | end_to_end | A supported native client downloads selected starter material and loads it from its native layout. | The client's own record shows that it loaded the material, with matching digests. | Tool discovery alone, or a file that exists but is never read, must not count as loading. |
| D-17-T05 | local_contract | Send a burst of forged sign-in tokens that carry unknown key identifiers. | At most one identity key read happens inside the pause and ordinary requests keep working. | With the pause removed, the number of key reads must grow with the burst. |
| D-17-T06 | local_contract | Anchor the catalogue to a new revision, which rewrites the trailing anchor line of every body, and carry the independent approvals across the move. | An approval carries only when the sole difference between the bytes its reviewers read and the body today is that line and the revision it names. A carried approval keeps its reviewers, their decisions and the digest they judged, and records that it was carried rather than freshly approved. | A body with a changed sentence beside the changed anchor line, a removed anchor line, a second anchor-looking line, a changed word inside the anchor line other than the revision, changed trailing whitespace, and a body whose recorded digest does not match it must each refuse the carry and return the item to candidate state, and a comparison that always carries must let every one of those cases through. |

### D-18: Ship the September 22 review: one main line, live checks and launch readiness

Owning steps: S-6.29, S-6.33, S-6.34, S-6.35, S-6.36, S-6.37, S-6.38, S-6.39. Acceptance dependencies: D-17.

Owning boundaries: `AGENTS.md`; `.github/workflows/fly-pilot.yml`; `src/loop_engine/core/service_runtime/web_assets/index.html`; `tools/test_context_routes.py`.

- Merge every branch and worktree onto main with a line-survival check after each merge, and keep only the snapshot branch.
- Restore what the September 22 merges dropped and prove it with the same check.
- Put the commit, push and release authority in one section of AGENTS.md and make every entry point agree.
- Apply the README plan so every entry point matches the code and the live state.
- Apply grants automatically after a catalogue release and state the client address source in every drill.
- Run the hosted website, catalogue, service and protocol checks on every hostname after each release and record them.
- Ship the website fixes from the persona and interface reviews.
- Prepare the fact-checked Y Combinator package for the owner.

Complete when: GitHub main, local main and production are one state; the live site passes every hosted check on every hostname; a first-time visitor can request an invitation and follow Get started to a working connection; the rules have one home.

Failure control: A merge that drops branch lines, a release that leaves the library empty, and a page that contradicts the live payment state must each fail a named check.

Authority: Commit, push and release under the owner authority recorded in CLAUDE.md and AGENTS.md; legal text, spending beyond the allowance and destructive operations still need the owner.

Rollback or safe stop: Redeploy the previous image digest recorded in the newest release record; restore any ref from the September 22 archive bundle.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-18-T01 | operational_drill | Release from main through the guarded workflow and run the hosted checks on every hostname. | Every hostname passes the website, catalogue and service checks and the library offers the approved items. | Removing the grant step must leave the library empty and fail the catalogue check. |
| D-18-T02 | local_contract | Replay each September 22 merge and compare the branch lines with the result. | Every line a branch added is present or its replacement is recorded. | The unrepaired merges must fail the check. |
| D-18-T03 | end_to_end | A first-time visitor requests an invitation and follows Get started. | The request is stored for review and every setup step works in order. | A payment state that contradicts registration must fail the page check. |

### D-19: Engines behind fixed edges for every functional component

Owning steps: S-6.30, S-6.31, S-6.32, S-6.40, S-6.41, S-6.42, S-6.60. Acceptance dependencies: D-12.

Owning boundaries: `src/loop_engine/core/boundary_registry.py`; `src/loop_engine/core/external_harness.py`; `src/loop_engine/core/harness_intelligence_search.py`.

- Index every engine slot in the boundary registry with its edge, protocol, engines and check.
- Declare engines with lifecycle, capabilities, effects, licence and cost model.
- Let the host declare installed engines, the initial choice and ordered fallbacks for each slot.
- Select engines without effects and record every decision with its reasons.
- Measure every engine inside the envelope and read qualified evidence for ranking.
- Build the harness executor slot with the Agent Client Protocol adapter first.
- Make hosted search a slot with the measured policy and a relevance floor.
- Search for existing projects and papers before each engine is built and record the decision.

Complete when: Adding, swapping or retiring an engine changes one adapter and one declaration and no neighbour; every selection is recorded; evidence reorders engines only under the declared rule.

Failure control: A slot without an edge, default or collected check fails conformance; evidence below the minimum sample cannot reorder engines; an in-process engine cannot satisfy a delegation step.

Authority: Engine choice never grants file, network, model or spending authority; comparison traffic for model-backed engines defaults to zero.

Rollback or safe stop: Switch the host choice back to the previous engine; engines are never deleted, only retired.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-19-T01 | local_contract | Register a new engine in one slot with only its adapter and declaration. | The engine becomes selectable after qualification with no call-site change. | An engine missing a required capability must be removed at eligibility with a recorded reason. |
| D-19-T02 | held_out_comparison | Run two engines side by side on a deterministic sample of one slot. | The decision records and measurements identify which engine served each request. | Evidence below the minimum sample must leave the declared order unchanged. |
| D-19-T03 | end_to_end | Delegate one real step through a harness engine chosen by the executor slot. | The step result, cost, time and acceptance are recorded and a second harness can replace the first by configuration. | An in-process engine must be refused for a step that requires delegation. |

### D-20: Meet the open standards and make served files safe to trust

Owning steps: S-6.43, S-6.44, S-6.45, S-6.46, S-6.47. Acceptance dependencies: D-17.

Owning boundaries: `src/loop_engine/core/service_runtime/http.py`; `src/loop_engine/core/plugin_bundles.py`; `tools/build_host_catalogue_manifest.py`; `pyproject.toml`.

- Negotiate the current and the previous Model Context Protocol revision at runtime and refuse unknown ones with the supported list.
- Serve skills, context files and plugins in the open formats and in each harness's own layout, and ship a package for Pi.
- Admit outside material only through a malicious-skill regression set, SPDX licences and a bill of materials.
- Close the dated deadlines and the small public-site and release gaps before inviting users.
- Measure each item against a no-skill arm and a raw-source arm before any benefit claim.

Complete when: A client on either protocol revision connects and loads an approved item in its own layout; every served item shows its licence, digest and measured or unmeasured effect; the dated deadlines are met.

Failure control: An unknown protocol revision, an item that breaks a harness's limits, a malicious skill, an unknown licence and an unmeasured benefit claim must each be refused by a named check.

Authority: Protocol and format work are engineering decisions. Model calls for the measurement arms need OWNER-17; paid plans above the allowance need OWNER-18.

Rollback or safe stop: Turn off the new protocol binding in the host configuration and keep serving 2025-11-25; withdraw a format layout without touching the items.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-20-T01 | end_to_end | Connect one client with the 2026-07-28 revision and one with 2025-11-25 and download an approved item with each. | Both connect, list the tools and download the item, and each decision names the selected revision. | A request for an unknown revision must be refused with the supported list before any effect. |
| D-20-T02 | local_contract | Emit one plugin item as an Agent Plugins 1.0.0 folder and lint every served skill. | The folder validates against the pinned schema and every skill passes each harness's limits. | A skill whose name breaks a harness's limit must be withheld from that harness. |
| D-20-T03 | local_contract | Run admission over the malicious-skill regression set. | Every malicious item is refused with a named reason and every benign item is accepted. | Replacing the scanner with one that accepts everything must fail the regression check. |

### D-21: Meet customers in the harness they already use

Owning steps: S-6.48, S-6.49, S-6.50, S-6.61. Acceptance dependencies: D-20.

Owning boundaries: `src/loop_engine/core/plugin_bundles.py`; `src/loop_engine/core/service_runtime/web_assets/client-recipes.json`; `embodiments/opencode`.

- Offer proven setup paths for every kind of customer, including a container with one process for each step's harness.
- Add a website picker for hardware, goals, resources and harness that returns one exact setup.
- Seed every download with starter context and instructions that configure the customer's harness for one harness per step.
- Publish subscription plugins for Hermes Agent and OpenClaw after recorded load tests.
- Build Baltor forks of OpenCode and Pi and measure them against upstream.

Complete when: A customer with any supported harness, hardware and resources follows one exact path to a working connection; the plugins and forks load selected items in recorded sessions.

Failure control: An unproven setup path, a plugin that writes a key to disk, a container recipe with broader authority than chosen and an unmeasured fork claim must each fail a named check.

Authority: Building plugins and forks is engineering work; publishing to another project's channel follows that project's rules; no model calls without OWNER-17.

Rollback or safe stop: Withdraw a setup path, plugin listing or fork release; the service and the items are unchanged.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-21-T01 | end_to_end | Follow the picker's path for one hardware and harness combination on a clean container. | The container connects, downloads the starter files and loads a selected item. | A path whose recorded install is missing must not be offered. |
| D-21-T02 | end_to_end | Install the Hermes Agent plugin with a personal key and load one item. | The session records the item offered, fetched, loaded and used. | A plugin build that writes the key to a file must fail the check. |
| D-21-T03 | held_out_comparison | Run the OpenCode fork and upstream OpenCode on the same frozen tasks. | Accepted work, tokens, time and cost are recorded for both. | A fork claim without the matched upstream run must fail the evidence check. |

### D-22: Learn from every request and grow the library by occupation and data work

Owning steps: S-6.51, S-6.52, S-6.53, S-6.54, S-6.58, S-6.62, S-6.63, S-6.64. Acceptance dependencies: D-19.

Owning boundaries: `src/loop_engine/core/retrieval.py`; `src/loop_engine/core/harness_intelligence_search.py`; `src/loop_engine/core/seeded_generation.py`.

- Record the item version with every request and detect wrong context and repeated asks.
- Analyse items fetched together and use the evidence for prefetch and ranking after the minimum sample.
- Add self-learning, hybrid BM25 and near-duplicate engines behind the search slot and measure each.
- Generate candidate intelligence along the occupation grid with recorded licences.
- Build data-work packs as text and as tested code with typed inputs.
- Record the model and the decision method of each step and analyse them over many tasks.

Complete when: Ranking and prefetch improve from measured fetched-together evidence; the library grows by occupation and data work through independent review; every step records its model and decision method.

Failure control: Evidence below the minimum sample, an engine that fails the relevance floor, a generated item without review, untested code and a decision beyond its step's authority must each be refused.

Authority: Usage analysis uses metadata only unless a customer opted in; generation with a model needs OWNER-17.

Rollback or safe stop: Switch search back to the previous engine and remove a ranking signal from the host configuration; candidates are never deleted, only left unapproved.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-22-T01 | held_out_comparison | Rank held-out queries with and without the fetched-together evidence. | The measured relevance and latency of both are recorded. | Evidence below the minimum sample must leave the ranking unchanged. |
| D-22-T02 | local_contract | Serve one data-work item as text and as code and run the code's tests. | The tests pass and the item carries its licence and digest. | Code without tests must be refused at admission. |
| D-22-T03 | local_contract | Generate candidates for one occupation cell. | Every candidate carries its source, licence and grid values and stays a candidate. | A generated item marked approved without a review record must fail the check. |

### D-23: Show, review, reach and scale

Owning steps: S-6.55, S-6.56, S-6.57, S-6.59. Acceptance dependencies: D-18.

Owning boundaries: `src/loop_engine/core/service_runtime/web_pages.py`; `src/loop_engine/core/service_runtime/web_assets/index.html`; `fly.toml`.

- Run persona reviews from inside the company and from customer personas after every release.
- Build landing pages and demonstration pages by role with recorded runs.
- Measure today's machine and write the scale plan with triggers and costs.
- Find popular posts and draft replies that a person approves and posts.

Complete when: Every release has a persona review; visitors find a recorded demonstration for their role; the scale plan names the first split and its trigger; replies go out only with a person's approval.

Failure control: A demonstration without a recorded run, a persona review without the live site, a scale change above the allowance and an automatic post must each fail a named check.

Authority: Spending above the allowance needs the owner; posting needs OWNER-19.

Rollback or safe stop: Withdraw a page or a demonstration; the scale plan changes nothing until approved.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-23-T01 | end_to_end | Pick a role on the demonstration page. | A recorded run for that role is shown with its cost and limits. | A demonstration whose recorded run is missing must fail the page check. |
| D-23-T02 | operational_drill | Run the persona review on the live site after a release. | Every finding is recorded as roadmap work or fixed. | A review that did not load the live site must be refused. |
| D-23-T03 | local_contract | Draft a reply for one found post. | The draft waits for a person's approval. | A configuration that posts without approval must fail the check. |

### D-24: Take requests for access and invite one person from them

Owning steps: S-6.12, S-6.15, S-6.21. Acceptance dependencies: D-17.

Owning boundaries: `src/loop_engine/core/service_runtime/waitlist.py`; `src/loop_engine/core/service_runtime/waitlist_checks.py`; `src/loop_engine/core/service_runtime/web_assets/index.html`; `tools/waitlist_operator.py`; `docs/guides/waiting-list-and-invitations.md`.

- Serve one public form that takes an email address and a short note, with no sign-in, and give every refusal its own typed code and its own words on the page.
- Keep the entries in the existing service collection as a versioned record with its own states, written through the same atomic batch contract as every other service record.
- Let an operator read the list and apply exactly one decision at a time, where repeating the same request identity replays the first decision and writes nothing.
- Erase the address and the note when a person asks to be taken off the list, through the same decision contract, leaving the one-way digest and the decision history.
- Offer the form, the links to it and the discount sentence only from the record the service publishes, so that a page never offers what the host cannot honour.
- Refuse an invitation that promises a discount unless a saved payment account report names that exact code and the service reports that checkout takes one.
- Count accepted entries for one source only where the host declared where the client address comes from, and record that no count was taken where it did not.
- Record the invitation before the account is prepared and before the message is sent, and record what happened to that message, sent or unknown, without repeating anything automatically.

Complete when: A visitor leaves an address on a service that keeps a waiting list, an operator sees it, invites one entry with a discount the payment account holds, and can erase an address on request. A service without a waiting list makes no offer at all.

Failure control: A flood from one machine, a repeated address, an address that already has an account, a second invitation for the same entry, an invitation whose code no checkout would take, and a removal that leaves the address in the record must all be refused.

Authority: No public registration. One invitation is one authorized email and one prepared account. The payment objects are created in test mode by the payment setup command, not by the invitation command, which holds no payment credential.

Rollback or safe stop: Remove the waiting list block from the host configuration. The page then offers nothing and the public endpoint answers that the service keeps no list. Entries already recorded stay readable by the operator.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-24-T01 | local_contract | Send more requests from one caller than the policy allows, on a host that declared no client address source and on one that declared a forwarded address header. | The undeclared host accepts every caller and answers that no count was taken; the declared host counts each forwarded address on its own. | Naming the socket peer where no source was declared must be shown to close the form after the allowance, which is the collapse the rule prevents. |
| D-24-T02 | local_contract | Remove one entry on request and read the stored record, not the view. | The address and the note are absent from the stored record, the state is removed, and the same address may ask again. | With nothing named as erased, the stored record must still hold the address, so the check can detect it. |
| D-24-T03 | end_to_end | Load the served page in a real browser against a service with a waiting list and against one without. | The form, its links and the discount sentence appear only where the service publishes that it keeps a list and that checkout takes a code, and an address typed into the form reaches the operator's listing. | A page that shows the form before the service answers must fail the same check. |
| D-24-T04 | local_contract | Invite one entry while checkout does not take a discount code, and while no payment account report names the code. | Both stop before the invitation is recorded and before any message is prepared, each with its own reason. | With the checkout rule removed, the code must be sent to someone who has nowhere to type it. |
| D-24-T05 | real_provider | Read the promotion codes in the payment account, then run the invitation with the report that names the created code. | The code exists in the account and the invitation carries the same code the report names. | An empty promotion code list must refuse the invitation. Read on September 21, 2026: the list was empty and no invitation could be sent. |

### D-25: Go fully live: open registration and self-serve paid onboarding

Owning steps: S-6.65, S-6.85, S-6.66, S-6.67, S-6.68, S-6.38, S-6.46. Acceptance dependencies: D-17, D-24.

Owning boundaries: `src/loop_engine/core/service_runtime/browser_identity.py`; `src/loop_engine/core/service_runtime/web_pages.py`; `src/loop_engine/core/service_runtime/web_assets/index.html`; `tools/check_hosted_website.mjs`; `.github/workflows/fly-pilot.yml`.

- Close the identity provider's back-door sign-up (OWNER-03, or the service-side guard), stage the sign-up secrets through standard input, and switch registration and email sign-up on.
- Keep one way in for customers, Baltor's sign-up, and three internal staff roles with permissions fixed in code: superadmin, developer and analytics. Retire invitations, the waiting list, operator-issued customer keys and the provider's raw sign-up as ways in.
- Run the whole funnel live: request, confirm, choose a password, subscribe, get set up, and a verified first load in the customer's own harness.
- Serve every built page and hostname surface with robots, sitemap, canonical and social metadata, and pass the responsive lab on three browser engines.
- Show real service status, give customers a support address and exercise the incident runbook once.
- Complete the account lifecycle: keys, usage, plan changes, cancellation, data export and account deletion.

Complete when: A stranger finds Baltor, creates an account, pays, connects their own harness and uses a package, can see status and reach support, and can leave with their data.

Failure control: The provider's public sign-up, a password set before confirmation, access before payment settles, a page missing from the site map and a status view that hides a failing check must each fail a named check.

Authority: The owner approved the terms and opening registration on September 23, 2026. Closing the provider's public sign-up needs OWNER-03 because settings access was never granted. Engineering makes no live charge; a customer paying is the product working. A privacy notice change for visitor measurement needs the owner.

Rollback or safe stop: Switch registration and email sign-up off in the host configuration so the waiting list takes requests again; redeploy the previous image by digest for page changes.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-25-T01 | end_to_end | Create an account on the live service with a fresh address. | Request, confirmation, password choice and first sign-in succeed, and the account is listed for the operator. | An account created through the provider's public sign-up path must be refused. |
| D-25-T02 | end_to_end | Subscribe with an operator-entitled test account and follow Get set up for one harness. | The entitlement is active, the setup path is exact, and the harness's own record shows the first package loaded with matching digests. | A download that the harness never reads must not count as a first load. |
| D-25-T03 | operational_drill | Crawl every page in the typed site map on every hostname after a release. | Every page answers with its own title and canonical address, and robots.txt and sitemap.xml list them. | Removing one route must fail the site map check. |
| D-25-T04 | operational_drill | Make one hosted check fail on a copy of the service. | The status view shows the failure and the incident runbook's rollback path is followed. | A status view that stays green must fail the drill. |

### D-26: Reach 10,000 and then 100,000 approved harness packages, then add 100 to 1,000 a day

Owning steps: S-6.69, S-6.70, S-6.81, S-6.82, S-6.83, S-6.40, S-6.62, S-6.63, S-6.64. Acceptance dependencies: D-20, D-22.

Owning boundaries: `tools/candidate_review`; `tools/prepare_harness_candidates.py`; `tools/review_catalogue_candidates.py`; `tools/build_catalogue_release_bundle.py`; `tools/research_source_watch.json`; `artifacts/hundredk-serving-probe-2026-09-22`.

- Calibrate the three-family review panel on malicious and benign controls and measure its throughput and error gate on Ollama Cloud models and the Codex command line.
- Run generation waves from the gap matrix and customer search misses with producers of at least two families, deterministic pre-checks, critique and repair.
- Scout skill, plugin, protocol server and harness file sources; import what may be copied with its licence, and turn the rest into idea records for original rewrites.
- Release approved packages daily as catalogue releases with customer-readable notes, and pass the 100,000-row serving probe.
- Maintain the library: re-verify on harness changes, merge near-duplicates, withdraw with reasons and rank by measured use.

Complete when: The library holds 10,000 and then 100,000 distinct approved packages served in each harness's own layout, and grows by 100 to 1,000 approved packages a day with every count and model call recorded.

Failure control: A self-approved package, changed bytes after review, a copied restricted body, a count that mixes candidates with approved packages and a day over its model-call ceiling must each be refused.

Authority: Model calls run through Ollama Cloud with the key already in the environment and through the Codex and Claude Code command lines, within the owner's existing subscriptions, each recorded with its model, usage and outcome, and stop before a declared daily ceiling. Approval is delegated to the independent panel; the owner can withdraw any package.

Rollback or safe stop: Point the host back at the previous catalogue release; candidates are never deleted, only left unapproved.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-26-T01 | held_out_comparison | Run the panel on frozen malicious and benign controls it has not seen. | The measured false-approval rate on malicious controls meets the declared gate, and throughput per hour is recorded. | A panel that approves every item must fail the gate. |
| D-26-T02 | local_contract | Push one wave through pre-checks, the panel and a catalogue release bundle. | Every released package has three approvals from non-producer families bound to its exact bytes. | A package approved by its producer's family must be refused. |
| D-26-T03 | operational_drill | Run the serving probe at 100,000 approved rows on the live machine size. | Search, listing and download meet the probe thresholds. | Lowering a threshold must fail the probe's own check. |
| D-26-T04 | local_contract | Give a scout a skill under a restrictive licence. | It produces an idea record and no copied text reaches a candidate. | A candidate whose text matches the restricted source must be refused. |

### D-27: Clear components: one index, contract test kits and one home for every topic and term

Owning steps: S-6.84, S-6.71, S-6.72, S-6.73. Acceptance dependencies: D-19.

Owning boundaries: `src/loop_engine/data/engine_slots.yaml`; `src/loop_engine/core/engines/slot_checks.py`; `src/loop_engine/core/component_contracts.py`; `docs/components/COMPONENT-GUIDE-MAP.yaml`; `tools/check_component_guides.py`; `terminology.yaml`.

- Generate one component index from the slot catalogue, component interactions, folder map, boundary registry, guide map and terminology, and refuse a stale index.
- Give every slot one contract test kit that every engine passes alone, add composition tests for joined slots and end-to-end journey tests, and run isolated bindings in containers.
- Keep one authoritative record per topic and one definition per term, map every alias to one current term, and refuse conflicting definitions.
- Write the functional component standard into the development rules: one short rule in AGENTS.md, one standard document that extends the engine slot design, and a check for each rule.

Complete when: Every component has one contract, one guide, one owning folder, tested engines and simple names that do not conflict, and all of it is findable in one generated index.

Failure control: A stale index, an engine that passes only its own tests, a term with two definitions and two records claiming one topic must each fail a named check.

Authority: Engineering work with no model calls, provider changes or spending.

Rollback or safe stop: Generated pages and checks can be switched off in continuous integration without touching runtime behavior.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-27-T01 | local_contract | Change one slot's contract version without regenerating the index. | The index check names the slot and fails. | An index check that ignores contract versions must fail its own mutant test. |
| D-27-T02 | local_contract | Run the step executor's contract kit against two engines and one deliberately broken engine. | Both engines pass the same fixtures and the broken engine fails. | A kit that accepts the broken engine must fail its mutant test. |
| D-27-T03 | local_contract | Add a second definition of an existing term in a new document. | The term conflict check refuses it. | Removing the check must let the conflict through, shown by a mutant. |

### D-28: Selectable engines at every slot, with a Baltor-native engine beside every adopted project

Owning steps: S-6.74, S-6.75, S-6.30, S-6.31, S-6.32, S-6.44, S-6.52. Acceptance dependencies: D-19, D-27.

Owning boundaries: `src/loop_engine/core/engines/slots.py`; `src/loop_engine/core/external_harness.py`; `src/loop_engine/data/component_interactions.yaml`.

- Map pinned, preferred and automatic selection onto the slot fields and record every decision.
- Wrap every adopted outside project as a pinned engine behind one slot and build a Baltor-native engine that passes the same kit.
- Serve multi-file packages through the Harness Working Directory Compiler with a native engine and an optional agent-harness engine, writing binaries and file modes byte for byte.
- Add the index-backed and hybrid search engines behind the search slot and measure each on the held-out query set.

Complete when: Any component's engine can be pinned, preferred or chosen automatically, replaced without touching its neighbours, and compared on recorded evidence.

Failure control: A pinned selection that falls back, an upstream type crossing an edge, a compiler that changes binary bytes or file modes and a ranking on evidence below the floor must each fail.

Authority: Engine choice never grants file, network, model or spending authority. Comparison traffic for model-backed engines defaults to zero.

Rollback or safe stop: Switch a slot's selection back to its previous engine in the host configuration; engines are retired, never deleted.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-28-T01 | local_contract | Pin an engine that is unavailable. | The step fails with the pinned engine named and no fallback runs. | A pinned selection that falls back must fail. |
| D-28-T02 | end_to_end | Compile one multi-file package with a binary asset and an executable script for two harnesses through each compiler engine. | Every file's bytes and mode match the source and each harness loads the package. | An engine that rewrites binary bytes must be refused at the edge. |
| D-28-T03 | held_out_comparison | Rank the held-out queries with the current, index-backed and hybrid search engines. | Recall, refusal accuracy and latency are recorded for each engine. | Evidence below the minimum sample must leave the declared order unchanged. |

### D-29: Agents that manage and improve the system

Owning steps: S-6.76, S-6.77, S-6.80, S-6.55, S-6.41, S-6.51. Acceptance dependencies: D-18.

Owning boundaries: `artifacts/agent-workflows-2026-09-23`; `tools/refresh_research_sources.py`; `docs/roadmap/roadmap.yaml`.

- Keep the state review, library wave, harness discovery, research sweep and plan validation workflows in the repository, parameterized and free of machine paths.
- Declare each recurring job with its schedule, workflow and an effect policy of reports or candidates only, and record every run.
- Refresh the Harness File Profiles weekly from each harness's own documentation and source.
- Run a persona review after every release and learn from retrieval: wrong context, repeated asks and items fetched together.
- Model the recurring jobs as Practitioner Loops that stage candidates for independent review.

Complete when: The system is reviewed, researched, measured and grown on a schedule, and every change an agent proposes reaches main or the live service only through review.

Failure control: A job that pushes, approves or publishes on its own must be refused by its effect policy, and a run without a record must fail the audit.

Authority: Recurring jobs write reports and candidates. Model calls follow the recorded authority with a per-run ceiling. Merging and releasing follow AGENTS.md.

Rollback or safe stop: Pause a recurring job through its scheduling state; its past reports stay.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-29-T01 | operational_drill | Run the daily state review on two consecutive days. | Both reports exist, name their inputs and differ only where the state changed. | A run that edits a repository must be refused by its effect policy. |
| D-29-T02 | local_contract | Change one harness's documented instruction file name in a fixture. | The profile refresh proposes a candidate profile change with evidence. | A silent profile edit must fail the check. |
| D-29-T03 | local_contract | Give a recurring job the effect policy of reports only and let its workflow attempt a push to main. | The push is refused before it leaves the machine and the refusal is recorded with the job and its policy. | With the effect policy check removed, a mutant must let the push through and fail a named test. |

### D-30: A release train for upgrades, features, packages and engines

Owning steps: S-6.78, S-6.79, S-6.35, S-6.57. Acceptance dependencies: D-18.

Owning boundaries: `CHANGELOG.md`; `pyproject.toml`; `fly.toml`; `tools/build_catalogue_release_bundle.py`.

- Record every release kind with a versioned record: the service by image digest, the catalogue by manifest digest, client recipes and plugins by version, and the local engine by package version.
- Generate a customer changelog page from those records.
- Put new features behind versioned host configuration flags and roll them out in stages.
- Publish the local engine to a package index with an upgrade command that negotiates versions with the service.
- Measure the machine under load and name the first scale step and its trigger.

Complete when: Customers get new features, packages and engines on a predictable train, can see what changed, and can upgrade or roll back safely.

Failure control: A release without a record, a flag that widens authority, a silent protocol downgrade and a scale change above the allowance must each fail.

Authority: Releases follow the guarded workflow from a checked main. Spending above the recorded allowance of 50 dollars a month needs the owner.

Rollback or safe stop: Point the host back at the previous release record, turn a flag off, or reinstall the previous local engine version.

Verification cases are required evidence, not recorded passes.

| Case | Evidence level | Scenario | Pass condition | Negative control |
|---|---|---|---|---|
| D-30-T01 | operational_drill | Release, then roll back to the previous image by digest. | The live checks pass on both, and both releases have records. | A release missing its record must fail the release check. |
| D-30-T02 | local_contract | Turn a flagged feature on for one account. | Only that account sees it, and turning it off restores the previous behavior without a release. | A flag read from an older record version must be refused. |
| D-30-T03 | end_to_end | Upgrade the local engine from the previous version. | It negotiates the protocol with the service and keeps the customer's settings. | A client that silently downgrades a required protocol must be refused. |

## Launch benefit drafts

These are proposed messages, not qualified performance claims.

### Put your models to work overnight

Give a complex task time to make progress with models running on your own machine, within the limits you set.

Required evidence: A declared long-running local-model task population, exact hardware and models, restart and cancellation tests, independent task checks, and a useful morning report. Local execution alone does not prove local inference or completion by morning.

Owning steps: S-6.8, S-6.9, S-6.24.

### Spend fewer tokens on repeated work

Reuse suitable code and pass relevant information to each step instead of regenerating everything or resending the whole history.

Required evidence: Matched task comparisons with a quality floor, complete input and output accounting including retries and helpers, failures, cache categories, and total cost. No significant or percentage savings claim before measured results.

Owning steps: S-6.3, S-6.6, S-6.11, S-6.19.

### Give each step the expertise it needs

Select useful guidance, tools and past findings for the work at hand, and request more information when a gap appears.

Required evidence: Reviewed domain material, permission and compatibility checks, actual loading evidence, and independent outcomes against absent, excessive, stale and misleading context. Right-sized does not mean always minimal or always correct.

Owning steps: S-6.4, S-6.7, S-6.9, S-6.10.

## Original planning windows

Historical planning targets, not a current schedule, release forecast or completion evidence.

| Hours from start | Work | Steps |
|---|---|---|
| 0 to 3 | Establish the plan, product contract, and durable catalogue | S-6.17, S-6.4, S-6.1, S-6.2, S-6.3 |
| 3 to 7 | Authentication, payments, and deployment preparation | S-6.13, S-6.21 |
| 7 to 12 | Connect the intelligence service and durable usage | S-6.5, S-6.6, S-6.7, S-6.8 |
| 12 to 18 | Website, subscriber dashboard, and qualified starter packages | S-6.10, S-6.9, S-6.20, S-6.11, S-6.23, S-6.12, S-6.24 |
| 18 to 22 | Qualify the release and rehearse recovery | S-6.14 |
| 22 to 24 | Authorized hosting, release decision, and paid activation | S-6.15, S-6.16 |
| 0 to 24 | Continue structural improvements and controlled experiments | S-6.18, S-6.19, S-6.22, S-6.25, S-6.26, S-6.27 |
| 0 to 24 | Streamline the main line to harness intelligence | S-6.28 |

## Launch work

| Step | Deliverable | Status | Dependencies |
|---|---|---|---|
| S-6.29 | Consolidate every branch and worktree onto main, restore what the September 22 merges dropped, and keep only the snapshot branch | building | S-6.28 |
| S-6.35 | Release automation and automated live checks after every release | building | S-6.26 |
| S-6.68 | Support, status and incident response for paying customers | proposed | S-6.35 |
| S-6.43 | Speak the current protocol revision: negotiate the 2026-07-28 Model Context Protocol beside 2025-11-25 | live_qualified | S-6.29 |
| S-6.33 | Website fixes from the persona and interface reviews | building | S-6.12 |
| S-6.67 | Serve every built page and hostname surface | building | S-6.33 |
| S-6.46 | Close the dated deadlines and small gaps before inviting users | proposed | S-6.35 |
| S-6.65 | Open public registration with email-first sign-up | building | S-6.24, S-6.46 |
| S-6.85 | One way in: every customer account comes from Baltor's sign-up, and internal staff roles are fixed in code | proposed | S-6.65 |
| S-6.34 | One home for rules and authority, and a documentation cleanup | building | S-6.17 |
| S-6.39 | Search access policy: protect the library from scraping, with a free quota to start | proposed | S-6.32 |
| S-6.38 | A familiar customer dashboard with the full account lifecycle | proposed | S-6.33 |
| S-6.66 | Self-serve paid onboarding with a verified first load in the customer's harness | proposed | S-6.65, S-6.21, S-6.48 |
| S-6.48 | Setup paths for every kind of customer, with seeded starter files | proposed | S-6.42 |
| S-6.55 | Persona reviews after every release | proposed | S-6.33 |
| S-6.44 | Harness Working Directory Compiler and native package compatibility | proposed | S-6.43 |
| S-6.49 | Subscription plugins for Hermes Agent and OpenClaw | proposed | S-6.44 |
| S-6.30 | Engines behind fixed edges: the shared engine framework | building | S-6.28 |
| S-6.31 | The harness executor slot: delegate each step to a standard harness | building | S-6.30 |
| S-6.42 | Harness landscape: forks of Pi and OpenCode, and independent instances in every supported harness | building | S-6.31 |
| S-6.50 | Baltor forks of OpenCode and Pi | proposed | S-6.42 |
| S-6.61 | One place for the customer's credentials and connections, with scoped access for every step | proposed | S-6.31 |
| S-6.32 | Hosted search as an engine slot with the measured policy and a relevance floor | proposed | S-6.30 |
| S-6.52 | More retrieval engines behind the search slot | proposed | S-6.32 |
| S-6.60 | A layer before every model call that decides one model or several | proposed | S-6.30 |
| S-6.40 | Grow the library: original package factory first, scheduled source ingestion later | proposed | S-6.30 |
| S-6.69 | The package factory: 10,000, then 100,000 approved packages, then 100 to 1,000 more each day | building | S-6.40, S-6.63, S-6.62 |
| S-6.81 | Source scouts: search tools for skills, plugins, protocol servers and harness files | proposed | S-6.40, S-6.76 |
| S-6.63 | An independent review panel of several model families | proposed | S-6.45 |
| S-6.62 | Catalogue releases and library settings with good defaults | building | S-6.40 |
| S-6.70 | Serve 100,000 packages: pass the capacity probe with paged listing and an indexed search | proposed | S-6.62, S-6.32 |
| S-6.83 | Maintain 100,000 packages: re-verification, near-duplicates, deprecation and withdrawal | proposed | S-6.69, S-6.51 |
| S-6.64 | Independently authored alternatives to restricted-source ideas | proposed | S-6.63 |
| S-6.54 | Data-work intelligence packs as text and as tested code | proposed | S-6.40 |
| S-6.53 | Generate intelligence along the occupation grid | proposed | S-6.40 |
| S-6.45 | Make served files safe to trust: a malicious-skill regression set, exact licences and a bill of materials | proposed | S-6.40 |
| S-6.41 | Harness run records for self-improvement | proposed | S-6.31 |
| S-6.51 | Learn from retrieval: wrong context, repeated asks and items fetched together | proposed | S-6.41 |
| S-6.58 | Choose the model and the decision method for each step | proposed | S-6.31 |
| S-6.37 | Demonstrations, case studies and benchmarks with and without Baltor, each on its own subdomain | proposed | S-6.33 |
| S-6.56 | Landing pages and demonstration pages by role | proposed | S-6.37 |
| S-6.47 | Measure each item against a no-skill arm and a raw-source arm before claiming a benefit | proposed | S-6.37 |
| S-6.36 | Y Combinator application package, fact-checked | building | S-6.34 |
| S-6.59 | Go-to-market: early, useful replies under popular posts, approved by a person | proposed | S-6.36 |
| S-6.57 | A scale plan from one machine to many services | proposed | S-6.35 |
| S-6.78 | A release train for the service, the catalogue, client recipes and plugins, and the local engine | proposed | S-6.35, S-6.62 |
| S-6.79 | Feature flags and staged rollout through versioned host configuration | proposed | S-6.78 |
| S-6.17 | Maintain one continuation plan and regenerate its status artifact | offline_verified | none |
| S-6.4 | Bind the provisioning catalogue to durable records and tenant disclosure authority | building | S-6.17 |
| S-6.13 | Prepare portable deployment definitions and procedures for every hosting family | building | S-6.17 |
| S-6.1 | Confine the complete provisioning write set | building | S-6.17 |
| S-6.2 | Make unresolved guardrail decisions stop dependent effects | building | S-6.17 |
| S-6.3 | Repair model-call occurrence identity, retention, and training persistence | building | S-6.17 |
| S-6.26 | Remove unused pre-launch compatibility while retaining versioned handshakes | building | S-6.17 |
| S-6.27 | Close independently reproduced contract and data-integrity defects | building | S-6.17 |
| S-6.28 | Streamline the main line to harness intelligence and delegate every step to a harness | building | S-6.17 |
| S-6.5 | Expose provisioning through a versioned Model Context Protocol service | building | S-6.4 |
| S-6.6 | Persist usage and telemetry with acknowledgments and reconciliation | building | S-6.4 |
| S-6.21 | Connect payment lifecycle to durable subscription entitlements | building | S-6.4 |
| S-6.7 | Wire public solving to the declared provisioning dependencies | building | S-6.1, S-6.2, S-6.4 |
| S-6.8 | Connect credential leases and resource admission to harness lifetime | proposed | S-6.7 |
| S-6.10 | Publish qualified starter packages and prove client retrieval | proposed | S-6.4, S-6.5 |
| S-6.9 | Qualify actual instruction and capability use in native harnesses | proposed | S-6.5, S-6.7, S-6.8 |
| S-6.20 | Complete the classification-grid generation and improvement pipeline | proposed | S-6.3, S-6.7, S-6.10 |
| S-6.11 | Publish solutions and verify standalone reuse on fresh inputs | proposed | S-6.9, S-6.20 |
| S-6.23 | Exercise every required internal component through its actual owning entry point | proposed | S-6.3, S-6.7, S-6.8, S-6.9, S-6.20, S-6.11 |
| S-6.12 | Build the website, subscriber dashboard, and operator workflows | building | S-6.5, S-6.6, S-6.21 |
| S-6.24 | Deliver client, authentication, endpoint-based model and native-harness onboarding | building | S-6.5, S-6.9, S-6.12 |
| S-6.14 | Qualify the release candidate on the exact exported tree | proposed | S-6.4, S-6.5, S-6.6, S-6.10, S-6.12, S-6.13, S-6.21, S-6.23, S-6.24, S-6.26, S-6.27 |
| S-6.15 | Deploy an authorized pilot and qualify its real request path | building | S-6.14 |
| S-6.16 | Activate approved paid access and publish the release decision | proposed | S-6.6, S-6.15, S-6.21 |

## Continued improvements

| Step | Deliverable | Status | Dependencies |
|---|---|---|---|
| S-6.25 | Expand the system map to every source file with explicit evidence limits | building | S-6.17 |
| S-6.18 | Reorganize coherent code families and update current callers | building | S-6.17, S-6.1, S-6.2, S-6.3 |
| S-6.19 | Continue flexible composition and controlled improvement research | proposed | S-6.3, S-6.20, S-6.14 |
| S-6.22 | Maintain sourced competitor, prior-art, funding, and strategic-path research | building | none |
| S-6.84 | Write the functional component standard into the development rules, with a check for each rule | proposed | S-6.30, S-6.34 |
| S-6.71 | One generated component index with a drift check | proposed | S-6.30, S-6.34 |
| S-6.72 | Contract test kits: every engine alone, components in groups, the system end to end | proposed | S-6.30, S-6.71 |
| S-6.73 | One topic and decision index, with a term conflict check | proposed | S-6.34, S-6.71 |
| S-6.74 | Pinned, preferred and automatic engine selection at every slot | proposed | S-6.30 |
| S-6.75 | An upstream engine and a Baltor-native engine for every adopted outside project | proposed | S-6.74, S-6.72 |
| S-6.76 | Reusable development workflows and recurring reviews with declared effect policies | ready | S-6.17 |
| S-6.77 | Maintenance as Practitioner Loops that stage candidates for independent review | proposed | S-6.76, S-6.41 |
| S-6.80 | Keep every Harness File Profile current with a verified weekly refresh | proposed | S-6.44, S-6.76 |
| S-6.82 | News and release watchers that turn changes into component work | proposed | S-6.81 |

## Every retained initiative

Legacy statuses remain historical component claims until current integration evidence is recorded.

| Workstream | Earlier steps | Continuation steps |
|---|---|---|
| Reusable capabilities and detection | S-0.5, S-1.10 | S-6.10, S-6.20, S-6.11 |
| Intelligence, storage, classification, and qualification | S-1.1, S-1.2, S-1.3, S-1.11, S-2.5, S-2.9, S-2.10, S-2.11, S-2.27, S-2.32, S-2.33, S-2.34, S-2.35, S-2.38, S-2.39 | S-6.2, S-6.4, S-6.10, S-6.20, S-6.23, S-6.32, S-6.40, S-6.45, S-6.51, S-6.52, S-6.53, S-6.54, S-6.62, S-6.63, S-6.64, S-6.69, S-6.70, S-6.81, S-6.82, S-6.83 |
| Harnesses, provisioning, loaded-file evidence, and authentication | S-2.2, S-2.28, S-2.29, S-2.30, S-2.31, S-2.36, S-2.37, S-2.40 | S-6.1, S-6.5, S-6.7, S-6.8, S-6.9, S-6.24, S-6.28, S-6.31, S-6.41, S-6.42, S-6.43, S-6.44, S-6.48, S-6.49, S-6.50, S-6.61, S-6.80 |
| Models, decisions, efficiency, cost, and learning | S-1.5, S-1.6, S-1.8, S-2.1, S-2.13, S-2.20, S-2.21, S-2.41, S-4.11 | S-6.3, S-6.6, S-6.19, S-6.47, S-6.58, S-6.60 |
| Flexible composition, solutions, configuration search, and research | S-1.4, S-1.7, S-2.3, S-2.4, S-2.6, S-2.7, S-2.15, S-3.1, S-3.2, S-3.3, S-3.4, S-3.5 | S-6.11, S-6.19, S-6.22, S-6.23, S-6.30, S-6.74, S-6.75 |
| Resource management, hibernation, and cloud capacity | S-2.22, S-2.23, S-2.24, S-2.25, S-2.26, S-4.8, S-4.9, S-4.10 | S-6.8, S-6.12, S-6.13, S-6.57 |
| Hosted service, portability, packaging, and paid operation | S-2.8, S-4.1, S-4.2, S-4.3, S-4.4, S-4.5, S-4.6, S-4.7, S-4.12, S-4.13, S-4.14, S-4.15, S-4.16 | S-6.5, S-6.6, S-6.12, S-6.13, S-6.14, S-6.15, S-6.16, S-6.21, S-6.24, S-6.35, S-6.33, S-6.38, S-6.39, S-6.46, S-6.65, S-6.85, S-6.66, S-6.67, S-6.68, S-6.78, S-6.79 |
| Organization, architecture artifact, and adversarial review | S-1.9, S-1.12, S-2.12, S-2.14, S-2.16, S-2.17, S-2.18, S-2.19, S-3.7 | S-6.17, S-6.18, S-6.25, S-6.26, S-6.27, S-6.29, S-6.34, S-6.55, S-6.71, S-6.72, S-6.73, S-6.76, S-6.77, S-6.84 |
| Branding, business paths, and later career research | S-5.1, S-5.2, S-5.3 | S-6.16, S-6.22, S-6.36, S-6.37, S-6.56, S-6.59 |

## Hosting coverage

Documented procedures are preparation, not live deployment qualification.

| Target | Status | Procedure |
|---|---|---|
| Vercel website and dashboard | documented | [Routine](../guides/hosting-and-deployment-procedures.md#vercel) |
| Vercel Python serving functions | documented | [Routine](../guides/hosting-and-deployment-procedures.md#vercel) |
| Supabase authentication and durable data | documented | [Routine](../guides/hosting-and-deployment-procedures.md#supabase) |
| Local containers and a single server | documented | [Routine](../guides/hosting-and-deployment-procedures.md#local-containers-and-single-server) |
| Fly.io Machines | documented | [Routine](../guides/hosting-and-deployment-procedures.md#flyio-machines) |
| Render | documented | [Routine](../guides/hosting-and-deployment-procedures.md#render) |
| DigitalOcean App Platform | documented | [Routine](../guides/hosting-and-deployment-procedures.md#digitalocean-app-platform) |
| Google Cloud Run | documented | [Routine](../guides/hosting-and-deployment-procedures.md#google-cloud-run) |
| Amazon Elastic Container Service and Fargate | documented | [Routine](../guides/hosting-and-deployment-procedures.md#amazon-elastic-container-service-and-fargate) |
| AWS App Runner | documented | [Routine](../guides/hosting-and-deployment-procedures.md#aws-app-runner) |
| Azure Container Apps | documented | [Routine](../guides/hosting-and-deployment-procedures.md#azure-container-apps) |
| Kubernetes on any qualified distribution | documented | [Routine](../guides/hosting-and-deployment-procedures.md#kubernetes-on-any-qualified-distribution) |
| Hetzner and other virtual server providers | documented | [Routine](../guides/hosting-and-deployment-procedures.md#virtual-servers) |
| Dedicated servers and on-premises hosting | documented | [Routine](../guides/hosting-and-deployment-procedures.md#dedicated-servers-and-on-premises-hosting) |
| Cloudflare Containers | documented | [Routine](../guides/hosting-and-deployment-procedures.md#cloudflare-containers) |
| Static frontend hosting with a separate service | documented | [Routine](../guides/hosting-and-deployment-procedures.md#static-frontends) |
| Additional providers through the same deployment contract | proposed | [Routine](../guides/hosting-and-deployment-procedures.md#additional-providers) |

## Decisions and independent work

- `hosting_authority`: approved. The owner delegated a real private pilot. Scope is recorded in artifacts/architecture-audit-2026-09-19/pilot-deployment-authority.json; Fly Baltor, iad, one Machine, 50 dollars monthly infrastructure, 10 dollars setup, no model calls or live customer charges.
  Independent work: Qualify the existing target, preserve domain and mail records, and keep other deployment families separate.
- `live_model_authority`: pending. An available exact model route and declared call, time, token, and spending authority for the live harness qualification.
  Independent work: Run offline protocol, storage, client, confinement, and failure checks.
- `payment_authority`: pending. The runtime sandbox and test credential are prepared. Public prices, product terms, live charging and exact paid-release activation still need owner approval.
  Independent work: Implement entitlements, durable usage, reconciliation, and a test payment adapter.
- `layer_classification`: pending. Resolve dedicated Harness Intelligence and external service views versus changing the canonical persistent-layer vocabulary.
  Independent work: Keep the dedicated components and references over the current four layers; prepare a migration decision with compatibility tests.

## Activity

- 2026-09-20T17:54:30Z: cloudflare_active_and_all_website_hostnames_verified. The registry publishes Cloudflare's assigned nameservers and the Free zone reports active. Root, www and app hostnames each pass 45 live website checks with valid HTTPS and source-matching assets. DNS-only records are configured; no Cloudflare proxy or web firewall claim is made. Some recursive resolvers still retain old nameservers or negative mail-record answers. Resend remains pending except its provider CNAME, which is verified. No email was sent and no paid-release gate is closed. The credential helper passes 23 checks and both new required-scope guards fail under removal controls. Owner domain cards now show prepared access and engineering-owned verification, not another manual setup request. Evidence: artifacts/architecture-audit-2026-09-19/domain-cutover-verification-2.json; artifacts/architecture-audit-2026-09-19/hosted-root-domain-1.json; artifacts/architecture-audit-2026-09-19/hosted-www-domain-1.json; artifacts/architecture-audit-2026-09-19/hosted-custom-domain-cutover-1.json
- 2026-09-20T17:45:57Z: cloudflare_records_and_registrar_nameservers_configured. Corrected the invalid OAuth scope request and verified a new Cloudflare grant with write permissions. Created the Free baltor.ai zone and 14 website, certificate and sender records. Namecheap accepted and read back dana.ns.cloudflare.com and nile.ns.cloudflare.com. Registry publication and Cloudflare activation remain pending. The owner confirms no existing mail or forwarding. The app hostname passes all 45 live browser checks after a validated host-configuration update and restart. Root and www certificates are requested but not yet qualified. Resend sender verification has started; no email was sent. Claude handoff includes native Namecheap authorization and the current Cloudflare grant, with 23 local credential checks. No extra machine, model call, live charge, source commit or push occurred. Evidence: artifacts/architecture-audit-2026-09-19/domain-cutover-progress-1.json; artifacts/architecture-audit-2026-09-19/hosted-custom-domain-cutover-1.json; tools/test_operator_credentials.py
- 2026-09-20T16:39:02Z: account_code_and_plain_language_site_deployed. Deployed Fly release 7 on the existing machine and volume after 5938 package checks, 284 focused launch checks, 120 local browser checks, seven container checks and 104 installed-service checks. Fifteen optional package checks remain untested. Exact identity network registration passes conformance. Hosted website, service and administrator checks pass 45, 16 and 12 cases respectively; the temporary administrator-test token was revoked. The first hosted browser attempt retained a stale-copy assertion and its failure; the repaired assertion also rejects a wrong secret destination. Public registration, billing and complete task execution remain unqualified and disabled where applicable. Evidence: artifacts/architecture-audit-2026-09-19/verification-deployment-account-code-1.json; artifacts/architecture-audit-2026-09-19/deployment-account-launch-slice-1.json; artifacts/architecture-audit-2026-09-19/hosted-account-code-2.json; artifacts/architecture-audit-2026-09-19/hosted-account-service-1.json; artifacts/architecture-audit-2026-09-19/hosted-account-admin-1.json
- 2026-09-20T16:13:38Z: claude_code_provider_access_handoff_verified. Installed five local-project Claude Code connections using dynamic keyring-backed headers and the existing Fly helper. Claude Code 2.1.271 reports all five connected. Thirteen named credential references are available; expired Resend and Cloudflare access tokens refreshed within existing grants. Fifteen offline helper checks pass and the selected Stripe sandbox was confirmed through the command wrapper. The first isolated Fly probe lacked the desktop session bus and the first Stripe command used an unsupported flag; corrected checks pass. The private export is permission-restricted and contains references, not raw secrets. Missing domain, authentication-settings and registrar permissions remain missing. No model session, domain change, deployment, payment or source publication occurred. Evidence: docs/guides/developer-credential-handoff.md; tools/operator_credentials.py; tools/test_operator_credentials.py; artifacts/architecture-audit-2026-09-19/credential-handoff-verification-1.json
- 2026-09-20T15:54:22Z: plain_language_site_and_broader_takeover_plan_checked_locally. Public How it works now uses steps, useful information and checked results in local source. Complete runtime definitions remain in technical documentation. All 120 local browser checks pass; the first failed route-placement attempt is retained. Focused checks pass 104 HTTP and 31 durable-runtime cases against an unchanged package identity. The current conformance run still fails on two undeclared identity network boundaries. Thirty-seven planning and architecture tests, documentation lint and 125 local file links pass. The main document now has twelve delivery packages, sixty actions, three benefit drafts and a downloadable Fable handoff. No new deployment, source commit, push, model call or live charge occurred. Evidence: artifacts/architecture-audit-2026-09-19/plain-language-handoff-browser-2.json; artifacts/architecture-audit-2026-09-19/handoff-focused-checks-1.json; docs/context/FABLE-5-1-HANDOFF-2026-09-20.md
- 2026-09-20T15:32:00Z: provider_access_checkpoint_and_fable_handoff_plan. Resend management access and Stripe runtime sandbox access are confirmed; the existing Supabase project responds with email confirmation enabled. Sender domains and Cloudflare zones are absent. New browser identity work is local only and two network-boundary conformance findings remain. Twelve delivery packages expand existing engineering steps; three launch benefit drafts have explicit evidence requirements. Public How it works copy is being simplified without renaming canonical runtime contracts. No deployment, model call, live charge, source commit or push is performed by this checkpoint. Evidence: docs/context/DEVELOPMENT-CHECKPOINT-2026-09-20.md; docs/context/FABLE-5-1-HANDOFF-2026-09-20.md; artifacts/architecture-audit-2026-09-19/account-website-browser-2.json
- 2026-09-20T05:12:58Z: guided_website_deployed_and_live_regression_checks_passed. Deployed the frozen website-journey image to the existing single Fly machine in iad without changing its resources or volume. All 5914 executed package checks passed, with 15 optional checks untested. The deployed website passed 42 checks, the service passed 16 and administrator lifecycle passed 12; the temporary test token was revoked. OpenCode 1.17.9 reconnected without a model turn. A second 84-request read-only latency sample had no failures; median lexical and character-similarity hybrid round trips were 62.3 and 57.0 milliseconds on the small diagnostic catalogue. The single HTML serialization guard was extended after its browser test caught missing new comparison data. No paid-release gate was closed, no model spending was enabled, and no source commit or push was made. Evidence: artifacts/architecture-audit-2026-09-19/hosted-website-journey-1.json; artifacts/architecture-audit-2026-09-19/hosted-service-attempt-7.json; artifacts/architecture-audit-2026-09-19/hosted-administrator-attempt-5.json; artifacts/architecture-audit-2026-09-19/native-opencode-connection-2.json; artifacts/architecture-audit-2026-09-19/verification-website-journey-2.json
- 2026-09-20T05:03:00Z: measured_website_journeys_native_connection_and_candidate_review. Reviewed signed-out pages for all nineteen identified original vendors, four adjacent references and Baltor. The main development file contains the current page comparison without changing historical feature claims. Guided client configuration, an actual browser protocol check, a first retrieval example and an access/data page pass 114 local browser checks. An adversarial delayed-response case reproduced and repaired cancellation of public setup data during sign-in, while sign-out still aborts credential-bound requests. OpenCode 1.17.9 connected to the live service without starting a model turn or changing permanent client settings. Eighty-four bounded read-only requests succeeded; the small diagnostic catalogue does not establish production capacity. Twelve records across four persistent layers and ten content families were staged through the existing atomic catalogue contract; normal search excludes them and no hosted publication or independent qualification occurred. Broad release gates remain open. Evidence: docs/research/WEBSITE-JOURNEY-REVIEW-2026-09-20.md; artifacts/architecture-audit-2026-09-19/guided-connection-browser-6.json; artifacts/architecture-audit-2026-09-19/native-opencode-connection-1.json; artifacts/architecture-audit-2026-09-19/service-latency-1.json; artifacts/architecture-audit-2026-09-19/candidate-intelligence-staging-1.json
- 2026-09-20T04:08:13Z: lighter_benefit_led_website_and_developer_checkpoint. The light-default website leads with reusable solutions and five customer problems. Server and client diagrams remain on How it works. All 5914 executed offline checks passed with 15 optional checks not tested; 85 local browser, 28 hosted browser, 16 hosted service and 12 administrator checks passed. A deployed backup was restored in a network-isolated local container with 15 passing checks, including restart and idempotency. The private archive remains outside Git and the temporary test container and volume were removed. The checkpoint routes future developers to existing owners, exact evidence and remaining work. All eight broad launch gates remain open. Evidence: docs/context/DEVELOPMENT-CHECKPOINT-2026-09-20.md; artifacts/architecture-audit-2026-09-19/verification-light-benefits-checkpoint-1.json; artifacts/architecture-audit-2026-09-19/hosted-light-benefits-1.json; artifacts/architecture-audit-2026-09-19/pilot-backup-restore-2.json
- 2026-09-20T03:26:32Z: public_website_intelligence_and_client_server_explanation_deployed. The redesigned Baltor website is deployed. It separates hosted intelligence from customer-controlled execution, labels request and response data, explains the four persistent intelligence layers and provides an interactive task-specific context example. All 78 local browser checks and 25 hosted browser checks passed, including narrow layouts, keyboard interaction, exact deployed assets and 200 percent text sizing locally. The existing hosted service and administrator checks still pass. The example is not an observed native harness run; public email registration and paid subscriptions remain incomplete. Evidence: artifacts/architecture-audit-2026-09-19/hosted-intelligence-website-1.json; artifacts/architecture-audit-2026-09-19/intelligence-website-browser-4.json; artifacts/architecture-audit-2026-09-19/intelligence-site-container-2.json
- 2026-09-20T02:56:08Z: email_free_administrator_and_prepared_supabase_project. The administrator can issue, inspect and revoke scoped testing credentials without email. The default limit is 20 active tokens; secrets are shown once and only digests persist. Twelve live administrator checks passed. Supabase project qfzxmjznlwiopgvfgtsw is healthy in us-east-1 on the quoted free profile. Resend Free is selected for authentication mail and Cloudflare Free is recommended for DNS; neither selection claims a completed connection. Evidence: artifacts/architecture-audit-2026-09-19/hosted-administrator-attempt-2.json; artifacts/architecture-audit-2026-09-19/pilot-deployment-progress.json
- 2026-09-20T01:40:10Z: real_private_pilot_and_operator_connections. The website responds over HTTPS on baltor-pilot.fly.dev. Sixteen live transport checks passed for authentication, metadata search, digest-bound body delivery, tenant isolation and retry accounting. Stripe Model Context Protocol access is verified for Baltor in test mode; Fly inspection tools are configured and checked. The Supabase account has been created and a fresh authorization is pending. Signup, production email, shared storage, Stripe runtime integration, native harness use and paid launch remain incomplete. Evidence: artifacts/architecture-audit-2026-09-19/hosted-service-attempt-3.json; artifacts/architecture-audit-2026-09-19/pilot-deployment-progress.json
- 2026-09-20T00:40:05Z: baltor_github_fly_connection_prepared. Fly access to Baltor and the saved system-keyring credential were verified. The GitHub pilot environment holds the protected token, accepts only main and has deployment disabled. A separate service image and manual workflow are prepared locally. No Fly application or paid resource was created; the workflow is not published or live qualified. Evidence: docs/guides/launch-setup-runbook.md; .github/workflows/fly-pilot.yml; tools/test_fly_deployment.py
- 2026-09-19T23:58:38Z: whole_system_document_and_fly_hosting_guidance. The main document covers eighteen architecture areas, including frontend, backend, all Loop roles, intelligence, retrieval, wrappers, verification, resources and improvement. Fly.io is the owner's preferred compute host; Supabase is the recommended data and identity target. Six concrete setup steps separate owner preparation from incomplete engineering. No resource was created and no purchase or deployment was authorized. Evidence: tools/architecture_report/diagrams.json; tools/architecture_report/hosting.json
- 2026-09-19T14:12:54Z: continuation_planned. Planning and artifact management are being installed; implementation findings remain open. Evidence: The September 19 review, ten local reproductions, current source checks, and the recovered Claude workstreams.
- 2026-09-19T19:17:24Z: local_service_and_report_integration. Local serving is implemented without hosted customer execution or a required LangGraph dependency. One self-contained HTML report is being generated from the roadmap, source inventory and preserved Claude matrices. Provider accounts, native materialization and paid launch remain open. Evidence: The durable checkpoint records 153 owning and dependent checks with 11 detected mutants. The local HTTP checkpoint records 39 checks with 17 detected mutants. Root command dispatch and nested architecture-map integration are under verification.
- 2026-09-19T23:07:18Z: website_and_decision_tools_locally_checked. The earlier frozen source passed 5852 executed checks, 204 focused checks and five removed-guard controls; the workspace passed 28 browser checks. A clean wheel install passed the 48-check service smoke test. These results belong to that source, not later changes or real providers. Evidence: artifacts/architecture-audit-2026-09-19/launch-slice-checkpoint.md
- 2026-09-19T23:07:18Z: owner_checklist_and_configurable_external_decisions. Fifteen owner preparation tasks and full embedded guides are being added to the main development file. Jev, Circuit and compatible decision endpoints use named host settings and shared gateway contracts. The owner clarified that model services are externally operated; no model launcher remains in this work. Evidence: docs/guides/jev-and-harness-decision-tools.md; tools/architecture_report/development.js
- 2026-09-19T23:29:29Z: endpoint_verification_and_primary_source_research. Current frozen source passes 5876 executed offline checks with 15 optional checks untested; 228 focused checks and five removed-guard controls pass. SoL-Pi is a candidate Pi extension profile, not a default or a new runtime. SemIf exposes uncalibrated scores and needs a distinct endpoint and confidence contract before integration. No model servers or weights were launched. Evidence: artifacts/architecture-audit-2026-09-19/decision-endpoints-checkpoint.md; docs/research/SOL-PI-HARNESS-REVIEW-2026-09-19.md; docs/research/SEMIF-DECISION-READOUT-REVIEW-2026-09-19.md
- 2026-09-20T21:30:00Z: takeover_review_gate_repairs_and_release_blockers. Claude Code reviewed the September 19 and 20 work after the previous developer reached its usage limit before deploying a release candidate. Read-only checks confirmed Fly release 7, host-key sign-in only, and closed registration and billing. An isolated rerun reproduced 30 of 30 conformance gates, 5,990 self-test checks, 206 tool tests, 336 focused checks and 131 browser checks. Two continuous integration suites failed and were repaired without weakening a check. A dropped link to the dimension discovery addendum was restored. 120 unregistered hardcoding findings in new files received exact reviewed entries, and the packaged browser library received one exclusion bound to its contents. The release candidate's rollback defect was proven against the real release 7 image and fixed with an owner-bound key record version. Identity key reads are now paused between attempts, the subscription reader ignores proxy settings from the environment, a durable write with a tuple is confirmed instead of reported unknown, two loosened negative controls are restored, and the browser library's licence terms are served. Package D-17 defines the private beta. Evidence: docs/context/TAKEOVER-CHECKPOINT-2026-09-20.md; artifacts/architecture-audit-2026-09-19/rollback-key-version-1.json
- 2026-09-20T21:40:00Z: first_release_from_a_committed_revision. The work of September 19 and 20 was committed and pushed to main. Its first continuous integration run failed in three ways that only a clean machine shows, which were repaired without weakening a check. The guarded release workflow then ran for the first time, stopped at a guard whose text match could never succeed, was repaired, and deployed release 8 from revision e63f614. Every hostname passes 46 website checks and the service passes 16 service and protocol checks. Deployment is switched off again. A monitoring-only DMARC record was added for the domain. Browser sign-in, personal client keys, registration and billing remain switched off. Evidence: artifacts/architecture-audit-2026-09-19/pilot-release-8.json; artifacts/architecture-audit-2026-09-19/domain-mail-policy-1.json

## Earlier artifact

[Claude System Map](https://claude.ai/code/artifact/a9e49f80-1fa5-4acc-af02-71e2dfa6786d) remains the recovered historical view.
This repository artifact is maintained from the plan. Editing the hosted Claude copy
requires a connected editing surface; this generator does not publish it.
