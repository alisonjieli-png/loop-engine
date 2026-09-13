# Loop Engine project review

Reviewed September 8, 2026, America/New_York. Repository: `/home/username/loop-engine`, branch `main`, revision `acfd826eeee3ea2c05b638031ff235b709a69eb2`, including the existing uncommitted changes.

Loop Engine has a coherent runtime model, substantial contract enforcement, and a passing component suite. The current checkout also has reproducible defects in sandbox termination, capability exposure, scheduling, record queries, and Studio. Its public acceptance checks fail. The recent session history preserves many failures honestly, but several corrections have not reached the canonical onboarding documents or main source tree. I would not use the passing self-test count as evidence that the current product workflows are ready for release.

This was a review. No project source was fixed, committed, published, or restored. Review scripts, a source snapshot, a built wheel, and test artifacts are in this report's temporary directory. No external model was called. Provider exercises used existing offline fixtures or a local HTTP fixture; Docker checks used the already installed pinned image with no container network access.

## Findings requiring attention

P1 means a failure of an important operational boundary or a major supported workflow. P2 means an actionable correctness or evidence defect with narrower impact. Experimental defects are explicitly separated from production behavior.

### 1. P1: A timed-out Docker command keeps running and can change files

[workspace_optional.py:194](/home/username/loop-engine/src/loop_engine/core/workspace_optional.py:194) uses `subprocess.run(..., timeout=...)` for the Docker client and immediately returns `command_timeout` on timeout. It does not stop or confirm termination of the container.

A real pinned-container probe slept for three seconds and then wrote a marker into its temporary workspace. With a one-second command limit, the runtime returned failure after 1.01 seconds. The container was still running. The marker appeared afterward. A unique container name was added solely to inspect and clean up that exact test container; it subsequently exited and Docker removed it.

This permits writes after the runtime has declared the command finished, including while a repair or verification step uses the same workspace. Track the exact container identity, terminate it on timeout, and confirm termination before reporting the result or starting dependent work. The current output-size limit also truncates only after `capture_output=True` has buffered the output; it is not a bound on host memory use.

### 2. P1: Three registered capabilities cannot be selected by the main solver

[adaptive_practitioner_records.py:1625](/home/username/loop-engine/src/loop_engine/core/adaptive_practitioner_records.py:1625) only handles five capability references and ends its availability expression with `else False`. It never offers `core.environment.describe`, `core.intelligence.search`, or `core.source.profile`, even with the relevant source and disclosure grants. The first two declare no required permissions.

This affects execution as well as prompt visibility: [adaptive_practitioner.py:406](/home/username/loop-engine/src/loop_engine/core/adaptive_practitioner.py:406) rejects proposals outside this same list. A probe with all applicable grants exposed five of eight declared capabilities.

There is another defect behind the hidden search capability. [adaptive_practitioner_orientation_capabilities.py:77](/home/username/loop-engine/src/loop_engine/core/adaptive_practitioner_orientation_capabilities.py:77) reads `portfolio.records`, which does not exist on the real `PractitionerContextPortfolio`. Passing `load_practitioner_context()` raises `AttributeError`. The handler also validates `kinds` but then searches with `kind=None`, ignoring it. Its advertised four-layer/history coverage exceeds the implemented Context record search.

Recent session logs describe fixes, but those changes are only in the isolated continuation worktree. They are not present on main. Integrate and verify the complete selection-to-execution path, including the actual portfolio type and accurate capability description.

### 3. P1: Concurrent reactive admissions can exceed the declared capacity

[reactive_scheduler.py:200](/home/username/loop-engine/src/loop_engine/core/reactive_scheduler.py:200) checks duplicates and pending count before taking a serialized writer transaction. A two-connection probe synchronized the existing count reads under `AdmissionPolicy(1)`. Both admissions succeeded, leaving two pending inputs.

A conflicting trigger ID also raises a raw SQLite `IntegrityError` without rolling back. The next legitimate claim on that scheduler then raises `OperationalError: cannot start a transaction within a transaction`.

The duplicate check, capacity check, trigger insertion, and activation insertion need one atomic transaction with rollback and a typed collision result.

Two additional P2 scheduler defects were reproduced:

- [claim():236](/home/username/loop-engine/src/loop_engine/core/reactive_scheduler.py:236) selects an item before excluding saturated series. With one active A, another queued A, and ready B, a global claim returns `None`; an explicit B claim succeeds. Select among eligible series before choosing work.
- [terminal():389](/home/username/loop-engine/src/loop_engine/core/reactive_scheduler.py:389) checks worker/fence identity but not lease expiry. A one-second lease accepted completion ten minutes later when no separate recovery call had run. Heartbeat can likewise renew an expired lease. Expiry must hold at each relevant transition, not only after another caller runs recovery.

