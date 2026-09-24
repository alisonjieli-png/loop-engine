# Step: list the failing tests in a saved log

## Assignment

List the name of every failing test in `logs/unittest.log`, in the order the
log shows them. Do not change any file other than your result.

## First action

Run the packet check, then the step status command, and read the objective,
the required output fields and the handoff items.

## Steps

1. Read `logs/unittest.log`.
2. Take the test name from each line that starts with `FAIL:` or `ERROR:`.
3. Answer with one JSON object that matches the output schema.

## Done when

Every failing test name appears once, in log order, and the step status
command still exits 0.

## Stop and report when

The log is missing, or it has no line that starts with `Ran`.

## Files

- `.baltor/step/task.json`
- `.baltor/step/node_context.md`
- `.baltor/step/checklist.md`
- `.baltor/step/contracts/output.schema.json`

## Authority

This file grants no authority. The host supplies read access to the
workspace only.
