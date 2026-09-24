---
name: write-step-result
description: "Save the result of the current focused step as a new numbered JSON file that is never overwritten, after a check of the required fields and top-level types in the packet's output schema. Use it when the result is ready, or later to publish a better result, through the step packet tools or the local script."
license: MIT
compatibility: "Python 3.10 or later, standard library only, for the script. Writes only below .baltor/state/portable-step-packet-plugin/results/."
metadata:
  version: "0.1.0"
---

# Write the step result

## When to use it

Use it when the result of the current step is ready. You may write again
later with a better result: each write gets the next number, and every
earlier file stays, so a reader can name the exact result it used.

## First action

Build the result as one JSON object with every field in
`output.required_fields` from the assignment card. Call the tool
`write_step_result` with the argument `result` set to that object. Without
the tool, send the object on standard input to the script in this skill's
`scripts/` folder, from the workspace root:

```bash
python3 -I -B .baltor/plugins/portable-step-packet-plugin/skills/write-step-result/scripts/write_result.py <<'RESULT'
{"version": "2.4.1", "release_date": "2026-09-18", "change_count": 3}
RESULT
```

## Steps

1. Use only field names that the output schema names.
2. Write the result with the tool or the script.
3. If `written` is false, read `problems`. Each one names a field. Fix that
   field and write again.
4. When `written` is true, keep `path`, `sequence` and `sha256`.
5. In your final message, name that `path` and `sha256`.

## Checks

- Every required field is present, and no other field when the schema
  forbids extra fields.
- Each top-level value has the JSON type its field names.
- No value looks like a key or a token; such a result is refused.

## Done when

The answer holds `"written": true`, and your final message names the result
`path` and its `sha256`.

## Stop and report when

- The same problem comes back after you fixed that field twice.
- The answer is an error such as `task_missing` or `step_folder_missing`, or
  the problem is `too_many_results`.
- The result needs a field the schema does not have. Report it; never add
  the field to pass.

## Known-wrong example

The result `{"release": "2.4.1"}` for the example step lacks the three
required fields and adds one unknown field. Nothing is written, and the
answer lists `missing_required_field: version`, the same for `release_date`
and `change_count`, and `unknown_field: release`.
