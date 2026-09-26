# Step function tag precision, September 26, 2026

This record measures the `step_function_rules` engine behind the
`library_step_function_tagging` slot (roadmap S-6.206) on real packages, judges a
fixed sample by hand, changes the rules where the sample shows a clear pattern,
and measures the same sample again. No served release carries the tags yet, so
the rules were run directly on the approved packages of one reviewed folder.

## What was measured

- Population: the 1,586 approved items of
  `/home/username/baltor-library/reviewed-2026-09-26-10/imported` (1,631 items,
  45 rejected). Package files were read from that folder and never copied into
  this repository. Titles came from the review export the folder was written
  from, `review-batches/2026-09-26-10`, because the reviewed catalogue writer
  names each item by its export title.
- Material: built exactly as `tools/write_reviewed_catalogue.py` builds it in
  `item_attributes`: the served kind, the harness kind, the title, the purpose,
  the entry text (the primary file, bounded to 6,000 characters) and the file
  roles.
- Tool: `tools/measure_step_function_tags.py`, added in this change. It writes
  the distribution, one line per item with tags and evidence, and a sample laid
  out for reading. With `--identities` it re-measures an earlier sample.
- Sample: 100 tagged items drawn with `random.Random(20260926)` from the items
  tagged under rules 1.0.0, sorted by identity. One judge (Claude Fable 5.1)
  read each item's title, purpose and the head of its entry text and judged
  every tag as correct, wrong or arguable, and noted functions the item clearly
  supports that the rules missed. `sample-verdicts.json` holds the identities,
  the verdicts, the evidence words and a note of at most ten quoted words per
  item.

Precision here is strict when only correct counts, and lenient when arguable
counts too. The recall gap counts items with at least one clearly supported
function that carries no tag; it is a lower bound, because the judge only noted
misses that were obvious from the text head.

## Before: rules 1.0.0

Distribution over the 1,586 approved items:

| Measure | Value |
|---|---|
| Tagged items | 1,481 (93.4 percent) |
| Untagged items | 105 (30 plugin manifests, 27 skills, 18 marketplaces, 11 commands, 8 contract schemas, 7 instruction files, 3 rules, 1 subagent) |
| Items with four tags | 909 |
| Items per function | acting 1,182; building 719; verification 556; analysis 527; writing 403; planning 337; operating 320; reviewing 285; reasoning 279; research 213 |

The top body words that drove acting were `command` (327 items), `apply` (252),
`run` (246), `cli` (209), `commands` (197) and `tools` (120). Operating was
driven by `ci` (89), `release` (42), `deploy` (39), `cd` (34) and `pipeline`
(34). The full lists are in `sample-verdicts.json` under
`before.distribution.top_words_per_function`.

Sample verdicts, 320 tags on 100 items:

| Function | Tags | Correct | Wrong | Arguable | Strict | Lenient |
|---|---|---|---|---|---|---|
| acting | 77 | 33 | 30 | 14 | 0.43 | 0.61 |
| analysis | 37 | 21 | 10 | 6 | 0.57 | 0.73 |
| building | 50 | 16 | 25 | 9 | 0.32 | 0.50 |
| operating | 25 | 2 | 17 | 6 | 0.08 | 0.32 |
| planning | 23 | 7 | 11 | 5 | 0.30 | 0.52 |
| reasoning | 16 | 7 | 3 | 6 | 0.44 | 0.81 |
| research | 12 | 7 | 2 | 3 | 0.58 | 0.83 |
| reviewing | 13 | 5 | 7 | 1 | 0.38 | 0.46 |
| verification | 35 | 23 | 4 | 8 | 0.66 | 0.89 |
| writing | 32 | 14 | 15 | 3 | 0.44 | 0.53 |
| all | 320 | 135 | 124 | 61 | 0.42 | 0.61 |

By evidence source: tags with a word in the name or purpose were correct 89 of
163 times (0.55 strict, 0.74 lenient); tags from body words only were correct
43 of 154 times (0.28 strict, 0.47 lenient); the three tags from a file role or
harness kind were all correct.

Recall gap before: 32 of 100 items had a clearly supported function without a
tag, 35 misses in all: writing 9, reviewing 7, analysis 6, verification 3,
operating 3, building 2, research 2, acting 1, planning 1, reasoning 1. Writing
was missed on items that produce a document (a persona, a PRD, a PR
description, social content, a postmortem). Reviewing was missed when `audit`
in the purpose scored two but lost the four-tag cut to body-only functions
that come earlier in the vocabulary.

