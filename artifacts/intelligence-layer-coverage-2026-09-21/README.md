# What the four intelligence layers hold, and the first tranche that fills two

Kind: measurement, decision record and candidate material. Date: 2026-09-21.
Base revision: `6a489b2eff78d1e7251d65e143edbd89f7250c4e`.

Nothing in this folder is approved, published or granted to a tenant. It adds
no item to the built-in package population, changes no host manifest and
edits no other agent's catalogue.

## Summary

Two of the four persistent intelligence layers hold nothing on a fresh
installation. The search reports both of them as `unqueried` and then answers
the question anyway, with ranked material from the other two layers and no
signal that the material is unrelated. This folder measures that, decides what
is missing, adds a first tranche of twenty-four candidate items to the two
empty layers, and records what the tranche still does not fix: a search with
no score floor answers a question it has no material for, whether the layer is
empty or full.

## 1. What each layer holds today

Measured by `measure.py`, which builds the real catalogue with an empty runs
directory and an empty guidance file, so the numbers are the built-in
population rather than this workstation's saved history.

```bash
PYTHONPATH=src python \
  artifacts/intelligence-layer-coverage-2026-09-21/measure.py \
  --report artifacts/intelligence-layer-coverage-2026-09-21/measurement-2026-09-21.json
```

| Layer | Items before | Items after | Where it lives |
|---|---:|---:|---|
| Context Intelligence | 441 | 441 | `src/loop_engine/intelligence/context/`, built by `core/context_catalog.py` |
| Code Intelligence | 81 | 81 | `src/loop_engine/code_nodes/` as 66 module references, plus 15 templates from `core/code_intelligence_assets.py` |
| Runtime History and Solution Intelligence | 0 | 14 | Built only from saved run directories under the runs directory. Nothing ships. |
| User Feedback Intelligence | 0 | 10 | Built only from a saved guidance file read by `AdviceStore`. Nothing ships. |
| Total | 522 | 546 | |

The "after" column is this folder's candidate pack added to the measurement,
not a change to the shipped population.

Two earlier numbers need care. The installed example
`examples/09_search_the_intelligence_layers/run.py` prints `1` for each of the
two lower layers. It writes one run and one piece of guidance itself, at the
start of the example, so those two items are the example's own and not part of
the package. The starter catalogue in `examples/29_intelligence_service/`
holds 49 items, all of them Context Intelligence (28) or Code Intelligence
(21); its own review sheet records `0` for the other two layers.

## 2. What a search returns today

The exact search, from `measure.py`, is `query_intelligence` with
`mode="lexical"`, `top_n=3` and `include_candidates=True`, over the built
catalogue. The third parameter decides whether a candidate item may be ranked
at all, and it is not the service default. Section 6 records what changes
without it. Five customer questions were run. The first four are aimed at the
two empty layers.

| Question | What came back before |
|---|---|
| "a previous run of this same import that failed and how it was repaired" | Three Context Intelligence question templates: `qform.repetition_circuit_breaker`, `qform.analogy_probe`, `qform.context_boundary_probe` |
| "what went wrong last time and what fixed it" | Three Context Intelligence question templates: `qform.acceptance_inversion`, `qform.worst_way`, `qform.reversibility` |
| "what guidance did the user give about dropping rows" | `code.module.run_analytics`, `looptmpl.custom_user_supplied`, `qform.smallest_first_step` |
| "a standing instruction about weakening a check to make the build pass" | `qform.smallest_first_step`, `improve.mining.0`, `qform.cheapest_check` |
| "a reusable solution for deduplicating customer records" | `code.module.solution_records`, `qform.train_or_call`, `qform.analogy_probe` |

This is the finding, stated as the measurement supports it. The two layers
hold nothing, and the response says so: every one of those five answers
carries

```json
"unqueried": ["runtime_history_solution_intelligence", "user_feedback_intelligence"]
```

and the same two names in `unqueried_public`. The hosted boundary reports
them too. `saas_routes.intelligence_surface("all", need=..., layer_records=...)`
returns both fields beside the same wrong-layer hits. This is designed
behaviour, written into the `query_intelligence` docstring in
`src/loop_engine/core/intelligence_layers.py`: missing layers are reported as
unqueried, never silently skipped.

What is missing is material, not a signal. The search still answers. It
answers a question about what happened last time with a template for asking a
question, and a question about what a person instructed with a module
reference, and it ranks those hits out of the two layers that do hold
something without having to be asked for them. Nothing in the response marks
a hit as a poor match, because there is no score floor and no
no-good-match result. A harness is told which layers were empty; it is not
told that the three items it received are unrelated to what it asked.

