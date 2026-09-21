# Starter catalogue review sheet

Kind: review sheet. It records what each item is and how to read it. The
decisions themselves are in the machine-readable record
[`reviews.json`](reviews.json), which is the approval evidence a host manifest
points at. The approval column in the table below stays empty: a reader looks
up a decision in one place, not two.

On 21 September 2026 three independent reviewers judged all 49 items. None of
them wrote an item it judged. Forty-three items were approved by all three.
Six were rejected by at least one reviewer, with the reason written down, and
stay candidates. `reviews.json` holds one row for each item, each reviewer's
decision and reason, and the rule that decided the outcome: an item is
approved only when every reviewer approves it, and one written objection
withholds approval.

## What this folder holds

The folder holds 49 skill-sized items that a customer's coding harness could
load for one step of a task. Each item is one Markdown body of 150 to 600
words with the same parts: when to use it, the steps, the checks, one
known-wrong example, what to record and the cited source.

```text
Starter catalogue candidates (49)
├── Context Intelligence (28)
│   ├── working methods for understanding, deciding, verifying and handing over
│   ├── question sets for model evaluation and review
│   └── two checklists compiled from model generated statements
├── Code Intelligence (21)
│   └── guides to reusable data cleaning, duplicate, copy, export and measurement code
├── Runtime History and Solution Intelligence (0)
└── User Feedback Intelligence (0)
```

| File | Purpose |
|---|---|
| `bodies/` | One body for each item. The body is the source of truth for the text, the digest and the size. |
| `specifications.json` | The items in the exact format that `tools/stage_intelligence_candidates.py` accepts. The `text` of each row equals its body. |
| `items.json` | The facts a harness item carries: identity, kind, purpose, source layer, source reference, licence, declared effects, harness styles, lifecycle tag, digest and size. Each `reference` object has the shape that `HarnessIntelligenceItem.reference()` returns. |
| `search-queries.json` | The plain customer queries that the check runs against the purposes, each with the item it must find and who wrote it. |
| `executed-examples.json` | 54 executed examples over 12 of the 21 Code Intelligence items. Each row names its item, the quote as the body writes it, the cited module and function, the arguments and the fields the body claims. The check runs each listed call against the cited module. It covers the rows in this file, not every value that a body quotes. |
| `refresh.py` | Recomputes the derived fields after a body was edited. It approves nothing and publishes nothing. |
| `reviews.json` | The independent review record, `starter_catalogue_independent_review/v1`. One row for each of the 49 items with each reviewer's decision and reason, the rule that decided the outcome, and the approval reference a host manifest points at. |
| `host-release/` | The release content generated from `reviews.json` and the bodies: `manifest.json` plus the 43 approved bodies and nothing else. It is copied into the service image. Do not edit it by hand. |
| `REVIEW.md` | This sheet. |

## The approved release content

`tools/build_host_catalogue_manifest.py` writes `host-release/`. It reads the
review record, refuses every item that any reviewer rejected, measures each
body file for its digest and size, and checks the declared licence against the
host licence policy the running host will apply. Run it without `--write` to
check the folder already in the repository, which is what the checks do:

```bash
PYTHONPATH=src python tools/build_host_catalogue_manifest.py \
  --catalogue examples/29_intelligence_service/starter-catalogue \
  --output examples/29_intelligence_service/starter-catalogue/host-release \
  --artifact-root /opt/baltor/catalogue \
  --accept-license MIT --grant pilot-owner:bodies:required
```

The release image copies `host-release/` to `/opt/baltor/catalogue`, owned by
the unprivileged service user and with no write bit. The host configuration on
the volume points `manifest_path` at `/opt/baltor/catalogue/manifest.json`. The
catalogue is release content, so it travels in the image; the volume holds
state only.

## Current state and planned steps

Current state on 20 September 2026 at revision `381efec`:

