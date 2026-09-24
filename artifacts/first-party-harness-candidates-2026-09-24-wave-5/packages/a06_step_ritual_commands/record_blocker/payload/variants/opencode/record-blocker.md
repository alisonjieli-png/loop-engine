---
description: "Write a blocker record for the current ticket, mark it blocked in the night queue status and name the next ticket."
---

# Record a blocker and move on

## Purpose
Use this when the current ticket cannot go on: a needed file, permission, decision or tool is missing, the same error came back after a changed approach, or the ticket's time is spent. The helper writes the record, marks the ticket blocked in `.baltor/night/queue-status.json` and names the next ticket.

## First action
Run:

```bash
python3 -I -B .baltor/record-blocker/scripts/blocker.py new --root .
```

Only if it refuses because no ticket is named and you have a ticket id, run it once more with `--ticket` and that id, and add the same option to `file`. Ticket id given with this command, if any: $ARGUMENTS

## Steps
1. Open the record path it prints. Replace every line that contains `(fill in` with real content. Keep the six headings and add no other heading.
2. What was tried: one line per attempt and what you changed between attempts.
3. Exact error: paste the exact error lines inside the code block. Do not summarize them. For a long output, save it under `.baltor/night/logs/` and write that path in backticks below the block; pasted lines must appear in that file.
4. Needed: what would let the work go on. From whom: the person, role or step that can provide it.
5. File the record:

```bash
python3 -I -B .baltor/record-blocker/scripts/blocker.py file --root .
```

6. If it lists `findings`, fix the record and run `file` again. `.baltor/record-blocker/examples/blocker-example.md` shows a record that passes.

## Output
The record under `.baltor/night/blockers/`, the ticket `blocked` and the queued tickets that depend on it `waiting`. Reply with the blocked id, the record path, `next` and `continue_with`. If `continue_with` names a ticket, work on that ticket next. If it is null, stop here; `not_started_because` says why. The step is done when `file` exits 0.

## Stop and report when
- A helper run exits with status 2, apart from the one repeat with `--ticket` above. Report its `reason`.
- `file` shows the same finding after two changes to the record.
- You have neither the error text nor a saved log. Report what you tried; never invent an error.
