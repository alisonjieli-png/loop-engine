# Ticket reproduction step packet

This file is a step template for ticket {{TICKET_ID}}. The host fills every marker in double braces before launch. If one is still there, stop and report `unrendered_step_input`.

## Assignment

Turn the behavior reported in ticket {{TICKET_ID}} into one new test that fails on the current code, and record the failure with the recorder. Change no product code. Triage step `{{TRIAGE_STEP_ID}}` chose the test file and the test name; both are in `.baltor/step/input.json`.

## First action

Read `.baltor/step/input.json`, then the ticket file at its `ticket_path`.

## Steps

1. Read the code under test and the existing tests in `test_file`. Follow their style.
2. Add one test named exactly `test_name` to `test_file`. It asserts the behavior the ticket expects. Change no other file.
3. Run tests only through the recorder, so every run is saved:

```bash
python3 -I -B .baltor/ticket-reproduction-packet/scripts/record_reproduction_run.py --input .baltor/step/input.json
```

4. Act on the `verdict` it prints:
   - `nonzero_exit_recorded`: in the evidence file's `output_tail`, find the line that shows the wrong behavior. An import, name, syntax or collection error, or a missing fixture, means your test is broken: repair it and run the recorder again.
   - `test_passed`: the code already does what the ticket expects. Write status `not_reproduced`. Do not force a failure.
   - `product_code_changed` or `other_test_files_changed`: change back by hand each listed file that you changed, then run the recorder again. Never revert a file you did not change; write status `blocked` and name it.
   - `test_file_missing`, `test_name_not_in_file` or `test_file_unchanged`: fix your test and run the recorder again.
   - `timed_out` or `command_not_started`: write status `blocked` and quote the problem.
5. Write `.baltor/step-output/output.json` in the shape of `.baltor/step/contracts/output.schema.json`, listing every evidence file.

## Done when

`output.json` matches its schema with status `reproduced` and a failure line quoted from the newest evidence file, `not_reproduced` with the evidence of the passing run, or `blocked` with the reason.

## Stop and report when

- The recorder exits with code 2. Write status `blocked` and copy its reason.
- The test could fail only after a change to product code. Write status `blocked`; that change belongs to the fix step.
- The same import, name, syntax or collection error returns after you wrote the test a different way. Write status `blocked` and quote the error.

## Files

- `.baltor/step/`: the host's files: `input.json`, `node_context.md`, `checklist.md`, the contracts and a made-up example in `examples/`. Read them; never edit them.
- `.baltor/step-output/`: your `output.json`, and one recorder evidence file per run in `evidence/`. Keep them all.

## Authority

This file grants no authority. The host must supply read access to the repository, write access only to `test_file` and `.baltor/step-output/`, and permission to run the recorder, which runs git and the host's test command. Install nothing, make no network request, and do not stage, commit or reset anything.