- The takeover checkpoint (`docs/context/TAKEOVER-CHECKPOINT-2026-09-20.md`) records that the hosted service serves one diagnostic record. The author of this folder did not observe the live service. None of these 49 items is in a host manifest in this repository.
- The items exist only in this folder. The staging tool accepts all 49 rows in an isolated database and keeps them as candidates.
- The serving path now refuses an item whose licence is empty, unknown, waiting for review, or not on the host's accepted list. The refusal happens before the item is registered and before its body is opened, and the message names the item. The default host policy accepts the identifier `MIT` and nothing else.
- Two items cannot be served. `check_a_table_join_before_trusting_it` and `make_a_data_pipeline_safe_to_run_again` are compiled from model generated statements and record the licence `unknown`, so the reader refuses a manifest that carries either of them, with the code `item_license_unknown`. Approving the text of those two items would not make them servable. Their rights must be settled first: either the licence of the generated statements is established and written into the item, or the item is rewritten from material whose licence is known, or the item is dropped. No host may list `unknown` as an accepted licence; the engine refuses such a policy.
- The other 47 items record the licence `MIT`, which the default host policy accepts. The check in `tools/test_starter_catalogue.py` builds its manifest from those 47, loads them through the real reader, and requires that each of the two refused items is refused by name.

What happened after that, on 21 September 2026:

- Three independent reviewers judged all 49 items. Their decisions and reasons are in `reviews.json`.
- 43 items were approved by all three and are in `host-release/manifest.json` with their approval references and the tenant grants.
- 6 items were rejected by at least one reviewer and stay candidates. They are not in the generated manifest and their bodies are not in the release image.
- The two items with the licence `unknown` are among the six. Their rights are still unsettled, so nothing about the review changes what the loader does with them: it refuses them with `item_license_unknown` before registration.

Remaining steps, not done here and not authorized by this folder:

- The rights of the two items with the licence `unknown` are settled, or those two items are rewritten from material whose licence is known, or they are dropped.
- The four other rejected items are repaired against their written reasons and resubmitted, which needs a new review.

## How to review one item

1. Open the body from the first column and read it as a customer would.
2. Open the cited source at revision `381efec` and check that the body says what the source says or does.
3. Check the licence state and the declared effects in `items.json`.
4. Write the decision in the approval column: approved with a name and a date, rejected with the reason, or the change that is needed.
5. After any edit of a body, run the refresh tool and then the checks. Run these commands from the repository root. The first command only reports stale items. The second rewrites the derived fields.

```bash
PYTHONPATH=src python examples/29_intelligence_service/starter-catalogue/refresh.py
PYTHONPATH=src python examples/29_intelligence_service/starter-catalogue/refresh.py --write
PYTHONPATH=src:tools python -m unittest tools.test_starter_catalogue
```

To look at the candidates in an isolated review catalogue, stage them with the
existing tool. It needs three new output paths and writes nothing else.

```bash
PYTHONPATH=src python tools/stage_intelligence_candidates.py \
  --specifications examples/29_intelligence_service/starter-catalogue/specifications.json \
  --database NEW_DATABASE_PATH --namespace starter.catalogue \
  --authorize-isolated-staging --export NEW_EXPORT_PATH --report NEW_REPORT_PATH
```

The existing host manifest reader accepts an approved item in this form: the
`reference` object from `items.json`, the `body_path`, an `approval_ref` that
names the owner's decision, and the tenant grants. Do not copy the lifecycle
tag without a decision. Every reference here carries the tag
`lifecycle: candidate`. When all 49 references are loaded unchanged, a request
that names `lifecycle: qualified` is offered 0 items and 49 are withheld. The
value of the tag after approval is an open decision for the later manifest
change. The reader binds an item by its identity, digest, source layer and
source reference, so the tag can change without a new digest. The
reader checks the size and the digest of the body again. Do not add an item
to a host manifest before it is approved. The reader treats every manifest
entry as approved. The reader decides the licence first, for every entry,
with or without grants, so an item whose licence this host does not accept
is refused before it is registered and before its body is opened.

## Layers without items

Runtime History and Solution Intelligence holds records of real runs with
verified outcomes. User Feedback Intelligence holds feedback from real
people. The private beta has produced neither yet. An item written for those
layers today would be invented evidence, so this catalogue has none. The first
real items can be compiled after invited users have run tasks and given
feedback, from records that name the exact run or the exact statement.

## What the owner should know before approving

