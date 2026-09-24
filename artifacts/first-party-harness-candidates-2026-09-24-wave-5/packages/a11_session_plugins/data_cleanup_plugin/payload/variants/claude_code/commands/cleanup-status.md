---
description: "Compare every cleaned CSV copy with its source by header and row count, using the declared pairs. Read-only."
---

# Cleanup status

## Purpose

Check that every cleaned copy named in `.baltor/step/cleanup-pairs.json` still
has its source's header, after the declared renames and in the same order,
and the same number of data rows, apart from the declared drops. This
command writes nothing.

## First action

Run this command with your shell tool, from the workspace root, and read the
JSON it prints:

```bash
python3 -I -B .baltor/plugins/data-cleanup-plugin/scripts/check_cleaned_counts.py --all
```

## Steps

1. Run the command above.
2. Exit 2 means the pairs file is missing or unreadable. Go to "Stop and
   report when".
3. Report one row per pair: cleaned file, status, source rows, cleaned rows
   and header match.
4. For each pair whose status is not `match`, copy its `details` exactly.
5. If every pair matches, say so in one line and continue your step.

## Output

The table, then one line per problem pair. Use only numbers from the JSON.
A row count is a count of CSV records, so a value with a line break inside
quotes is still one row.

## Stop and report when

- Exit 2: report `error` and `detail`.
- A pair is `missing_source` or `unreadable`. Never recreate or edit a
  source file.
- A mismatch could pass only by editing `cleanup-pairs.json`. That file is
  fixed for the step. Report the mismatch instead.
