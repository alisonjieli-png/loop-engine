# Cleaning application step packet: context

## Objective

Produce a cleaned copy of one table by applying only the approved rules of a reviewed plan, with a record of every changed cell and every held cell. The source table stays byte for byte the same.

## Relevant context

- A plan comes from the cleaning plan step. A reviewer then sets each proposed rule to `approved` or `rejected` and names themself in `reviewed_by`. Rules marked `dropped` or `rejected` are never applied.
- For each cell, the approved rules of its column run in plan order. If one rule cannot read the value (for example a date that two formats read differently), the whole cell is held: it keeps its source value and goes to `holds.jsonl`.
- When the reviewer approved every proposed rule, each rule's changed and held counts equal the `evidence` that the plan step recorded. A rejected rule can change the counts of the other rules in its column.
- The plan records the table's SHA-256 digest. A table that changed after planning is refused, because the reviewed evidence no longer describes it.

## Current state

The plan exists and its review is finished. No output file exists yet in the output folder.

## Contracts and input

- The rendered input values follow `.baltor/step/contracts/input.schema.json`.
- The plan must follow `.baltor/step/contracts/plan.schema.json`.
- `changes.jsonl` lines hold `row` (data row number, starting at 1, blank lines not counted), `column`, `before`, `after` and `rules`.
- `holds.jsonl` lines hold `row`, `column`, `value`, `rule` and `reason`.
- `apply_summary.json` follows `.baltor/step/contracts/output.schema.json` and is written last, only after the self-checks pass.

## Acceptance

- Every checked cell of the copy equals the source cell, unless one change log line names that cell with the exact before and after values.
- The source digest after the run equals the digest in the plan.
- The report quotes the summary's own counts and names the hold list.
