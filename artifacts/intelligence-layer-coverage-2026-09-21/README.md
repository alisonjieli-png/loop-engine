# What the four intelligence layers hold, and the first tranche that fills two

Kind: measurement, decision record and candidate material. Date: 2026-09-21.
Base revision: `6a489b2eff78d1e7251d65e143edbd89f7250c4e`.

Nothing in this folder is approved, published or granted to a tenant. It adds
no item to the built-in package population, changes no host manifest and
edits no other agent's catalogue.

## Summary

Two of the four persistent intelligence layers hold nothing on a fresh
installation. A customer's question aimed at either of them is answered with
material from the other two, confidently and wrongly. This folder measures
that, decides what is missing, and adds a first tranche of twenty-four
candidate items to the two empty layers.

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
`mode="lexical"`, `top_n=3`, over the built catalogue. Five customer
questions were run. The first four are aimed at the two empty layers.

| Question | What came back before |
|---|---|
| "a previous run of this same import that failed and how it was repaired" | Three Context Intelligence question templates: `qform.repetition_circuit_breaker`, `qform.analogy_probe`, `qform.context_boundary_probe` |
| "what went wrong last time and what fixed it" | Three Context Intelligence question templates: `qform.acceptance_inversion`, `qform.worst_way`, `qform.reversibility` |
| "what guidance did the user give about dropping rows" | `code.module.run_analytics`, `looptmpl.custom_user_supplied`, `qform.smallest_first_step` |
| "a standing instruction about weakening a check to make the build pass" | `qform.smallest_first_step`, `improve.mining.0`, `qform.cheapest_check` |
| "a reusable solution for deduplicating customer records" | `code.module.solution_records`, `qform.train_or_call`, `qform.analogy_probe` |

This is the finding. The search does not fail and does not say the layer is
empty. It answers a question about what happened last time with a template
for asking a question, and a question about what a person instructed with a
module reference. A harness that receives those results has no way to tell
that the layer it asked about holds nothing.

The same five questions after the candidate pack is added:

| Question | What came back after |
|---|---|
| "a previous run of this same import that failed and how it was repaired" | `classify_a_failed_check_before_changing_the_work`, `run_the_restore_before_you_call_the_backup_a_backup`, `recorded_direction_keep_failures_as_visible_as_successes` |
| "what went wrong last time and what fixed it" | `recorded_direction_do_not_weaken_a_failing_check`, `recorded_direction_never_end_on_a_fixed_attempt_count`, `a_truthy_value_is_not_a_granted_permission` |
| "what guidance did the user give about dropping rows" | Three User Feedback Intelligence items, none of them about dropping rows |
| "a standing instruction about weakening a check to make the build pass" | `build_a_test_fixture_from_the_real_typed_object`, `classify_a_failed_check_before_changing_the_work`, `recorded_direction_build_general_mechanisms` |
| "a reusable solution for deduplicating customer records" | `code.module.solution_records`, `qform.train_or_call`, and one User Feedback item |

Read those honestly. Questions one and two are now answered from the right
layers. Question three still returns nothing about dropping rows, because no
such guidance exists to return; what changed is that the answers now come from
the guidance layer instead of from a module reference. Question four is a
miss: the item that states exactly that instruction,
`recorded_direction_do_not_weaken_a_failing_check`, is not in the first three
for that phrasing, although it is first for the plainer "a check is failing
and i want to change it so the build goes green". Question five is unchanged
and should be, because this pack holds nothing about deduplication.

The full report, with every hit, is in
[measurement-2026-09-21.json](measurement-2026-09-21.json).

## 3. What is missing, and why

A customer connects a coding harness and asks for help with a real task. Four
things the service should be able to hand back and cannot.

| Missing | Why a customer needs it | Addressed here |
|---|---|---|
| A record of a failure and the repair that fixed it | The fifth customer problem the product exists to answer is the same mistakes appearing again. A layer that holds no failure cannot prevent a repeated one. | Yes, 9 of the 14 Runtime History items are a recorded failure, repair or the decision that classified one. |
| A recorded decision with its alternatives and its reason | A harness that cannot see why a choice was made re-argues it every run, at full model cost. | Yes, 4 items. |
| A measurement with its population and its limits | Without the population, a number becomes a claim. The layer should hand back the limits with the number. | Yes, 1 item, and it deliberately does not copy the timings out of its report. |
| Standing guidance with a scope, a strength and a timing | Guidance buried in a prompt cannot be found, consulted or responded to. The layer exists so a step can find it and record what it did about it. | Yes, 10 User Feedback items, each with its scope, strength and timing stated. |

Two gaps this tranche does not close, recorded rather than hidden.

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

### Candidate or approved

All twenty-four are **candidates**. None is approved.

The only thing that has judged them is the mechanical check in
`tools/test_intelligence_layer_coverage.py`. It verifies the record contracts,
that every digest is the SHA-256 of its body recomputed independently, that
every licence is one the default host policy accepts, that both layers are
covered, that every cited source file exists at the recorded revision, that
every item declares a version and no effects, that no item claims an approval,
and that thirty-four plain customer queries each find their item. A passing
check is not an approval. Approval means a person who did not write the item
decides against written criteria and the record names them.

## 5. Checks run

| Command | Result |
|---|---|
| `PYTHONPATH=src:tools python -m unittest tools.test_intelligence_layer_coverage` | 13 tests, OK |
| `PYTHONPATH=src python .../pack/build.py` | 24 items, no stale rows |
| `PYTHONPATH=src python tools/stage_intelligence_candidates.py ... --namespace layer.coverage` | 24 records committed to an isolated database, all 24 excluded from normal search, all 24 found by their review probe |
| `python -m loop_engine --conformance` | all gates pass |
| hardcoding audit against the recorded baseline | exit 0, no new high finding |

Each of the eight rules in the check has its known-wrong cases, twenty-one in
all, and the check fails if a rule stops reporting one. Two of them were also
run against the files on disk: appending a line to a body without rebuilding
was reported by `digest_matches_its_body` and
`specification_text_equals_its_body`, and setting one item to `registered`
with an approval naming its own author was reported by
`every_item_is_an_unapproved_candidate`. Both files were restored afterwards.

## 6. Limits

- Lexical search over a 24-item pack. This is a coverage measurement and a
  smoke check, not a relevance benchmark and not evidence that any item helped
  a task.
- No model was called. No network was reached. No hosted service was changed.
- Five of the ten adversarial reviewer queries missed on their first run, and
  two of those returned nothing at all. The purposes were widened with the
  customer's words and the queries were left unchanged. The original misses
  are recorded in `pack/search-queries.json`.
- Offered, fetched, loaded, used and verified are separate facts. This work
  establishes that the items can be **offered** by a search and that their
  bodies can be **fetched** by digest. It establishes nothing beyond that.
