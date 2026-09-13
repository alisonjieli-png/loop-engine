"""Offline proposal, evidence-binding, and task-conditioning controls.

Host evidence resolvers in this module validate authored fixtures only.
No real task completion, model invocation, or intelligence promotion is claimed.
"""
from __future__ import annotations

from dataclasses import replace

from .model.fragments import GenerationError
from .search import GridSearchAdapter, RandomSearchAdapter, VectorWarmStartAdapter, propose_configurations
from .search_records import SearchObjective, SearchObservation, SearchRequest, SearchServices, SearchTask
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
    return {"tests": tests}
