# Claude Opus 5 review of Loop Engine, September 14, 2026

This review covers the complete task-solving pipeline, the owner's artificial
general intelligence direction, and the recent Codex sessions in this
repository. It reviews committed revision `e089f60`, whose hosted continuous
integration run passed. Codex's 67 uncommitted working-tree entries are
reviewed separately in the section on uncommitted work.

Every check in this review was offline. No provider or model call was made.
Findings are either reproduced by a probe (the probe path is named) or
labeled as a reading of the code or records.

## Summary

The engine is not yet able to solve realistic tasks reliably, but the
language model is not the main obstacle.

- Nine live cells executed on September 14. The engine's own verification
  accepted one (CS-001). No cell has an independent evaluator.
- A careful reading of the delivered files finds correct or substantively
  correct work in five of the nine cells. The control loop rejected it,
  lost it, or never wrote it.
- Three control defects account for most of the calls spent: a verifier
  comparison that demands exact JSON equality, an intake deadlock for tasks
  delivered as prompt text, and project refusals whose reasons are replaced
  with `invalid_value`.
- The default acceptance path lets one model grade its own work. A probe in
  which every role believed that six times seven is 48 ended
  `COMPLETED_VERIFIED`.
- The experiment and learning loop is open after dispatch. Grid order is
  fixed, no search method runs, no evaluator is bound, cells cannot see each
  other's history, and the learning journal is written and read at different
  paths.
- The engine can only see text. A ZIP archive, image, spreadsheet, or Parquet
  file is excluded before sandboxed code can use it, and no archive
  capability exists. 105 of the 111 admitted Kaggle tasks keep their data
  only in ZIP archives.

The architecture's design inventory is far ahead of the one-task loop. The
most valuable next work is not more dimensions. It is trustworthy
evaluation, then the control defects, then intake, then a small
cross-family proof.

## Live evidence: what the nine executed cells did

Source: the live campaign records under
`.loop-engine-dev/fabric-readiness-20260913-N8fyhI/`, rebuilt from each
cell's Run History. Probes and timelines:
`.loop-engine-dev/fable-review-probe-20260914/live-cell-forensics/`.

Every executed cell used `harness: native_gateway` with
`harness_fallback: none`. The cells configured for registered alternative
harnesses failed before any model call. No OpenCode, Codex, or Pi process
produced a solution.

| Task and route | Terminal | Calls | Prompt tokens, first to largest | Delivery | What happened |
|---|---|---:|---|---|---|
| CS-001 flash | `COMPLETED_VERIFIED` | 44 | 14,600 to 33,100 | references | Accepted at pass 6. |
| FIN-001 flash | `VERIFICATION_FAILED` | 69 | 14,600 to 27,900 | references | Report written at pass 5; the verifier then failed operationally. |
| OPS-001 flash | `VERIFICATION_FAILED` | 144 | 14,600 to 40,700 | references | Deliverable at pass 4; 18 more passes of decide, verify, and route. |
| DA-001 flash | `NO_PROGRESS` | 100 | 14,300 to 37,500 | inline | All 14 project proposals refused; analysis drafted but never written. |
| AE-001 flash | `BLOCKED_MATERIAL_INPUT` | 168 | 14,500 to 42,800 | inline | Asked the owner how attachments could be made available. |
| ML-001 flash | `BLOCKED_MATERIAL_INPUT` | 232 | 14,400 to 48,100 | inline | A spawned run wrote the deliverable; the owner run ended with zero artifacts. |
| PM-001 flash | provider allowance exhausted | 60 | 14,300 to 26,400 | inline | Four project proposals refused before the allowance ran out. |
| AE-001 pro | `NO_PROGRESS` | 18 | 14,500 to 22,300 | inline | Seven of nine decision responses failed schema admission. |
| CS-001 pro | cancelled by the operator | 489 | 14,600 to 54,700 | references | Deliverables at pass 2, then 76 more passes. |

