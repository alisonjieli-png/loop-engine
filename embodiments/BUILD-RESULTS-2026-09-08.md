# Experimental workspace build results, 2026-09-08

The workspace now preserves alternatives rather than selecting one design for every project. This build adds independently launchable canonical-runtime experiments, source mirrors, remix plans and controlled-mutation plans. It also links the independently developed catalogs instead of copying them into another unqualified runtime.

## What exists

| Collection | Contents | State |
|---|---|---|
| Canonical execution arrangements | Native, fresh process, persistent session, session pool, parallel portfolio, durable reactive | Six runnable deterministic mechanism implementations |
| Additional designs | Adaptive tree, reuse first, OpenCode per step, brokered container, local agent host, transactional semantics, speculative decoding | Seven explicit plans; launchers refuse until qualified |
| Source mirrors | new_overnight_build, overnight, vigil, speculative_prompting, overnight-docs | Five immutable archived source collections with provenance; overnight has an additional newer catalog snapshot |
| Remixes | Repair with governed reuse; hybrid gateway/tools; local product with durable solver; horizons with scoped pull | Four integration plans with exact qualification obligations |
| Mutations | Process lifetime, context slicing, routing, decomposition, reuse, containment, restart, serving | Eight experiment folders, with implemented versus planned status |
| Linked axis experiments | Claude's `devtools/embodiment_axes` | 30 embodiments across seven families; self-checks rerun successfully |

There is no default winning embodiment. The source mirrors preserve original implementations as research inputs; they are not automatically imported or promoted. Prepared source workspaces must be outside the governed product tree, while the archives remain inside the mirror folders.

## Observed canonical comparison

All six arrangements used the same first twelve tasks from the frozen 1,000-task study, a 60-second per-arrangement grant and configured concurrency of two. The backend performed trusted deterministic sum, histogram and stable-unique operations. A separate verifier computed expected values outside the producer.

| Arrangement | Verified tasks | Candidate attempts | Worker processes observed | Wall seconds |
|---|---:|---:|---:|---:|
| Native | 12/12 | 12 | 1 | 0.407 |
| Fresh process | 12/12 | 12 | 12 | 5.380 |
| Persistent session | 12/12 | 12 | 1 | 0.864 |
| Session pool | 12/12 | 12 | 2 | 1.284 |
| Parallel portfolio | 12/12 | 24 | 24 over the bounded run | 4.947 |
| Durable reactive | 12/12 | 12 | 1 | 1.558 |

These are single-pass mechanism timings on a shared machine. The portfolio deliberately spends twice as many candidate attempts. They do not measure OpenCode startup, provider tokens, model quality, real-repository repair or a universal architecture winner. All model-call counts in this comparison were zero by construction of the explicitly deterministic backend.

Evidence: [comparison.json](../artifacts/embodiment-comparison-2026-09-08/comparison.json). Each arrangement has its own manifest, attempts, canonical Run History and reactive output database alongside that file.

## Qualification

- All 1,000 task folders passed positive-reference and deliberately wrong-output controls. The population digest is `95c3a4a20a6e9195da79168bfe63bf22b9e9f9e04bcaa3119888a5cfddb778d6`.
- The lab's 19 tests passed in a clean virtual environment with user-site startup excluded. They cover actual packet delivery, process identity, state separation, cancellation, bad-candidate refusal, failed-attempt accounting, persisted history, current/random/as-of serving, archive integrity and path refusal.
- All five archived source collections were digest-checked and prepared successfully in private workspaces. Preparation did not execute them.
- The newer overnight catalog snapshot at `8a6c4214c1cfaea4ab6b7f22468843d419310df2` passed 71 scripted tests with network denied and source mounted read-only.
- All 30 axis-catalog self-checks passed, including its container smoke. These remain independent reference experiments, not product execution authority.
- Source conformance and clean-wheel conformance passed. The wheel was built and installed in a new virtual environment; all six arrangements then verified three tasks each against the installed runtime with no source-package fallback.
- Ruff, Markdown structure checks and `git diff --check` passed. The lab qualification is added to CI before the existing hardcoding audit step.

One broad source self-test attempt hit a timeout in the unchanged optional MCP SDK mismatch/cleanup check. Its seven checks passed alone. Claude's handoff reports a separate full pass of 3,412 checks in 1,392 seconds. Those are separate observations; this report does not relabel the timed-out attempt as successful. The pre-existing hardcoding CI failure is not resolved by this build.

## Review corrections retained

The [handoff review](../artifacts/review-2026-09-07/HANDOFF-REVIEW-2026-09-08.md) records the latest findings. Notably, static import counts do not establish that the entire memory subtree is unused; some package initializers are incorrectly classified as dark by that approximation. The uncommitted speculative_prompting catalog contains 33 described folders but only 15 with implementation code. The overnight selector normalizes away meaningful string literals, and its fingerprint does not cover all implementation dependencies.

The external pandas startup hook was reproduced falsifying a comparison. It remains untouched; new qualification used an isolated environment. The reported exposed provider key needs rotation before further live runs. No key was inspected or printed here, and other agents' long-running processes were not terminated.

## Next qualification boundary

The next phase is to bind real model and harness adapters to these experiments under exact model, capacity, effect, environment and budget contracts. Start with a small independently checked task population, preserve every failed or unavailable attempt, and compare one axis at a time before combining treatments. Source availability, a folder, or a successful scripted run does not establish live readiness.

No commit, push, deployment or provider benchmark was performed by this build.
