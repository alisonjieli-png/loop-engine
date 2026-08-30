"""Executable checks for append-only reactive output serving.

Owns restart, history, immutability, verifier, and tamper proof for the store.
It is verification only and never becomes an output authority itself.
"""
from __future__ import annotations

import os
import tempfile

from ..loop.atomic_primitives import LoopValue, LoopValueCreateRequest
from ..loop.recursive_loop import LoopLedger
from ..loop.reactive_contracts import (
    CandidateVerdict, MetricDirection, PortfolioPolicy, PortfolioView,
    RankingDimension)
from ..loop.reactive_outputs import (
    CandidateEvaluation, CandidateOutput, ConfidenceVector, OutputQuery,
    PortfolioBuildRequest, build_output_portfolio)
from .reactive_output_store import (
    ReactiveOutputStoreError, SQLiteReactiveOutputStore)
from .runtime_observer import RuntimeObservationServices


def _candidate(candidate_id: str, answer: int) -> CandidateOutput:
    value = LoopValue.create(
        {"answer": answer}, LoopValueCreateRequest(
            "answer/v1", "answer", f"producer-{candidate_id}",
            "core.fixture.output"))
    return CandidateOutput(
        candidate_id, "series-serve", "run-1", "activation-1",
        f"producer-{candidate_id}", "answers", "topic-serve", "subject",
        "snapshot", "watermark", value.to_ref(), (), "a" * 64, "b" * 64,
        "2026-08-29T13:00:00Z", "2026-08-29T13:00:00Z")


def _evaluation(candidate_id: str, score: float) -> CandidateEvaluation:
    return CandidateEvaluation(
        f"evaluation-{candidate_id}", candidate_id,
        (f"verifier-{candidate_id}",), "policy-verify", "1.0.0",
        CandidateVerdict.VERIFIED, "2026-08-29T13:01:00Z",
        ConfidenceVector(
            evidence_coverage=score, independent_verification=score,
            deterministic_verification=score, freshness=1, applicability=1),
        risk=1 - score, cost=0.1, latency=0.1, novelty=0.5)