A reviewer's reading of the delivered files, which is not a qualified
independent evaluation:

- CS-001 flash meets all three acceptance criteria. One sentence blurs a
  retry with a new upload, and one claim comes from another task's
  attachment. Its "independent" check used the same model.
- FIN-001's report is arithmetically correct: 510 against 605, a
  discrepancy of 95 USD split into 60, 25, and 10.
- OPS-001's runbook substantively meets its criteria.
- ML-001's orphaned audit addresses all three criteria.
- CS-001 pro produced deliverables whose values matched every expected value
  in the verifier's cases.

Correction to an earlier record: the September 14 live-cells report says
AE-001 and ML-001 ended blocked on material they did not have. The material
was in the prompt. Both questions asked about the engine's own capabilities.

## Why correct work was not accepted

Each root cause below was confirmed in the committed code.

| Root cause | Calls affected | Committed code | Addressed by Codex's uncommitted work? |
|---|---:|---|---|
| The independent verifier requires exact canonical JSON equality. A case that expects some fields fails when the program prints all of them, and an operational verifier failure leaves only a return of the result. | about 612 | `src/loop_engine/core/independent_verification.py:472-500` (comparison at line 488) | No |
| Tasks delivered as prompt text cannot write a file. Source inspection is offered only when source references exist, and project generation then refuses because nothing was inspected. | 578 across 5 cells, 0 artifacts | `adaptive_practitioner_records.py:1849-1864`, `adaptive_practitioner_project.py:347-381` | Yes, uncommitted and not run live |
| Project refusal reasons are replaced. `GeneratedProjectError` subclasses `ValueError`, so `construct()` turns explanations such as "inline code refused" into `commands[N]: invalid_value`. | at least 79 | `src/loop_engine/core/generated_project.py:130`, `:413-417` | No |
| A spawned run's deliverable never reaches its owner. Spawned Practitioners receive no source references and return only a JSON summary, so their files are never registered as the owner's results. | ML-001, not separable | `adaptive_practitioner_scope.py:96`, `:172` | Not seen |
| Structured-response admission failures. Decisive once; 28 of CS-001's 37 responses needed a code-fence strip. | about 22 rejected responses | model response admission | Partly |

The call counts overlap in places and should not be summed.

Prompt size compounds these defects. About 95 to 97 percent of all tokens
were prompt tokens. Every cell began near 14,500 prompt tokens. In the final
verification packet of CS-001 pro, the context blocks totaled 178 KB. The
current state was 81 KB and held 57 failure entries, of which only 15 were
distinct. The recovery panel exceeded the context window from pass 65.

## The solve pipeline at `e089f60`

```text
loop-engine solve (or the campaign's run_trial)
└── Starting Practitioner Loop: practitioner.reference_nine_step, non-deterministic
    ├── intake: task text, attachments, and source references
    ├── kernel passes: loop condition steps_remain, exit condition steps_complete
    │   ├── orient, decide_next, and method selection (model steps)
    │   ├── packet assembly: 13 labeled context blocks
    │   ├── model gateway and provider adapter
    │   ├── act: a one-Loop Solution graph around the selected capability
    │   │   └── Docker execution of the generated project
    │   ├── verify: a semantic step plus a practitioner.verifier Loop on the same model
    │   └── route, recovery panel, and supervision ladder
    └── terminal projection bound to Run History
```

The "Solution Canvas" recorded for an action is a single-Loop wrapper
compiled and run once around that capability call
(`adaptive_practitioner_capabilities.py:386-408`). Nothing compiles delivered
work into a multi-step reusable graph or runs it again on fresh input.

Findings from the solve-pipeline probes
(`.loop-engine-dev/fable-review-probe-20260914/solve-pipeline/`):

