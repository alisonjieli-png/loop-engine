# Verify the requested output, not the successful return

A command that ends without an error has not proved anything about its result. Check the artifact itself against the acceptance criteria of the original task.

## When to use it

Use it before reporting that a task is complete, and after every action whose result will be used by another step or another person.

## Steps

1. State the rejection test first: what would a result have to show to be rejected as wrong or incomplete?
2. Ask whether the operation produced the requested output or merely returned successfully.
3. Ask whether the result is the requested artifact or only an intermediate state.
4. Compare the artifact with the required output format exactly: columns, schema, file layout and interface signature. List every deviation.
5. Check whether deterministic tests, source evidence and artifact checks support the result.
6. Mark each acceptance criterion as satisfied, unsatisfied or unknown.
7. Map every blocking gap to one acceptance criterion from the preserved task. Optional improvements and newly proposed requirements stay advisory. They do not silently redefine completion.
8. Do not let the producer of the work be its own final verifier. Keep the confidence of the producer separate from independent evidence. A review that could not run is not a pass.
9. When full acceptance is not possible, keep the best candidate, the completed analysis, the missing pieces and the limits. Do not claim acceptance.

## Checks

- Every acceptance criterion has a state and an observation behind it.
- The checked subject is the exact artifact that will be delivered.
- Completion is not reported until the requested artifact or state change exists and is verified.

## Known-wrong example

A script ends with exit status 0 and prints that it is done. The output file exists and is empty, because a filter removed every row. A second case: the file has the right rows, and one column is named `customer id` where the required name is `customer_id`. The next system rejects the file. Both cases pass a check of the return status and fail a check of the artifact.

## What to record

- Each acceptance criterion with its state and its evidence.
- Every deviation from the required format.
- Who verified, and whether that was independent of the producer.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the questions of the verify step, and the guidance records about artifact completion, independent verification and the scope of verification.
- `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml`: the work function for verifying, falsifying and critiquing.
- `src/loop_engine/strings/question_engine.py`: the question forms named `format_conformance` and `acceptance_inversion`.

Licence: MIT. Compiled from revision eb757bc.
