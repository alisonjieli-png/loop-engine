# Write a step handoff note

## Purpose
Use this at the end of a focused step, finished or not. The next harness starts fresh and knows only this note, so every finished result needs a file this step wrote or changed.

## First action
Run this command and read the note path it prints:

```bash
python3 -I -B .baltor/write-step-handoff/scripts/step_handoff.py init --root .
```

It takes the step id from `.baltor/step/task.json`. Only if it refuses with "no step id" and you have a step id, run it once more with `--step-id` and that id. A step id can come only from the message that ran this command.

## Steps
1. Open the note. Replace every line that contains `(fill in` with real content. Keep the six headings. Add no other heading and no code block.
2. Status: `complete`, `partial` or `blocked`.
3. Done: one line per finished result, with the path of a file this step wrote or changed in backticks, such as a saved test log. A folder or a file under `.baltor/step/` does not count.
4. Remaining: one line per unfinished item, or `none` when the status is complete.
5. Open questions: one line per question and who can answer it, or `none`.
6. First action for the next harness: one line with exactly one command or one file path in backticks.
7. Check the note. If you added `--step-id` in the first action, add it here too:

```bash
python3 -I -B .baltor/write-step-handoff/scripts/step_handoff.py check --root .
```

8. Fix each line in `findings`, then run the check again. `.baltor/write-step-handoff/examples/handoff-example.md` shows a note that passes.

## Output
The note under `.baltor/handoffs/` and, once the check passes, its record at `record_path` beside it. Reply with the note path, the record path and the status. The step is done when the check exits 0.

## Stop and report when
- A helper run exits with status 2, apart from the one repeat with `--step-id` above. Report its `reason`.
- No file proves a result. Move that result to Remaining instead of claiming it.
- The same finding stays after you changed the note twice. Report the finding and the note path.
