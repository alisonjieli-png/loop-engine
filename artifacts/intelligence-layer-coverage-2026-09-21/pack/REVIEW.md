# Layer coverage pack review sheet

Kind: review sheet for the owner. Date: 2026-09-21.
Every item in this folder is a candidate. Nothing here is approved,
published, granted to a tenant or added to a host manifest. The approval
column is empty on purpose.

## What this folder holds

Twenty-four items for the two persistent intelligence layers that hold
nothing in the built-in population. Fourteen are recorded runs, decisions,
failures, repairs and one measurement, taken from this repository's own saved
evidence. Ten are guidance a person recorded, each with its scope, strength
and timing.

```text
Layer coverage pack candidates (24)
├── Context Intelligence (0, covered by the starter catalogue)
├── Code Intelligence (0, covered by the starter catalogue)
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

| File | Purpose |
|---|---|
| `bodies/` | One body for each item. The body is the source of truth for the text, the digest and the size. |
| `build.py` | The drafts, and the tool that measures each body through the engine's own `item_from_body` and rewrites the two derived records. It approves nothing and publishes nothing. |
| `specifications.json` | The items in the exact format `tools/stage_intelligence_candidates.py` accepts. The `text` of each row equals its body. |
| `items.json` | Identity, kind, purpose, source layer, source reference with revision, licence, declared effects, lifecycle tag, digest, size, item version, licence state, an empty approval record and the provenance. Each `reference` object has the shape `HarnessIntelligenceItem.reference()` returns. |
| `search-queries.json` | Thirty-four plain customer queries, each with the item it must find and who wrote it. |
| `REVIEW.md` | This sheet. |

## What each item carries before it could become active

| Requirement | Where it is |
|---|---|
| Immutable source identity | `reference.source_ref`, a repository path with the revision `6a489b2eff78d1e7251d65e143edbd89f7250c4e` appended. |
| Provenance | `provenance.authoring`, `provenance.source_revision`, `provenance.note` and `provenance.repository_sources`. The staging tool independently records `assistant_authored_from_repository_sources` and `not_independently_qualified`. |
| Licence state | `license_state` is `declared` and `reference.license` is `MIT`, the licence of this repository, which is the only identifier the default host policy accepts. The staging tool separately records `pending_review` in its own staged payload. |
| Version | `item_version` is `1.0.0` for every item. A changed body needs a new version. The staging tool also computes a content-derived `record_version`. |
| Typed contract | `reference.record_type` is `harness_intelligence_item/v1`. The file carries `layer_coverage_candidate_items/v1`. A check rebuilds every reference through the engine's own typed item and refuses a malformed one. |
| Declared effects | `reference.declared_effects` is empty for every item. These bodies are prose. None executes, reads a file or reaches a network. |
| Digest | `reference.digest`, the SHA-256 of the body bytes, measured by `item_from_body` and recomputed independently by the check. |
| Lifecycle | `lifecycle` is `candidate` and the lifecycle tag is `candidate` for every item. `approval.approved` is `false` and both approval fields are empty. |

## Approval state

**No item in this pack is approved.** All twenty-four are candidates.

The only thing that has passed judgement on them is the mechanical check in
`tools/test_intelligence_layer_coverage.py`, which verifies contracts,
digests, licences, provenance and retrieval. A passing check is not an
approval. Approval is a person who did not write the item deciding, against
written criteria, that it is correct and useful, and the approval record
naming them. That has not happened.

Two separate facts to keep apart when reading the table below:

1. The body was measured and its derived records are consistent. Every row.
2. The body says what its cited source says. Nobody independent has checked
   this for any row.

## Items for review

Open the body, open the cited source at revision `6a489b2`, and write the
decision in the last column: approved with a name and a date, rejected with
the reason, or the change needed.

### Runtime History and Solution Intelligence

| Item | Family | Cited source | Approval |
|---|---|---|---|
| `classify_a_failed_check_before_changing_the_work` | decision | `fly-service-container-attempt-1.json`, `-3.json` | |
| `a_client_reader_that_assumes_one_response_encoding` | failure_remedy | `guided-connection-browser-1.json`, `-3.json`, `web_assets/service.js` | |
| `a_test_producer_that_returns_booleans_hides_which_check_ran` | failure_remedy | `runtime-regression-repairs.md` | |
| `build_a_test_fixture_from_the_real_typed_object` | failure_remedy | `runtime-regression-repairs.md` | |
| `two_scanners_that_disagree_may_be_measuring_two_populations` | decision | `runtime-regression-repairs.md` | |
| `a_short_candidate_pool_can_hide_an_eligible_match` | repair | `intelligence-access-repairs.md`, `core/retrieval.py` | |
| `an_unavailable_backend_must_not_look_like_an_empty_result` | failure_remedy | `intelligence-access-repairs.md`, `core/retrieval.py` | |
| `a_fixture_that_asks_for_less_than_it_requires` | decision | `intelligence-access-repairs.md` | |
| `a_write_is_confirmed_by_an_acknowledgment_and_a_readback` | repair | `storage-write-repairs.md` | |
| `say_plainly_when_two_writes_are_not_one_transaction` | decision | `storage-write-repairs.md` | |
| `a_truthy_value_is_not_a_granted_permission` | repair | `storage-write-repairs.md` | |
| `run_the_restore_before_you_call_the_backup_a_backup` | failure_remedy | `pilot-backup-restore-1.json`, `-2.json` | |
| `read_a_latency_report_by_its_population_and_its_limits` | measurement | `service-latency-1.json` | |
| `paying_for_something_is_not_permission_to_see_it` | repair | `provisioning-access-repairs.md` | |

### User Feedback Intelligence

| Item | Family | Cited source | Approval |
|---|---|---|---|
| `recorded_direction_do_not_weaken_a_failing_check` | owner_constraint | `AGENTS.md`, persistent general solving record | |
| `recorded_direction_build_general_mechanisms` | owner_constraint | `AGENTS.md` | |
| `recorded_direction_never_end_on_a_fixed_attempt_count` | owner_instruction | `AGENTS.md` | |
| `recorded_direction_decide_what_you_can_decide` | owner_priority | `CLAUDE.md` | |
| `recorded_direction_marketing_language_is_not_a_factual_claim` | owner_correction | `docs/guides/product-style-guide.md` | |
| `recorded_direction_keep_failures_as_visible_as_successes` | owner_constraint | `AGENTS.md` | |
| `recorded_direction_offered_fetched_loaded_used_and_verified_are_separate` | owner_constraint | `AGENTS.md` | |
| `recorded_direction_do_not_infer_behaviour_from_names_or_prose` | owner_constraint | `AGENTS.md`, `CLAUDE.md` | |
| `recorded_direction_state_observed_inferred_assumed_and_missing_separately` | owner_instruction | `AGENTS.md`, `ASTRA.md` | |
| `recorded_direction_write_public_pages_in_plain_english` | owner_instruction | `AGENTS.md`, `docs/guides/product-style-guide.md` | |

## What a reviewer should challenge first

Three honest weaknesses, stated before anyone finds them.

1. **The guidance in the User Feedback layer is this project's own owner's
   guidance.** It reads as transferable engineering direction and it is real,
   dated and cited. It is still not the reviewing customer's guidance. A
   customer's own User Feedback layer starts empty and fills from their
   people. This pack shows the shape and seeds ten transferable statements;
   it does not pretend to be somebody else's feedback.
2. **The Runtime History items are drawn from this repository's audit, not
   from a customer's runs.** Each is a real recorded failure, repair,
   decision or measurement with its evidence file named. They are priors, not
   proof that the same choice suits another task.
3. **Nobody independent has read a body against its source.** The check
   verifies that the cited files exist and that the derived records match the
   bodies. It cannot verify that a sentence in a body is a fair summary of
   the file it cites. That is the review being asked for.

## After any edit of a body

Run these from the repository root. The first reports what is stale. The
second rewrites the derived records. The third runs the checks.

```bash
PYTHONPATH=src python \
  artifacts/intelligence-layer-coverage-2026-09-21/pack/build.py
PYTHONPATH=src python \
  artifacts/intelligence-layer-coverage-2026-09-21/pack/build.py --write
PYTHONPATH=src:tools python -m unittest tools.test_intelligence_layer_coverage
```

To look at the candidates in an isolated review catalogue, stage them with
the existing tool. It needs three new output paths, writes nothing else, and
cannot update the hosted service, create a tenant grant or promote a record.

```bash
PYTHONPATH=src python tools/stage_intelligence_candidates.py \
  --specifications \
  artifacts/intelligence-layer-coverage-2026-09-21/pack/specifications.json \
  --database NEW_DATABASE_PATH --namespace layer.coverage \
  --authorize-isolated-staging --export NEW_EXPORT_PATH --report NEW_REPORT_PATH
```

## Steps this folder does not take and does not authorize

- Approving or rejecting any item.
- Adding any item to a host manifest or granting it to a tenant.
- Publishing anything to the hosted service.
- Changing the built-in package population, the starter catalogue, or the
  generated catalogue index.
