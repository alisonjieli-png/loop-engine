# Cleaning application step packet

This is a step template. The host fills every value in double braces before the step starts. If a double-brace marker is left, stop and report `unrendered_step_input`.

## Assignment

Apply only the approved rules of the reviewed plan `{{PLAN_PATH}}` to a copy of the table `{{TABLE_PATH}}`. The copy, a cell-level change log and a hold list go into `{{OUTPUT_DIR}}`. The source table is never edited. The step script does all the cleaning. Your job is to run it, confirm its self-checks and report the result.

## First action

Check the inputs without writing anything:

```bash
python3 -I -B .baltor/step/scripts/apply_plan.py --table {{TABLE_PATH}} --plan {{PLAN_PATH}} --out-dir {{OUTPUT_DIR}} --check-only
```

## Steps

1. Read the printed JSON. Continue only when `status` is `ready`. It lists the rules it will apply and the rules it will leave out.
2. Run the same command again without `--check-only`.
3. Read the summary it prints. It names the copy, `changes.jsonl`, `holds.jsonl` and `apply_summary.json`.
4. Confirm that every value under `checks` is `true`.
5. Report, from the summary: changed and held cells per rule, the rules not applied and why, and the path of the hold list. A held cell keeps its source value; a person decides it later.

## Done when

`{{OUTPUT_DIR}}/apply_summary.json` exists, its `status` is `applied`, and every value under `checks` is `true`.

## Stop and report when

- A command exits 2 (refused input). Give its JSON unchanged as your report. Common causes: a rule is still `proposed`, no rule is approved, a rule names no reviewer, the table changed after the plan was made, or an output file already exists.
- A command exits 1. The self-check found a difference between the copy and the logs. Report it and do not run the command again.
- The only way forward seems to be editing the plan or the table. Do not edit either; report instead.

## Files

- `.baltor/step/node_context.md`: objective, the order of work and acceptance.
- `.baltor/step/checklist.md`: checks before and after the work.
- `.baltor/step/contracts/plan.schema.json`: the reviewed plan the script accepts.
- `.baltor/step/contracts/output.schema.json`: the summary shape.
- `.baltor/step/examples/approved_plan.json` and `.baltor/step/examples/output.json`: a reviewed plan and the summary it produced.

## Authority

This file grants no authority. The host must grant reading `{{TABLE_PATH}}` and `{{PLAN_PATH}}`, creating new files only inside `{{OUTPUT_DIR}}`, and starting `python3` for `.baltor/step/scripts/apply_plan.py`. The step needs no network and no other command.
