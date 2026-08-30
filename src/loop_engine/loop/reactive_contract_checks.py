"""Executable checks for reactive Loop policy and output contracts.

Owns safe-default, composition, ranking, and refusal proof for passive records.
It is verification only and never executes or publishes a candidate.
"""
from __future__ import annotations

from dataclasses import replace

from .atomic_primitives import LoopValue, LoopValueCreateRequest
from .reactive_contracts import (
    ActivationPolicy, AdmissionPolicy, CandidateVerdict, EmissionPolicy,
    ExplorationPolicy,
    ExplorationStrategy, InputSchedulingPolicy, MetricDirection,
    OutputCardinality, OutputPortDefinition,
    OutputUpdateSemantics, PersistenceMode, PortfolioPolicy, PortfolioView,
    RankingDimension, ReactiveContractError,
    ReactiveLivenessPolicy, ReactiveLoopProfile, RetentionPolicy,
    ServingPolicy, TriggerKind)
from .reactive_outputs import (
    CandidateEvaluation, CandidateOutput, ConfidenceVector, OutputQuery,
    PortfolioBuildRequest, build_output_portfolio)


def _candidate(candidate_id: str, value: int) -> CandidateOutput:
    payload = LoopValue.create(
        {"answer": value}, LoopValueCreateRequest(
            "answer/v1", "answer", f"loop-{candidate_id}",
            "core.fixture.candidate"))
    return CandidateOutput(
        candidate_id, "series-1", "run-1", "activation-1",
        f"loop-{candidate_id}", "answers", "topic-1", "subject-1",
        "snapshot-1", "watermark-1", payload.to_ref(), (), "a" * 64,
        "b" * 64, "2026-08-29T12:00:00Z", "2026-08-29T12:00:00Z",
        diversity_tags=(f"route:{candidate_id}",))


def _evaluation(candidate_id: str, score: float, verdict) \
        -> CandidateEvaluation:
    return CandidateEvaluation(
        f"evaluation-{candidate_id}", candidate_id,
        (f"verifier-{candidate_id}",), "policy-evaluate", "1.0.0",
        verdict, "2026-08-29T12:01:00Z",
        ConfidenceVector(
            evidence_coverage=score, source_quality=score,
            deterministic_verification=score,
            independent_verification=score, freshness=1.0,
            applicability=1.0), risk=1.0 - score,
        cost=0.2, latency=0.1, novelty=0.5,
        rejection_reasons=("failed independent verification",)
        if verdict is CandidateVerdict.REJECTED else ())


