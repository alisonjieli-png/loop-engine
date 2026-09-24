---
name: "verify-criteria-have-evidence"
description: "Match every acceptance criterion in a ticket checklist to at least one evidence entry, such as a test name, command result or file, and fail when any criterion has none."
license: MIT
compatibility: "Python 3.10 or later, standard library only. Reads a Markdown or JSON checklist, JSON evidence entries and the files they cite."
metadata:
  version: "0.1.0"
---
# Verify acceptance criteria have evidence

A ticket is done only when each acceptance criterion has evidence that holds up. The bundled script matches every criterion to evidence entries and checks each entry against real files: a test must pass in a saved test output, a command needs its saved output and the expected exit code, and a file must exist. A ticked box is never evidence.

## When to use it

Use it at the end of a ticket, after the fix is checked and before the ticket is reported done. You need the ticket checklist and the evidence entries.

## First action

From the workspace root, run the script. SKILL_DIR is the folder that holds this file. If you do not know it, run `ls -d .*/skills/verify-criteria-have-evidence` and use the folder it prints.

```bash
python3 -I -B SKILL_DIR/scripts/verify_criteria_evidence.py --criteria CRITERIA_FILE --evidence EVIDENCE_FILE
```

## Steps

1. Replace CRITERIA_FILE with the ticket checklist and EVIDENCE_FILE with the evidence JSON your task names, both as relative paths.
2. If your task names no evidence file, give the entries on standard input with `--evidence -`, as [references/evidence-format.md](references/evidence-format.md) shows. Cite saved files; never state a result from memory.
3. Run the command and read the JSON it prints.
4. Copy `verdict`, `uncovered`, `contradicted`, `unknown_criteria` and `evidence_problems` into your answer.
5. Answer every item in [references/checklist.md](references/checklist.md).

## Checks

- Exit 0, verdict `pass`: every criterion has an entry that holds up and none that contradicts it.
- Exit 1, verdict `fail`: `uncovered` lists criteria without such an entry, `contradicted` lists criteria with a failing test or a wrong exit code, and `unknown_criteria` lists entries that name no real criterion.
- Exit 2, verdict `refused`: an input could not be read; `reason` says why.
- `evidence_problems` explains every entry that did not count.

## Done when

Your answer holds the verdict, every uncovered, contradicted or unknown item, and one reply for each checklist item.

## Stop and report when

- The verdict is `fail` or `refused`. Do not tick boxes, edit the evidence or rerun tests to change it unless your task says so.
- The script finds no criteria in the checklist.

## Known-wrong example

The box "AC-4: The change log names the fix" is ticked, but no evidence entry names AC-4. The script lists AC-4 in `uncovered`, warns that it is ticked without evidence, and exits 1.
