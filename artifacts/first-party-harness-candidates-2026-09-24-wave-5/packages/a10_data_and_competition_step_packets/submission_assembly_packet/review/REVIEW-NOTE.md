# Review note: submission assembly step packet

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a10_data_and_competition_step_packets, model family anthropic, September 23, 2026, against the pinned revision `a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`. This note is never delivered to a customer's harness.

## Method

One focused step: build the submission file for a run chosen before the step. `assemble_submission.py` finds the run's single line in the experiment ledger and confirms that the recorded test predictions and the test data still have the digests written there. It confirms that the prediction ids equal the sample submission ids, and checks values by type: probabilities between 0 and 1, finite real numbers, or labels at a 0.5 threshold. It then writes the predictions in the sample's exact header and row order. A self-check re-reads the built bytes before anything is written. A provenance record names the run, the ledger line and its digest, the cross-validation score, the run flags and every file digest, and states `"upload": "not_uploaded"`. The model runs a check-only pass, the full run, and reports; it never picks a run and never uploads.

## Authoring basis and sources

Original text and code written for this wave under the MIT licence. The package follows `src/loop_engine/core/service_runtime/catalogue_packages.py`, and `contracts/task.json` holds exactly the `node_assignment/v3` fields of `src/loop_engine/core/node_provisioning.py`. `examples/25_host_runtime/competition_prediction.py` is a related practice in the repository: its formatter checks identifiers, template order, finite values and probability shape and does not submit. This packet is a standard-library step that starts from a ledger record instead of refitting a frozen selection in a container; no code or text was copied.

## Inputs and outputs

Input: the rendered values in `contracts/input.schema.json` (sample path, ledger path, run id, id column, value type, output folder), whose patterns keep values safe inside the shell command. The ledger line must be an `experiment_record/v1` with `outputs.test_predictions` and `data.test` paths and digests, as the wave 5 `baseline_training_packet` writes them. Output: `RUN_ID.submission.csv` and `RUN_ID.submission_record.json` following `contracts/output.schema.json`.

## Effects

`reads_fs` for the ledger, the prediction file, the test data and the sample. `writes_fs` for two new files; existing files are refused. `spawns_process` because the model starts `python3` for the script. There is no network use, no competition command line tool, no upload, no model call from code and no secret. `contracts/task.json` lists only `reads_fs` and `writes_fs` because the delivered-file vocabulary rule refuses the word in the name `spawns_process`; the host adds that effect.

## Closest existing items

The scout found no existing item for this step. The wave 5 verifier `validate_submission_file` (a15) independently checks any submission file against a sample; this packet builds the file and ties it to a run, and its own self-check does not replace that independent verifier. The a02 `rank_experiments_by_fold_scores` and a06 `pick_next_experiment` packages help choose runs; this step only takes the run id it is given.

## Positive example

With the synthetic sample, test data, predictions and two-line ledger in the tests, the run `baseline-ridge-01` produces a four-row file whose rows follow the sample order (T003, T001, T002, T004) rather than the prediction file order, and a record equal to `examples/output.json` with every check true.

## Known-wrong example

Someone reruns a model after the run was logged, overwrites the prediction file, and submits it under the old run's score. The digest check refuses predictions that changed after the run was recorded, and a changed test file is refused too. Other tested refusals: an unknown run id, a run id that appears twice, prediction ids that differ from the sample, a probability of 1.2, a sample with two prediction columns, an existing output, and a self-check that sees rows out of sample order.

In the second pass a probe showed that the first script decoded the ledger with replacement characters, so a damaged ledger passed and the recorded `line_sha256` was computed from the repaired text instead of the line's bytes. The script now refuses a ledger line that is not UTF-8 and hashes the exact line bytes; for a valid ledger the digest is unchanged, so `examples/output.json` did not move. The test `test_ledger_that_is_not_utf8_is_refused` was written first and failed on the old script; it passes now, and restoring the lenient decoding makes it fail again (mutant check in the log).

The third pass, on September 24, 2026, found that Python's `float()` also reads number text such as `1_0` or `0.8_1` and digits of other scripts. The old script copied such text into the submission as written, and its own self-check passed it, although a competition platform may refuse the file. The script now accepts only plain ASCII decimal notation such as `0.25` or `1e-06`, both when it converts a value and when it re-reads the built file. The test `test_number_text_that_is_not_plain_decimal_is_refused` was written first and failed on the old script; it passes now, and removing either of the two guards makes it fail again (mutant check in the log). `examples/output.json` did not change.

## Harness placement and verification state

`AGENTS.md` is composed into the step root for Codex, OpenCode and Pi (observed in recorded probes) and Kimi CLI (unverified). `CLAUDE.md` holds `@AGENTS.md` for Claude Code (file observed, import documented). `GEMINI.md` is a byte copy for Gemini CLI (documented). Step files go to `.baltor/step/`, the licence to `.baltor/submission-assembly-packet/LICENSE`, and the test file is deliberately not placed. No harness binary was run, so native loading is unobserved. The command starts `python3 -I -B`; the host must bind a trusted interpreter.

A producer-side host walkthrough placed the packet by each of the six placement maps and ran the rendered check-only command, then the same command without `--check-only`, against the ledger line and test prediction file that the wave 5 `baseline_training_packet` had just written, with a 12-row sample submission in reversed id order. Every check was true, `upload` stayed `not_uploaded`, the rows followed the sample order and the values equalled the recorded predictions. It is a script-level probe, not a native harness run and not a model run. The third pass repeated it on the final bytes, including the new plain-number check, with the same result.

## Customer requests

- "Make the submission file from run baseline-ridge-01 and make sure it matches the sample."
- "Which run and which data produced the file we are about to submit?"
- "Prepare the submission, but do not upload it; I will do that myself."

## Limits

- One id column and one prediction column only; multi-column and multiclass probability submissions are out of scope.
- Class labels other than 0 and 1 are not produced; `binary_label` uses a fixed 0.5 threshold.
- Probabilities and real numbers are copied as written in the prediction file, and only plain ASCII decimal notation is accepted.
- The digest checks prove that files did not change after the run was recorded, not that the run was a good choice.
- The value type names differ from the brief packet: its `class_label` corresponds to `binary_label` here for 0 and 1 targets; a host that chains the two maps the name.
- Check history: the first pass left one passing report and no failing report. The second pass, on September 23, 2026, logged its runs in `packages/submission_assembly_packet/PRECHECKS.txt` beside the assignment folder (the layout check refuses extra entries in the package folder), including the failing known-wrong test, a failed first mutant attempt and its successor. It changed the payload after its last checker run and ended before `fill` and `check` ran again, so its newest report described older bytes. The third pass, on September 24, 2026, saved a snapshot of the earlier state beside the assignment folder, added the test and repair above, stated the plain-number rule in `references/node_context.md`, and ran `fill`, `check` and `check-all` on the final bytes; its runs are appended to the same log. Each check also saved a `precheck-*.json` report beside this note, and `review/PRECHECKS.txt` keeps the first pass's log.
- The cited sources are unchanged between the pinned revision and `origin/main` at `e8069610` (checked on September 24, 2026).
