# Review note: cleaning plan step packet

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a10_data_and_competition_step_packets, model family anthropic, September 23, 2026, against the pinned revision `a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`. This note is never delivered to a customer's harness.

## Method

One focused step: profile one delimited UTF-8 table and hand over a column-by-column cleaning plan. `plan_tool.py draft` counts, per column, empty cells, cells that need trimming, missing-value tokens, letter-case variants, number styles and date formats. It drafts rules from a closed set of five operations (`trim_whitespace`, `missing_tokens_to_empty`, `map_values`, `parse_number`, `parse_date`), each with evidence counted from the data. The model only judges meaning: keep or drop each rule, narrow its parameters, write a reason and ask questions. `plan_tool.py check --write-evidence` recounts every rule's evidence, so no number in the plan is typed by the model. It fails a plan that deletes a suggestion, sets a rule to approved, orders a column's rules wrongly or leaves a reason empty. The table is never opened for writing. When a column's values would lose a leading 0 as numbers (a postal code such as `01234`), the draft asks a question instead of drafting `parse_number`, and the check warns about any number rule the model adds for such a column. That decision needs the column's meaning, so it goes to the model and the reviewer, not to a default rule.

## Authoring basis and sources

Original text and code written for this wave under the MIT licence. The package follows `src/loop_engine/core/service_runtime/catalogue_packages.py`. `contracts/task.json` holds exactly the `node_assignment/v3` fields of `src/loop_engine/core/node_provisioning.py`. `src/loop_engine/code_nodes/text_conformance_operations.py` is a related practice in the repository (profile a column, then propose rules with the share that justified them); no code or text was copied from it. The cleanup study at the pinned revision measured that loaded material cost more prompt tokens and that one prose item misled a cheap model, so the deterministic work sits in a tested script and the always-loaded text stays short.

## Inputs and outputs

Input: the rendered values described by `contracts/input.schema.json` (table path, output folder, row cap, delimiter). Its patterns keep every value safe inside the shell commands of `AGENTS.md`; the host validates values against it before rendering and refuses a file that still holds a double-brace marker. Output: `table_profile.json` (`table_profile/v2`) and `cleaning_plan.json` (`cleaning_plan/v1`, `contracts/output.schema.json`) with rules marked `proposed` or `dropped`, counted evidence, reasons and questions. The profile went from version 1 to version 2 in the second pass because it gained a leading-zero count per number style that the check reads; the check refuses a profile of any other version before it writes anything. The plan record kept version 1 because its shape did not change.

## Effects

`reads_fs` for the table, the plan and the profile. `writes_fs` for two new files in the output folder and the evidence fields of the plan. `spawns_process` because the model starts `python3` for the script. There is no network use, no model call from code and no secret. `contracts/task.json` lists only `reads_fs` and `writes_fs`: the delivered-file vocabulary rule refuses the word in the name `spawns_process`, so the host must add that effect when it grants the step. The Authority section says this in plain words.

## Closest existing items

- Pilot `profile_one_csv`: a quality report for one CSV that proposes no rules. This packet proposes rules, counts their evidence and hands a checked plan to a reviewer.
- Starter `profile_text_column_before_cleaning`: prose for one text column. This packet covers every column, numbers and dates included, with tested code.
- Wave 5 a01 executors such as `parse_dates_by_declared_formats` convert one column on request. This packet plans only and changes no data; the wave 5 `cleaning_apply_packet` applies a reviewed plan.

## Positive example

The eight-row synthetic customer table in the tests yields eight suggested rules and one date question. The finished plan in `examples/output.json` narrows the date formats to day-first, because three dates have a day above 12 in first place and no value needs month-first. It drops the missing-token rule for the country `NA`, adds a question about empty spend values, and passes the read-only check.

## Known-wrong example

A model treats `NA` in a column of two-letter country codes as missing and keeps the rule, so Namibia would vanish from the data. The reason requirement makes that judgment visible to the reviewer. The mechanical errors are refused by the check, each with a test: evidence typed by hand, a deleted suggestion, a rule set to `approved` in the plan step, a parse rule placed before the missing-token rule, and a table changed after the draft.