- Authoring. An assistant (Claude Code) wrote every body from the cited sources at revision `381efec`, and the self tests of the nine cited source modules pass at that revision (113 checks). An adversarial review then found one statement that the code does not have: the capitalisation body said that a mixed case value such as `iPhone` keeps its capitals, and the code rewrites it to `Iphone` at 0.95 and applies that. The body was corrected from the executed behaviour. The scenarios in the known-wrong examples are illustrations written for this catalogue. No independent person has reviewed any body.
- Executed examples, and how far they reach. `executed-examples.json` holds 54 rows over 12 of the 21 Code Intelligence items. For each row the check proves four things: the quote stands in its own body word for word, the module the row runs is one of the sources that this item cites, the function is one of the symbols that this item names, and the call produces every field the row lists with the value the body gives. A row that expects no field, or that names a field the result does not have, is refused, so the file cannot be emptied while the check stays green. What the check does not prove: a value that a body quotes without a row here is not executed by anything. Nine Code Intelligence items have no row: `layer_exception_catalogs_with_precedence`, `escalate_uncertain_values_with_candidates`, `find_duplicate_records_with_blocking_keys`, `propose_a_dedupe_without_deleting_rows`, `copy_a_table_with_corrections_never_in_place`, `export_a_standalone_python_package`, `verify_an_export_in_an_isolated_interpreter`, `refuse_secrets_and_unsafe_paths_in_generated_files` and `write_a_pinned_container_and_batch_job`. A row runs one function with arguments written in JSON, and the examples of those nine need a typed object to be built first, such as a field specification, a conformance policy, an exception catalog layer, an export specification or a table location, or they need an effect on the machine, such as a database, files or a separate interpreter. Four of the nine quote concrete values in their text, so a reviewer must check those by hand against the cited source. The 28 Context Intelligence items have no rows either; they describe working methods and question sets, and this check runs nothing for them.
- Licence. 47 items are compiled from material authored in this repository, which its `LICENSE` file places under MIT. Two items are compiled from statements that a language model generated during work in this repository. Their licence is recorded as `unknown` with the state `needs_review`, and their provenance names the generator and the digests of the eight source rows. The task for this catalogue allowed at most eight such rows, and eight are used. The hosted service refuses both of them by name, as the section above records, so they cannot be served until their rights are settled.
- Declared effects. The rule: an item declares every effect that one of its steps tells the reader to perform on the reader's own machine, which means reading or listing files, writing files, starting a command or using the network. A method that only transforms values it was given declares nothing. A step that asks a question, or that names an analysis without telling the reader how to run it, declares nothing, and a harness that chooses to run such an analysis needs its own authority for it. An item without effects declares an empty list. Twelve items declare effects under this rule: `layer_exception_catalogs_with_precedence`, `copy_a_table_with_corrections_never_in_place`, `export_a_standalone_python_package`, `verify_an_export_in_an_isolated_interpreter`, `refuse_secrets_and_unsafe_paths_in_generated_files`, `write_a_pinned_container_and_batch_job`, `verify_the_requested_output`, `check_for_existing_work_before_building`, `measure_the_environment_before_relying_on_it`, `make_a_data_pipeline_safe_to_run_again`, `test_driven_change_red_green_refactor` and `package_one_skill_for_two_coding_harnesses`. The environment item declares `reads_fs`, `network` and `spawns_process`, because its steps list files, measure tool versions with commands and test network access. The pipeline item declares `reads_fs`, because its second step reads the statements of an existing pipeline. The other 37 items were read against the same rule and declare nothing. The effect names are the ones the engine defines: `pure`, `reads_fs`, `writes_fs`, `reads_secret`, `network` and `spawns_process`. A write to a database table has no name among them, so the pipeline item records that write in its steps and declares no effect for it. The service lists an item only when the request states every effect that the item declares, and the current web and protocol surfaces send no effects. These twelve items would be withheld today. That needs a decision in the engine. The declared effects were not reduced to avoid it.
- Lifecycle tag. Every reference carries the tag `lifecycle: candidate`. A request that names no lifecycle still matches a tagged item, so the tag alone does not hide a candidate. Approval and the host manifest remain the gate.
- Vocabulary. The bodies use no internal runtime vocabulary. The cited paths contain the package name `loop_engine`, and the integration item cites paths that contain the command name of this repository. The check removes cited source paths before it looks for forbidden words.
- Search. The purpose of each item is the text that the hosted search reads. All 49 title probes of the staging tool return their own item first. The file `search-queries.json` keeps 31 plain customer queries, and the check requires that each one finds its item among the first three results of a local emulation of the hosted search. The author of the purposes wrote 26 of them. A reviewer wrote 15 unseen queries afterwards, and 10 of the 15 found their item. The five that missed are kept in the file, and synonyms such as dedupe, skewed, umlauts, unreachable and ask the user were added to the purposes until they passed. The other ten reviewer queries were not saved. The queries were tuned against the purposes, so this is a smoke check and not a relevance benchmark.
- Size. The staging tool accepts at most 50 rows in one population. This catalogue uses 49.
- Omitted on purpose: ontology values, context policies, templates of the runtime, module references, `terminology.yaml`, benchmark evidence and anything about this project's own internals.

