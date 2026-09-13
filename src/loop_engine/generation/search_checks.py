"""Offline proposal, evidence-binding, and task-conditioning controls.

Host evidence resolvers in this module validate authored fixtures only.
No real task completion, model invocation, or intelligence promotion is claimed.
"""
from __future__ import annotations

from dataclasses import replace

from .model.fragments import GenerationError
from .search import GridSearchAdapter, RandomSearchAdapter, VectorWarmStartAdapter, propose_configurations
from .search_records import (SearchCursor, SearchObjective, SearchObservation, SearchRequest,
                             SearchServices, SearchTask)
from .space import ConfigurationAxis, ConfigurationSpace, content_digest


def fixtures():
    space = ConfigurationSpace("test-space", "1.0.0", (
        ConfigurationAxis("x", "integer_range", minimum=0, maximum=999999999),
        ConfigurationAxis("y", "integer_range", minimum=0, maximum=9)))
    task = SearchTask("test-task", content_digest("task"), "task/test@1.0.0",
                      "test-evaluator@1.0.0", "test-features@1.0.0", (1.0, 0.0))
    objective = (SearchObjective("test-loss@1.0.0", "minimize"),)
    request = SearchRequest(space, task, objective, batch_size=3, draw_limit=10, seed=42)
    return request


def observation(request, identity, index=0, **changes):
    row = SearchObservation(identity, request.task, request.space.digest, index,
        request.objectives, (1.0,), "completed", "occurrence:" + identity, "history:" + identity,
        content_digest("history:" + identity), "evaluation:" + identity,
        content_digest("evaluation:" + identity), "search_feedback")
    return replace(row, **changes)


