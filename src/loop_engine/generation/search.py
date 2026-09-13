"""Task-conditioned proposal work owned by the canonical Practitioner Loop.

Adapters propose configuration addresses. This boundary checks applicability,
deduplicates evidence and proposals, preserves exclusions, and records exact
inputs and outputs. It does not run tasks, infer permissions, or promote a
candidate. Existing Run History and catalog services own durable records.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import random

from .model.fragments import GenerationError
from .search_records import SearchRequest, SearchServices
from .space import content_digest


def _eligible_evidence(request, services):
    accepted, excluded = [], []
    ids, occurrences = set(), set()
    for observation in request.observations:
        reason = ""
        occurrence = (observation.history_ref, observation.trial_occurrence_ref)
        if observation.trial_id in ids or occurrence in occurrences:
            reason = "duplicate_trial_or_evidence"
        elif observation.space_digest != request.space.digest:
            reason = "configuration_space_changed"
        elif observation.configuration_index >= request.space.cardinality:
            reason = "configuration_address_invalid"
        elif observation.objectives != request.objectives:
            reason = "objectives_not_comparable"
        elif observation.data_partition != "search_feedback":
            reason = "sealed_evaluation_must_not_guide_search"
        elif (observation.task.contract_ref != request.task.contract_ref
              or observation.task.evaluator_ref != request.task.evaluator_ref):
            reason = "task_contract_or_evaluator_not_comparable"
        elif services.resolve_evidence is None:
            reason = "evidence_resolver_unavailable"
        else:
            try:
                if services.resolve_evidence(observation) is not True:
                    reason = "evidence_not_validated"
            except Exception:
                reason = "evidence_resolution_failed"
        ids.add(observation.trial_id)
        occurrences.add(occurrence)
        if reason:
            excluded.append({"trial_id": observation.trial_id, "reason": reason})
        else:
            accepted.append(observation)
    return tuple(accepted), excluded


def _assemble(request, services):
    observations, excluded = _eligible_evidence(request, services)
    proposals, refused, drawn = [], [], 0
    seen = set()
    if not request.allow_repeated_configurations:
        seen.update(v.configuration_index for v in observations
                    if v.task.digest == request.task.digest)
    settings = services.adapter.settings()
    state = {"next_cursor": None, "search_exhausted": False}
    for proposal in services.adapter.propose(request, observations, state):
        drawn += 1
        if drawn > request.draw_limit:
            raise GenerationError("optimizer exceeded this batch's declared draw limit")
        index, parents, rationale = proposal
        if any(parent not in {v.trial_id for v in observations} for parent in parents):
            raise GenerationError("optimizer cites evidence that was not admitted")
        if type(index) is not int or not 0 <= index < request.space.cardinality:
            raise GenerationError("optimizer proposed an address outside the declared space")
        reasons = list(request.space.exclusions(index))
        if index % request.shard_count != request.shard_index:
            reasons.append("outside_declared_shard")
        if index in seen:
            reasons.append("configuration_already_observed_or_proposed")
        if reasons:
            refused.append({"configuration_index": index, "reasons": reasons})
            continue
        seen.add(index)
        config = request.space.configuration_at(index)
        proposals.append({"candidate_id": request.space.digest + ":" + str(index),
            "configuration_index": index, "configuration": config,
            "configuration_digest": content_digest(config), "parent_trial_ids": list(parents),
            "proposal_method": services.adapter.adapter_ref, "rationale": rationale,
            "state": "proposed", "executed": False, "task_accepted": False})
        if len(proposals) >= request.batch_size:
            break
    return {"record_type": "configuration_search_batch/v1", "request_digest": request.digest,
            "space_digest": request.space.digest, "raw_cardinality_decimal": str(request.space.cardinality),
            "valid_cardinality": None, "adapter_ref": services.adapter.adapter_ref,
            "adapter_settings": settings, "task_digest": request.task.digest,
            "observations_supplied": len(request.observations),
            "observations_validated": [v.trial_id for v in observations],
            "excluded_observations": excluded, "proposals": proposals,
            "refused_proposals": refused, "draws": drawn, **state,
            "exhaustion_scope": "declared_cursor_and_shard_only",
            "task_execution_performed": False, "promotion_performed": False}


def propose_configurations(request: SearchRequest, services: SearchServices, *, parent=None):
    """Run one proposal operation under the existing canonical Loop runtime."""
    from ..loop.encapsulate import as_practitioner_loop
    if not isinstance(request, SearchRequest) or not isinstance(services, SearchServices):
        raise GenerationError("proposal work requires typed request and services")
    return as_practitioner_loop("propose task-conditioned configurations",
                                lambda: _assemble(request, services), parent=parent)


@dataclass(frozen=True)
class GridSearchAdapter:
    """Streaming exact enumeration with resumable, disjoint shard cursors."""

    adapter_ref: str = "generation.exact_enumeration@1.0.0"

    def settings(self):
        return {"method": "exact_enumeration"}

    def propose(self, request, observations, state):
        index = request.cursor
        index += (request.shard_index - index) % request.shard_count
        for _ in range(request.draw_limit):
            if index >= request.space.cardinality:
                state["search_exhausted"] = True
                break
            current = index
            index += request.shard_count
            state["next_cursor"] = min(index, request.space.cardinality)
            state["search_exhausted"] = index >= request.space.cardinality
            yield current, (), "next address in the declared exact-enumeration shard"


@dataclass(frozen=True)
class RandomSearchAdapter:
    """Explicit seeded exploration; sampling is not exhaustive coverage."""

    adapter_ref: str = "generation.random_search@1.0.0"

    def settings(self):
        return {"method": "random_search"}

    def propose(self, request, observations, state):
        generator = random.Random(request.seed)
        size = (request.space.cardinality + request.shard_count - 1 - request.shard_index) // request.shard_count
        if size <= 0:
            return
        for _ in range(request.draw_limit):
            index = request.shard_index + request.shard_count * generator.randrange(size)
            yield index, (), "seeded exploration in the declared shard"


@dataclass(frozen=True)
class VectorWarmStartAdapter:
    """Propose configurations from similar tasks, without copying their scores."""

    minimum_similarity: float
    adapter_ref: str = "generation.vector_warm_start@1.0.0"

    def __post_init__(self):
        if (type(self.minimum_similarity) not in (int, float)
                or not math.isfinite(self.minimum_similarity)
                or not -1 <= self.minimum_similarity <= 1):
            raise GenerationError("cosine similarity threshold must be between -1 and 1")

    def settings(self):
        return {"method": "vector_warm_start", "minimum_similarity": self.minimum_similarity,
                "transfers_scores": False}

    def propose(self, request, observations, state):
        target = request.task
        def unit_vector(values):
            magnitude = max((abs(value) for value in values), default=0)
            if not magnitude:
                return ()
            scaled = tuple(value / magnitude for value in values)
            length = math.hypot(*scaled)
            return tuple(value / length for value in scaled)

        target_unit = unit_vector(target.features)
        if not target_unit:
            raise GenerationError("vector warm start requires a nonzero task feature vector")
        ranked = []
        # Prefer non-dominated measurements within each source task. Scores
        # from different tasks are not pooled into a fictitious common label.
        def dominates(left, right):
            if left.task.digest != right.task.digest:
                return False
            comparisons = [((a <= b, a < b) if objective.direction == "minimize"
                            else (a >= b, a > b))
                           for a, b, objective in zip(left.values, right.values, request.objectives)]
            return all(v[0] for v in comparisons) and any(v[1] for v in comparisons)

        measured = [v for v in observations if v.state == "completed"
                    and all(value is not None for value in v.values)]
        for observation in observations:
            source = observation.task
            if (observation.state != "completed" or any(v is None for v in observation.values)
                    or source.feature_space_ref != target.feature_space_ref
                    or len(source.features) != len(target.features)):
                continue
            if any(dominates(other, observation) for other in measured):
                continue
            source_unit = unit_vector(source.features)
            if not source_unit:
                continue
            similarity = sum(a * b for a, b in zip(target_unit, source_unit))
            if similarity >= self.minimum_similarity:
                ranked.append((similarity, observation))
        ranked.sort(key=lambda item: (-item[0], item[1].trial_id))
        for similarity, observation in ranked[:request.draw_limit]:
            yield (observation.configuration_index, (observation.trial_id,),
                   f"cosine similarity {similarity:.8g}; must be evaluated on the current task")


def self_test() -> dict:
    from .search_checks import run_checks
    return run_checks()