An earlier draft of this section said a harness had "no way to tell that the
layer it asked about holds nothing." That was wrong. The reviewer disproved
it by running the same call, and the field was absent from the report only
because `searched()` kept the layer and identity of each hit and dropped the
rest. Both fields are now recorded for every answer.

The same five questions after the candidate pack is added, with the same
`include_candidates=True`:

| Question | What came back after |
|---|---|
| "a previous run of this same import that failed and how it was repaired" | `classify_a_failed_check_before_changing_the_work`, `run_the_restore_before_you_call_the_backup_a_backup`, `recorded_direction_keep_failures_as_visible_as_successes` |
| "what went wrong last time and what fixed it" | `recorded_direction_do_not_weaken_a_failing_check`, `recorded_direction_never_end_on_a_fixed_attempt_count`, `a_truthy_value_is_not_a_granted_permission` |
| "what guidance did the user give about dropping rows" | Three User Feedback Intelligence items, none of them about dropping rows |
| "a standing instruction about weakening a check to make the build pass" | `build_a_test_fixture_from_the_real_typed_object`, `classify_a_failed_check_before_changing_the_work`, `recorded_direction_build_general_mechanisms` |
| "a reusable solution for deduplicating customer records" | `code.module.solution_records`, `qform.train_or_call`, and one User Feedback item |

Read those honestly, one question at a time.

| Question | After the pack | How to read it |
|---|---|---|
| 1 | Two Runtime History items, one User Feedback item | **On target.** The question asks for a run that failed and its repair. The top two are a recorded classification of a failed check and a recorded restore exercise. |
| 2 | Two User Feedback items, one Runtime History item | **Partly on target.** All three come from the two newly filled layers, but the question asks what went wrong last time and the top two are standing guidance about failing checks and attempt counts, not a record of a run. |
| 3 | Three User Feedback items, none about dropping rows | **Still not answered.** No guidance about dropping rows exists to return. The layer is no longer empty, so `unqueried` no longer names it, and the three wrong items are better written than the three wrong items before. |
| 4 | Two Runtime History items, one User Feedback item, none of them the matching instruction | **A miss.** `recorded_direction_do_not_weaken_a_failing_check` states exactly that instruction and is not in the first three for this phrasing, although it is first for the plainer "a check is failing and i want to change it so the build goes green". |
| 5 | Unchanged in the first two places; one User Feedback item displaces the third | **Not answered, and not answerable here.** This pack holds nothing about deduplication. An unrelated User Feedback item still took a place in the first three, which is the same missing score floor as question three. |

Only question one is answered well. Questions three and five are not answered
by this tranche, and the pack does not make them answerable. On question three
the change is arguably for the worse: before, a customer asking about their
own guidance got an obviously unrelated module reference; after, they get
three confident, well-written statements of this repository's owner's
instructions. The wrong answer became more plausible. Section 3 records that
as an open gap.

The full report is in
[measurement-2026-09-21.json](measurement-2026-09-21.json). It carries four
answer sets: before and after, each at `include_candidates=True` and at the
service default of `False`, and each answer records its `unqueried`,
`unqueried_public`, excluded count and excluded reasons.

## 3. What is missing, and why

A customer connects a coding harness and asks for help with a real task. Four
things the service should be able to hand back and cannot.

| Missing | Why a customer needs it | Addressed here |
|---|---|---|
| A record of a failure and the repair that fixed it | The fifth customer problem the product exists to answer is the same mistakes appearing again. A layer that holds no failure cannot prevent a repeated one. | Yes, 9 of the 14 Runtime History items are a recorded failure, repair or the decision that classified one. |
| A recorded decision with its alternatives and its reason | A harness that cannot see why a choice was made re-argues it every run, at full model cost. | Yes, 4 items. |
| A measurement with its population and its limits | Without the population, a number becomes a claim. The layer should hand back the limits with the number. | Yes, 1 item, and it deliberately does not copy the timings out of its report. |
| Standing guidance with a scope, a strength and a timing | Guidance buried in a prompt cannot be found, consulted or responded to. The layer exists so a step can find it and record what it did about it. | Yes, 10 User Feedback items. Each states its guidance type, scope, strength and timing as a value from the owning module's closed vocabulary, not as prose that looks like one. Section 4 records the repair that made timing typed. |

Three gaps this tranche does not close, recorded rather than hidden.

1. **Reusable Solution records.** The `solution` category group of the third
   layer is for a reusable Solution specification or compiled composition. The
   catalogue builder reads only saved run directories, so it cannot load saved
   `SolutionLibrary` assets into that layer at all. That is a code gap, not a
   material gap, and it is named in
   `docs/components/intelligence-layers/README.md`. This tranche adds no
   `solution` item, because adding one would not be retrievable.
