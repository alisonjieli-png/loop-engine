---
description: "Show the overnight ticket queue position, the next ticket check command, each closed ticket outcome and the last handoff. Read-only."
---

# Night status

## Purpose

Show where the overnight ticket run stands: the next open ticket with its
check command, the outcome of every closed ticket and the last handoff.
This command writes nothing. It is a live read-out, not the morning report.

## First action

Run this command from the workspace root and read its JSON output:

```bash
python3 -I -B .baltor/plugins/overnight-ticket-plugin/scripts/night_status.py
```

## Steps

1. Run the command above.
2. If the exit code is 2, go to "Stop and report when".
3. Read `next_ticket`, `counts`, `last_handoff`, `problems` and `notes`.
4. Report a table with one row per ticket: position, ticket id and outcome,
   where `open` means no result record yet.
5. Under the table, write one line for the next ticket with its `check`
   command and one line for the last handoff.
6. If `problems` is not empty, list each problem code with its path.

## Output

The table and at most five short lines. Copy ticket ids, outcomes, counts
and commands exactly from the JSON. Never give an outcome to a ticket that
has no record.

## Stop and report when

- The exit code is 2: the queue is missing or refused. Report `error` and
  `detail`.
- The exit code is 1: a result record has a problem, for example
  `record_from_another_queue`. Report the problems and start no new ticket.
- `next_ticket` is null: every ticket is closed. Report the status and do no
  more ticket work.
