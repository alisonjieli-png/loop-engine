---
name: "verify-morning-report-claims"
description: "Check each item a morning report marks complete against its cited evidence files, digests and exit codes, and list every claim the evidence does not support."
license: MIT
compatibility: "Python 3.10 or later, standard library only. Reads a JSON or Markdown morning report, including a night_morning_report/v1 record, and the files it cites."
metadata:
  version: "0.1.0"
---
# Verify morning report claims

A morning report can say more than the night proved. The bundled script opens every file that a complete item cites. It checks that the file exists, still has the cited digest, agrees with the cited exit code, and that at least one cited file shows a passing run by itself. It changes nothing.

## When to use it

Use it after a morning report is written and before anyone reads it as the result of the night. You need the report file, and its evidence paths must be relative to the workspace root.

## First action

From the workspace root, run the script. SKILL_DIR is the folder that holds this file. If you do not know it, run `ls -d .*/skills/verify-morning-report-claims` and use the folder it prints.

```bash
python3 -I -B SKILL_DIR/scripts/verify_report_claims.py --report REPORT_FILE
```

## Steps

1. Replace REPORT_FILE with the path of the report. When the report exists as JSON and as Markdown, check the JSON file.
2. Run the command and read the JSON it prints.
3. Copy `verdict`, `unsupported`, `needs_reading`, `report_problems` and `warnings` into your answer.
4. For each item in `needs_reading`, read the claim and the cited file. Write one sentence that says whether the claim describes what the file shows.
5. Answer every item in [references/checklist.md](references/checklist.md).

## Checks

- Exit 0, verdict `pass`: every complete item is supported.
- Exit 1, verdict `fail`: `unsupported` lists each item with its problems, and `report_problems` lists counts that do not match the entries.
- Exit 1, verdict `review`: nothing is refused, but `needs_reading` lists claims that only a reader can judge.
- Exit 2, verdict `refused`: the report could not be read; `reason` says why.
- [references/claim-rules.md](references/claim-rules.md) explains the formats and every problem name.

## Done when

Your answer holds the verdict, every unsupported item with its problems, one sentence for each item in `needs_reading`, and one reply for each checklist item.

## Stop and report when

- The verdict is `fail` or `refused`. Do not edit the report, the evidence or the handoffs to change it.
- `warnings` says a status word is not known. Ask what it means. Add `--claim-word` only when your task says that word means complete.

## Known-wrong example

A report marks T-205 verified and cites a test log with exit 0. The summary line of the log says 1 failed, 5 passed. The script lists T-205 under `unsupported` with `exit_code_contradicted` and `no_passing_gate_evidence`, and exits 1.