1. **Self-grading acceptance (high).** Independence is labeled
   `isolated_context_shared_model_separate_controller`
   (`independent_verification.py:557`), and the same model writes and
   approves the case expectations (`:294-337`). Probe `p5` ends
   `COMPLETED_VERIFIED` after 10 calls with the delivered answer 48 for six
   times seven. This review re-ran the probe with an identical result.
2. **Terminal mislabels (high).** A provider usage limit after an orientation
   that holds a question becomes `BLOCKED_MATERIAL_INPUT`. A format-repair
   stall carrying a runtime capability question becomes
   `BLOCKED_MATERIAL_INPUT` in autonomous mode. A supervision stop or
   exhausted pass limit after project attempts becomes `VERIFICATION_FAILED`
   with the summary "Generated and verified the requested project."
   (`solve_runtime.py:399-411`, `:535-539`; `solve_terminal.py:39-75`).
   The campaign prompt asks for material questions while the campaign runs
   in autonomous interaction mode (`task_database_campaign.py:299`, `:478`).
3. **A format-repair stall ends the run (high).** `ModelResponseRepairStalled`
   is a `RuntimeError` and escapes the recovery exception handling
   (`adaptive_practitioner_recovery.py:313-314`,
   `model_response_admission.py:145`). Probe `p6` ends `NO_PROGRESS` after
   three calls without engaging the supervision ladder.
4. **Accepted but unfinished runs have no bound (medium to high).** The
   unaccepted-pass counter resets on `accept` and `accept_provisional`
   (`kernel.py:758-763`, `:784-787`). Probe `p3` ran 60 passes and 420 calls
   until an external ceiling stopped it. `SolveRequest` refuses a
   `supervision` argument, so the per-cell supervision level cannot reach a
   campaign trial.
5. **Prompt growth (medium).** Three portfolio blocks take 36 to 37 KB on
   every call, 44.5 percent of all bytes in probe `p2`.
   `previous_project_attempts` grows from 2 to 20,939 bytes and
   `available_file_checkpoints` from 2 to 15,575. The latest-attempt bound
   applies only to a list with a different name (`context_budget.py:257-264`).
   `compacted_policy` has no caller outside its own module's checks.
6. **Pass count inflation (low).** Reported passes include synthetic
   escalation records: 33 reported against 27 real passes.

What holds: refused-verdict loops stop at 9, 18, and 27 passes without
declared ceilings; `selected_references` delivery materializes exactly the
selected inputs; `stop_success` requires an accepted verdict, passing checks,
and an exact evaluation binding.

## The experiment and learning loop

Probes: `.loop-engine-dev/fable-review-probe-20260914/experiment-fabric/`.

| Step | Status at `e089f60` | Evidence |
|---|---|---|
| Catalog, admission, source freeze | Wired and exercised | 1,771 tasks: 1,606 ready, 151 needing metadata, 14 awaiting data. |
| Configuration space | Wired, but narrow | 5 axes and 320 configurations per task. Ten of twelve catalog factors never reach execution. |
| Next-configuration selection | Fixed order | `task_database_campaign.py:743` computes `(round + task_position) % cardinality`. No search, preference, or meta-selection code runs. |
| Dispatch | Wired and exercised | Declared per-cell call and pass limits reach execution. |
| Independent evaluation | Absent | No cell has an evaluator. Every finished cell is recorded as requiring independent task-specific review, and nothing can mark it accepted. |
| Evidence and reporting | Records only | Links re-verify, but the represented, proposed, dispatched, evaluated, accepted, and promoted counts do not exist. |
| Learning | Absent in campaigns | Each cell has its own `runs_dir`. |
| Promotion | Implemented, not wired | Only the manual command-line path uses the learning journal. |
| Later reuse | Absent | The journal is written to `~/.loop-engine/memory/` and read from `<runs_dir>/learning/`. |

Campaign runner defects:

1. **A restart after a provider wait drops the waited cell (high).** The
   attempt counter resets, the occurrence directory already exists, and the
   cell is recorded as failed with `FileExistsError`. Every allowance reset
   and relaunch loses cells silently.
