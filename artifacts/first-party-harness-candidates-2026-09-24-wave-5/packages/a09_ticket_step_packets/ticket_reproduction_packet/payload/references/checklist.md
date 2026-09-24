# Ticket reproduction: checklist

## Before work

- [ ] No marker in double braces is left in the step files or in `input.json`.
- [ ] You know `test_file`, `test_name`, `test_path_prefixes` and `host_placed_paths` from `input.json`.
- [ ] You will change `test_file` and write in `.baltor/step-output/`, and nothing else.

## Before handoff

- [ ] The new test has exactly the name `test_name` and asserts one behavior from the ticket.
- [ ] No product file, no other test file and no file in `.baltor/step/` changed.
- [ ] The newest evidence file was written by the recorder, not by hand.
- [ ] The quoted failure line appears word for word in that file's `output_tail`.
- [ ] `.baltor/step-output/output.json` matches the output schema and lists every evidence file.
