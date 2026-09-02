# Live Kaggle diagnostic, 2026-09-02: why a real run produced nothing

This is the current state of the tree. It supersedes the status lines in
`CODE-REVIEW-2026-09-02.md` and `EVERYTHING-IS-A-LOOP-AUDIT-2026-09-01.md`,
which remain unedited as point-in-time records.

The occasion was a live Kaggle run, `adaptive-29ce1f81218cf8d814eb0c62`, on
Playground Series S6E9 through the Tactical Engineering route. It ended
`BLOCKED_MATERIAL_INPUT` after 226 model calls, 32 passes, 1599 loops and
2268 seconds, with no submission. Reading its raw `solve_progress` stream
against the code found five defects, four of them invisible to every gate in
this repository.

## 1. What actually failed

| # | Defect | How it showed in the run |
|---|---|---|
| 1 | Two path spaces for one file | Runtime facts stated the bare admitted path and called it the only admitted path; `core.generated_project` materialized the same file under an `inputs/` prefix. The model used what the runtime told it, and the input-use check refused it. |
| 2 | Refusals carried no reason | `as_practitioner_loop` wraps a failing deterministic check, and the untyped fallback described the wrapper. The model read "deterministic check validate generated project input use raised inside loop 1470 (evidence on the ledger)" about twenty times while the sentence naming the wrong path sat two links down `__cause__`. |
| 3 | The action fence was blind | Three `core.generated_project` refusal paths returned a result packet without calling `note_failure`, so the model-visible view read `recent_failures: []`, `refusals_issued: 0` throughout. |
| 4 | Typed outputs counted as produced | The candidate declared `submission.csv`, `metrics.json`, `report.md` and `verification.json` as both authored files and expected artifacts. The model typed them — a standard deviation of exactly zero, a mean equal to the sample submission's constant, a 6009-byte submission that cannot hold 286,571 rows — and the artifact check passed on all four. |
| 5 | A real competition could not be placed at all | The workspace capped every file at a flat 16 MB. The real files are 7.7 MB, 18.3 MB and 44.7 MB, so only the submission template was placed. No model reasoning could have reached a result. |

Defects 1 and 5 are the runtime misdescribing itself. Defect 2 is why the run
could not recover: every recovery path consumed a message with no content in
it. Defect 3 is why the anti-repetition law never fired. Defect 4 is why an
earlier pass reported results it had never computed.

## 2. Why more machinery would not have helped

The run executed the full recovery ladder: `diagnose_stall`, the
`failure_diagnostician`, `strategy_mutator` and `recovery_adjudicator`
personas, twelve diagnostics, then soft reset, reframe and cold restart. The
loop behaved as designed. What it reasoned over was false or empty. More
steps produce more passes of the same wrong conclusion; more templates
template the wrong action. Self-healing is a function of feedback quality, not
of loop count.

## 3. What changed

Three commits on `main`: `9dc646b`, `94522e9`, `17438c4`.

- One rule for where a supplied file is materialized, `project_input_path`,
  called by both the materializer and the facts projection. Runtime facts
  state `sandbox_paths`, `byte_counts` and `placement_capacity` beside the
  admitted paths.
- `rejection_from_exception` reports the deepest cause and names the wrappers
  it travelled through, for every capability. The input-use refusal names the
  literal the code opened, the path it should have been, and the admitted set.
  Refused next-action kinds and ambiguity states now name the rejected value
  and the admitted vocabulary.
- All three generated-project refusal paths record on the fence, keyed by
  manifest digest, so an identical failed project is refused before it costs
  anything while a corrected one stays admissible.
- An expected artifact and an authored file may no longer share a path. The
  repository's own fixtures carried the same shape and were corrected, which
  is why the gap survived every gate.
- `core.source_role_orientation`: one bounded model call states what each
  supplied file is, over the deterministic profile rather than a byte prefix,
  admitted only against the manifest the runtime holds, citing fields the
  runtime actually profiled, saved per manifest digest.
- `core.source.profile` states per field how many distinct values were seen,
  some of them, and whether they all parse as numbers.
- `core.runtime_capacity`: every capacity on the path from task to data to
  model call is measured or derived, never declared, and a self-test refuses
  any capacity-shaped integer reintroduced into those modules.

## 4. What the live evidence shows

Real competition files, pulled with the Kaggle API and byte-identical to the
failing run's log: `train.csv` 44,707,646, `test.csv` 18,298,347,
`sample_submission.csv` 7,737,432.

Provider probes accepted live on both `ollama_cloud` and `tacticalengineering`.

On a solve against those real files through the Tactical route:

- `practitioner.source_roles.stated` fired, and the reading was "a
  `Will_Buy_EV` field which holds categorical labels rather than continuous
  numbers". The failing run had called the same column continuous and chosen a
  regressor with a root mean squared error.
- The project candidate authored `solution.py` and `verification.py` and
  declared `submission.csv`, `metrics.json`, `report.md` and
  `verification.json` as expected artifacts, with no overlap.
- Generated code opened `inputs/.../train.csv`, the sandbox path.
- All three real files materialized; `input_use_validation` passed.
- The command ran and the four expected artifacts were reported
  `present: false`, `verified: false`. Nothing was fabricated.

## 5. What is not proven

- **No green end-to-end submission on real data.** Every wall the failing run
  hit is gone and failures are now reported honestly. That is a different and
  weaker claim than "it solves the competition".
- The local run's command failed with `ModuleNotFoundError: pandas`, which is
  an artifact of this machine: Docker is present here, so the project ran in a
  plain Python image, while Kaggle has no Docker and a preinstalled data stack.
- A Kaggle notebook pushed through the API does not inherit secret access, so
  the kernel run stopped before the solve. See `kaggle/README.md`.
- The remaining physical bound on a supplied input exists only because the
  ingest path reads whole files into memory. Streaming the digest and the
  write would remove the memory constraint entirely. Not done.

## 6. Items from the previous review that no longer stand

- "Tactical Engineering and Mistral routes are live-untested in this
  environment" (item 11): Tactical Engineering is live-tested, including a
  full solve against the real competition data. Mistral remains untested.
- "the Practitioner's verdict trusts the artifacts it produced" (item 9): the
  authoring half is closed, because an artifact the model typed is no longer
  admissible as an expected artifact. An independent evaluator Loop with a
  held-out split is still missing, so the item stands in part.

Everything else in that list stands unchanged.

## 7. Gates

Self-test 1826 of 1826; conformance all gates pass; Kaggle offline harness 3
cells across binary, regression and multiclass; adaptive acceptance checks 26
of 26; hardcoding delta gate with `--fail-on-new high` clean; repository
orientation snapshot regenerated.