2. **An interrupted trial blocks its campaign (high).** The interruption
   marker is never cleared, and the `reconcile` command only adds another
   record. The live pro campaign root is in this state now.
3. **Selection never uses measurements (high).** Search proposals are
   compatible with the campaign space, but the worker has no selection input.
4. **No evaluator can be bound (high).** The campaign evidence and report
   functions accept only a root path, so no cell can become a search
   observation.
5. **Per-cell history isolation (medium to high).** This is the same
   structural defect found in the September 7 review.
6. **Journal path mismatch and missing staging (medium).** Self-improvement
   candidates stay in memory, and the Constitution's enforcement test for
   self-approval does not exist.
7. **The report cannot show the loop's counts (medium).**
8. **The executed space omits most declared dimensions (medium).**
9. **An allowance refusal followed by a failed re-probe exits instead of
   suspending (low to medium).** The live flash root is in this state.

## The task population beyond the thirteen attempted tasks

Excluding one task whose dataset was deleted, 1,605 tasks are admitted.
Every data link and attachment is intact.

| Kind | Tasks | Attempted | Data the engine can use today | Independent evaluation |
|---|---:|---:|---|---|
| OpenML benchmarks: 911 classification, 529 regression | 1,440 | 0 | Yes. ARFF text; all but five under 1 GB; 70.6 GB in total. | Feasible generically: each task declares its target, metric, and official split file. In all 31 sampled tasks, the delivered dataset contains the labels of held-out rows. |
| Kaggle competitions: 72 tabular or text, 17 image, audio, or video, 22 unclear | 111 | 0 | No for the 105 tasks whose data exists only as ZIP archives, and no for media. Five tasks are 10 GB or larger. | No task has local test labels. A holdout must be carved from training data. |
| Synthetic tickets and exercises | 54 | 13 | Yes, when delivered as references. | 27 have acceptance criteria; none has a rubric evaluator. |

97 percent of the admitted tasks are machine learning. The other eighteen job
families have two to eight tasks each.

Intake facts confirmed in the committed code:

- A file is admitted only if it decodes as UTF-8 text
  (`adaptive_practitioner_source.py:332-354`). A probe confirmed that a ZIP
  archive and a PNG image are excluded as `binary_or_unsupported_encoding`,
  while CSV and ARFF text are admitted.
- Only admitted files can be selected and copied into the sandbox
  (`adaptive_practitioner_project.py:354`).
- The sandbox side already accepts bytes
  (`GeneratedProjectInputArtifact.content` in `generated_project.py:540-557`).
- No archive capability exists. The Practitioner's capabilities are
  `core.environment.describe`, `core.generated_project`,
  `core.intelligence.search`, `core.source.inspect`, `core.source.profile`,
  `core.verifier.execute`, `core.verify.differential`, `core.web.get`,
  `core.web.search`, and `core.workspace.read`.
- A request for an excluded file returns "unknown paths" with an empty list of
  exclusions, so the model is never told the file is binary
  (`adaptive_practitioner_source.py:441-452`). A probe with a folder holding a
  ZIP archive, a spreadsheet, a PNG image, and a CSV file reproduced this.
- External harness processes receive only the task text in a fresh work
  folder. No task file is mounted (`harness_process.py:237-264`).
- Inputs are copied whole into memory. On this machine the ceiling measured
  9.4 GB, half of the available memory.
- The task `bin-ego-360-challenge-classification` is admitted and queued,
  but its frozen snapshot certifies only the 1,320-byte note left after its
  69.75 GiB archive was deleted. Admission trusts the catalog's `ready`
  status and never compares declared archives with the snapshot.

## Codex's uncommitted work

Codex's 55 modified and 6 new files implement the September 14
best-available resolution and action-vector requirements recorded in
[ASTRA.md](../../ASTRA.md). This review probed a snapshot whose `git diff`
digest begins `11b35ca4`, identical to the live tree at 15:40 UTC. Probes:
`.loop-engine-dev/fable-review-probe-20260914/codex-inflight/`.

