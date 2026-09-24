---
description: "Choose one next experiment from the ledger and notes, with expected effect, cost and ending rule, and refuse a configuration that already ran."
argument-hint: "[preference]"
---

# Pick the next experiment

## Purpose
Use this between experiment runs, for example in a data science competition. It turns the ledger and your notes into one next experiment with an expected effect, a cost and an ending rule. The helper refuses a configuration that already ran, failed runs included, and a setting the ledger does not know.

## First action
Run:

```bash
python3 -I -B .baltor/pick-next-experiment/scripts/experiment_ledger.py summary --root .
```

Then read `.baltor/experiments/notes.md` if the summary names it. Preference given with this command, if any: $ARGUMENTS

## Steps
1. Start from `best`. If `lead_within_fold_spread` is true, its lead is smaller than the spread of its fold scores, so treat it as uncertain.
2. Choose one change of one or two keys from `known_keys` that the ledger or the notes give a reason for. Prefer a key that was never varied. Do not repeat a failed change without fixing its cause.
3. Write `.baltor/experiments/proposal.json` in the format of `.baltor/pick-next-experiment/examples/proposal.json`: the full `config`, `base`, a `change` that names every key you change, `reason`, `expected_effect` with the ledger metric, `cost`, and an `ending_rule` that contains a number.
4. Check and record it:

```bash
python3 -I -B .baltor/pick-next-experiment/scripts/experiment_ledger.py propose --root .
```

5. If it reports `findings`, change the proposal and run `propose` again. To rerun a failed run after fixing its cause outside the configuration, such as more memory, set `retry_of` to its id and describe the fix in `environment_change`.

## Output
One new ledger line with status `planned`. Reply with its id, the change, the expected effect, the cost and the ending rule. The step is done when `propose` exits 0. Do not start the experiment here; the helper's `record` subcommand logs its result later.

## Stop and report when
- A helper run exits 2, for example because the ledger or its header line is missing. Report its `reason`.
- A finding says the ledger budget has no minutes left.
- A finding says a key you need is not a setting of this ledger. Only a person adds settings.
- A second, different proposal is also refused as a repeat. Report both fingerprints.
