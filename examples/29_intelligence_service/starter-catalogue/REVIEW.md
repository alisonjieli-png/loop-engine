# Starter catalogue review sheet

Kind: review sheet for the owner. Every item in this folder is a candidate.
No item has been approved, published, granted to a tenant or added to a host
manifest. The approval column below is empty on purpose.

## What this folder holds

The folder holds 123 skill-sized items that a customer's coding harness could
load for one step of a task. Each item is one Markdown body of 150 to 600
words with the same parts: when to use it, the steps, the checks, one
known-wrong example, what to record and the cited source.

```text
Starter catalogue candidates (123)
├── Context Intelligence (102)
│   ├── working methods for understanding, deciding, verifying and handing over
│   ├── test design, debugging, and code review for correctness and security
│   ├── dependencies and licences, database changes, interfaces and failures
│   ├── secrets, logging, performance measurement and data validation
│   ├── prompts, model choice, acceptance criteria, releases and incidents
│   ├── briefing an agent and checking what it produced
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
| `executed-examples.json` | Every example that a Code Intelligence body quotes, with the exact call that produces it. The check runs each call against the cited module. |
| `refresh.py` | Recomputes the derived fields after a body was edited. It approves nothing and publishes nothing. |
| `REVIEW.md` | This sheet. |

## Two kinds of body, and how to tell them apart

Each item declares in `items.json` how its body relates to the file it cites.
The check refuses a body whose text disagrees with that declaration.

| Grounding in `provenance` | What it means | Closing sentence in the body |
|---|---|---|
| `restates_cited_source` | The body says what the cited file says or does. Read the file to review it. | `Compiled from revision 381efec.` |
| `general_practice_beside_cited_source` | The body is ordinary engineering practice written here in its own words. The cited file is a related practice in this repository, not the source of the words. | `Written for this catalogue at revision 381efec.` |

A body of the second kind also carries this sentence, and a body of the first
kind must not: "The steps above are ordinary engineering practice, written for
this catalogue in its own words."

## Current state and planned steps

Current state on 21 September 2026 at revision `381efec`:

- The takeover checkpoint (`docs/context/TAKEOVER-CHECKPOINT-2026-09-20.md`) records that the hosted service serves one diagnostic record. The author of this folder did not observe the live service. No item here is in a host manifest in this repository.
- The items exist only in this folder. The staging tool accepts one bounded population of at most 50 rows, so the check stages this catalogue as 3 populations taken in file order, and every row is accepted as a candidate in an isolated database.
- Every item declares a licence. 2 record `unknown` with the state `needs_review`, which a host's list of accepted licences is expected to refuse.

Planned steps, not done here and not authorized by this folder:

- The owner, or the independent review the owner delegated this to, approves or rejects each item in the table below.
- A later change adds each approved item to the host manifest with the approval reference and the tenant grants.
- A release from a committed revision serves them.

## How to review one item

1. Open the body from the first column and read it as a customer would.
2. Check the grounding in `items.json`. For a body that restates its source, open the cited file at revision `381efec` and check that the body says what the source says or does. For a body of general practice, judge the practice itself and check that the one sentence about the cited file is true.
3. Check the licence state and the declared effects in `items.json`.
4. Write the decision in the approval column: approved with a name and a date, rejected with the reason, or the change that is needed.
5. After any edit of a body, run the refresh tool and then the checks. Run these commands from the repository root. The first command only reports stale items. The second rewrites the derived fields.

```bash
PYTHONPATH=src python examples/29_intelligence_service/starter-catalogue/refresh.py
PYTHONPATH=src python examples/29_intelligence_service/starter-catalogue/refresh.py --write
PYTHONPATH=src:tools python -m unittest tools.test_starter_catalogue
```

To look at the candidates in an isolated review catalogue, stage them with the
existing tool. It needs three new output paths and writes nothing else. It
accepts at most 50 rows in one run, so split `specifications.json` into
populations of that size before staging, or stage the population you want to
read.

```bash
PYTHONPATH=src python tools/stage_intelligence_candidates.py \
  --specifications ONE_POPULATION_FILE \
  --database NEW_DATABASE_PATH --namespace starter.catalogue \
  --authorize-isolated-staging --export NEW_EXPORT_PATH --report NEW_REPORT_PATH