The work fixes real defects. Tasks delivered as prompt text can reach
project generation, runtime capability questions no longer become questions
for the owner, `solved` still requires `COMPLETED_VERIFIED`, source-limited
tasks stay out of candidate and verified counts, and an adapter cannot grade
its own vector.

1. **Blocker: the tree fails the full self-test and conformance.**
   `practitioner_context_intelligence.yaml` changed from digest `b95c66b4` to
   `18bfe3c2`, but the unmodified `manifest.yaml` (line 20) and
   `ontology/index.json` (line 65) still pin the old digest. Extension
   discovery aborts the self-test after 2,823 seconds. Conformance passes 22
   gates and fails 5: an unclassified module, two modules over the 800-line
   cap, a self-test the suite never runs, semantic identities, and a stale
   architecture map. This review confirmed the digest mismatch on the live
   tree.
2. **High: an accepted, verified result cannot finish while the verifier
   lists any remaining work.** The new route guard rewrites `stop_success` to
   `continue`, and an accept verdict resets the unaccepted-pass counter. A
   probe ran 150 route passes without a stop. Codex's own success fixture with
   one optional remaining item reports `solved: false`.
3. **High: a COMPLETE resolution can be runtime boilerplate.** With zero model
   calls, a run returns `COMPLETED_PARTIAL` with `resolution_status: COMPLETE`
   because `next_action_plan` holds the runtime string "Configure a supported
   model route or install a compatible capability." Provider-unavailable and
   cancelled runs also produce complete packages, and the campaign page counts
   both. This review re-ran both probes with identical results.
4. **Medium: nine failure classes collapse into `COMPLETED_PARTIAL`,** and the
   campaign page shows no underlying failure code.
5. **Medium: vector axes are the verifier model's self-report,** and stage
   grades come from control flow, so correct stages can be recorded as having
   hurt.
6. **Medium: one unknown process check blocks acceptance,** treating unknown
   as false.
7. **Medium: the outcome-vector policy has no field on any request,** so it
   cannot become a campaign dimension.
8. **Low: harness paths receive the policy as data.** Enforcement stays in the
   owning Loop, which suffices for one-step recipes but not for native
   multi-turn loops.

### Reconciled onto main

The owner then asked for all committed and uncommitted work on one working
branch. Codex's exact uncommitted tree is preserved at
`refs/backup/codex-inflight-20260914` and committed unchanged as `96fba39`.
The fix commit `aca062f` makes it pass every gate and resolves findings 1 to
3:

- An accepted, deterministically verified result publishes and stops by
  default. `OutcomeVectorPolicy` 1.1.0 adds `after_acceptance`, with
  `continue_while_work_remains` kept as an explicit level. A failed output or
  a misaligned process still repairs or reframes.
- A resolution package is `COMPLETE` only when substantive work completed a
  method. Interruptions report `OPERATIONAL_INTERRUPTION`, and
  `COMPLETED_PARTIAL` names only a complete package. Three negative controls
  cover runtime guidance alone, a restated task, and a provider interruption.
- The gate repairs are the portfolio manifest digest and version, the
  regenerated ontology index, architecture map, semantic projection, and
  dictionary page, the packaged contract copies, module registration, three
  declared size exceptions, and eighteen hardcoding findings fixed at their
  owners.

The campaign page now shows each cell's underlying failure code, which
addresses the reporting half of finding 4. Findings 5 to 8 remain open.
The commit message of the documentation commit that adds this report
records the verification counts for the final tree.

Two items were deliberately not merged. The August showcase-v4 stash, pinned at
`refs/backup/stash-showcase-v4-20260825`, predates the architecture rewrite
and touches 243 files. The six snapshot worktrees under `.loop-engine-dev`
are evidence for the live campaigns; their never-committed edits are earlier
drafts of work already on `main`.