2. **A customer's own history and a customer's own guidance.** Both layers are
   designed to fill from the customer's runs and the customer's people. A
   shipped pack seeds them; it does not replace them.
3. **A search that declines to answer.** Filling a layer does not make the
   search say "nothing here matches". `query_intelligence` returns the
   `top_n` best-ranked items whatever their score, and no hit carries a
   this-is-a-poor-match signal. The branch's own measurement shows it:
   question three asks about guidance on dropping rows, no such guidance
   exists, and three unrelated User Feedback items come back ranked. Before
   the pack the same question returned three unrelated items from other
   layers. A score floor, or an explicit no-good-match result, is the
   remaining work, and nothing on this branch adds either. Until it exists,
   filling a layer raises the quality of the writing in a wrong answer
   without lowering the chance of getting one.

Nothing in this pack is wired into the shipped population, a host manifest or
a tenant grant. Today a customer asking question three still receives the
`qform.*` templates. When the pack is wired in and approved, they receive the
new items instead. Neither answer is about dropping rows.

## 4. The first tranche

Twenty-four candidate items, in [pack/](pack/). Fourteen for Runtime History
and Solution Intelligence, ten for User Feedback Intelligence. Every item is
drawn from a record that exists in this repository, and cites it.

```text
Layer coverage pack (24 candidates, 0 approved)
├── Runtime History and Solution Intelligence (14)
│   ├── decision (4)
│   ├── failure_remedy (5)
│   ├── repair (4)
│   └── measurement (1)
└── User Feedback Intelligence (10)
    ├── owner_constraint (5)
    ├── owner_instruction (3)
    ├── owner_priority (1)
    └── owner_correction (1)
```

Every item carries an immutable source identity (a repository path with the
revision appended), provenance, a licence state, a version, a typed contract,
declared effects and a digest measured from its body. The full table, and
what a reviewer should challenge first, are in the
[review sheet](pack/REVIEW.md).

Each of the ten User Feedback bodies states its guidance in a small table
whose Guidance type, Scope, Strength and Timing are values from the owning
module's closed vocabularies, `user_feedback_intelligence.GUIDANCE_TYPES`,
`SCOPES`, `STRENGTHS` and `TIMINGS`. Timing was free prose in all ten until
2026-09-21; the store refuses an unknown timing, so a table that looked typed
carried one field the store would have rejected. The prose is kept on a
separate "Timing in the recorded words" row, and a check now validates all
four rows against the module constants. Those ten bodies are `item_version`
`1.1.0` for that change. The fourteen Runtime History bodies did not change
and stay at `1.0.0`.

### Candidate or approved

All twenty-four are **candidates**. None is approved.

The only thing that has judged them is the mechanical check in
`tools/test_intelligence_layer_coverage.py`. It verifies the record contracts,
that every digest is the SHA-256 of its body recomputed independently, that
every licence is one the default host policy accepts, that both layers are
covered, that every item declares a version and no effects, that no item
claims an approval, and that thirty-four plain customer queries each find
their item. Two rules deserve their exact wording.

**Cited sources are resolved at the recorded revision, not in the working
tree.** `pack/source-tree.json` records the git object name of each of the
eighteen distinct cited paths at
`6a489b2eff78d1e7251d65e143edbd89f7250c4e`, and the provenance rule resolves a
citation there. An earlier version of the rule asked whether
`ROOT / source` was a file, which is existence in whatever tree the check runs
in: a file added after that revision would have passed, and a file moved away
from it would have failed for a reason unrelated to the item. A separate
check reads the same eighteen paths back out of git and compares the object
names, so the listing is not the pack's own word for itself. Without git, or
without that revision in the clone, that check reports the listing as
unconfirmed instead of passing.

**The query set keeps its adversarial half.** The thirty-four queries are
twenty-four written by the author of the purposes and ten written by a
reviewer against purposes they did not write, five of which missed on their
first run. The reviewer queries carry the evidence, so the check holds a
floor of ten of them, a floor of five rows still marked
`missed_before_purpose_was_widened`, and the floor of thirty overall. Deleting
nine reviewer queries, or dropping the record of which ones first missed, now
fails the check rather than leaving a green suite behind a weaker claim.

A passing check is not an approval. Approval means a person who did not write
the item decides against written criteria and the record names them.

## 5. Checks run

| Command | Result |
|---|---|
| `PYTHONPATH=src:tools python -m unittest tools.test_intelligence_layer_coverage` | 17 tests, OK |
| `PYTHONPATH=src python .../pack/build.py` | 24 items, 18 cited sources, source tree recorded, no stale rows |
| `PYTHONPATH=src python .../measure.py --report ...` | before 522 items, after 546, four answer sets written |
| `PYTHONPATH=src python tools/stage_intelligence_candidates.py ... --namespace layer.coverage` | 24 records committed to an isolated database. Its report records `normal_search_hits 0` and `normal_search_excluded 24`, the same exclusion the service default produces, and every item found by its own review probe |
| `python -m loop_engine --conformance` | all gates pass |
| hardcoding audit against the recorded baseline | exit 0, no new high finding |

