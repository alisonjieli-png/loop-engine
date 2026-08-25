"""Independent rank-based reference metrics for the SciFact benchmark.

This module does not import the benchmark runner or Loop Engine. It provides
the second metric path used to reject evaluator drift.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ReferenceMetrics:
    ndcg_at_10: float
    recall_at_10: float
    mrr_at_10: float
    queries: int


def calculate_reference_metrics(
    qrels: Mapping[str, Mapping[str, int]],
    rankings: Mapping[str, Sequence[str]],
) -> ReferenceMetrics:
    """Calculate macro nDCG, recall, and reciprocal rank at rank 10."""
    ndcg_total = 0.0
    recall_total = 0.0
    reciprocal_rank_total = 0.0
    for query_id in sorted(qrels, key=lambda value: (len(value), value)):
        relevance = qrels[query_id]
        ranked = tuple(rankings.get(query_id, ()))[:10]
        gains = [int(relevance.get(document_id, 0)) for document_id in ranked]
        dcg = sum(
            gain / math.log2(rank + 2) for rank, gain in enumerate(gains)
        )
        ideal_gains = sorted(
            (int(value) for value in relevance.values()), reverse=True
        )[:10]
        ideal_dcg = sum(
            gain / math.log2(rank + 2)
            for rank, gain in enumerate(ideal_gains)
        )
        ndcg_total += dcg / ideal_dcg if ideal_dcg else 0.0

        relevant_ids = {
            document_id
            for document_id, value in relevance.items()
            if int(value) > 0
        }
        retrieved_relevant = relevant_ids.intersection(ranked)
        recall_total += (
            len(retrieved_relevant) / len(relevant_ids) if relevant_ids else 0.0
        )
        reciprocal_rank_total += next(
            (
                1.0 / rank
                for rank, document_id in enumerate(ranked, start=1)
                if document_id in relevant_ids
            ),
            0.0,
        )

    count = len(qrels)
    if count == 0:
        raise ValueError("the reference evaluator needs at least one query")
    return ReferenceMetrics(
        ndcg_at_10=ndcg_total / count,
        recall_at_10=recall_total / count,
        mrr_at_10=reciprocal_rank_total / count,
        queries=count,
    )