```

The existing host manifest reader accepts an approved item in this form: the
`reference` object from `items.json`, the `body_path`, an `approval_ref` that
names the approval decision, and the tenant grants. Do not copy the lifecycle
tag without a decision. Every reference here carries the tag
`lifecycle: candidate`. When all 123 references are loaded unchanged, a request
that names `lifecycle: qualified` is offered 0 items and 123 are withheld. The
value of the tag after approval is an open decision for the later manifest
change. The reader binds an item by its identity, digest, source layer and
source reference, so the tag can change without a new digest. The
reader checks the size and the digest of the body again. Do not add an item
to a host manifest before it is approved. The reader treats every manifest
entry as approved.

## Layers without items

Runtime History and Solution Intelligence holds records of real runs with
verified outcomes. User Feedback Intelligence holds feedback from real
people. The private beta has produced neither yet. An item written for those
layers today would be invented evidence, so this catalogue has none. The first
real items can be compiled after invited users have run tasks and given
feedback, from records that name the exact run or the exact statement.

## What the owner should know before approving

- Authoring. An assistant (Claude Code) wrote every body. 49 of them restate the cited repository sources; the quoted examples in those bodies were run against the code at revision `381efec`, and the self tests of the nine cited source modules pass at that revision (113 checks). An adversarial review then found one statement that the code does not have: the capitalisation body said that a mixed case value such as `iPhone` keeps its capitals, and the code rewrites it to `Iphone` at 0.95 and applies that. The body was corrected from the executed behaviour, and 53 quoted examples over 12 items now live in `executed-examples.json`, where a check runs each call and compares the result with the words of the body. The other 74 bodies are ordinary engineering practice written here in plain words; they quote no code and no other project, and each names one related file in this repository with one sentence about what that file does. The scenarios in the known-wrong examples are illustrations written for this catalogue. No independent person has reviewed any body.
- Licence. 121 items are compiled from, or written beside, material authored in this repository, which its `LICENSE` file places under MIT. 2 items are compiled from statements that a language model generated during work in this repository. Their licence is recorded as `unknown` with the state `needs_review`, and their provenance names the generator and the digests of the eight source rows. The task for this catalogue allowed at most eight such rows, and eight are used.
- Declared effects. The rule: an item declares every effect that one of its steps tells the reader to perform on the reader's own machine, which means reading or listing files, writing files, starting a command or using the network. A method that only transforms values it was given declares nothing. A step that asks a question, or that names an analysis without telling the reader how to run it, declares nothing, and a harness that chooses to run such an analysis needs its own authority for it. An item without effects declares an empty list. 86 items declare effects under this rule, and `items.json` names them one by one. For example, the environment item declares `reads_fs`, `network` and `spawns_process`, because its steps list files, measure tool versions with commands and test network access; the pipeline item declares `reads_fs`, because its second step reads the statements of an existing pipeline. The effect names are the ones the engine defines: `pure`, `reads_fs`, `writes_fs`, `reads_secret`, `network` and `spawns_process`. A write to a database table has no name among them, so the pipeline item records that write in its steps and declares no effect for it. The service lists an item only when the request states every effect that the item declares, and the current web and protocol surfaces send no effects. Those 86 items would be withheld today. That needs a decision in the engine. The declared effects were not reduced to avoid it.
- Lifecycle tag. Every reference carries the tag `lifecycle: candidate`. A request that names no lifecycle still matches a tagged item, so the tag alone does not hide a candidate. Approval and the host manifest remain the gate.
- Vocabulary. The bodies use no internal runtime vocabulary. The cited paths contain the package name `loop_engine`, and the integration item cites paths that contain the command name of this repository. The check removes cited source paths before it looks for forbidden words.
- Search. The purpose of each item is the text that the hosted search reads. Every one of the 123 title probes of the staging tool finds its own item among the first three. The file `search-queries.json` keeps 105 plain customer queries, and the check requires that each one finds its item among the first three results of a local emulation of the hosted search. Of those, a reviewer wrote 15 unseen queries against the first 49 purposes and 10 found their item; the five that missed are kept, and synonyms such as dedupe, skewed, umlauts, unreachable and ask the user were added to the purposes until they passed. The author wrote 74 more queries for the new items before running any of them; 20 missed on the first run, and the purposes were given the words those queries used until every one passed. No query was changed to fit a purpose. Because the purposes were adjusted to the queries, this is a smoke check and not a relevance benchmark.
- Size. The staging tool accepts at most 50 rows in one population. This catalogue holds 123 rows and is staged as 3 populations.
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
| [write_a_regression_test_that_pins_a_defect](bodies/write_a_regression_test_that_pins_a_defect.md) | Context Intelligence | Makes a repaired defect stay repaired. The test is seen to fail before the repair. | `src/loop_engine/core/independent_failure_review.py` | MIT, declared | |
| [choose_test_cases_from_boundaries_and_classes](bodies/choose_test_cases_from_boundaries_and_classes.md) | Context Intelligence | Replaces guesswork about test inputs with a small covering set that includes the limits. | `src/loop_engine/core/evaluation_suite.py` | MIT, declared | |
| [isolate_a_flaky_test_before_trusting_it](bodies/isolate_a_flaky_test_before_trusting_it.md) | Context Intelligence | Ends the habit of rerunning a suite until it is green, and names the real cause. | `src/loop_engine/core/run_validity.py` | MIT, declared | |
| [prove_a_check_can_fail_when_the_behaviour_is_removed](bodies/prove_a_check_can_fail_when_the_behaviour_is_removed.md) | Context Intelligence | Shows that a new guard can actually fail, so a passing check means something. | `src/loop_engine/core/independent_failure_review.py` | MIT, declared | |
| [reduce_a_failure_to_a_minimal_reproduction](bodies/reduce_a_failure_to_a_minimal_reproduction.md) | Context Intelligence | Produces a small shareable failing case with the private data left out. | `src/loop_engine/core/task_materials.py` | MIT, declared | |
| [bisect_a_regression_across_revisions](bodies/bisect_a_regression_across_revisions.md) | Context Intelligence | Names the change that broke something instead of arguing about it. | `src/loop_engine/core/run_validity.py` | MIT, declared | |
| [bisect_a_failure_across_inputs_and_settings](bodies/bisect_a_failure_across_inputs_and_settings.md) | Context Intelligence | Explains why the same code behaves differently in two environments. | `src/loop_engine/core/route_health.py` | MIT, declared | |
| [read_a_failure_report_and_name_the_first_wrong_value](bodies/read_a_failure_report_and_name_the_first_wrong_value.md) | Context Intelligence | Repairs the origin of a wrong value instead of the place where it surfaced. | `src/loop_engine/core/capability_rejection.py` | MIT, declared | |
| [review_a_change_for_correctness](bodies/review_a_change_for_correctness.md) | Context Intelligence | Puts correctness before style and asks for a failing input with every finding. | `src/loop_engine/strings/decision_schemas.py` | MIT, declared | |
| [review_a_change_for_what_is_missing](bodies/review_a_change_for_what_is_missing.md) | Context Intelligence | Finds the absent work, which leaves no line for a reviewer to comment on. | `src/loop_engine/strings/ask_strategies.py` | MIT, declared | |
| [review_error_paths_and_partial_failure](bodies/review_error_paths_and_partial_failure.md) | Context Intelligence | Covers the state that a half finished operation leaves behind. | `src/loop_engine/catalog/protocol.py` | MIT, declared | |
| [review_shared_state_for_ordering_defects](bodies/review_shared_state_for_ordering_defects.md) | Context Intelligence | Finds the read then write sequences that break under real traffic. | `src/loop_engine/catalog/protocol.py` | MIT, declared | |
| [review_untrusted_input_for_injection](bodies/review_untrusted_input_for_injection.md) | Context Intelligence | Follows untrusted values to the interpreter that would act on them. | `src/loop_engine/core/model_response_admission.py` | MIT, declared | |
| [review_authorisation_on_every_path](bodies/review_authorisation_on_every_path.md) | Context Intelligence | Catches the export or search path that skips the rule the page applies. | `src/loop_engine/core/workspace_operations.py` | MIT, declared | |
| [review_file_paths_for_traversal_and_link_escape](bodies/review_file_paths_for_traversal_and_link_escape.md) | Context Intelligence | Keeps uploads, downloads and archive entries inside one folder. | `src/loop_engine/core/task_materials.py` | MIT, declared | |
| [review_generated_output_before_it_is_executed](bodies/review_generated_output_before_it_is_executed.md) | Context Intelligence | Treats code written by a model as material to inspect, not to run. | `src/loop_engine/core/service_runtime/http_entrypoint.py` | MIT, declared | |
| [review_a_new_dependency_before_adding_it](bodies/review_a_new_dependency_before_adding_it.md) | Context Intelligence | Weighs the permanent cost of a package before the first import lands. | `src/loop_engine/core/code_intelligence_assets.py` | MIT, declared | |
| [record_the_licence_of_every_bundled_component](bodies/record_the_licence_of_every_bundled_component.md) | Context Intelligence | Answers a licence question from a generated file instead of from memory. | `src/loop_engine/core/harness_intelligence.py` | MIT, declared | |
| [pin_dependency_versions_and_verify_them](bodies/pin_dependency_versions_and_verify_them.md) | Context Intelligence | Makes two builds of the same revision install the same bytes. | `src/loop_engine/core/skill_registry.py` | MIT, declared | |
| [respond_to_a_vulnerable_dependency_report](bodies/respond_to_a_vulnerable_dependency_report.md) | Context Intelligence | Turns an advisory into a defensible decision instead of a mass upgrade. | `src/loop_engine/core/asset_lifecycle.py` | MIT, declared | |
| [plan_a_schema_change_in_compatible_steps](bodies/plan_a_schema_change_in_compatible_steps.md) | Context Intelligence | Keeps old and new code working while a database shape changes. | `src/loop_engine/core/service_runtime/http_entrypoint.py` | MIT, declared | |
| [write_a_migration_that_is_safe_to_run_twice](bodies/write_a_migration_that_is_safe_to_run_twice.md) | Context Intelligence | Survives the retried deployment and the script someone ran twice. | `src/loop_engine/catalog/protocol.py` | MIT, declared | |
| [backfill_a_large_table_in_bounded_batches](bodies/backfill_a_large_table_in_bounded_batches.md) | Context Intelligence | Touches millions of rows without locking the table or filling the log. | `src/loop_engine/core/night_budget.py` | MIT, declared | |
| [rehearse_a_migration_on_a_copy_of_real_data](bodies/rehearse_a_migration_on_a_copy_of_real_data.md) | Context Intelligence | Measures the lock and the rollback before production feels them. | `src/loop_engine/code_nodes/database_copy.py` | MIT, declared | |
| [design_a_request_and_response_contract](bodies/design_a_request_and_response_contract.md) | Context Intelligence | Settles inputs, results, failures and guarantees before the handler exists. | `src/loop_engine/core/workspace_contracts.py` | MIT, declared | |
| [version_an_interface_so_older_callers_keep_working](bodies/version_an_interface_so_older_callers_keep_working.md) | Context Intelligence | Separates a compatible change from one that needs a new version. | `src/loop_engine/catalog/protocol.py` | MIT, declared | |
| [negotiate_a_supported_version_at_connection_time](bodies/negotiate_a_supported_version_at_connection_time.md) | Context Intelligence | Finds a mismatch at the handshake rather than in the middle of the work. | `src/loop_engine/core/template_negotiation.py` | MIT, declared | |
| [return_errors_a_caller_can_act_on](bodies/return_errors_a_caller_can_act_on.md) | Context Intelligence | Gives a caller a stable code, a remedy and a reason to retry or not. | `src/loop_engine/core/model_token_preflight.py` | MIT, declared | |
| [bound_a_list_endpoint_with_paging_and_limits](bodies/bound_a_list_endpoint_with_paging_and_limits.md) | Context Intelligence | Stops one request from asking for unbounded work, data or time. | `src/loop_engine/core/service_api.py` | MIT, declared | |
| [classify_a_failure_before_deciding_to_retry](bodies/classify_a_failure_before_deciding_to_retry.md) | Context Intelligence | Stops a retry series against a wrong credential or a bad request. | `src/loop_engine/core/provider_failure_classes.py` | MIT, declared | |
| [retry_with_backoff_inside_a_declared_budget](bodies/retry_with_backoff_inside_a_declared_budget.md) | Context Intelligence | Keeps a recovering service from being knocked down by synchronised retries. | `src/loop_engine/core/recovery.py` | MIT, declared | |
| [make_a_write_safe_to_repeat_with_an_idempotency_key](bodies/make_a_write_safe_to_repeat_with_an_idempotency_key.md) | Context Intelligence | Prevents the second charge when a caller repeats after a timeout. | `src/loop_engine/catalog/protocol.py` | MIT, declared | |
| [set_timeouts_and_cancel_an_outbound_call](bodies/set_timeouts_and_cancel_an_outbound_call.md) | Context Intelligence | Stops one slow dependency from holding every request thread. | `src/loop_engine/core/runtime_capacity.py` | MIT, declared | |
| [keep_partial_work_when_a_long_job_is_interrupted](bodies/keep_partial_work_when_a_long_job_is_interrupted.md) | Context Intelligence | Turns a restart into lost minutes instead of a lost night. | `src/loop_engine/core/run_checkpoint.py` | MIT, declared | |
| [keep_secrets_out_of_source_and_settings](bodies/keep_secrets_out_of_source_and_settings.md) | Context Intelligence | Leaves nothing in the repository or the image for anyone to copy. | `src/loop_engine/core/service_runtime/http_entrypoint.py` | MIT, declared | |
| [scope_a_credential_to_the_smallest_permission](bodies/scope_a_credential_to_the_smallest_permission.md) | Context Intelligence | Limits what a mistaken or stolen credential can reach. | `src/loop_engine/core/credential_leases.py` | MIT, declared | |
| [rotate_a_credential_without_an_outage](bodies/rotate_a_credential_without_an_outage.md) | Context Intelligence | Replaces a key while the system keeps running, with a way back. | `src/loop_engine/core/service_api.py` | MIT, declared | |
| [respond_to_a_leaked_credential](bodies/respond_to_a_leaked_credential.md) | Context Intelligence | Withdraws the key first, before the cleanup that does not contain anything. | `src/loop_engine/core/credential_leases.py` | MIT, declared | |
| [write_a_log_line_that_is_safe_to_share](bodies/write_a_log_line_that_is_safe_to_share.md) | Context Intelligence | Gives a reader something to act on without exposing anything. | `src/loop_engine/core/otel_export.py` | MIT, declared | |
| [remove_personal_data_before_it_reaches_a_log](bodies/remove_personal_data_before_it_reaches_a_log.md) | Context Intelligence | Stops sensitive values at the writer instead of cleaning storage later. | `src/loop_engine/core/semantic_event_history.py` | MIT, declared | |
| [choose_log_levels_and_what_belongs_in_each](bodies/choose_log_levels_and_what_belongs_in_each.md) | Context Intelligence | Keeps the error stream small enough that somebody still reads it. | `src/loop_engine/core/event_vocabulary.py` | MIT, declared | |
| [carry_one_correlation_identifier_across_services](bodies/carry_one_correlation_identifier_across_services.md) | Context Intelligence | Turns a two day cross system investigation into one search. | `src/loop_engine/core/otel_export.py` | MIT, declared | |
| [measure_before_optimising](bodies/measure_before_optimising.md) | Context Intelligence | Stops effort going into a phase that holds five percent of the time. | `src/loop_engine/core/operation_cost_capture.py` | MIT, declared | |
| [build_a_repeatable_performance_test](bodies/build_a_repeatable_performance_test.md) | Context Intelligence | Separates a real gain from the difference between two identical runs. | `src/loop_engine/core/ngram_benchmark.py` | MIT, declared | |
| [read_a_profile_and_find_the_dominant_cost](bodies/read_a_profile_and_find_the_dominant_cost.md) | Context Intelligence | Points at the caller when the callee only looks expensive. | `src/loop_engine/core/operation_cost_records.py` | MIT, declared | |
| [use_percentiles_not_averages_for_response_time](bodies/use_percentiles_not_averages_for_response_time.md) | Context Intelligence | Shows the customer waiting eleven seconds that the average hides. | `src/loop_engine/core/ngram_benchmark.py` | MIT, declared | |
| [validate_input_at_the_boundary_and_refuse_early](bodies/validate_input_at_the_boundary_and_refuse_early.md) | Context Intelligence | Turns a misspelled field from a silent default into a refusal. | `src/loop_engine/core/settings_loader.py` | MIT, declared | |
| [write_a_data_contract_for_a_table_or_feed](bodies/write_a_data_contract_for_a_table_or_feed.md) | Context Intelligence | Makes a producer side change a decision rather than a surprise. | `src/loop_engine/core/observation_expectations.py` | MIT, declared | |
| [handle_missing_values_without_inventing_them](bodies/handle_missing_values_without_inventing_them.md) | Context Intelligence | Keeps unknown apart from zero, all the way into the report. | `src/loop_engine/core/model_gateway_accounting.py` | MIT, declared | |
| [assemble_the_context_for_one_step](bodies/assemble_the_context_for_one_step.md) | Context Intelligence | Gives a step what it needs as named parts that can be changed one at a time. | `src/loop_engine/core/llm_work_packet.py` | MIT, declared | |
| [decide_what_to_leave_out_of_a_prompt](bodies/decide_what_to_leave_out_of_a_prompt.md) | Context Intelligence | Protects the instruction and the exact input when the window is full. | `src/loop_engine/core/context_budget.py` | MIT, declared | |
| [keep_instructions_and_supplied_text_apart](bodies/keep_instructions_and_supplied_text_apart.md) | Context Intelligence | Stops a sentence inside a ticket acting as an instruction to the model. | `src/loop_engine/core/prompt_elements.py` | MIT, declared | |
| [carry_earlier_decisions_forward_without_the_whole_transcript](bodies/carry_earlier_decisions_forward_without_the_whole_transcript.md) | Context Intelligence | Keeps the decision that fell out of the window, for twenty words. | `src/loop_engine/core/context_artifacts.py` | MIT, declared | |
| [choose_a_smaller_model_for_a_bounded_decision](bodies/choose_a_smaller_model_for_a_bounded_decision.md) | Context Intelligence | Directly cuts model spend on the steps that run thousands of times. | `src/loop_engine/core/typed_decision.py` | MIT, declared | |
| [compare_a_smaller_model_against_the_larger_one](bodies/compare_a_smaller_model_against_the_larger_one.md) | Context Intelligence | Makes a model switch a measured decision instead of an impression. | `src/loop_engine/core/model_demand.py` | MIT, declared | |
| [set_an_output_size_from_a_known_limit](bodies/set_an_output_size_from_a_known_limit.md) | Context Intelligence | Stops a guessed limit quietly truncating every long answer. | `src/loop_engine/core/model_capabilities.py` | MIT, declared | |
| [write_acceptance_criteria_a_reviewer_can_check](bodies/write_acceptance_criteria_a_reviewer_can_check.md) | Context Intelligence | Settles the argument about done before the work starts. | `src/loop_engine/core/independent_judgment.py` | MIT, declared | |
| [turn_a_vague_request_into_a_testable_statement](bodies/turn_a_vague_request_into_a_testable_statement.md) | Context Intelligence | Finds the real requirement behind a sentence like make it better. | `src/loop_engine/core/development_planning.py` | MIT, declared | |
| [separate_required_from_optional_in_a_request](bodies/separate_required_from_optional_in_a_request.md) | Context Intelligence | Lets a tradeoff be made without another conversation. | `src/loop_engine/core/parameter_resolution.py` | MIT, declared | |
| [run_a_release_check_list_before_deploying](bodies/run_a_release_check_list_before_deploying.md) | Context Intelligence | Catches the missing setting and the wrong revision in one minute. | `src/loop_engine/code_nodes/smoke_ladder.py` | MIT, declared | |
| [write_a_rollback_plan_before_the_release](bodies/write_a_rollback_plan_before_the_release.md) | Context Intelligence | Decides the way back while there is still time to think. | `src/loop_engine/core/recovery.py` | MIT, declared | |
| [release_behind_a_switch_that_can_be_turned_off](bodies/release_behind_a_switch_that_can_be_turned_off.md) | Context Intelligence | Makes the risky moment a setting change rather than a deployment. | `src/loop_engine/core/guardrail_intelligence.py` | MIT, declared | |
| [verify_a_release_after_it_is_live](bodies/verify_a_release_after_it_is_live.md) | Context Intelligence | Finds the silent failure that a health endpoint never shows. | `src/loop_engine/core/artifact_constraints.py` | MIT, declared | |
| [run_an_incident_review_without_blame](bodies/run_an_incident_review_without_blame.md) | Context Intelligence | Produces changes to the system instead of a finding about a person. | `src/loop_engine/core/independent_failure_review.py` | MIT, declared | |
| [build_an_incident_timeline_from_evidence](bodies/build_an_incident_timeline_from_evidence.md) | Context Intelligence | Settles what happened before anyone argues about why. | `src/loop_engine/code_nodes/run_playback.py` | MIT, declared | |
| [turn_an_incident_into_a_check_that_would_have_caught_it](bodies/turn_an_incident_into_a_check_that_would_have_caught_it.md) | Context Intelligence | Converts a lesson into something that runs without anyone remembering. | `src/loop_engine/core/heuristic_adoption.py` | MIT, declared | |
| [write_a_task_brief_for_an_agent](bodies/write_a_task_brief_for_an_agent.md) | Context Intelligence | Gives an agent a finished thing to aim at and a way to be checked. | `src/loop_engine/core/external_harness.py` | MIT, declared | |
| [state_the_permissions_and_limits_of_an_assignment](bodies/state_the_permissions_and_limits_of_an_assignment.md) | Context Intelligence | Turns an accidental action outside the task into a refusal. | `src/loop_engine/core/harness_confinement.py` | MIT, declared | |
| [split_a_large_request_into_assignable_parts](bodies/split_a_large_request_into_assignable_parts.md) | Context Intelligence | Makes each piece finishable and checkable, with the joining named. | `src/loop_engine/code_nodes/solution_graph_validation.py` | MIT, declared | |
| [supply_the_files_and_facts_an_assignment_needs](bodies/supply_the_files_and_facts_an_assignment_needs.md) | Context Intelligence | Stops an attempt being lost to a broken path or an old example. | `src/loop_engine/core/information_access.py` | MIT, declared | |
| [verify_an_agent_result_without_trusting_its_summary](bodies/verify_an_agent_result_without_trusting_its_summary.md) | Context Intelligence | Finds the skipped test behind an accurate sounding summary. | `src/loop_engine/core/independent_evidence.py` | MIT, declared | |
| [check_generated_code_against_the_request](bodies/check_generated_code_against_the_request.md) | Context Intelligence | Breaks the agreement between code and the tests the same model wrote. | `src/loop_engine/core/differential_verification.py` | MIT, declared | |
| [reproduce_the_evidence_a_report_claims](bodies/reproduce_the_evidence_a_report_claims.md) | Context Intelligence | Exposes the removed cases behind a confident improvement number. | `src/loop_engine/core/independent_verification.py` | MIT, declared | |
| [review_a_failed_check_before_repairing_the_work](bodies/review_a_failed_check_before_repairing_the_work.md) | Context Intelligence | Keeps a check from being edited until it records whatever the code does. | `src/loop_engine/strings/verification_prompts.py` | MIT, declared | |
