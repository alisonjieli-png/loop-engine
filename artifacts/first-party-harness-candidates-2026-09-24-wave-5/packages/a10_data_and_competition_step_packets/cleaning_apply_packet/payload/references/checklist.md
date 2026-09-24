# Cleaning application step packet: checklist

## Before work

- [ ] No double-brace marker is left in `AGENTS.md`.
- [ ] The run with `--check-only` printed `"status": "ready"` and wrote no file.
- [ ] Every rule it will apply is marked `approved` with a reviewer in the plan.

## Before handoff

- [ ] `apply_summary.json` exists and its `status` is `applied`.
- [ ] Every value under `checks` in the summary is `true`.
- [ ] The report gives changed and held cells per rule and names the hold list.
- [ ] Neither the plan nor the source table was edited.
