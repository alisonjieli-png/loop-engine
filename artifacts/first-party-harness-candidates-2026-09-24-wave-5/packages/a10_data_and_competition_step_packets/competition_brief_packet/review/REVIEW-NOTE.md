# Review note: competition brief step packet

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a10_data_and_competition_step_packets, model family anthropic, September 23, 2026, against the pinned revision `a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`. This note is never delivered to a customer's harness.

## Method

One focused step: turn the saved pages of a data science competition into a structured brief of 15 facts (task, target column and type, metric and direction, id column, prediction columns and value type, the three data files, external data, daily submission limit, team size and deadline). `brief_tool.py start` records page digests and the header of every CSV data file and writes a brief in which every fact is null. The model reads the pages and fills each fact with a value and a quote copied from a page, or leaves it null with a question. `brief_tool.py check` verifies the quotes word for word after folding only formatting (Unicode form, typographic quotes, emphasis marks, spaces). It also checks each metric's direction and that a metric quote names the metric. From the data headers it confirms that the target is a training column the test file lacks, that the id column is in the test and sample files, and that the sample holds exactly the id and prediction columns. When a quote is not found, the finding says where the words are: on another page (with the page to name), or in the closest sentence of the named page by shared words (the sentence is shown in the compared form, so copying it passes the word-for-word test), or nowhere close. Small models often paraphrase; this turns the repair into copying instead of searching again.

## Authoring basis and sources

Original text and code written for this wave under the MIT licence. The package follows `src/loop_engine/core/service_runtime/catalogue_packages.py`, and `contracts/task.json` holds exactly the `node_assignment/v3` fields of `src/loop_engine/core/node_provisioning.py`. `benchmarks/kaggle_competitions/contract.py` is a related practice in the repository: it reads the target as the column present in the training file and absent from the prediction file, confirmed by the sample submission, because taking the last column picks a feature in one recorded competition. The check here applies the same rule in new code; no code or text was copied.

## Inputs and outputs

Input: the rendered values in `contracts/input.schema.json` (pages folder, data folder, brief path); pages are `.md` or `.txt` files. Output: one `competition_brief/v1` file following `contracts/output.schema.json`.

## Effects

`reads_fs` for the pages and the data files, which are hashed and whose headers are read. `writes_fs` for the new brief file, which the model then edits. `spawns_process` because the model starts `python3` for the script. There is no network use, no model call from code and no secret. Nothing is uploaded or submitted. `contracts/task.json` lists only `reads_fs` and `writes_fs` because the delivered-file vocabulary rule refuses the word in the name `spawns_process`; the host adds that effect. The assignment expected no process effect for this packet; the check script was added so that quotes are verified by code instead of trusted.

## Closest existing items

- Starter `orient_on_a_task_and_write_its_contracts`: general prose questions for any task. This packet is specific to competitions, fills a typed record and verifies every quote and column fact by code.
- Pilot `profile_one_csv` and the a02 modeling tools work on data files; none of them reads the competition pages.

## Positive example

For the three synthetic pages and three CSV files in the tests, `examples/output.json` fills 14 facts with exact quotes. The team size is not stated, so it stays null with the question "What is the largest team size allowed in this competition?". The check passes.

## Known-wrong example

A model takes the last training column, `region`, as the target. The check refuses it because `region` is also a column of the test file, so it is a feature. Other tested refusals: a paraphrased quote, the metric `rmse` quoted from an AUC sentence, the direction `minimize` for AUC, prediction columns that the sample lacks, a missing fact without a question, a question for a filled fact, a count the quote does not state, and a page changed after start.

In the second pass a probe showed that the first check told a model only to "copy the exact words" after a paraphrase, which leaves a small model to search the page again and often paraphrase again. The test `test_a_quote_that_is_not_found_points_to_the_page_sentence` (paraphrase, right quote on the wrong page, unrelated quote) was written first and failed on the old script; it passes now, and removing the hint makes it fail again (mutant check in the log).

The third pass, on September 24, 2026, found one more gap with a producer probe of likely small-model mistakes. When the model broke the JSON syntax of the brief while filling it (one missing comma), the check refused with exit 2, and `AGENTS.md` tells the model to stop on exit 2, so the step would end on a slip the model could repair itself. The check now reports the syntax error, with its line and column, as a finding with exit 1, so the rule of fixing findings and checking again applies. Exit 2 stays for a missing or oversized brief and for pages or data files the script cannot read. The test `test_broken_json_edit_is_a_finding_to_fix` was written first and failed on the old script; it passes now, and restoring the refusal makes it fail again (mutant check in the log).

## Harness placement and verification state

`AGENTS.md` is composed into the step root for Codex, OpenCode and Pi (observed in recorded probes) and Kimi CLI (unverified). `CLAUDE.md` holds `@AGENTS.md` for Claude Code (file observed, import documented). `GEMINI.md` is a byte copy for Gemini CLI (documented). Step files go to `.baltor/step/`, the licence to `.baltor/competition-brief-packet/LICENSE`, and the test file is deliberately not placed. No harness binary was run, so native loading is unobserved. The commands start `python3 -I -B`; the host must bind a trusted interpreter.

A producer-side host walkthrough placed the packet by each of the six placement maps, rendered the markers, ran both shell blocks of the rendered `AGENTS.md` as written on the 40-row synthetic data of the baseline packet with these pages, and passed the brief's target, id column, metric, target type, file names and value type to the wave 5 `baseline_training_packet` and `submission_assembly_packet`, which both accepted them. It is a script-level probe, not a native harness run and not a model run. The third pass repeated the walkthrough on the final bytes with the same result, and also replayed a brief with one missing comma: the check reported it as a finding with exit 1, and the corrected brief passed.

## Customer requests

- "Read the competition pages and tell me the target, the metric and what the submission file must look like."
- "Before we train anything, write down the rules of this competition with quotes."
- "Is higher better for this metric, and how many submissions can we make each day?"

## Limits

- A quote check proves that the words are on a page, not that the value was read correctly; a reviewer still reads the brief.
- Pages must be saved as text; HTML is not read.
- Metric names outside the list use `other`, and their quotes are not checked for a metric name.
- A competition whose test file really holds the target column fails the target check; the step then stops and reports.
- Row counts are recorded only for data files up to 64 MiB.
- The closest-sentence hint ranks sentences by shared words. It points to a place to read; it does not decide the fact, and the other checks still apply to the copied words.
- The brief's `prediction_value_type` uses `class_label` where the submission packet's value type says `binary_label`; a host that chains the two maps the name.
- Check history: the first pass left one passing report and no failing report. The second pass, on September 23, 2026, logged its runs in `packages/competition_brief_packet/PRECHECKS.txt` beside the assignment folder (the layout check refuses extra entries in the package folder), including the failing known-wrong test, a failed first mutant attempt and its successor. It changed the payload after its last checker run and ended before `fill` and `check` ran again, so its newest report described older bytes. Producer probes of that pass also left `__pycache__` folders in the payload (their times match the walkthrough), which the layout check refuses. The third pass, on September 24, 2026, saved a snapshot of the earlier state beside the assignment folder, removed the generated folders, added the syntax-slip test and repair above, and ran `fill`, `check` and `check-all` on the final bytes; its runs are appended to the same log. Each check also saved a `precheck-*.json` report beside this note, and `review/PRECHECKS.txt` keeps the first pass's log.
- The cited sources are unchanged between the pinned revision and `origin/main` at `e8069610` (checked on September 24, 2026).
