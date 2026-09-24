# Review note: cleaning application step packet

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a10_data_and_competition_step_packets, model family anthropic, September 23, 2026, against the pinned revision `a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`. This note is never delivered to a customer's harness.

## Method

One focused step: apply only the rules marked approved in a reviewed cleaning plan to a copy of one table. `apply_plan.py --check-only` validates the plan against `contracts/plan.schema.json`, confirms that the table digest equals the digest recorded in the plan, and refuses a plan whose review is unfinished. For each cell, the approved rules of its column run in plan order; if one rule cannot read the value, the whole cell is held and keeps its source value. The full run writes the copy, `changes.jsonl` (one line per changed cell with before, after and the rules that changed it) and `holds.jsonl`. It then re-reads the copy and compares every cell with the source and the change log. Only when every check passes does it write `apply_summary.json`. The source table is never opened for writing. The model runs the commands and reports; it makes no cleaning decision.

## Authoring basis and sources

Original text and code written for this wave under the MIT licence. The package follows `src/loop_engine/core/service_runtime/catalogue_packages.py`, and `contracts/task.json` holds exactly the `node_assignment/v3` fields of `src/loop_engine/core/node_provisioning.py`. `src/loop_engine/code_nodes/database_copy.py` is a related practice in the repository (copy with corrections to a new target, never in place, with the source digest checked before and after); no code or text was copied from it. The five operations are the same code as in the wave 5 `cleaning_plan_packet`, so evidence counted at planning time and cells changed here follow one definition.

## Inputs and outputs

Input: the rendered values in `contracts/input.schema.json` (table path, plan path, output folder), whose patterns keep values safe inside the shell commands, and a plan following `contracts/plan.schema.json`. Output: `cleaned` plus the table's extension, `changes.jsonl`, `holds.jsonl` and `apply_summary.json` (`cleaning_apply_summary/v1`, `contracts/output.schema.json`).

## Effects

`reads_fs` for the table and the plan. `writes_fs` for four new files in the output folder; existing files are refused, never overwritten. `spawns_process` because the model starts `python3` for the script. There is no network use, no model call from code and no secret. `contracts/task.json` lists only `reads_fs` and `writes_fs` because the delivered-file vocabulary rule refuses the word in the name `spawns_process`; the host adds that effect when it grants the step.

## Closest existing items

- Starter `copy_a_table_with_corrections_never_in_place`: prose that restates repository code for copying with corrections. This packet is an executable step with a cell-level change log, a hold list and a self-check before the summary.
- Starter `apply_hold_or_escalate_each_correction`: prose on confidence thresholds. This packet holds by rule outcome (a value no declared format reads, two formats that disagree, an unmapped value) and uses no confidence score.
- Wave 5 `raw_data_stays_read_only` is a rule file, and `verify_cleaned_copy_change_log` is an independent check of a finished copy. This packet is the step between them and does not replace the independent check.

## Positive example

`examples/approved_plan.json` is a reviewed plan for the eight-row synthetic customer table in the tests. Applying it changes 16 cells, holds three dates that day-first and month-first read differently, leaves the dropped `NA` country rule and the rejected `n/a` notes rule unapplied, and produces exactly `examples/output.json` with every check true.

A producer-side host walkthrough also fed this step a plan produced by the wave 5 `cleaning_plan_packet` itself (draft, the model's edits replayed from that packet's example, recount, then a simulated review that approved every proposed rule except `r8`). The rendered first action returned `ready` and wrote nothing; the full run changed 19 cells, held none because that plan narrows the dates to day-first, and every self-check was true with the source digest unchanged. It is a script-level probe, not a native harness run. The third pass repeated it on the final bytes with the same counts.

## Known-wrong example

A cleanup edits the source file in place and keeps no record, so a wrong rule found later cannot be undone and nobody can tell which cells changed. This step refuses to write over any existing file, checks the source digest before and after, and fails when the copy holds a difference that the change log does not name. Tests cover an unfinished review, an approval without a reviewer, a plan with no rule marked approved, a table changed after planning, an existing output, a path outside the workspace, and a copy edited without a log line.

## Harness placement and verification state

`AGENTS.md` is composed into the step root for Codex, OpenCode and Pi (observed in recorded probes) and Kimi CLI (unverified). `CLAUDE.md` holds `@AGENTS.md` for Claude Code (file observed, import documented). `GEMINI.md` is a byte copy for Gemini CLI (documented). Step files go to `.baltor/step/`, the licence to `.baltor/cleaning-apply-packet/LICENSE`, and the test file is deliberately not placed. No harness binary was run, so native loading is unobserved. The commands start `python3 -I -B`; the host must bind a trusted interpreter.

## Customer requests

- "Apply the fixes I signed off to a copy of the file and show me every cell that changed."
- "Clean the export, but do not touch the original and list anything you could not fix."
- "Which rows still need a person after the cleanup?"

## Limits

- The table must be UTF-8 and at most 64 MiB; the step refuses rather than truncates.
- Blank lines are skipped and counted; row numbers count data rows only.
- The copy keeps every value that no rule changed, but quoting style and a missing final line break can differ from the source bytes.
- Held cells wait for a person; this step does not resolve them.
- The second pass changed no behavior of this step. It replaced literal no-break space characters in the number operation with visible escapes, added a test that pins that operation to the plan step's results, and updated the profile digest in `examples/approved_plan.json` (and so the plan digest in `examples/output.json`) after the plan step's profile gained a leading-zero count.
- Check history: the first pass left one passing report and no failing report. The second pass, on September 23, 2026, logged its runs in `packages/cleaning_apply_packet/PRECHECKS.txt` beside the assignment folder (the layout check refuses extra entries in the package folder), including the walkthrough and the mutant checks of the sibling packets. It changed this payload after its last checker run and ended before `fill` and `check` ran again, so its newest report described older bytes. The third pass, on September 24, 2026, changed no payload byte of this package. A producer probe confirmed that a reviewed plan that is not valid JSON is still refused with exit 2 here, which is right because this step must not edit the plan. The pass ran `fill`, `check` and `check-all` on the final bytes and appended those runs to the same log. Each check also saved a `precheck-*.json` report beside this note, and `review/PRECHECKS.txt` keeps the first pass's log.
- The cited sources are unchanged between the pinned revision and `origin/main` at `e8069610` (checked on September 24, 2026).