def self_test() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    ranking = PortfolioPolicy(
        "policy-verified", "1.0.0", PortfolioView.VERIFIED_TOP_K,
        (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE, 3),
         RankingDimension("risk", MetricDirection.MINIMIZE, 1)),
        maximum_results=2)
    default_profile = ReactiveLoopProfile(
        "profile-one-shot", "1.0.0", ActivationPolicy(), AdmissionPolicy(1),
        InputSchedulingPolicy(), PersistenceMode.EPHEMERAL,
        ExplorationPolicy(),
        (OutputPortDefinition(
            "result", "answer", "answer/v1", OutputCardinality.SINGLE,
            OutputUpdateSemantics.IMMUTABLE),),
        ranking, EmissionPolicy(), ServingPolicy(1), RetentionPolicy(1, 1),
        ReactiveLivenessPolicy(30))
    check("safe_default_is_reactive_capable_but_one_shot",
          not default_profile.activation.reactivation_enabled
          and default_profile.persistence is PersistenceMode.EPHEMERAL
          and default_profile.activation.accepted_triggers
          == (TriggerKind.EXPLICIT_REQUEST,))

    durable_profile = ReactiveLoopProfile(
        "profile-monitor", "1.0.0",
        ActivationPolicy(
            (TriggerKind.PUSH_EVENT, TriggerKind.SCHEDULE,
             TriggerKind.INFORMATION_CHANGED), reactivation_enabled=True,
            debounce_seconds=1, cooldown_seconds=5,
            minimum_information_delta=0.01),
        AdmissionPolicy(100),
        InputSchedulingPolicy("priority_aging", 0.01),
        PersistenceMode.DURABLE_SERIES,
        ExplorationPolicy(
            ExplorationStrategy.SEEDED_RANDOM, 3, random_seed=7,
            settings_axes=("model_route", "context_profile")),
        (OutputPortDefinition(
            "recommendations", "ranked_answer", "answer/v1", "portfolio",
            "supersede"),), ranking, EmissionPolicy(),
        ServingPolicy(100, (PortfolioView.VERIFIED_TOP_K,
                            PortfolioView.ALL_ATTEMPTED)),
        RetentionPolicy(1000, 1000, True), ReactiveLivenessPolicy(60))
    check("durable_profile_composes_independent_policy_dimensions",
          durable_profile.activation.reactivation_enabled
          and durable_profile.exploration.maximum_variants == 3
          and not durable_profile.serving.pull_reactivates_producer)

    candidates = (_candidate("candidate-a", 1),
                  _candidate("candidate-b", 2),
                  _candidate("candidate-c", 3))
    evaluations = (
        _evaluation("candidate-a", 0.7, CandidateVerdict.VERIFIED),
        _evaluation("candidate-b", 0.9, CandidateVerdict.VERIFIED),
        _evaluation("candidate-c", 1.0, CandidateVerdict.REJECTED),
    )
    snapshot = build_output_portfolio(PortfolioBuildRequest(
        "series-1", "topic-1", 1, "watermark-1",
        "2026-08-29T12:02:00Z", ranking, candidates, evaluations))
    check("portfolio_rank_is_policy_versioned_not_candidate_state",
          [entry.candidate_ref for entry in snapshot.entries]
          == ["candidate-b", "candidate-a"]
          and not hasattr(candidates[0], "rank")
          and snapshot.policy_digest == ranking.content_digest)
    check("rejected_candidate_remains_in_considered_history",
          "candidate-c" in snapshot.considered_candidate_refs
          and "candidate-c" in snapshot.rejected_candidate_refs)

    changed_policy = PortfolioPolicy(
        "policy-low-cost", "1.0.0", PortfolioView.TOP_K,
        (RankingDimension("cost", MetricDirection.MINIMIZE),),
        maximum_results=3)
    changed = build_output_portfolio(PortfolioBuildRequest(
        "series-1", "topic-1", 2, "watermark-1",
        "2026-08-29T12:03:00Z", changed_policy, candidates, evaluations))
    check("same_candidates_support_a_different_ranked_view",
          changed.policy_digest != snapshot.policy_digest
          and changed.portfolio_version == 2)

    pareto_policy = PortfolioPolicy(
        "policy-pareto", "1.0.0", PortfolioView.PARETO,
        (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE),
         RankingDimension("risk", MetricDirection.MINIMIZE)),
        maximum_results=3)
    tradeoffs = (
        replace(evaluations[0], risk=0.1),
        replace(evaluations[1], risk=0.9),
        evaluations[2],
    )
    pareto = build_output_portfolio(PortfolioBuildRequest(
        "series-1", "topic-1", 3, "watermark-1",
        "2026-08-29T12:04:00Z", pareto_policy, candidates, tradeoffs))
    check("pareto_view_keeps_non_dominated_tradeoffs",
          {entry.candidate_ref for entry in pareto.entries}
          == {"candidate-a", "candidate-b"}
          and "candidate-c" in pareto.rejected_candidate_refs)

    archive_candidate = _candidate("candidate-d", 4)
    archive_policy = PortfolioPolicy(
        "policy-archive", "1.0.0", PortfolioView.ALL_ATTEMPTED,
        (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE),),
        maximum_results=4)
    archive = build_output_portfolio(PortfolioBuildRequest(
        "series-1", "topic-1", 4, "watermark-1",
        "2026-08-29T12:05:00Z", archive_policy,
        candidates + (archive_candidate,), evaluations))
    check("all_attempted_view_preserves_rejected_and_unevaluated_candidates",
          {entry.candidate_ref for entry in archive.entries}
          == {"candidate-a", "candidate-b", "candidate-c", "candidate-d"}
          and next(entry for entry in archive.entries
                   if entry.candidate_ref == "candidate-d").evaluation_ref == "")

    refused = []
    cases = (
        lambda: ActivationPolicy(
            (TriggerKind.PUSH_EVENT,), reactivation_enabled=False),
        lambda: ExplorationPolicy(
            ExplorationStrategy.SEEDED_RANDOM, 2),
        lambda: ServingPolicy(1, pull_reactivates_producer=True),
        lambda: AdmissionPolicy(1, deduplicate=False),
        lambda: CandidateEvaluation(
            "evaluation-bad", "candidate-a", ("verifier",), "policy",
            "1.0.0", CandidateVerdict.REJECTED,
            "2026-08-29T12:01:00Z", ConfidenceVector()),
    )
    for case in cases:
        try:
            case()
            refused.append(False)
        except ReactiveContractError:
            refused.append(True)
    check("unsafe_or_ambiguous_reactive_contracts_fail_closed",
          all(refused), str(refused))

    query = OutputQuery(
        "series-1", "topic-1", PortfolioView.VERIFIED_TOP_K,
        maximum_results=2, as_of_portfolio_version=1,
        minimum_derived_score=0.5)
    check("output_query_is_read_only_and_as_of_versioned",
          query.as_of_portfolio_version == 1
          and query.view is PortfolioView.VERIFIED_TOP_K)

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "reactive_contract_self_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
