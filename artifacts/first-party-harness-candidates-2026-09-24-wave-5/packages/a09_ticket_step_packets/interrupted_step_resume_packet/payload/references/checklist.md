# Interrupted step resume: checklist

## Before work

- [ ] No marker in double braces is left in the step files or in `input.json`.
- [ ] The drift check ran first, and you know its verdict.

## Before handoff

- [ ] After `drift` or `not_resumable`, nothing outside `.baltor/resume-output/` changed.
- [ ] After `match`, the first thing you did was the printed `first_action`.
- [ ] You ran only commands that the interrupted instructions show.
- [ ] You changed no file in `.baltor/resume/` or `.baltor/step/`, and undid none of the changed files the handoff lists.
- [ ] Every output the interrupted instructions require exists, or the stop reason is written.
- [ ] `.baltor/resume-output/record.json` matches its schema and lists every path you wrote.