def self_test() -> dict:
    tests: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    policy = PortfolioPolicy(
        "policy-serve", "1.0.0", PortfolioView.VERIFIED_TOP_K,
        (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE),), 2)
    candidates = (_candidate("candidate-one", 1),
                  _candidate("candidate-two", 2))
    evaluations = (_evaluation("candidate-one", 0.7),
                   _evaluation("candidate-two", 0.9))

    with tempfile.TemporaryDirectory() as temporary:
        path = os.path.join(temporary, "outputs.sqlite")
        ledger = LoopLedger(id_namespace="output-store")
        store = SQLiteReactiveOutputStore(
            path, RuntimeObservationServices(ledger=ledger))
        for candidate in candidates:
            store.append_candidate(candidate)
        for evaluation in evaluations:
            store.append_evaluation(evaluation)
        first = build_output_portfolio(PortfolioBuildRequest(
            "series-serve", "topic-serve", 1, "watermark",
            "2026-08-29T13:02:00Z", policy, candidates, evaluations))
        store.append_portfolio(first)
        current = store.query(OutputQuery(
            "series-serve", "topic-serve", PortfolioView.VERIFIED_TOP_K))
        check("current_portfolio_is_served_without_running_producer",
              current.entries[0].candidate_ref == "candidate-two"
              and current.candidates[0].producer_loop_id
              == "producer-candidate-two")

        second = build_output_portfolio(PortfolioBuildRequest(
            "series-serve", "topic-serve", 2, "watermark-2",
            "2026-08-29T13:03:00Z", policy, candidates, evaluations))
        store.append_portfolio(second)
        as_of = store.query(OutputQuery(
            "series-serve", "topic-serve", PortfolioView.VERIFIED_TOP_K,
            as_of_portfolio_version=1))
        check("as_of_query_preserves_prior_portfolio_version",
              as_of.snapshot.portfolio_version == 1
              and store.query(OutputQuery(
                  "series-serve", "topic-serve",
                  PortfolioView.VERIFIED_TOP_K)).snapshot.portfolio_version == 2)
        check("portfolio_history_is_append_only",
              [item.portfolio_version for item in store.portfolio_history(
                  OutputQuery("series-serve", "topic-serve",
                              PortfolioView.VERIFIED_TOP_K))] == [1, 2])

        store.append_candidate(candidates[0])
        store.append_evaluation(evaluations[0])
        store.append_portfolio(second)
        check("exact_replay_is_idempotent",
              store.get_candidate("candidate-one") == candidates[0])

        mutation_refused = False
        changed = _candidate("candidate-one", 999)
        try:
            store.append_candidate(changed)
        except ReactiveOutputStoreError:
            mutation_refused = True
        check("candidate_identity_cannot_be_reused_for_changed_output",
              mutation_refused)

        self_verification_refused = False
        self_evaluation = CandidateEvaluation(
            "evaluation-self", "candidate-one",
            ("producer-candidate-one",), "policy-verify", "1.0.0",
            CandidateVerdict.VERIFIED, "2026-08-29T13:04:00Z",
            ConfidenceVector(independent_verification=1))
        try:
            store.append_evaluation(self_evaluation)
        except ReactiveOutputStoreError:
            self_verification_refused = True
        check("producer_cannot_be_sole_verifier", self_verification_refused)

        gap_refused = False
        gap = build_output_portfolio(PortfolioBuildRequest(
            "series-serve", "topic-serve", 4, "watermark-4",
            "2026-08-29T13:05:00Z", policy, candidates, evaluations))
        try:
            store.append_portfolio(gap)
        except ReactiveOutputStoreError:
            gap_refused = True
        check("portfolio_versions_must_be_contiguous", gap_refused)
        archive_candidate = _candidate("candidate-three", 3)
        store.append_candidate(archive_candidate)
        archive_policy = PortfolioPolicy(
            "policy-archive", "1.0.0", PortfolioView.ALL_ATTEMPTED,
            (RankingDimension("evidence_coverage", MetricDirection.MAXIMIZE),),
            3)
        archive = build_output_portfolio(PortfolioBuildRequest(
            "series-serve", "topic-serve", 1, "watermark-archive",
            "2026-08-29T13:06:00Z", archive_policy,
            candidates + (archive_candidate,), evaluations))
        store.append_portfolio(archive)
        archive_result = store.query(OutputQuery(
            "series-serve", "topic-serve", PortfolioView.ALL_ATTEMPTED))
        check("all_attempted_store_view_serves_unevaluated_candidate_metadata",
              len(archive_result.candidates) == 3
              and len(archive_result.evaluations) == 2
              and any(not entry.evaluation_ref
                      for entry in archive_result.entries))
        from .event_vocabulary import to_canonical_events
        families = {item["type"] for item in to_canonical_events(ledger.events)}
        check("output_records_use_canonical_run_events",
              {"output.candidate.stored", "output.evaluation.stored",
               "output.portfolio.stored"} <= families)
        store.close()

        reopened = SQLiteReactiveOutputStore(path)
        replay = reopened.query(OutputQuery(
            "series-serve", "topic-serve", PortfolioView.VERIFIED_TOP_K))
        check("portfolio_survives_store_restart",
              replay.snapshot.portfolio_version == 2)
        reopened._connection.execute(
            "UPDATE reactive_portfolios SET body = ? "
            "WHERE portfolio_version = 2", ('{"changed":true}',))
        reopened._connection.commit()
        tamper_refused = False
        try:
            reopened.query(OutputQuery(
                "series-serve", "topic-serve",
                PortfolioView.VERIFIED_TOP_K))
        except ReactiveOutputStoreError:
            tamper_refused = True
        check("changed_portfolio_body_fails_digest_verification",
              tamper_refused)
        reopened.close()

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "reactive_output_store_self_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
