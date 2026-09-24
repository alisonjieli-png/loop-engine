# Submission assembly step packet

This is a step template. The host fills every value in double braces before the step starts. If a double-brace marker is left, stop and report `unrendered_step_input`.

## Assignment

Build the submission file for the run `{{RUN_ID}}` from the test predictions recorded for it in the experiment ledger `{{LEDGER_PATH}}`. The file must match the sample submission `{{SAMPLE_SUBMISSION_PATH}}`: the same header, the same ids and the same row order. Write it and a provenance record into `{{OUTPUT_DIR}}`. Do not choose another run and do not upload anything. Uploading is a separate decision for a person.

## First action

Check every input without writing anything:

```bash
python3 -I -B .baltor/step/scripts/assemble_submission.py --sample {{SAMPLE_SUBMISSION_PATH}} --ledger {{LEDGER_PATH}} --run-id {{RUN_ID}} --id-column {{ID_COLUMN}} --value-type {{VALUE_TYPE}} --out-dir {{OUTPUT_DIR}} --check-only
```

## Steps

1. Continue only when the printed `status` is `ready`. Note its `run_flags`.
2. Run the same command again without `--check-only`. It prints the provenance record.
3. Confirm that every value under `checks` is `true` and that `upload` is `not_uploaded`.
4. Report the submission path and its SHA-256 digest, the run id, the cross-validation mean score and every run flag. Put run flags first; `suspiciously_perfect` means the run may use leaked information.
5. State that the file was not uploaded and that uploading needs a person's decision.

## Done when

`{{OUTPUT_DIR}}/{{RUN_ID}}.submission.csv` and `{{OUTPUT_DIR}}/{{RUN_ID}}.submission_record.json` exist, and every check in the record is `true`.

## Stop and report when

- A command exits 2 (refused input). Give its JSON unchanged as your report. Common causes: a run id that is not in the ledger, predictions or test data that changed after the run was recorded, ids that differ from the sample, or probabilities outside 0 to 1.
- A command exits 1. The built file failed its self-check; report the checks.
- The work seems to need picking a better run or uploading. Both are outside this step.

## Files

- `.baltor/step/node_context.md`: objective, value types and acceptance.
- `.baltor/step/checklist.md`: checks before and after the work.
- `.baltor/step/contracts/output.schema.json`: the shape of the provenance record.
- `.baltor/step/examples/output.json`: a record for a small synthetic run.

## Authority

This file grants no authority. The host must grant reading the ledger, the recorded prediction and test files and `{{SAMPLE_SUBMISSION_PATH}}`, creating new files only inside `{{OUTPUT_DIR}}`, and starting `python3` for `.baltor/step/scripts/assemble_submission.py`. The step needs no network, no competition command line tool and no other command.
