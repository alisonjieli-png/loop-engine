# Step context

## Objective

List the failing test names from one saved unittest log.

## Relevant context

The log was written by `python3 -m unittest -v`. A failing test has a line
that starts with `FAIL:` or `ERROR:`, followed by the test name.

## Current state

An earlier step saved the log at `logs/unittest.log`. No result exists yet.

## Contracts and input

The answer matches `contracts/output.schema.json`: one object with the list
`failing_tests`.

## Acceptance

Every failing name appears once, in log order, and no passing test is listed.