A second known-wrong case was found in the second pass by probing the script: the first draft proposed `parse_number` for a zero-padded postal code column, turning `01234` into `1234`, with no question. A small model that keeps drafted rules would have damaged every such code. The test `test_zero_padded_codes_get_a_question_instead_of_a_number_rule` was written first and failed on the old script; it passes now, and removing either the draft guard or the check warning makes it fail again (mutant check in the log).

A third known-wrong case was found in the third pass, on September 24, 2026, by a producer probe of likely small-model mistakes. When the model broke the JSON syntax of the plan while editing it (one missing comma), the check refused with exit 2, and `AGENTS.md` tells the model to stop on exit 2. The step would then end on a slip that the model could repair itself. The check now reports the syntax error, with its line and column, as a finding with exit 1 and writes nothing, so the normal rule of fixing findings and checking again applies. Exit 2 stays for what the model must not change: the table, the profile, and a plan that lost its table or profile section. The test `test_broken_json_edit_is_a_finding_to_fix` was written first and failed on the old script; it passes now, and restoring the refusal makes it fail again (mutant check in the log).

## Harness placement and verification state

`AGENTS.md` is composed into the step root for Codex, OpenCode and Pi (observed in recorded probes) and Kimi CLI (unverified). `CLAUDE.md` holds `@AGENTS.md` for Claude Code (file observed, import documented). `GEMINI.md` is a byte copy for Gemini CLI (documented). Step files go to `.baltor/step/`, the licence to `.baltor/cleaning-plan-packet/LICENSE`. The test file is review material and is deliberately not placed, which keeps the step folder small. No harness binary was run, so native loading of this package is unobserved. The commands start `python3 -I -B`; the host must bind a trusted interpreter, because a `python3` found first on the path can be replaced.

A producer-side host walkthrough placed the packet by each of the six placement maps, rendered the markers from `examples/input.json`, ran the two shell blocks of the rendered `AGENTS.md` exactly as written, replayed the model's edits from `examples/output.json`, and handed the recounted plan, after a simulated review, to the wave 5 `cleaning_apply_packet`, which accepted and applied it with every self-check true. It is a script-level probe, not a native harness run and not a model run. The third pass repeated the walkthrough on the final bytes with the same result, and also replayed a plan with one missing comma: the check reported it as a finding with exit 1, and the corrected plan passed.

## Customer requests

- "Before we clean this export, tell me which fixes each column needs and show me the evidence."
- "Can a small local model draft the cleaning rules so that I only have to approve them?"
- "Some dates look like 03/04/2025. Which order does this file use?"

## Limits

- Five operations only. Outliers, duplicates, names and addresses are out of scope.
- The profile reads at most the rendered row cap. Later rows may hold other values, and the check warns when the cap was reached.
- Month names parse in the C locale, so they are English.
- Evidence examples show up to three real cell values. A host with sensitive data decides whether the step may see them.
- The thresholds are fixed heuristics reported in the profile: a 90 percent parse share, a 5 percent share per date format, and at most 30 distinct values for case variants.
- The leading-zero guard sees only values that parse as numbers. A code column that mixes letters and digits gets no number rule anyway.
- Check history: the first pass left one passing report and no failing report. The second pass, on September 23, 2026, logged its runs in `packages/cleaning_plan_packet/PRECHECKS.txt` beside the assignment folder (the layout check refuses extra entries in the package folder): a skip-runs timing probe, the baseline run, the walkthrough, the failing known-wrong tests, a failed first mutant attempt and its successor. It changed the payload after its last checker run and ended before `fill` and `check` ran again, so its newest report described older bytes. Producer probes of that pass also left `__pycache__` folders in the payload (their times match the walkthrough and the example regeneration), which the layout check refuses. The third pass, on September 24, 2026, saved a snapshot of the earlier state beside the assignment folder, removed the generated folders, added the syntax-slip test and repair above, and ran `fill`, `check` and `check-all` on the final bytes. Its runs are appended to the same log. Each check also saved a `precheck-*.json` report beside this note, and `review/PRECHECKS.txt` keeps the first pass's log.
- The cited sources are unchanged between the pinned revision and `origin/main` at `e8069610` (checked on September 24, 2026), so a re-pin changes no source digest.