### 4. P1: Valid unknown token usage breaks Studio

[studio_server.py:176](/home/username/loop-engine/src/loop_engine/core/studio_server.py:176) and [line 216](/home/username/loop-engine/src/loop_engine/core/studio_server.py:216) add `prompt_tokens + eval_tokens` directly. Run History deliberately permits missing usage as `None`.

A valid history created through `RunHistory.append()`, `commit()`, and `save()` with missing usage causes both the run list and run detail projections to raise `TypeError`. The corresponding API wrapper raises an uncaught `LoopError`. One affected run also breaks the summary that consumes the list.

Carry unknown totals, known subtotals, and completeness through the UI. Do not fix this by replacing unknown usage with zero. The existing browser fixture has no semantic calls and does not cover this case.

### 5. P1, local environment: System Python falsifies a pandas comparison

[/home/username/.local/lib/python3.14/site-packages/usercustomize.py:20](/home/username/.local/lib/python3.14/site-packages/usercustomize.py:20) overrides a quantity comparison, and [line 40](/home/username/.local/lib/python3.14/site-packages/usercustomize.py:40) replaces `pandas.read_csv`.

A fresh system-Python probe reading a row with `qty=900, stock_status=low` returned `True` for `bool((df['qty'] <= 50).all())`. The expected result is `False`. The repository's Python 3.10 virtual environment does not load the hook. This review's core checks used that environment or a fresh isolated installation.

The earlier [handoff review:73](/home/username/loop-engine/artifacts/review-2026-09-07/HANDOFF-REVIEW-2026-09-08.md:73) had already identified this problem. Its author and origin are not established by the inspected logs. System-Python pandas evidence affected by this hook needs clean re-execution; this does not automatically invalidate runs performed in a separate clean container. The hook was left unchanged because this request was for a review.

### 6. P1, verification: Public acceptance fails, and CI skips the checks that expose it

Fresh execution of [run_acceptance.py](/home/username/loop-engine/examples/22_product_quickstart/run_acceptance.py:324) fails on task A with `VERIFICATION_FAILED`. The fixture writes `sample.json` in [line 179](/home/username/loop-engine/examples/22_product_quickstart/run_acceptance.py:179) but does not declare it as an input or output. [independent_verification.py:166](/home/username/loop-engine/src/loop_engine/core/independent_verification.py:166) consequently refuses an undeclared dependency file.

The installed-wheel CLI fixture hits the same verification failure, attempts to continue, exhausts its supplied responses, and ends with `PROVIDER_UNAVAILABLE`. This is a local fixture failure, not evidence of an external provider outage. The source acceptance runner stops at task A, so tasks B through D were not exercised by that command.

