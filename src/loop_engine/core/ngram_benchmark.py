"""Frozen development and holdout benchmark for exact n-gram retrieval.

The benchmark runs a passive exact index against source-controlled judgments.
It records retrieval quality, timing, index size, and judged pair errors while
keeping model calls, network access, and persistent intelligence out of scope.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

from .ngram_retrieval import (
    DocumentSimilarityRequest,
    FusionPolicy,
    GovernedNgramQueryRequest,
    NgramDocument,
    NgramIndex,
    NgramLoopContext,
    NgramLoopOperation,
    NgramQueryRequest,
    NgramRetrievalError,
    NgramSpaceDefinition,
    _operation_as_loop,
    query_as_loop,
    tokenize,
)


BENCHMARK_SCHEMA_VERSION = "1.0.0"


def _round(value: float) -> float:
    return round(float(value), 12)


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(0, min(len(ordered) - 1,
                      math.ceil(fraction * len(ordered)) - 1))
    return ordered[rank]


def _query_metrics(ranked_ids: list[str], relevance: dict[str, float],
                   top_k: int) -> dict:
    selected = ranked_ids[:top_k]
    relevant = {document_id for document_id, grade in relevance.items()
                if grade > 0}
    retrieved_relevant = sum(document_id in relevant for document_id in selected)
    recall = retrieved_relevant / len(relevant) if relevant else 1.0
    precision = retrieved_relevant / top_k
    reciprocal_rank = next(
        (1.0 / rank for rank, document_id in enumerate(selected, start=1)
         if document_id in relevant), 0.0)
    dcg = sum((2.0 ** relevance.get(document_id, 0.0) - 1.0)
              / math.log2(rank + 1)
              for rank, document_id in enumerate(selected, start=1))
    ideal = sorted(relevance.values(), reverse=True)[:top_k]
    ideal_dcg = sum((2.0 ** grade - 1.0) / math.log2(rank + 1)
                    for rank, grade in enumerate(ideal, start=1))
    ndcg = dcg / ideal_dcg if ideal_dcg else 1.0
    return {"recall_at_k": _round(recall),
            "precision_at_k": _round(precision),
            "reciprocal_rank": _round(reciprocal_rank),
            "ndcg_at_k": _round(ndcg)}


def _validate_fixture(fixture: dict) -> None:
    if not isinstance(fixture, dict):
        raise NgramRetrievalError("benchmark fixture must be an object")
    if fixture.get("schema_version") != BENCHMARK_SCHEMA_VERSION:
        raise NgramRetrievalError(
            f"benchmark schema_version must be {BENCHMARK_SCHEMA_VERSION}")
    if not str(fixture.get("benchmark_id", "")).strip():
        raise NgramRetrievalError("benchmark_id must be non-empty")
    if not fixture.get("documents") or not fixture.get("queries"):
        raise NgramRetrievalError("benchmark needs documents and queries")
    splits = {str(query.get("split", "")) for query in fixture["queries"]}
    if splits != {"dev", "holdout"}:
        raise NgramRetrievalError(
            "frozen benchmark must contain dev and holdout queries")
    query_ids = [str(query.get("query_id", ""))
                 for query in fixture["queries"]]
    if any(not query_id for query_id in query_ids) \
            or len(query_ids) != len(set(query_ids)):
        raise NgramRetrievalError("query_id values must be unique and non-empty")
    if any(not query.get("relevance") for query in fixture["queries"]):
        raise NgramRetrievalError("every query needs relevance judgments")
    top_k = fixture.get("top_k", 5)
    if not isinstance(top_k, int) or top_k < 1:
        raise NgramRetrievalError("top_k must be a positive integer")


def run_benchmark_fixture(fixture: dict, *, fixture_digest: str = "") -> dict:
    """Run one exact benchmark object without external I/O or model calls."""
    _validate_fixture(fixture)
    space = NgramSpaceDefinition.from_dict(fixture.get("space", {}))
    documents = tuple(NgramDocument.from_dict(value)
                      for value in fixture["documents"])
    started = time.perf_counter_ns()
    index = NgramIndex(documents, space=space)
    build_time_ms = (time.perf_counter_ns() - started) / 1_000_000.0
    top_k = int(fixture.get("top_k", 5))
    policy = FusionPolicy()
    details: list[dict] = []
    by_split: dict[str, list[dict]] = {"dev": [], "holdout": []}
    for query in fixture["queries"]:
        allowed_scopes = tuple(query.get("allowed_scopes", ())) or None
        started = time.perf_counter_ns()
        result = index.query(NgramQueryRequest(
            str(query["query"]), allowed_scopes=allowed_scopes, top_k=top_k,
            lexical_scores=query.get("lexical_scores"),
            semantic_scores=query.get("semantic_scores"),
            fusion_policy=policy))
        latency_ms = (time.perf_counter_ns() - started) / 1_000_000.0
        ranked_ids = [hit.document_id for hit in result.hits]
        relevance = {str(document_id): float(grade)
                     for document_id, grade in query["relevance"].items()}
        metrics = _query_metrics(ranked_ids, relevance, top_k)
        row = {"query_id": str(query["query_id"]),
               "split": str(query["split"]),
               "query": str(query["query"]),
               "allowed_scopes": list(allowed_scopes or ()),
               "ranked_document_ids": ranked_ids,
               "relevance": relevance, "top_k": top_k,
               "latency_ms": _round(latency_ms),
               "result_precision": result.result_precision,
               "scope_filter_excluded": result.excluded_by_scope_count,
               "metrics": metrics,
               "score_explanations": [
                   {"document_id": hit.document_id,
                    "score": hit.score,
                    "score_contributions": {
                        name: dict(value) for name, value
                        in hit.score_contributions.items()}}
                   for hit in result.hits]}
        details.append(row)
        by_split[row["split"]].append(row)

    split_results = {}
    for split, rows in by_split.items():
        latencies = [row["latency_ms"] for row in rows]
        split_results[split] = {
            "query_count": len(rows), "top_k": top_k,
            "recall_at_k": _round(sum(row["metrics"]["recall_at_k"]
                                      for row in rows) / len(rows)),
            "precision_at_k": _round(sum(row["metrics"]["precision_at_k"]
                                         for row in rows) / len(rows)),
            "mrr": _round(sum(row["metrics"]["reciprocal_rank"]
                              for row in rows) / len(rows)),
            "ndcg_at_k": _round(sum(row["metrics"]["ndcg_at_k"]
                                    for row in rows) / len(rows)),
            "latency_ms": {
                "mean": _round(sum(latencies) / len(latencies)),
                "p50": _round(_percentile(latencies, 0.50)),
                "p95": _round(_percentile(latencies, 0.95)),
            },
        }

    pair_threshold = float(fixture.get("pair_threshold", 0.5))
    if not 0 <= pair_threshold <= 1:
        raise NgramRetrievalError("pair_threshold must be between zero and one")
    pair_rows = []
    false_merge = false_split = positive = negative = 0
    for judgment in fixture.get("pair_judgments", ()):
        same_entity = bool(judgment["same_entity"])
        similarity = index.document_similarity(DocumentSimilarityRequest(
            str(judgment["left_id"]), str(judgment["right_id"])))
        predicted_same = similarity >= pair_threshold
        false_merge += int(predicted_same and not same_entity)
        false_split += int(not predicted_same and same_entity)
        positive += int(same_entity)
        negative += int(not same_entity)
        pair_rows.append({"pair_id": str(judgment["pair_id"]),
                          "split": str(judgment.get("split", "holdout")),
                          "left_id": str(judgment["left_id"]),
                          "right_id": str(judgment["right_id"]),
                          "same_entity_judgment": same_entity,
                          "similarity": similarity,
                          "threshold": pair_threshold,
                          "predicted_same": predicted_same})
    pair_metrics = {
        "supported": bool(pair_rows), "pair_count": len(pair_rows),
        "threshold": pair_threshold, "false_merge_count": false_merge,
        "false_split_count": false_split,
        "false_merge_rate": _round(false_merge / negative) if negative else None,
        "false_split_rate": _round(false_split / positive) if positive else None,
        "judgments": pair_rows,
    }
    manifest = index.manifest()
    return {
        "record_type": "ngram_retrieval_benchmark/v1",
        "benchmark_id": fixture["benchmark_id"],
        "benchmark_version": str(fixture.get("benchmark_version", "1")),
        "fixture_digest": fixture_digest,
        "fixture_state": "frozen",
        "result_precision": "exact", "approximation": None,
        "space_ref": space.space_ref, "index_digest": index.index_digest,
        "document_count": index.document_count,
        "query_count": len(details),
        "all_queries_evaluated": len(details) == len(fixture["queries"]),
        "zero_model_calls": True,
        "build_time_ms": _round(build_time_ms),
        "serialized_index_size_bytes":
            manifest["serialized_index_size_bytes"],
        "term_count": manifest["term_count"],
        "posting_count": manifest["posting_count"],
        "splits": split_results, "queries": details,
        "pair_metrics": pair_metrics,
        "measurement_notes": [
            "rankings and metrics are deterministic for the frozen fixture",
            "latency and build time are observations from this process",
            "pair labels are fixture judgments, not intelligence truth",
            "this is external retrieval, not learned model n-gram embeddings",
        ],
    }


def run_frozen_benchmark(path: str | Path) -> dict:
    """Load and run one exact frozen fixture, preserving its byte digest."""
    selected = Path(path)
    raw = selected.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        fixture = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NgramRetrievalError(f"invalid benchmark JSON: {exc}") from exc
    return run_benchmark_fixture(fixture, fixture_digest=digest)


def run_frozen_benchmark_as_loop(path: str | Path, *, parent=None,
                                 ledger=None) -> dict:
    """Run the frozen benchmark through a deterministic Practitioner Loop."""
    wrapped = _operation_as_loop(NgramLoopOperation(
        "benchmark exact statistical n-gram retrieval", "practitioner",
        "practitioner.code_execution", "spawned_by"),
        lambda: run_frozen_benchmark(path),
        NgramLoopContext(parent=parent, ledger=ledger))
    return {**wrapped, "benchmark": wrapped["value"]}


def run_contract_checks(frozen_fixture: str = "") -> dict:
    """Run deterministic retrieval contracts and an optional frozen benchmark."""
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    space = NgramSpaceDefinition()
    check("space_identity_is_versioned_and_digest_pinned",
          len(space.definition_digest) == 64
          and NgramSpaceDefinition.from_dict(space.to_dict()) == space,
          space.space_ref)
    changed = NgramSpaceDefinition(character_n_range=(2, 5))
    check("space_digest_changes_with_term_identity",
          changed.definition_digest != space.definition_digest)
    check("normalization_is_pinned_and_identifier_aware",
          tokenize("HTTPResponse_customer-ID", space)
          == ("http", "response", "customer", "id"))
    documents = (
        NgramDocument("address.main", "normalize customer addresses and ZIP",
                      "tenant:a"),
        NgramDocument("address.other", "normalize customer addresses and ZIP",
                      "tenant:b"),
        NgramDocument("schema", "validate Schema.org JSON-LD records",
                      "tenant:a"),
        NgramDocument("routing", "local-only model routing and cloud refusal",
                      "tenant:a"),
    )
    index = NgramIndex(documents, space=space)
    stats = index.statistics("customer addresses", allowed_scopes=("tenant:a",))
    term = next(row for row in stats["terms"]
                if row["unit"] == "word" and row["term"] == "1:addresses")
    check("term_document_collection_frequency_and_idf_are_exact",
          term["query_term_frequency"] == 1
          and term["document_frequency"] == 1
          and term["collection_frequency"] == 1
          and term["result_precision"] == "exact")
    typo = index.query(NgramQueryRequest(
        "normalise customer addrsses", top_k=2,
        allowed_scopes=("tenant:a",)))
    check("character_ngrams_retrieve_a_bounded_typo",
          typo.hits and typo.hits[0].document_id == "address.main")
    check("scope_filtering_precedes_ranking",
          all(hit.scope == "tenant:a" for hit in typo.hits)
          and typo.excluded_by_scope_count == 1
          and "address.other" not in {hit.document_id for hit in typo.hits})
    fused = index.query(NgramQueryRequest(
        "structured records", allowed_scopes=("tenant:a",),
        lexical_scores={"schema": 12.0, "routing": 1.0,
                        "address.other": 99.0},
        semantic_scores={"schema": 0.8, "routing": 0.1}, top_k=2))
    check("external_scores_are_explainable",
          fused.hits and fused.hits[0].document_id == "schema"
          and fused.hits[0].score_contributions["lexical"][
              "weighted_score"] > 0
          and fused.hits[0].score_contributions["semantic"][
              "weighted_score"] > 0)
    check("results_do_not_materialize_bodies_or_claim_truth",
          all(not hit.to_dict()["body_materialized"] for hit in fused.hits)
          and "not intelligence truth" in fused.to_dict()["evidence_boundary"]
          and "not model-internal" in fused.to_dict()[
              "implementation_boundary"])
    try:
        index.query(NgramQueryRequest("x", approximate=True))
    except NotImplementedError:
        check("untested_approximation_fails_explicitly", True)
    else:
        check("untested_approximation_fails_explicitly", False)
    try:
        NgramIndex((documents[0], documents[0]))
    except NgramRetrievalError:
        check("duplicate_document_identity_is_rejected", True)
    else:
        check("duplicate_document_identity_is_rejected", False)
    request = NgramQueryRequest("local routing", allowed_scopes=("tenant:a",))
    check("exact_ranking_is_deterministic",
          index.query(request).to_dict() == index.query(request).to_dict())
    from ..loop.recursive_loop import LoopLedger
    ledger = LoopLedger()
    governed = query_as_loop(
        GovernedNgramQueryRequest(
            index, NgramQueryRequest(
                "schema json", allowed_scopes=("tenant:a",), top_k=2)),
        NgramLoopContext(ledger=ledger))
    init = next(event for event in ledger.events
                if event.get("loop_id") == governed["loop_id"]
                and event.get("event") == "init")
    check("governed_query_uses_canonical_intelligence_loop",
          governed["model_calls"] == 0
          and init.get("role") == "intelligence"
          and init.get("profile_id") == "intelligence.search"
          and init.get("relationship_kind") == "starting"
          and bool(init.get("loop_definition_digest")))
    benchmark = run_frozen_benchmark(frozen_fixture) if frozen_fixture else None
    if benchmark is not None:
        check("frozen_dev_and_holdout_benchmark_completed",
              benchmark["all_queries_evaluated"]
              and set(benchmark["splits"]) == {"dev", "holdout"},
              benchmark["fixture_digest"])
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "ngram_retrieval_self_test/v1",
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests), "tests": tests,
            "benchmark": benchmark}


__all__ = (
    "BENCHMARK_SCHEMA_VERSION", "run_benchmark_fixture",
    "run_contract_checks", "run_frozen_benchmark",
    "run_frozen_benchmark_as_loop",
)