Each of the ten rules in the check has its known-wrong cases, thirty-seven in
all, counted from `KNOWN_WRONG` rather than by hand. The earlier count of
twenty-one in this section was wrong when it was written; the table then held
twenty-five. The check fails if a rule stops reporting one. Neutering any rule
to return nothing leaves every one of its own cases unreported, so the named
`test_<rule>_rejects_its_known_wrong_cases` fails rather than passing quietly.

Six cases were also run against the real files on disk, each applied, the
whole check run, and the file restored. The rule column is what `problems()`
named; the test column is what the run failed.

| Known-wrong case applied to the files | Rule that named it | Tests that failed |
|---|---|---|
| The Timing row goes back to the free prose it held before | `guidance_fields_use_the_engine_vocabularies`, `digest_matches_its_body`, `specification_text_equals_its_body` | `test_the_shipped_pack_reports_no_problem`, `test_the_pack_is_not_stale_against_its_bodies` |
| The Scope row carries `company`, which `SCOPES` does not hold | the same three | the same two |
| A cited path is removed from `source-tree.json` | `provenance_names_a_revision_and_real_repository_sources` | `test_the_shipped_pack_reports_no_problem`, `test_the_pack_is_not_stale_against_its_bodies` |
| An object name of forty zeroes is planted in `source-tree.json` | none; a planted name is only visible against git | `test_the_recorded_source_tree_is_what_git_holds_at_that_revision`, `test_the_pack_is_not_stale_against_its_bodies` |
| The ten reviewer-written queries are deleted and the count padded to thirty with the author's own | `the_query_set_keeps_its_adversarial_record` | `test_the_shipped_pack_reports_no_problem` |
| The record of which queries first missed is deleted | `the_query_set_keeps_its_adversarial_record` | `test_the_shipped_pack_reports_no_problem` |

An earlier draft of that fourth row also named
`test_a_planted_object_name_is_reported_against_git` among the failures. It
does not fail, and the re-run above is where that was caught. That test plants
the same forty zeroes into its own in-memory copy and asserts that git reports
the path, so it goes on passing when the file on disk already carries the
planted name. It is a self-contained known-wrong case for the git comparison,
not a detector of this on-disk edit. The row now records the two tests that
did fail.

Earlier, two more were run the same way: appending a line to a body without
rebuilding was reported by `digest_matches_its_body` and
`specification_text_equals_its_body`, and setting one item to `registered`
with an approval naming its own author was reported by
`every_item_is_an_unapproved_candidate`.

## 6. Limits

- **The after table is measured with `include_candidates=True`, which the
  service does not use.** `IntelligenceSearchRequest.include_candidates`
  defaults to `False`, and `saas_routes.intelligence_surface` leaves it there,
  so every hosted call today runs with `False`. At `False` all twenty-four
  pack items are excluded with the reason
  `candidate_or_inactive_requires_review`, and every after answer is identical
  to its before answer, for all five questions. The staging run reports the
  same thing as `normal_search_hits 0 / normal_search_excluded 24`. Both sets
  are in `measurement-2026-09-21.json` as `answers` and
  `answers_at_the_service_default`. On the shipped retrieval path this pack
  changes nothing at all until an independent approval moves the items out of
  candidate state. That is the exclusion working as designed, not a defect.
  The same set carries one more measured fact worth stating plainly: at the
  service default the after answers still report both layers in `unqueried`
  and `unqueried_public`, because every item that would have filled them was
  excluded. Adding twenty-four candidates does not make either layer count as
  queried on the path the service actually uses.
- **No relevance floor exists, before or after.** The search returns the three
  best-ranked items whatever their score. Section 3, gap three.
- Lexical search over a 24-item pack. This is a coverage measurement and a
  smoke check, not a relevance benchmark and not evidence that any item helped
  a task.
- No model was called. No network was reached. No hosted service was changed.
- Five of the ten adversarial reviewer queries missed on their first run, and
  two of those returned nothing at all. The purposes were widened with the
  customer's words and the queries were left unchanged. The original misses
  are recorded in `pack/search-queries.json`, and the check now holds a floor
  on how many of those records must remain.
- Offered, fetched, loaded, used and verified are separate facts. This work
  establishes that the items can be **offered** by a search **when candidates
  are explicitly admitted**, and that their bodies can be **fetched** by
  digest. It establishes nothing beyond that.
