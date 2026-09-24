# Ticket reproduction step packet

This example stands for the host's own rendered copy of the interrupted step's instructions for ticket T-104. It is shorter than a real copy.

## First action

Read `.baltor/step/input.json`, then the ticket file at its `ticket_path`.

## Steps

1. Add one test named exactly `test_name` to `test_file`.
2. Run tests only through the recorder, so every run is saved:

```bash
python3 -I -B .baltor/ticket-reproduction-packet/scripts/record_reproduction_run.py --input .baltor/step/input.json
```

3. Write `.baltor/step-output/output.json` and list every evidence file.

## Done when

`output.json` matches its schema with status `reproduced`, `not_reproduced` or `blocked`.