### Fixed after reconciliation

The full offline self-test on the reconciled tree then passed 4757 of 4768
checks. All eleven failures came from the recursive spawn fixture. Its
scripted verification answer assessed one criterion, while each verify step
must now assess every criterion it registers. The fix commit `aca062f`
corrects the fixture and keeps the stricter contract. Product solve
acceptance, which the self-test does not run, failed for the same reason: its
scripted verifier answers carried no action vector. A later commit binds those
answers to the criteria registered in the actual verify prompt.

Commit `89553f2` then fixes three root causes from the table above:

- A refused generated project keeps its reason. `construct()` preserves a
  typed refusal with its location instead of reporting `invalid_value`.
- A request for a source that was not admitted names each matching
  exclusion and its reason. Basenames, absolute paths, and paths inside an
  excluded directory match.
- An independent verifier case may declare `json_subset` and a finite
  numeric tolerance, as well as exact JSON and exact text. The oracle review
  is asked to refuse a policy looser than the task justifies.

The other root causes keep the status recorded above.

## The owner's direction and the proof ladder

The owner's September 2 steering prompt,
[AGI LoopNode Network](../prompts/AGI-LOOPNODE-NETWORK-SELF-ORIENTING-FOOD-FOR-THOUGHT.md),
asks a system to orient on its own records before adding anything, warns
that "a missing operator looks exactly like bad reasoning" and that two
correct boundaries can leave a hole between them, and orders a proof campaign
from P0 to P26 by information value. The September 14 campaign failed in
exactly those ways: the intake deadlock and the text-only admission are
holes between correct boundaries, and the transcripts read like a model that
cannot think when it could not act.

| Proof steps | Status on current evidence |
|---|---|
| P0 to P3: orientation and single decisions | Demonstrated live. |
| P4 to P6: operator selection, batched versus split calls | An uncontrolled comparison exists: one-call compact trials produced executable candidates while the reference path spent 18 to 168 calls on AE-001. |
| P7 to P10: tool action, code action, format failure, action diagnosis | Mechanically present; diagnosis loops on masked refusals and the intake deadlock. |
| P11 and P12: backtracking and new graph versions | Soft reset and cold restart occurred without changing outcomes; graph versions not evidenced. |
| P13 and P14: baseline plus challenger, asynchronous challenger | Not run live. |
| P15 and P16: context overflow prevention and ablation | Failed live: the context window was exceeded from pass 65. No ablation run. |
| P17: provider failure and resume | Failed: restarts after a provider wait drop cells. |
| P18 and P19: model variation and step-profile comparison | Not matched; one profile is fixed. |
| P20 to P23: micro data analysis, machine learning, ticket repair, research | Attempted; failed through control defects. |
| P24: resume and replay | Failed: an interrupted trial blocks its campaign. |
| P25: cross-run learning candidate | One coarse hypothesis, nothing promoted, and the journal paths do not meet. |
| P26: five families with independent rubrics, side by side | Not done: no evaluator is bound. |

The research direction since September 12, including billions of
configurations, adaptive search, meta-selectors, wrapper layers, and
recursive improvement through a harness fabric, is sound as a direction. Its
precondition is missing. An optimizer or self-improvement cycle can only be
as good as the signal that grades outcomes, and today that signal both
rejects correct work (exact JSON matching) and accepts self-graded work (the
same model as verifier). Evaluation is the keystone for every later step.

## Recent Codex sessions

Audit probes: `.loop-engine-dev/fable-review-probe-20260914/codex-sessions/`.
Rollouts: `~/.codex/sessions/2026/09/12` to `14`.

From September 12 to now, 85 commits landed: 78 by Claude sessions and 7 by
Codex. Codex added 10,643 lines, mostly source, development tools, and tests.
Its last turn ended at 14:35 UTC on September 14 with no final message,
leaving 67 uncommitted working-tree entries.