def run_checks():
    tests = []

    def check(name, value):
        tests.append({"name": name, "passed": bool(value)})

    request = fixtures()
    grid = SearchServices(GridSearchAdapter())
    result = propose_configurations(request, grid)
    batch = result["value"]
    check("configuration_search_uses_canonical_loop",
          result["loop_id"].startswith("loop") and result["model_calls"] == 0
          and result["loop_definition_id"] and not batch["task_execution_performed"])
    check("ten_billion_space_yields_only_requested_batch",
          batch["raw_cardinality_decimal"] == "10000000000"
          and [v["configuration_index"] for v in batch["proposals"]] == [0, 1, 2])
    check("proposals_never_claim_execution_or_acceptance",
          all(not v["executed"] and not v["task_accepted"]
              for v in batch["proposals"]) and not batch["promotion_performed"])
    next_batch = propose_configurations(replace(request, cursor=batch["next_cursor"]), grid)["value"]
    check("grid_cursor_resumes_without_repeating_addresses",
          [v["configuration_index"] for v in next_batch["proposals"]] == [3, 4, 5])
    shard = propose_configurations(replace(request, shard_count=3, shard_index=1), grid)["value"]
    check("grid_shard_contains_only_owned_addresses",
          [v["configuration_index"] for v in shard["proposals"]] == [1, 4, 7])
    random = SearchServices(RandomSearchAdapter())
    first = propose_configurations(request, random)["value"]
    repeated = propose_configurations(request, random)["value"]
    check("seeded_exploration_repeats_exact_proposals", first == repeated)
    original = observation(request, "one", 0)
    exact = replace(request, observations=(original,))
    unresolved = propose_configurations(exact, grid)["value"]
    check("unresolved_evidence_cannot_change_the_search",
          unresolved["observations_validated"] == []
          and unresolved["excluded_observations"][0]["reason"] == "evidence_resolver_unavailable")
    trusted_fixture = SearchServices(GridSearchAdapter(), resolve_evidence=lambda row: True)
    used = propose_configurations(exact, trusted_fixture)["value"]
    check("resolved_observation_prevents_implicit_repeat",
          used["proposals"][0]["configuration_index"] == 1)
    duplicate = replace(original, trial_id="copy")
    copied = propose_configurations(replace(request, observations=(original, duplicate)), trusted_fixture)["value"]
    check("copied_history_is_not_independent_evidence",
          copied["observations_validated"] == ["one"]
          and copied["excluded_observations"][0]["reason"] == "duplicate_trial_or_evidence")
    legitimate = replace(original, trial_id="repeat", trial_occurrence_ref="occurrence:repeat",
                         evaluation_ref="evaluation:repeat", evaluation_digest=content_digest("repeat"))
    repeated = propose_configurations(replace(request, observations=(original, legitimate)), trusted_fixture)["value"]
    check("distinct_occurrences_in_one_history_remain_distinct_trials",
          repeated["observations_validated"] == ["one", "repeat"])
    incompatible = replace(original, objectives=(SearchObjective("other@1.0.0", "maximize"),))
    excluded = propose_configurations(replace(request, observations=(incompatible,)), trusted_fixture)["value"]
    check("incomparable_objectives_are_excluded",
          excluded["excluded_observations"][0]["reason"] == "objectives_not_comparable")
    sealed = propose_configurations(replace(request, observations=(
        replace(original, data_partition="sealed_final"),)), trusted_fixture)["value"]
    check("sealed_final_scores_cannot_guide_search",
          sealed["observations_validated"] == []
          and sealed["excluded_observations"][0]["reason"] == "sealed_evaluation_must_not_guide_search")
    missing = replace(original, values=(None,))
    check("unknown_measurement_stays_unknown", missing.values == (None,))
    for bad in (float("nan"), float("inf"), True):
        try:
            replace(original, values=(bad,))
            check(f"invalid_measurement_{bad}_refused", False)
        except GenerationError:
            check(f"invalid_measurement_{bad}_refused", True)
    similar = replace(request.task, task_id="similar", task_digest=content_digest("similar"))
    distant = replace(request.task, task_id="distant", task_digest=content_digest("distant"), features=(0.0, 1.0))
    warm = replace(request, observations=(
        observation(request, "near", 15, task=similar),
        observation(request, "far", 25, task=distant)))
    vector = SearchServices(VectorWarmStartAdapter(0.5), resolve_evidence=lambda row: True)
    preferred = propose_configurations(warm, vector)["value"]
    check("task_vectors_select_related_candidates_without_transferring_scores",
          [v["configuration_index"] for v in preferred["proposals"]] == [15]
          and preferred["proposals"][0]["parent_trial_ids"] == ["near"]
          and preferred["adapter_settings"]["transfers_scores"] is False)
    opposite = replace(warm, task=replace(request.task, features=(0.0, 1.0)))
    changed = propose_configurations(opposite, vector)["value"]
    check("different_task_features_change_the_candidate_prior",
          [v["configuration_index"] for v in changed["proposals"]] == [25])
    wrong_features = replace(similar, feature_space_ref="other-features@1.0.0")
    wrong = propose_configurations(replace(request, observations=(
        observation(request, "wrong", 15, task=wrong_features),)), vector)["value"]
    check("incompatible_feature_encoders_are_not_mixed", not wrong["proposals"])

    # Exact-task identity is the task, not its feature encoding: evidence
    # recorded before features were attached still blocks a repeat.
    featureless = replace(request.task, feature_space_ref="", features=())
    unencoded = propose_configurations(replace(request, observations=(
        observation(request, "nf", 0, task=featureless),)), trusted_fixture)["value"]
    check("evidence_recorded_without_task_features_still_blocks_a_repeat",
          unencoded["observations_validated"] == ["nf"]
          and [v["configuration_index"] for v in unencoded["proposals"]] == [1, 2, 3]
          and request.task.identity_digest == featureless.identity_digest
          and request.task.digest != featureless.digest)
    # One evaluation artifact is one measurement whatever trial id it carries.
    refiled = replace(original, trial_id="refiled", trial_occurrence_ref="occurrence:refiled",
                      history_ref="history:refiled", history_digest=content_digest("history:refiled"))
    twice = propose_configurations(replace(request, observations=(original, refiled)), trusted_fixture)["value"]
    same_bytes = replace(original, trial_id="bytes", trial_occurrence_ref="occurrence:bytes",
                         evaluation_ref="evaluation:bytes")
    identical = propose_configurations(replace(request, observations=(original, same_bytes)), trusted_fixture)["value"]
    check("one_evaluation_artifact_counts_once",
          twice["observations_validated"] == ["one"]
          and twice["excluded_observations"][0]["reason"] == "duplicate_evaluation_artifact"
          and identical["observations_validated"] == ["one"]
          and identical["excluded_observations"][0]["reason"] == "duplicate_evaluation_artifact")
    # A changed evaluator implementation under the same reference is excluded
    # when both sides state their evaluator digest; an unstated one is not judged.
    judged = replace(request, task=replace(request.task, evaluator_digest=content_digest("judge-2")))
    stale = observation(judged, "stale", 4, task=replace(judged.task, evaluator_digest=content_digest("judge-1")))
    unstated = observation(judged, "unstated", 5, task=replace(judged.task, evaluator_digest=""))
    verdict = propose_configurations(replace(judged, observations=(stale, unstated)), trusted_fixture)["value"]
    check("a_changed_evaluator_implementation_is_excluded_when_both_digests_are_stated",
          verdict["observations_validated"] == ["unstated"]
          and verdict["excluded_observations"][0]["reason"] == "evaluator_implementation_changed"
          and judged.task.digest != request.task.digest)
    try:
        replace(request.task, evaluator_digest="not-a-digest")
        check("an_evaluator_digest_must_be_a_digest", False)
    except GenerationError:
        check("an_evaluator_digest_must_be_a_digest", True)
    # The target task's own measurements cannot crowd related tasks out of
    # the warm start's draw allowance.
    crowded = replace(warm, draw_limit=3, observations=tuple(
        observation(request, f"own-{i}", i) for i in range(3)) + warm.observations)
    surfaced = propose_configurations(crowded, vector)["value"]
    check("exact_task_measurements_do_not_crowd_out_related_candidates",
          [v["configuration_index"] for v in surfaced["proposals"]] == [15]
          and surfaced["draws"] <= 3)
    # The public entry point keeps the typed refusal.
    try:
        propose_configurations(replace(warm, task=replace(request.task, features=(0.0, 0.0))), vector)
        check("the_public_entry_raises_the_typed_refusal", False)
    except GenerationError as exc:
        check("the_public_entry_raises_the_typed_refusal", "nonzero task feature vector" in str(exc))
    check("the_batch_record_names_its_request_in_plain_fields",
          batch["request"] == {"seed": 42, "cursor": 0, "shard_count": 1, "shard_index": 0,
                               "batch_size": 3, "draw_limit": 10,
                               "allow_repeated_configurations": False})
    empty = propose_configurations(replace(request, space=ConfigurationSpace("tiny", "1.0.0", (
        ConfigurationAxis("x", "integer_range", minimum=0, maximum=0),)),
        shard_count=3, shard_index=2), random)["value"]
    check("an_empty_shard_is_reported_exhausted_by_seeded_exploration",
          empty["proposals"] == [] and empty["search_exhausted"] is True)

    # A cursor is bound to the space and shard that produced it.
    sharded = propose_configurations(replace(request, shard_count=3, shard_index=1), grid)["value"]
    cursor = SearchCursor.from_dict(sharded["cursor_record"])
    check("the_batch_names_its_cursor_with_space_and_shard",
          cursor.space_digest == request.space.digest and (cursor.shard_count, cursor.shard_index) == (3, 1)
          and cursor.next_index == sharded["next_cursor"] and cursor.exhausted is False)
    resumed = propose_configurations(replace(request, shard_count=3, shard_index=1, cursor_record=cursor), grid)["value"]
    check("a_bound_cursor_resumes_exactly_where_its_shard_stopped",
          [v["configuration_index"] for v in resumed["proposals"]] == [10, 13, 16]
          and resumed["request"]["cursor"] == cursor.next_index)
    for name, bad in (("another_shard", dict(shard_count=2, shard_index=0)),
                      ("another_space", dict(space=ConfigurationSpace("other", "1.0.0", (
                          ConfigurationAxis("x", "integer_range", minimum=0, maximum=99),)),
                          shard_count=3, shard_index=1)),
                      ("a_disagreeing_integer_cursor", dict(shard_count=3, shard_index=1, cursor=5))):
        try:
            replace(request, cursor_record=cursor, **bad)
            check(f"a_cursor_handed_to_{name}_is_refused", False)
        except GenerationError:
            check(f"a_cursor_handed_to_{name}_is_refused", True)
    finished = SearchCursor(request.space.digest, 1, 1 - 1, None, True)
    ended = propose_configurations(replace(request, cursor_record=finished), grid)["value"]
    check("an_exhausted_cursor_resumes_at_the_end_and_proposes_nothing",
          ended["proposals"] == [] and ended["search_exhausted"] is True
          and ended["request"]["cursor"] == request.space.cardinality)
    check("a_random_batch_carries_no_cursor_record",
          propose_configurations(request, random)["value"]["cursor_record"] is None)
    try:
        SearchCursor(request.space.digest, 1, 0, None, False)
        check("a_cursor_without_a_next_index_must_be_exhausted", False)
    except GenerationError:
        check("a_cursor_without_a_next_index_must_be_exhausted", True)

    # Every record has a typed reader that refuses unknown or missing fields.
    full = replace(request, observations=(original, legitimate), cursor_record=cursor,
                   shard_count=3, shard_index=1)
    rebuilt = SearchRequest.from_dict(full.to_dict())
    check("records_round_trip_through_their_typed_readers_with_equal_digests",
          rebuilt.digest == full.digest and rebuilt.space.digest == full.space.digest
          and rebuilt.task == full.task and rebuilt.observations == full.observations
          and rebuilt.cursor == full.cursor and rebuilt.cursor_record == cursor
          and ConfigurationSpace.from_dict(request.space.to_dict()).digest == request.space.digest
          and SearchObservation.from_dict(original.to_dict()).digest == original.digest
          and SearchTask.from_dict(replace(request.task, evaluator_digest=content_digest("j")).__dict__
                                   | {"features": list(request.task.features)}).evaluator_digest
          == content_digest("j"))
    for name, broken in (("an_unknown_field", {**original.to_dict(), "extra": 1}),
                         ("a_missing_field", {k: v for k, v in original.to_dict().items() if k != "state"}),
                         ("another_record_type", {**original.to_dict(), "record_type": "configuration_search_batch/v1"})):
        try:
            SearchObservation.from_dict(broken)
            check(f"{name}_is_refused_by_the_observation_reader", False)
        except GenerationError:
            check(f"{name}_is_refused_by_the_observation_reader", True)
    try:
        ConfigurationSpace.from_dict({**request.space.to_dict(), "record_type": "configuration_axis/v1"})
        check("a_space_record_of_another_type_is_refused", False)
    except GenerationError:
        check("a_space_record_of_another_type_is_refused", True)
    return {"tests": tests}
