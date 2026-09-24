# Ticket fix verification: checklist

## Before work

- [ ] No marker in double braces is left in the step files or in `input.json`.
- [ ] `input.json` names the base revision, both test commands and the reproduction test digest.

## Before handoff

- [ ] You read the evidence file and the diff file of the newest checks run.
- [ ] The summary names every path in `changed_paths` and every failed check.
- [ ] You looked for deleted, skipped or loosened tests and for secret values in the diff and in `new_paths`.
- [ ] For `ready_for_review`, the message check printed `"passed": true`.
- [ ] You changed no code, no test and no file in `.baltor/step/`, and ran no other command.
- [ ] `output.json` matches the output schema, `committed` is false, and `blocker` is set only for `blocked`.