The ten most misleading words. The count is the number of wrong tags in the
sample whose evidence included the word, beside the correct tags it also
supported:

| Function | Word | Wrong | Correct | Pattern |
|---|---|---|---|---|
| acting | apply | 11 | 7 | "apply the template", "apply the rules" |
| building | create | 11 | 7 | creating documents, personas, replies, PRs |
| acting | command | 10 | 10 | a command file naming itself |
| building | build | 9 | 11 | "build a table", build failures that are checked |
| acting | run | 9 | 14 | "run by the agent", read-only items that say run |
| building | generate | 8 | 4 | generating documents and replies |
| building | implementation | 7 | 2 | "Do NOT load for: implementation" |
| operating | pipeline | 6 | 0 | planning, triage, evaluation and LLM pipelines |
| planning | plan | 6 | 5 | PLAN.md read as an input |
| acting | applies | 5 | 1 | "the rule applies" |

Close behind with five wrong each: `report`, `summary` and `docs` (writing) and
`scope` (planning). Two Polish items were tagged operating from `ci`, which is
a Polish pronoun.

## Changes made in rules 1.1.0

Each change follows a pattern the sample showed, and each has a known-wrong
check in `src/loop_engine/core/library_ingestion/step_function_checks.py`
with a `removed_` control that fails when the change is reverted.

1. Body words alone need four distinct matches (`BODY_ONLY_MINIMUM = 4`). A
   word in the name or purpose, or a file role, still suffices on its own. The
   simulation on the judged sample tried three first: it removed 41 wrong and
   19 correct tags but admitted 24 body-only tags with three words of which
   about nine looked right. Four removed more wrong tags and admitted fewer.
   Removing body-only tags entirely gave the highest precision on kept tags
   (0.61 strict) but left 20 of the 100 sample items untagged and lost 43
   correct tags; not taken. Checks:
   `body_words_alone_need_four_distinct_matches_but_one_purpose_word_suffices`,
   `removed_body_only_minimum_tags_three_incidental_body_words`.
2. Among equal scores a function with name, purpose or role evidence ranks
   above one with body words only (`HEADLINE_FIRST`). This keeps `audit` in a
   purpose within the four tags. Checks:
   `name_or_purpose_evidence_outranks_body_words_at_equal_score`,
   `removed_headline_first_drops_the_audit_tag_behind_four_body_only_functions`.
3. Words dropped: `apply`, `applies` (acting); `ci`, `cd`, `pipeline`,
   `pipelines`, `alert`, `alerts`, `infrastructure`, `infra` (operating);
   `create`, `creates`, `creating`, `generate`, `generates`, `generating`,
   `generator` (building); `approve`, `approval`, `pull request`,
   `pull requests` (reviewing). Each supported at least two wrong tags and at
   most one correct tag in the sample, or, for `apply` and `create`, wrong tags
   well above correct ones on a generic verb. `command`, `run`, `build`,
   `check` and `test` were kept: they drove as many correct tags as wrong ones.
   Checks: `dropped_words_no_longer_score_their_function`,
   `removed_word_drops_score_apply_pipeline_create_and_pull_request_again`.
4. Words added: `implementing`, `coding` (building); `inspecting`,
   `diagnosing`, `investigating`, `measuring`, `comparing`, `evaluating`
   (analysis); `verifying`, `validating` (verification); `deploying`, `ci/cd`,
   `continuous integration`, `continuous delivery`, `continuous deployment`
   (operating); `deciding`, `judging`, `weighing` (reasoning); `authoring`,
   `summarizing` (writing). The sample had "Use when implementing multiplayer"
   with no building tag and "inspecting janitor status, diagnosing why
   memories are decaying" with no analysis tag. Checks:
   `added_ing_forms_tag_their_function_from_the_purpose`,
   `removed_added_words_leave_implementing_and_diagnosing_untagged`.
5. The engine version is 1.1.0, `describe()` reports `body_only_minimum`, and
   the evidence of a body-only tag lists all four words.

The suite ran with 17 of 17 checks passing (11 before this change).
`tools.test_write_reviewed_catalogue_imported` passed its 3 tests: the fixture
review skill is still tagged `["reviewing"]` and the tag still reaches the
bundle line.

