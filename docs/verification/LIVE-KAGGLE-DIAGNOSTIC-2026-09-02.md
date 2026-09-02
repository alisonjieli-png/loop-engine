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

## 5. Two runs, one verified and one not

The notebook ran twice on 2026-09-02, against the same competition and the
same three files, with different providers. Read them together; either one
alone misdescribes the state.

| | 14:22 run | 15:08 run |
|---|---|---|
| Route | `ollama_cloud` | `tacticalengineering` |
| Model | `deepseek-v4-flash:0731` | `gemma-4-coding-abliterated` |
| Run id | `adaptive-7b7fd04e0e75bc3785e30abb` | `adaptive-c143ca11dc3e0c5625aa7590` |
| Outcome | `COMPLETED_VERIFIED`, `solved: true` | exit 1, no submission |

The engine, the task, and the data were identical. What differed was the
model, and one specific gap in the capability set that only the second run's
failure mode reaches. Section 5.2 is that gap; it is the open item.

### 5.1 The verified run

Kaggle run `adaptive-7b7fd04e0e75bc3785e30abb` reached `COMPLETED_VERIFIED`
in 2729 seconds over 77 model calls, 11 tool calls and 692 loops. The run this
document opens with spent 226 calls and 2268 seconds to reach
`BLOCKED_MATERIAL_INPUT` with nothing.

What the artifacts show, read from the downloaded run rather than from the
terminal code:

- `submission.csv` is 7,894,696 bytes and holds 286,571 rows, matching
  `test_rows` exactly. The failing run's was 6,009 bytes.
- Every one of those 286,571 predictions is distinct, ranging 0.000000 to
  0.969723 with a mean of 0.174871 and a standard deviation of 0.266983. The
  failing run reported a standard deviation of exactly zero.
- `id` runs 668,665 to 955,235, continuing from the 668,665 training rows.
- The task was read as binary classification on `Will_Buy_EV`, scored with
  ROC AUC over three folds. The failing run called the same column continuous
  and chose a regressor with a root mean squared error.
- Two models were fitted and compared on per-fold scores: logistic regression
  at a mean AUC of 0.93810, random forest at 0.93344. The better one was
  selected.
- The source role reading named all three files from their profiles:
  `train.csv` as the labeled training data, `test.csv` as the prediction
  input, `sample_submission.csv` as the output contract. No name was inferred
  from a filename.

The run also repaired itself on a real defect rather than by retrying. The
first attempt produced every artifact and read every source at its sandbox
path, but `verify.py` exited 1 because it could not independently confirm the
input directory had not been written to. The loop diagnosed that specific
check and changed the design: a `snapshot_input.py` step now records the input
tree — paths, sizes, mtimes, and content hashes — before `solution.py` runs,
so `verify.py` can compare against it and prove the read-only guarantee. The
next attempt exited 0 with "Verification passed: all checks succeeded", and
`deterministic_checks_passed` is true.

### 5.2 The run that did not solve it, and why

`adaptive-c143ca11dc3e0c5625aa7590` failed for one reason, and it is a gap in
this repository rather than in the model's reasoning.

`gemma-4-coding-abliterated` wrote `src/pipeline.py` with an unterminated
string literal at line 131. The runtime reported the SyntaxError exactly, and
the model reached the correct conclusion immediately: read the file, find the
bad line, fix it. It then could not read the file.

- `core.source.inspect` refused: "source inspection requested unknown paths
  ['src/pipeline.py']; inspect manifest_paths for the exact admitted paths".
  That capability admits the supplied source manifest, and a generated
  workspace file is not in it.
- `core.generated_project` refused a `cat` command: "generated commands must
  execute reviewed files, not inline code" and "generated commands must use
  the registered Python executable".

Neither refusal is wrong. `core.source.inspect` guards the input boundary and
`core.generated_project` guards the execution boundary, and both should. But
between them there is no admitted way for a run to read back a file it wrote
itself, so a model that must repair its own code has to do it blind.

The record shows the loop working correctly against that wall rather than
failing to notice it. The action fence recorded every refusal with its exact
cause, fenced `core.generated_project` after five failures, and the model
worked out the right workaround by pass 11 — "use `core.generated_project`
with a `cat` command" — which was then refused for a different and also
correct reason. Soft reset fired at pass 16, cold restart at pass 19, and
twenty passes carried the same sentence because the missing observation was
never obtainable. More steps, more perspectives, and more recovery machinery
would each have produced another pass of the same correct conclusion.

The 14:22 run never hit this because its generated code parsed the first
time. The gap was always there; only a syntactically invalid generation
reaches it.

## 6. What is not proven

- **No competition score.** The submission was produced and independently
  verified for schema, row count, column order, identifier coverage and value
  range. It has not been submitted, so nothing here says how it ranks. The
  0.938 is a local three-fold cross-validated figure, not a leaderboard
  result.
- **One run on one competition, on one model.** A single verified solve is not
  a claim about unseen tasks, and the same engine on the same task with a
  different model produced nothing. Section 5.2 names one reason; it is not
  established that it is the only one.
- **The read-back gap is open.** No capability lets a run inspect a file it
  generated. Until that exists, any run whose model emits invalid code has no
  route to repair it.
- The local run's command failed with `ModuleNotFoundError: pandas`, which is
  an artifact of this machine: Docker is present here, so the project ran in a
  plain Python image, while Kaggle has no Docker and a preinstalled data stack.
- A Kaggle notebook pushed through the API does not inherit secret access, so
  the kernel run stopped before the solve. See `kaggle/README.md`.
- The remaining physical bound on a supplied input exists only because the
  ingest path reads whole files into memory. Streaming the digest and the
  write would remove the memory constraint entirely. Not done.

## 7. Items from the previous review that no longer stand

- "No green end-to-end submission on real data" (section 5 of the earlier
  draft of this document): closed by the run above, with the narrower
  limitations now recorded in its place.
- "Tactical Engineering and Mistral routes are live-untested in this
  environment" (item 11): Tactical Engineering is live-tested, including a
  full solve against the real competition data. Mistral remains untested.
- "the Practitioner's verdict trusts the artifacts it produced" (item 9): the
  authoring half is closed, because an artifact the model typed is no longer
  admissible as an expected artifact. An independent evaluator Loop with a
  held-out split is still missing, so the item stands in part.

Everything else in that list stands unchanged.

## 8. Gates

Self-test 1826 of 1826; conformance all gates pass; Kaggle offline harness 3
cells across binary, regression and multiclass; adaptive acceptance checks 26
of 26; hardcoding delta gate with `--fail-on-new high` clean; repository
orientation snapshot regenerated.
