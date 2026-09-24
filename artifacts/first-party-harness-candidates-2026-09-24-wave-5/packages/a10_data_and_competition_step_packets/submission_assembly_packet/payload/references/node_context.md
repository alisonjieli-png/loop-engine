# Submission assembly step packet: context

## Objective

Produce one submission file that matches the sample submission exactly, built from a named recorded run, with a record that ties the file to that run and its data.

## Relevant context

- The run was chosen before this step, for example by comparing ledger records. This step never picks a run.
- A submission can be trusted only through its link to the run, so the script refuses predictions or test data whose digests differ from the ledger line.
- Competition platforms usually reject a file whose header, ids or row count differ from the sample, so the file copies the sample's header and id order.

## Current state

The ledger holds a line for the run id, with the path and digest of its test predictions and of its test data. No submission for this run exists in the output folder.

## Contracts and input

- The rendered input values follow `.baltor/step/contracts/input.schema.json`.
- The ledger line is an `experiment_record/v1` with `outputs.test_predictions` and `data.test`, each with a path and a SHA-256 digest. The prediction file has the header: the id column, then `prediction`.
- `value_type`: `probability` keeps values from 0 to 1 as written, `real_number` keeps any finite number as written, and `binary_label` writes 1 for a value of 0.5 or more and 0 otherwise. Every prediction must be a plain decimal number such as `0.25` or `1e-06`; other spellings are refused.
- The sample submission has exactly two columns: the id column and one prediction column.

## Acceptance

- The record follows `.baltor/step/contracts/output.schema.json`, and every check in it is true.
- The report names the run id, the digests, the cross-validation score and every run flag.
- Nothing was uploaded.