Verified claims: the 4,710 source checks and 4,664 clean-wheel checks for
`078fffc`, the 103 laboratory tests, the September 13 check counts, the live
call and token totals, the worker stops and the pro cancellation, and the
diagnosis that 717 of 746 recorded semantic-stage calls went to control or
recovery. Eight of nine cited arXiv papers were opened during the session.

Contradicted or partial claims:

- The commit title of `d806759` says it runs and persists the full campaign;
  the same session recorded `No route to host` and zero completed tasks.
- "Pushed the verified changes through `0737cc5`": the hardcoding gate had
  not been rerun, and `078fffc` added ten new high findings that turned CI red
  until `e089f60`.
- The source freeze of 1,606 tasks includes the task whose archive was
  deleted.

Owner requests not fulfilled: testing all tasks across all dimensions (13
task identities reached, 7 with calls on the flash route); a per-task count of
solutions produced, executed, and verified in the report; a working
Solution Canvas and matrix of solutions; an explanation of the exact changes
and their justification, asked three times on September 14; live
qualification of OpenCode, Codex, and Pi as Practitioner realizations.

Process issues: Codex ran the two task-database archive deletions (227.5
GiB) only after the owner authorized them, but the catalog was not updated;
`task_database/` (276 GB) and `task-campaign-runs/` (6 GB) sit in the
checkout untracked and not ignored; a Claude commit swept in 48 files Codex
had staged three seconds earlier; and Codex asked the owner four questions
after being told not to ask for information it could find itself.

## Repository and governance

- None of the 21 enforcement tests named in the
  [Constitution](../architecture/CONSTITUTION.md) exists in code under that
  name. Twelve of the fifteen invariant identifiers checked have no entry in
  `architecture.yaml`. Some invariants are enforced under other names, for
  example `canonical_runtime_refuses_subclassing` in
  `src/loop_engine/architecture_contract.py` and
  `adversarial_improvement_cannot_self_promote` in
  `src/loop_engine/_conformance_test.py`.
- `git ls-files --others --exclude-standard` now returns 77,975 paths from
  the task database and campaign runs. `tools/make_checkpoint.py` and the
  development orientation audit enumerate that command.
- Six detached snapshot worktrees are registered under `.loop-engine-dev/`.
- Of the last 200 pushes to `main`, 82 passed continuous integration. The
  manual live Ollama job has never been dispatched.
- The machine-wide pandas patch reported on September 8 was neutralized on
  September 9. Its patched body remains as `usercustomize.py.bak`.

## Recommended sequence

Order matters here, because each step makes the next one measurable.

1. **Trustworthy acceptance first.** Bind task-owned evaluators and report
   self-verified and evaluator-verified acceptance separately. For OpenML,
   seal the held-out labels and score predictions with each task's declared
   metric. Replace exact JSON equality in the verifier with declared
   comparison policies, such as field subsets and numeric tolerances.
2. **Remove the control defects that waste most calls.** Preserve refusal
   reasons, add terminal precedence so interruptions and questions are named
   correctly, route format-repair stalls to the supervision ladder, and return
   spawned outputs to their owners by digest.
3. **Self-resolving intake.** Name every exclusion, admit binary files for
   sandboxed code, and mount large inputs read-only, as set out in the
   [intake research](../research/SELF-RESOLVING-INTAKE-SANDBOXES-AND-SHARING-2026-09-14.md).
4. **Close the experiment loop.** Fix restart and interruption handling in the
   campaign runner, bind evaluators into the campaign evidence functions, add a
   history-sharing axis, use one learning journal root, and let a selection
   policy choose cells from measured results.
5. **Keep prompts bounded.** Deduplicate failure history by fingerprint, keep a
   stable static prefix, and apply the latest-attempt bound to every growing
   list.
6. **Prove it small.** Replay the five failed live cells offline as regression
   cases, then run one task from each of at least five job families with
   independent evaluators before scaling toward the full grid.