## After: rules 1.1.0 on the same sample and population

Distribution over the same 1,586 approved items:

| Measure | Before | After |
|---|---|---|
| Tagged items | 1,481 | 1,312 (82.7 percent) |
| Untagged items | 105 | 274 (68 plugin manifests, 60 skills, 51 commands, 39 marketplaces, 22 instruction files, 17 subagents, 9 rules, 8 contract schemas) |
| Items with four tags | 909 | 331 |
| acting | 1,182 | 779 |
| analysis | 527 | 314 |
| building | 719 | 315 |
| operating | 320 | 111 |
| planning | 337 | 216 |
| reasoning | 279 | 185 |
| research | 213 | 159 |
| reviewing | 285 | 246 |
| verification | 556 | 512 |
| writing | 403 | 378 |

Sample verdicts on the same 100 identities. Kept tags keep their verdict, the
32 tags the new rules added were judged (11 correct, 8 arguable, 13 wrong),
and the 23 correct tags the new rules removed count as misses:

| Function | Tags before, after | Strict before, after | Lenient before, after |
|---|---|---|---|
| acting | 77, 44 | 0.43, 0.52 | 0.61, 0.66 |
| analysis | 37, 20 | 0.57, 0.70 | 0.73, 0.95 |
| building | 50, 21 | 0.32, 0.48 | 0.50, 0.67 |
| operating | 25, 6 | 0.08, 0.33 | 0.32, 0.67 |
| planning | 23, 18 | 0.30, 0.44 | 0.52, 0.67 |
| reasoning | 16, 13 | 0.44, 0.46 | 0.81, 0.85 |
| research | 12, 12 | 0.58, 0.50 | 0.83, 0.67 |
| reviewing | 13, 11 | 0.38, 0.64 | 0.46, 0.73 |
| verification | 35, 36 | 0.66, 0.53 | 0.89, 0.78 |
| writing | 32, 31 | 0.44, 0.55 | 0.53, 0.68 |
| all | 320, 212 | 0.42, 0.53 | 0.61, 0.73 |

Correct tags fell from 135 to 112, wrong tags from 124 to 58, arguable from 61
to 42. Body-only tags fell from 154 to 55 and are still the weak part: 17
correct, 26 wrong, 12 arguable (0.31 strict). Verification and research got
worse, because four body words such as `check`, `test`, `tests` and `verify`
still tag verification on a plan or an editing command, and `research`,
`discover`, `sources` tag research on a plan interview.

Recall gap after: 44 of 100 items with a clearly supported function untagged,
58 misses: analysis 13, acting 11, building 8, verification 7, writing 6,
reviewing 5, operating 3, research 3, reasoning 2. The increase is the price of
the body-only rule: instruction files and manifests with a placeholder purpose
such as "instruction_file X" lose correct acting and building tags that their
body carried, and a dropped word such as `create` no longer helps an item that
does generate code.

## Limits

- One judge, one pass, reading at most the first 1,400 characters of each
  entry text plus a quote around every evidence word. Another judge would
  disagree on some arguable rows.
- 100 items from one reviewed folder of imported packages; native
  model-authored items were not sampled.
- The vocabulary is English. Polish, Spanish, Chinese, Japanese and Korean
  items in the sample were tagged from incidental English words or not at all;
  a Spanish incident protocol that writes a postmortem has no writing tag.
- The population numbers count rule output, not correctness; only the sample
  was judged.

## Files

- `README.md`: this record.
- `sample-verdicts.json`: the sample identities, every tag with its verdict and
  evidence words before and after, the per-function precision, the evidence
  source split, the recall gap, the twenty most misleading words, and the
  population distributions with the top eight words per function.
- Scratch outputs (distribution, one line per item, the reading layout) were
  written under `$HOME/.le-ci-tmp/tag-precision/` and are not part of the
  repository.

## Current and planned behaviour

Current: rules 1.1.0 are what `tools/write_reviewed_catalogue.py` will use for
the next reviewed folder. No served release carries step function tags yet, so
nothing live changed with this record.

Planned, not done here: a text model engine behind the same edge, which the
slot declaration already allows; a second judge on the same sample to measure
agreement; a vocabulary for the non-English items; and a measurement after the
first release that carries the tags, on the served lines rather than on the
reviewed folder.
