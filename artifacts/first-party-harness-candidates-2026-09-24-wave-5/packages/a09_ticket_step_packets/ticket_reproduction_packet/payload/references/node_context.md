# Ticket reproduction: step background

## Objective

Show the defect in ticket {{TICKET_ID}} with one new automated test that fails today, before anyone tries to fix it.

## Relevant context

- A test that nobody saw failing proves nothing about the defect. The next step makes the fix, and the step after it checks that this same test now passes.
- The recorder saves the digest of the test file. If the fix step edits this test later, the verification step notices.
- The failure must come from the behavior in the ticket. A failure while the test file is loaded or collected only shows that the test is broken.
- The recorder records any run that exits with a non-zero code as `nonzero_exit_recorded`. It cannot tell a real reproduction from a broken test; that judgment is yours, from the output it saves. `output_mentions_test_name` false is a hint that the failure came from somewhere else.
- The recorder runs the test only while `test_file` is the one changed file, apart from the host's files. It also saves the digest of `input.json`; the host compares it with the input it wrote, so an edited input voids the step.
- Notes about this repository from the host: {{REPOSITORY_NOTES}}

## Current state

Triage step `{{TRIAGE_STEP_ID}}` answered go and proposed the test file and the test name. No test has been written for this ticket yet, and no product file has changed. `.baltor/step-output/` is empty.

## Contracts and input

- Input: `.baltor/step/input.json`, described by `.baltor/step/contracts/input.schema.json`. Read it; never edit it.
- Output: `.baltor/step-output/output.json`, one `ticket_reproduction_record/v1` object described by `.baltor/step/contracts/output.schema.json`.
- Evidence: one `ticket_reproduction_run/v1` file per recorder run, in the `evidence_dir` of the input, inside `.baltor/step-output/`.

## Acceptance

- `test_file` is the only changed file, apart from `.baltor/step-output/` and the files the host placed.
- No file in `.baltor/step/` changed, and every evidence file records the digest of the input the host wrote.
- The quoted failure line appears in the cited evidence file and shows the reported behavior.
- A passing test is reported as `not_reproduced`, never bent into a failure.
- Every recorder run is still on disk and listed in `evidence_files`.