## Review table

| Identity | Layer | Why it is useful | Source | Licence state | Approval |
|---|---|---|---|---|---|
| [profile_text_column_before_cleaning](bodies/profile_text_column_before_cleaning.md) | Code Intelligence | Stops cleaning rules from being chosen by column name. The measured shares decide. | `src/loop_engine/code_nodes/text_conformance_operations.py` | MIT, declared | |
| [normalize_whitespace_and_unicode_text](bodies/normalize_whitespace_and_unicode_text.md) | Code Intelligence | Removes invisible text defects first and keeps lossy folding as an explicit choice. | `src/loop_engine/code_nodes/text_conformance_operations.py` | MIT, declared | |
| [restore_capitalisation_of_names](bodies/restore_capitalisation_of_names.md) | Code Intelligence | Fixes names in all upper case without breaking acronyms, particles and Mc or Mac surnames. | `src/loop_engine/code_nodes/text_conformance_operations.py` | MIT, declared | |
| [canonicalize_company_legal_suffixes](bodies/canonicalize_company_legal_suffixes.md) | Code Intelligence | Gives one style for Inc, LLC and Ltd, and sends ambiguous suffixes such as AS and SA to review. | `src/loop_engine/code_nodes/text_conformance_operations.py` | MIT, declared | |
| [normalize_phone_numbers](bodies/normalize_phone_numbers.md) | Code Intelligence | Rewrites only numbers whose digits can be explained. No guessed country codes. | `src/loop_engine/code_nodes/text_conformance_operations.py` | MIT, declared | |
| [normalize_website_addresses](bodies/normalize_website_addresses.md) | Code Intelligence | Normalizes scheme and host and never changes the case of a path. | `src/loop_engine/code_nodes/text_conformance_operations.py` | MIT, declared | |
| [normalize_and_recover_email_addresses](bodies/normalize_and_recover_email_addresses.md) | Code Intelligence | Repairs spelled out symbols and mistyped domains, and refuses cells it cannot repair safely. | `src/loop_engine/code_nodes/field_recovery.py` | MIT, declared | |
| [apply_hold_or_escalate_each_correction](bodies/apply_hold_or_escalate_each_correction.md) | Code Intelligence | The core rule for safe automatic correction: weakest signal, two thresholds, original value kept. | `src/loop_engine/code_nodes/text_conformance_operations.py` | MIT, declared | |
| [layer_exception_catalogs_with_precedence](bodies/layer_exception_catalogs_with_precedence.md) | Code Intelligence | Keeps one customer's exceptions out of every other dataset and makes each decision traceable. | `src/loop_engine/code_nodes/text_conformance.py` | MIT, declared | |
| [escalate_uncertain_values_with_candidates](bodies/escalate_uncertain_values_with_candidates.md) | Code Intelligence | Sends only uncertain cells to a model or a person, with candidates and a way to abstain. | `src/loop_engine/code_nodes/text_conformance.py` | MIT, declared | |
| [find_duplicate_records_with_blocking_keys](bodies/find_duplicate_records_with_blocking_keys.md) | Code Intelligence | Finds duplicates without comparing all rows with all rows, and reports groups it skipped. | `src/loop_engine/code_nodes/duplicate_detection.py` | MIT, declared | |
| [score_duplicate_pairs_by_weakest_signal](bodies/score_duplicate_pairs_by_weakest_signal.md) | Code Intelligence | Prevents merges on a shared email or phone alone. The weakest field decides. | `src/loop_engine/code_nodes/duplicate_detection.py` | MIT, declared | |
| [propose_a_dedupe_without_deleting_rows](bodies/propose_a_dedupe_without_deleting_rows.md) | Code Intelligence | Makes a merge a reviewable proposal. No row is deleted and weak links never build clusters. | `src/loop_engine/code_nodes/duplicate_detection.py` | MIT, declared | |
| [detect_malformed_values_by_dominant_pattern](bodies/detect_malformed_values_by_dominant_pattern.md) | Code Intelligence | Finds values that break a column format and says honestly when a column has no format. | `src/loop_engine/code_nodes/field_recovery.py` | MIT, declared | |
| [split_address_lines_into_components](bodies/split_address_lines_into_components.md) | Code Intelligence | Splits addresses from declared patterns and reports a missing optional parser instead of guessing. | `src/loop_engine/code_nodes/address_components.py` | MIT, declared | |
| [copy_a_table_with_corrections_never_in_place](bodies/copy_a_table_with_corrections_never_in_place.md) | Code Intelligence | Corrected data goes to a new target, and digests prove that the source did not change. | `src/loop_engine/code_nodes/database_copy.py` | MIT, declared | |
| [export_a_standalone_python_package](bodies/export_a_standalone_python_package.md) | Code Intelligence | Turns session code into an installable package with a digest for every file. | `src/loop_engine/code_nodes/solution_export.py` | MIT, declared | |
| [verify_an_export_in_an_isolated_interpreter](bodies/verify_an_export_in_an_isolated_interpreter.md) | Code Intelligence | Shows hidden dependencies that a development environment hides, and runs code only with authority. | `src/loop_engine/code_nodes/solution_export.py` | MIT, declared | |
| [refuse_secrets_and_unsafe_paths_in_generated_files](bodies/refuse_secrets_and_unsafe_paths_in_generated_files.md) | Code Intelligence | Blocks keys, traversal and symbolic link escapes before generated files are shared. | `src/loop_engine/code_nodes/solution_export.py` | MIT, declared | |
| [write_a_pinned_container_and_batch_job](bodies/write_a_pinned_container_and_batch_job.md) | Code Intelligence | Safe defaults for batch jobs: pinned image, no privileges, no platform retry of external effects. | `src/loop_engine/code_nodes/solution_export.py` | MIT, declared | |
| [read_the_train_validation_gap](bodies/read_the_train_validation_gap.md) | Code Intelligence | Turns two scores into a named verdict and catches the common direction mistake with error metrics. | `src/loop_engine/code_nodes/measurement.py` | MIT, declared | |
| [choose_metrics_by_task_type_and_industry](bodies/choose_metrics_by_task_type_and_industry.md) | Context Intelligence | Names the right and the misleading metrics for each task type and industry. | `src/loop_engine/code_nodes/measurement.py` | MIT, declared | |
| [freeze_the_success_metric_before_measuring](bodies/freeze_the_success_metric_before_measuring.md) | Context Intelligence | Prevents success from being defined after the results are seen. | `src/loop_engine/code_nodes/measurement.py` | MIT, declared | |
| [orient_on_a_task_and_write_its_contracts](bodies/orient_on_a_task_and_write_its_contracts.md) | Context Intelligence | A complete question list for understanding a request, ending in a checkable task statement. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [carry_competing_readings_of_a_request](bodies/carry_competing_readings_of_a_request.md) | Context Intelligence | Avoids building the wrong thing from an ambiguous request. One cheap observation decides. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [forecast_an_action_then_compare](bodies/forecast_an_action_then_compare.md) | Context Intelligence | Makes long or costly actions judgeable: expectation first, comparison afterwards. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [diagnose_a_stall_and_change_strategy](bodies/diagnose_a_stall_and_change_strategy.md) | Context Intelligence | Ends series of repeated attempts. The third failure of one shape forces a changed strategy. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [verify_the_requested_output](bodies/verify_the_requested_output.md) | Context Intelligence | Checks the artifact against the acceptance criteria, not the exit status. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [choose_review_perspectives](bodies/choose_review_perspectives.md) | Context Intelligence | Replaces one vague review request with named perspectives that each ask one sharp question. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [deliver_the_best_available_result_when_blocked](bodies/deliver_the_best_available_result_when_blocked.md) | Context Intelligence | Gives a useful, honestly labelled result when the literal task cannot be finished. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [resolve_missing_information](bodies/resolve_missing_information.md) | Context Intelligence | Fewer and better questions to the person. Everything the system can find out stays inside it. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [choose_one_next_action](bodies/choose_one_next_action.md) | Context Intelligence | One bounded action with an expected observation, so causes stay identifiable. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [report_observed_derived_assumed_and_unknown](bodies/report_observed_derived_assumed_and_unknown.md) | Context Intelligence | Stops reports from claiming absence for things that were never searched. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [check_for_existing_work_before_building](bodies/check_for_existing_work_before_building.md) | Context Intelligence | Prevents rebuilding what exists and reusing what does not apply. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [measure_the_environment_before_relying_on_it](bodies/measure_the_environment_before_relying_on_it.md) | Context Intelligence | Plans from measured capacity, not from a number in a document. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [hand_over_a_result_its_consumer_can_use](bodies/hand_over_a_result_its_consumer_can_use.md) | Context Intelligence | Shapes the result for its reader and checks provenance and privacy before it leaves. | `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml` | MIT, declared | |
| [plan_and_split_work_with_explicit_joins](bodies/plan_and_split_work_with_explicit_joins.md) | Context Intelligence | Splits work into checkable parts with written dependencies and joined authority. | `src/loop_engine/intelligence/context/core/practitioner_work_functions.yaml` | MIT, declared | |
| [ask_a_model_with_a_declared_answer_shape](bodies/ask_a_model_with_a_declared_answer_shape.md) | Context Intelligence | Makes model replies parseable by contract and question variation reproducible. | `src/loop_engine/strings/question_engine.py` | MIT, declared | |
| [questions_to_ask_before_starting_work](bodies/questions_to_ask_before_starting_work.md) | Context Intelligence | Thirteen short questions that find a wrong goal before effort is spent. | `src/loop_engine/strings/question_engine.py` | MIT, declared | |
| [decide_whether_a_step_needs_a_model](bodies/decide_whether_a_step_needs_a_model.md) | Context Intelligence | Directly addresses model cost: a function where a function is enough, a model for judgment. | `src/loop_engine/strings/question_engine.py` | MIT, declared | |
| [look_for_structure_the_model_missed](bodies/look_for_structure_the_model_missed.md) | Context Intelligence | Expert questions about residuals and hidden structure, each with the analysis that answers it. | `src/loop_engine/strings/interrogation.py` | MIT, declared | |
| [check_that_a_result_is_stable_and_generalizes](bodies/check_that_a_result_is_stable_and_generalizes.md) | Context Intelligence | Separates a real improvement from seed noise and tests a result beyond its sample. | `src/loop_engine/strings/interrogation.py` | MIT, declared | |
| [audit_data_splits_for_errors_and_leakage](bodies/audit_data_splits_for_errors_and_leakage.md) | Context Intelligence | Finds the leakage that produces scores that are too good. | `src/loop_engine/strings/interrogation.py` | MIT, declared | |
| [analyse_errors_by_segment_and_cluster](bodies/analyse_errors_by_segment_and_cluster.md) | Context Intelligence | Finds the one fix that removes the largest group of failures. | `src/loop_engine/strings/interrogation.py` | MIT, declared | |
| [review_an_accepted_solution_adversarially](bodies/review_an_accepted_solution_adversarially.md) | Context Intelligence | Finds the unknown that acceptance silently relied on, and turns lessons into candidates. | `src/loop_engine/strings/interrogation.py` | MIT, declared | |
| [test_driven_change_red_green_refactor](bodies/test_driven_change_red_green_refactor.md) | Context Intelligence | A bounded test driven change with exact evidence and no widening of permissions. | `src/loop_engine/skills/software-tdd-red-green-refactor/SKILL.md` | MIT, declared | |
| [package_one_skill_for_two_coding_harnesses](bodies/package_one_skill_for_two_coding_harnesses.md) | Context Intelligence | A working pattern for shipping the same skills to Claude Code and Codex without drift. | `integrations/README.md` | MIT, declared | |
| [check_a_table_join_before_trusting_it](bodies/check_a_table_join_before_trusting_it.md) | Context Intelligence | Catches joins that multiply or drop rows. Model generated source, so the licence needs review. | `src/loop_engine/governance/candidates/part-00000.jsonl` | unknown, needs review | |
| [make_a_data_pipeline_safe_to_run_again](bodies/make_a_data_pipeline_safe_to_run_again.md) | Context Intelligence | Makes reruns and backfills safe. Model generated source, so the licence needs review. | `src/loop_engine/governance/candidates/part-00000.jsonl` | unknown, needs review | |