The [latest CI run for this exact commit](https://github.com/alisonjieli-png/loop-engine/actions/runs/34188241659) passes the self-test and conformance on Python 3.10, 3.11, and 3.12, then fails the hardcoding gate. The later qualification, examples, product acceptance, and default-install steps are skipped. Documentation and distribution-build jobs pass. This review reproduced the current dirty-tree hardcoding failure: 308 new high-severity scanner findings relative to its baseline, with no invalid allowlist entries. These are scanner findings, not 308 independently confirmed bugs.

Repair the acceptance fixtures for the current independent-verification contract and make behavioral gates execute independently of the hardcoding job while retaining both as required checks. Merely resetting the hardcoding baseline would not repair the observed product failure.

### 7. P2: The solve memory reader and public learning commands use different stores

[solve_learned_memory.py:53](/home/username/loop-engine/src/loop_engine/code_nodes/solve_learned_memory.py:53) reads `<runs_dir>/learning/candidates.jsonl`. The learning/review/promotion CLI uses `CandidateJournal()` in [cli_operations.py:776](/home/username/loop-engine/src/loop_engine/cli_operations.py:776), whose configured root is `LOOP_ENGINE_MEMORY_DIR` or `~/.loop-engine/memory` in [learning_cycle.py:45](/home/username/loop-engine/src/loop_engine/memory/storage/learning_cycle.py:45).

A properly staged, independently reviewed, promoted record in the configured journal passed validation, but the solve returned `no_journal` and selected nothing. The new test manually populates the alternate runs-directory location, so it misses continuity with the public workflow. Resolve both through one typed journal binding. Automatic staging from successful solves remains separate unfinished work; reading operator-promoted records does not prove automatic cross-task learning.

### 8. P2: Managed-record queries apply the result limit before the complete scope

[record_operations.py:303](/home/username/loop-engine/src/loop_engine/core/record_operations.py:303) asks the backend for a limited result set, then [line 306](/home/username/loop-engine/src/loop_engine/core/record_operations.py:306) applies the configured record-ID prefix.

Two records created through approved `RecordOperationService` calls, `aaa.one` and `zzz.one`, share the same namespace/layer/collection but have different host prefixes. The `zzz.` service's `query(limit=1)` returns `not_found`, while `get('zzz.one')` returns `found`. The public query has no offset to recover the hidden result. Apply the complete scope before pagination, retaining the final defensive scope check.

### 9. P2: Canonical handoff text repeats withdrawn evidence and overstates import analysis

[CODEX-START-HERE.md:146](/home/username/loop-engine/docs/context/CODEX-START-HERE.md:146) still reports nine-of-ten survival and a ten-percent false-acceptance rate. The [campaign correction:97](/home/username/loop-engine/docs/verification/UNSEEN-NOVEL-TASK-CAMPAIGN-2026-09-06.md:97) withdraws that interpretation: three prompts conflict with their oracles, the word-square reference is inconsistent, and the claimed larger stress result has no saved record. Those three contradictory tasks consumed 172 of the recorded 283 calls. The v2 population repairs the experiment; it is not fresh successful live evidence.

[EVERYTHING-LEARNED-2026-09-08.md:278](/home/username/loop-engine/docs/context/EVERYTHING-LEARNED-2026-09-08.md:278) also uses static reachability to infer that the whole memory subsystem is untouched. [reachability_report.py:87](/home/username/loop-engine/src/loop_engine/reachability_report.py:87) traverses test-body imports and omits implicit parent-package imports. A clean runtime import loaded memory package initializers the scanner classified as unreached. Conversely, an import does not prove an operation was called or had an effect.

Propagate corrections into the canonical entry documents. Use separate import, invocation, and observable-effect evidence. Neither the 129/406 runtime-import count nor the 240/430 static count measures operational capability coverage.

### 10. P2, committed experiments: Three mechanisms pass their self-checks but fail independent probes

These findings concern `devtools/embodiment_axes`, which explicitly implements experimental designs outside the canonical runtime. They are not automatically defects in production stores or solving.

| Location | Reproduction | Consequence |
|---|---|---|
| [Portfolio:62](/home/username/loop-engine/devtools/embodiment_axes/decomposition/04-portfolio/embodiment.py:62) | `run(World.build(16, seed=2), Port())` reports accepted but returns net 7967 instead of 4637; caller input has zero reads. | It reconstructs and verifies a seed-11 world using only the caller's shard count. Matching-seed tests conceal the wrong-subject verification. |
| [Governed journal:47](/home/username/loop-engine/devtools/embodiment_axes/memory/04-governed-journal/embodiment.py:47) | Modify `store.recall(world)['net']`; later reads return the changed answer with status still `promoted`. | Public reads expose mutable promoted state without a new review or event. Return immutable values or defensive copies. |
| [Port accounting:86](/home/username/loop-engine/devtools/embodiment_axes/shared/port.py:86) | A dispatch followed by injected `TimeoutError` leaves one physical dispatch, zero recorded calls, and zero prompt bytes. | Failed calls disappear from measurements. Record dispatch before execution and preserve failed outcomes and unknown usage. |

The documents generally label deterministic mechanism results correctly and do not present them as live model quality. Preserve that distinction while repairing the experiment controls.

### 11. P2, uncommitted lab: Worker provenance does not establish installed-wheel execution

[process_adapter.py:33](/home/username/loop-engine/devtools/embodiment_lab/process_adapter.py:33) inserts checkout `src` into worker `PYTHONPATH`, even if the controller's interpreter uses an installed wheel. [source_identity():20](/home/username/loop-engine/devtools/embodiment_lab/__main__.py:20) hashes only lab Python files, excluding the imported Loop Engine runtime.

Thus a wheel-controller test launched from the checkout can silently exercise source in its worker arms, and the experiment identity does not distinguish that runtime. This is a confirmed provenance weakness; the historical comparison layout was not established sufficiently to invalidate a particular saved wheel result. Pin and report actual loaded module paths and runtime digests for the controller and workers.

### 12. P2, publication: New documentation links escape the standalone repository

[README.md:116](/home/username/loop-engine/README.md:116) links to `../solver-lab/README.md`. Similar links occur in [embodiments/README.md:4](/home/username/loop-engine/embodiments/README.md:4). They resolve on this host but not in a normal standalone checkout. The offline link gate in [ci.yml:85](/home/username/loop-engine/.github/workflows/ci.yml:85) makes this a pending publication blocker. Use a valid public destination or describe the local sibling workspace without a broken relative link.

## Verification performed now

| Check | Observed result | Limit |
|---|---|---|
| Source offline self-test, Python 3.10.20 | 3,412/3,412 passed in 416.652 seconds; zero provider calls | Existing suite does not cover the independent failures above. |
| Source architecture conformance | All 27 gates passed | Structural conformance is not behavioral completeness. |
| Repository conformance | Passed, 430 Python files, zero problems | Source-tree scope. |
| Fresh wheel build | Passed | Built from an isolated copy of the current source. |
| Wheel identity | All 430 Python files match snapshot bytes; no local Run History/Studio state or experimental modules | See [package-identity.json](package-identity.json). |
| Fresh base installation | Nine packages installed; dependency check passed | Initial offline install lacked cached dependencies; ordinary package fetch then succeeded. |
| Base-wheel self-test | 3,367/3,367 passed in 344.905 seconds; zero provider calls | Optional DuckDB, MCP, model2vec, NumPy/pandas/sklearn, and OpenTelemetry SDK adapters were not tested in the base install. |
| Base-wheel conformance | All 27 gates passed | Independent installed environment outside checkout. |
| Host-runtime examples | 140/140 tests passed | Offline/component population. |
| Development assurance canaries | 19/19 passed | The actual hardcoding delta still fails. |
| Qualification-lab runner | 3/3 passed | Runner tests, not independent task-quality qualification. |
| Canonical experimental lab | 19/19 passed | Deterministic mechanisms. |
| Axis self-checks | 27 embodiments across six families passed | Placement excluded to avoid implicit image pulls; independent probes found defects. |
| README CLI/configuration/history checks | 12/12 passed | Does not run the failing successful-solve fixture. |
| Source product acceptance | Failed task A: `VERIFICATION_FAILED` | Remaining three tasks not reached. |
| Installed-wheel CLI acceptance | Failed: `PROVIDER_UNAVAILABLE` after local fixture exhaustion | Earlier cause was independent-verification refusal. No external provider outage tested. |
| Studio browser checks | 30 views over 15 routes, desktop/mobile, passed; zero browser errors or page overflow | Deterministic zero-semantic-call fixture; missing-usage case fails separately. Screenshots inspected. |
| Hardcoding delta on dirty checkout | Failed; 308 new high-severity findings | Scanner output, not an independently adjudicated bug count. |
| Whitespace check | Passed | No source edits from this review. |

Primary fresh artifacts: [source suite](self-test.log), [source conformance](conformance.log), [base suite](base-self-test.log), [base conformance](base-conformance.log), [host tests](host-tests.log), [hardcoding summary](hardcoding-summary.json), [product outcome](product-acceptance/task-a.json), [README checks](readme-check.json), and [browser audit](studio-browser.log). The acceptance logs contain local fixture prompts and are not a proposed public evidence export.

Final state check: all 430 current source Python files still match the pre-build snapshot, HEAD remains `acfd826`, and the original seven modified tracked files plus seven untracked status entries remain preserved. The review's local Studio server was stopped after browser verification.

## Architecture and product assessment

The intended classification remains coherent:

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

The single Loop type, explicit role/mode separation, candidate lifecycle, source identity, exact-effect approvals, and digest-bound histories provide useful boundaries. The review did not reproduce another acceptance or permission bypass in the inspected host-verifier, semantic qualification/CAS, or managed-record approval paths. That is a bounded review result, not a security certification.

The most serious gaps occur where components meet: capability registration versus selection, CLI journal configuration versus solve configuration, unknown accounting versus UI arithmetic, scheduler admission versus concurrent writers, and Docker client timeout versus workload lifetime. These are practical defects that structural gates and unit fixtures can miss.

The public solver currently has a limited execution envelope. Automatic persistent learning, broad unseen-task competence, universal compilation across embodiments, and production overnight operation remain unproven. The semantic runtime and reuse machinery have meaningful typed/offline coverage, but that coverage does not establish general model quality or transfer benefit. The current host API has broader task evidence than the built-in small-Python quickstart, with host-owned execution and independent verification remaining essential.

Documentation and workflow volume make correction propagation a maintenance issue. A historical report can correctly withdraw a claim while the start-here document continues repeating it. The current experiments add further copies and result formats. Prefer one current status index bound to saved evidence, and test observable behavior at public boundaries before treating another passing module or comparison arm as a completed capability.

## Recent session logs and edits

The review inventoried all 48 readable Codex rollout files whose metadata identifies this project. Four belong to this review and were excluded from historical analysis. It streamed/indexed 44 historical files containing 91,039 JSONL records. Selected semantic review prioritized three main CLI sessions with 41,469 records, roughly 205 MB, plus recent requests, final responses, failure receipts, and artifact-linked actions. This was not a semantic reading of every record. Older deleted rollouts described by earlier reports were not recoverable from the active processes inspected.

The main recent session is [rollout-2026-09-07T18-01-08-01a07de3-afa6-7c31-8407-043ebb187e9d.jsonl](/home/username/.codex/sessions/2026/09/07/rollout-2026-09-07T18-01-08-01a07de3-afa6-7c31-8407-043ebb187e9d.jsonl:1797). Raw conversation bodies and credentials are not reproduced here.

| Period or log anchor | What the available evidence supports |
|---|---|
| September 5-6 parser/host/training work | Source and wheel checks and real task attempts exist. Finals usually retain failures and distinguish local scores, CI status, and unproven generalization. |
| September 6 generalization final | All 84 saved cases passed while the Sales source still had wrong totals. Fourteen attempts and seven invalidated acceptances were retained. Passing saved cases was not sufficient acceptance evidence. |
| Latest session, line 1797 | Reports 49 independent projects and 48 selected checks with explicit limits. Inventory and selected checks do not establish universal compilation. |
| Lines 3301 and 3324 | Atomic handoff results used human decomposition and assembly. The clarification says so explicitly. Main was not shown to discover those graphs autonomously. Claimed native fixes are confined to the continuation worktree. |
| Line 5142 | Eight live attempts and 27 fresh OpenCode instances were reported; multi-component source repair still failed. Instance count is not an established physical model-call count. No commit/push was claimed for that round. |
| Line 6211 | The session ends with `usage_limit_exceeded` at September 9 02:16 UTC, without completing the latest mandate. |

The [latest deliverable status](/home/username/loop-engine/artifacts/universal-compiler-audit-2026-09-09/deliverable-status.json:3) explicitly says `mandate_complete: false`. Its [review:408](/home/username/loop-engine/artifacts/universal-compiler-audit-2026-09-09/REVIEW.md:408) lists remaining integration, accounting, reuse, and overnight proofs. The initial temporary-filesystem failure and later successful test retry are preserved. This is unfinished work, not a falsely completed universal-compiler delivery. The present request authorizes reviewing it, not continuing its earlier model calls or publishing work.

Main began with seven modified tracked files and seven untracked directory/file entries covering experiments and review artifacts. Those changes remained preserved. The isolated solver-lab continuation worktree is detached at the same base revision, with relevant uncommitted capability fixes; it must not be confused with the current main implementation.

The older showcase worktree is 154 commits behind main at `3491e23`, with no branch-only commits. Its expanded dirty inventory is 547 paths: 235 modified, eight deleted, and 304 untracked. All present dirty files share a September 6 modification burst, which does not identify their owner. All dirty source blobs are represented somewhere in main's committed history; unmatched material is showcase/reference media and tooling. Eleven edited historical Run Histories, containing 137 events, validate through the current loader, and their 22 event/manifest files match current main. No history-integrity regression was reproduced there. This is an ownership/reconciliation concern, not permission to delete or merge that worktree.

## Suggested repair order

1. Close the Docker workload-lifetime hole and make reactive admission atomic. Add tests for post-timeout writes, two-connection admission, collision rollback, expired leases, and cross-series eligibility.
2. Repair and run the public product acceptance path in an isolated installation. Make CI report all required behavioral gates even when the separate hardcoding check fails.
3. Connect the actual capability list, real Context portfolio, configured learning journal, record scope, and nullable-usage Studio path through public-boundary tests.
4. Resolve the system-Python hook and rerun affected evaluations in an isolated environment. Propagate withdrawn benchmark claims and unfinished-work status into canonical onboarding.
5. Repair experimental input identity, mutable recall, failed-call accounting, and runtime provenance before drawing new comparisons. Continue universal-compiler work only as separately authorized implementation, with fresh task/evaluator controls where new quality claims are intended.

These recommendations are not implemented by this review. They preserve the existing architectural model and identify the checks that would demonstrate each repair.
