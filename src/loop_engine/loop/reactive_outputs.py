"""Immutable candidate, evaluation, portfolio, and query records.

Owns reactive output identity and deterministic portfolio projection contracts.
These passive records do not execute, persist, publish, or grant access.
"""
from __future__ import annotations

from dataclasses import dataclass

from .atomic_primitives import LoopValueRef
from .reactive_contracts import (
    CandidateVerdict, MetricDirection, PortfolioPolicy, PortfolioView,
    ReactiveContractError, _SEMVER, _bounded_score, _digest, _enum,
    _identity, _names, _timestamp)


@dataclass(frozen=True)
class CandidateOutput:
    """Immutable output produced by one finite Loop activation."""

    candidate_id: str
    series_id: str
    run_id: str
    activation_id: str
    producer_loop_id: str
    output_port_ref: str
    topic_ref: str
    subject_ref: str
    input_snapshot_ref: str
    input_watermark: str
    payload_ref: LoopValueRef
    evidence_refs: tuple[str, ...]
    settings_digest: str
    procedure_digest: str
    generated_at: str
    valid_from: str
    valid_until: str = ""
    expires_at: str = ""
    diversity_tags: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (
                ("candidate_id", self.candidate_id),
                ("series_id", self.series_id), ("run_id", self.run_id),
                ("activation_id", self.activation_id),
                ("producer_loop_id", self.producer_loop_id),
                ("output_port_ref", self.output_port_ref),
                ("topic_ref", self.topic_ref),
                ("subject_ref", self.subject_ref),
                ("input_snapshot_ref", self.input_snapshot_ref),
                ("input_watermark", self.input_watermark)):
            _identity(label, value)
        if not isinstance(self.payload_ref, LoopValueRef):
            raise ReactiveContractError(
                "candidate payload must use an exact LoopValueRef")
        object.__setattr__(
            self, "evidence_refs", _names("evidence_refs", self.evidence_refs))
        object.__setattr__(
            self, "diversity_tags",
            _names("diversity_tags", self.diversity_tags))
        object.__setattr__(
            self, "supersedes", _names("supersedes", self.supersedes))
        _digest("settings_digest", self.settings_digest)
        _digest("procedure_digest", self.procedure_digest)
        _timestamp("generated_at", self.generated_at)
        _timestamp("valid_from", self.valid_from)
        _timestamp("valid_until", self.valid_until, optional=True)
        _timestamp("expires_at", self.expires_at, optional=True)
        if self.candidate_id in self.supersedes:
            raise ReactiveContractError("candidate cannot supersede itself")

    def to_dict(self) -> dict:
        return {
            "record_type": "candidate_output/v1",
            "candidate_id": self.candidate_id, "series_id": self.series_id,
            "run_id": self.run_id, "activation_id": self.activation_id,
            "producer_loop_id": self.producer_loop_id,
            "output_port_ref": self.output_port_ref,
            "topic_ref": self.topic_ref, "subject_ref": self.subject_ref,
            "input_snapshot_ref": self.input_snapshot_ref,
            "input_watermark": self.input_watermark,
            "payload_ref": self.payload_ref.to_dict(),
            "evidence_refs": list(self.evidence_refs),
            "settings_digest": self.settings_digest,
            "procedure_digest": self.procedure_digest,
            "generated_at": self.generated_at, "valid_from": self.valid_from,
            "valid_until": self.valid_until, "expires_at": self.expires_at,
            "diversity_tags": list(self.diversity_tags),
            "supersedes": list(self.supersedes),
        }

    @classmethod
    def from_dict(cls, value: dict) -> "CandidateOutput":
        expected = {
            "record_type", "candidate_id", "series_id", "run_id",
            "activation_id", "producer_loop_id", "output_port_ref",
            "topic_ref", "subject_ref", "input_snapshot_ref",
            "input_watermark", "payload_ref", "evidence_refs",
            "settings_digest", "procedure_digest", "generated_at",
            "valid_from", "valid_until", "expires_at", "diversity_tags",
            "supersedes",
        }
        if (not isinstance(value, dict) or set(value) != expected
                or value.get("record_type") != "candidate_output/v1"):
            raise ReactiveContractError("candidate output has an invalid shape")
        body = dict(value)
        body.pop("record_type")
        body["payload_ref"] = LoopValueRef.from_dict(body["payload_ref"])
        for field_name in (
                "evidence_refs", "diversity_tags", "supersedes"):
            body[field_name] = tuple(body[field_name])
        return cls(**body)


@dataclass(frozen=True)
class ConfidenceVector:
    """Evidence-aware confidence dimensions, never one model-only number."""

    model_assessment: float = 0.0
    evidence_coverage: float = 0.0
    source_quality: float = 0.0
    deterministic_verification: float = 0.0
    independent_verification: float = 0.0
    historical_calibration: float = 0.0
    council_agreement: float = 0.0
    freshness: float = 0.0
    applicability: float = 0.0
    execution_success: float = 0.0
    contradiction: float = 0.0

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            _bounded_score(name, value)

    def metric(self, name: str) -> float:
        if name not in self.__dict__:
            raise ReactiveContractError(
                f"confidence metric {name!r} is unavailable")
        return float(getattr(self, name))

    def to_dict(self) -> dict[str, float]:
        return {name: float(value) for name, value in self.__dict__.items()}

    @classmethod
    def from_dict(cls, value: dict) -> "ConfidenceVector":
        if not isinstance(value, dict) or set(value) != set(cls().__dict__):
            raise ReactiveContractError("confidence vector has an invalid shape")
        return cls(**value)


@dataclass(frozen=True)
class CandidateEvaluation:
    """Independent, versioned assessment of one immutable candidate."""

    evaluation_id: str
    candidate_ref: str
    evaluator_loop_refs: tuple[str, ...]
    policy_ref: str
    policy_version: str
    verdict: CandidateVerdict | str
    evaluated_at: str
    confidence: ConfidenceVector
    risk: float = 0.0
    cost: float = 0.0
    latency: float = 0.0
    novelty: float = 0.0
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for label, value in (
                ("evaluation_id", self.evaluation_id),
                ("candidate_ref", self.candidate_ref),
                ("policy_ref", self.policy_ref)):
            _identity(label, value)
        if not _SEMVER.fullmatch(self.policy_version):
            raise ReactiveContractError(
                "evaluation policy version must use MAJOR.MINOR.PATCH")
        object.__setattr__(
            self, "verdict", _enum(
                self.verdict, CandidateVerdict, "candidate verdict"))
        evaluators = _names("evaluator_loop_refs", self.evaluator_loop_refs)
        if not evaluators:
            raise ReactiveContractError(
                "candidate evaluation requires an evaluator Loop")
        object.__setattr__(self, "evaluator_loop_refs", evaluators)
        object.__setattr__(
            self, "rejection_reasons",
            _names("rejection_reasons", self.rejection_reasons))
        _timestamp("evaluated_at", self.evaluated_at)
        if not isinstance(self.confidence, ConfidenceVector):
            raise ReactiveContractError(
                "candidate evaluation requires ConfidenceVector")
        for name in ("risk", "cost", "latency", "novelty"):
            _bounded_score(name, getattr(self, name))
        if (self.verdict in {CandidateVerdict.REJECTED,
                             CandidateVerdict.RETRACTED}
                and not self.rejection_reasons):
            raise ReactiveContractError(
                "rejected or retracted evaluation needs reasons")

    def metric(self, name: str) -> float:
        if name in {"risk", "cost", "latency", "novelty"}:
            return float(getattr(self, name))
        return self.confidence.metric(name)

    def to_dict(self) -> dict:
        return {
            "record_type": "candidate_evaluation/v1",
            "evaluation_id": self.evaluation_id,
            "candidate_ref": self.candidate_ref,
            "evaluator_loop_refs": list(self.evaluator_loop_refs),
            "policy_ref": self.policy_ref,
            "policy_version": self.policy_version,
            "verdict": self.verdict.value,
            "evaluated_at": self.evaluated_at,
            "confidence": self.confidence.to_dict(),
            "risk": self.risk, "cost": self.cost,
            "latency": self.latency, "novelty": self.novelty,
            "rejection_reasons": list(self.rejection_reasons),
        }

    @classmethod
    def from_dict(cls, value: dict) -> "CandidateEvaluation":
        expected = {
            "record_type", "evaluation_id", "candidate_ref",
            "evaluator_loop_refs", "policy_ref", "policy_version", "verdict",
            "evaluated_at", "confidence", "risk", "cost", "latency",
            "novelty", "rejection_reasons",
        }
        if (not isinstance(value, dict) or set(value) != expected
                or value.get("record_type") != "candidate_evaluation/v1"):
            raise ReactiveContractError(
                "candidate evaluation has an invalid shape")
        body = dict(value)
        body.pop("record_type")
        body["evaluator_loop_refs"] = tuple(body["evaluator_loop_refs"])
        body["rejection_reasons"] = tuple(body["rejection_reasons"])
        body["confidence"] = ConfidenceVector.from_dict(body["confidence"])
        return cls(**body)


@dataclass(frozen=True)
class PortfolioEntry:
    """One candidate rank under one exact portfolio policy version."""

    candidate_ref: str
    evaluation_ref: str
    rank: int
    derived_score: float
    rank_dimensions: tuple[tuple[str, float], ...]
    inclusion_reason: str

    def to_dict(self) -> dict:
        return {
            "candidate_ref": self.candidate_ref,
            "evaluation_ref": self.evaluation_ref, "rank": self.rank,
            "derived_score": self.derived_score,
            "rank_dimensions": [list(item) for item in self.rank_dimensions],
            "inclusion_reason": self.inclusion_reason,
        }

    @classmethod
    def from_dict(cls, value: dict) -> "PortfolioEntry":
        expected = {
            "candidate_ref", "evaluation_ref", "rank", "derived_score",
            "rank_dimensions", "inclusion_reason",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise ReactiveContractError("portfolio entry has an invalid shape")
        body = dict(value)
        body["rank_dimensions"] = tuple(
            (str(item[0]), float(item[1])) for item in body["rank_dimensions"])
        return cls(**body)


@dataclass(frozen=True)
class OutputPortfolioSnapshot:
    """Immutable point-in-time ranked view over attempted candidates."""

    series_id: str
    topic_ref: str
    portfolio_version: int
    policy_id: str
    policy_version: str
    policy_digest: str
    view: PortfolioView | str
    input_watermark: str
    generated_at: str
    entries: tuple[PortfolioEntry, ...]
    considered_candidate_refs: tuple[str, ...]
    rejected_candidate_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for label, value in (("series_id", self.series_id),
                             ("topic_ref", self.topic_ref),
                             ("policy_id", self.policy_id),
                             ("input_watermark", self.input_watermark)):
            _identity(label, value)
        if (not isinstance(self.portfolio_version, int)
                or isinstance(self.portfolio_version, bool)
                or self.portfolio_version < 1):
            raise ReactiveContractError(
                "portfolio version must be a positive integer")
        if not _SEMVER.fullmatch(self.policy_version):
            raise ReactiveContractError("portfolio policy version is invalid")
        _digest("policy_digest", self.policy_digest)
        object.__setattr__(
            self, "view", _enum(self.view, PortfolioView, "portfolio view"))
        _timestamp("generated_at", self.generated_at)
        if any(not isinstance(item, PortfolioEntry) for item in self.entries):
            raise ReactiveContractError(
                "portfolio entries must be typed records")
        if tuple(item.rank for item in self.entries) != tuple(
                range(1, len(self.entries) + 1)):
            raise ReactiveContractError("portfolio ranks must be contiguous")
        considered = set(self.considered_candidate_refs)
        selected = {item.candidate_ref for item in self.entries}
        rejected = set(self.rejected_candidate_refs)
        if not selected <= considered or not rejected <= considered:
            raise ReactiveContractError(
                "portfolio selections must have been considered")
        if selected & rejected:
            raise ReactiveContractError(
                "selected and rejected candidates cannot overlap")

    def to_dict(self) -> dict:
        return {
            "record_type": "output_portfolio_snapshot/v1",
            "series_id": self.series_id, "topic_ref": self.topic_ref,
            "portfolio_version": self.portfolio_version,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_digest": self.policy_digest, "view": self.view.value,
            "input_watermark": self.input_watermark,
            "generated_at": self.generated_at,
            "entries": [item.to_dict() for item in self.entries],
            "considered_candidate_refs": list(
                self.considered_candidate_refs),
            "rejected_candidate_refs": list(self.rejected_candidate_refs),
        }

    @classmethod
    def from_dict(cls, value: dict) -> "OutputPortfolioSnapshot":
        expected = {
            "record_type", "series_id", "topic_ref", "portfolio_version",
            "policy_id", "policy_version", "policy_digest", "view",
            "input_watermark", "generated_at", "entries",
            "considered_candidate_refs", "rejected_candidate_refs",
        }
        if (not isinstance(value, dict) or set(value) != expected
                or value.get("record_type") != "output_portfolio_snapshot/v1"):
            raise ReactiveContractError(
                "output portfolio snapshot has an invalid shape")
        body = dict(value)
        body.pop("record_type")
        body["entries"] = tuple(
            PortfolioEntry.from_dict(item) for item in body["entries"])
        body["considered_candidate_refs"] = tuple(
            body["considered_candidate_refs"])
        body["rejected_candidate_refs"] = tuple(
            body["rejected_candidate_refs"])
        return cls(**body)


@dataclass(frozen=True)
class PortfolioBuildRequest:
    """Cohesive deterministic inputs for one portfolio projection."""

    series_id: str
    topic_ref: str
    portfolio_version: int
    input_watermark: str
    generated_at: str
    policy: PortfolioPolicy
    candidates: tuple[CandidateOutput, ...]
    evaluations: tuple[CandidateEvaluation, ...]


def _score(evaluation: CandidateEvaluation, policy: PortfolioPolicy) \
        -> tuple[float, tuple[tuple[str, float], ...]]:
    dimensions = []
    score = 0.0
    total_weight = sum(item.weight for item in policy.dimensions)
    for dimension in policy.dimensions:
        raw = evaluation.metric(dimension.name)
        oriented = raw if dimension.direction is MetricDirection.MAXIMIZE \
            else 1.0 - raw
        score += oriented * dimension.weight
        dimensions.append((dimension.name, raw))
    return score / total_weight, tuple(dimensions)


def _oriented_metrics(
        evaluation: CandidateEvaluation,
        policy: PortfolioPolicy) -> tuple[float, ...]:
    return tuple(
        evaluation.metric(dimension.name)
        if dimension.direction is MetricDirection.MAXIMIZE
        else 1.0 - evaluation.metric(dimension.name)
        for dimension in policy.dimensions)


def _pareto_frontier(eligible, policy: PortfolioPolicy):
    frontier = []
    for candidate in eligible:
        candidate_vector = _oriented_metrics(candidate[1], policy)
        dominated = False
        for alternative in eligible:
            if alternative is candidate:
                continue
            alternative_vector = _oriented_metrics(alternative[1], policy)
            if (all(left >= right for left, right in zip(
                    alternative_vector, candidate_vector))
                    and any(left > right for left, right in zip(
                        alternative_vector, candidate_vector))):
                dominated = True
                break
        if not dominated:
            frontier.append(candidate)
    return frontier


def build_output_portfolio(
        request: PortfolioBuildRequest) -> OutputPortfolioSnapshot:
    """Build one policy-bound snapshot without mutating candidates."""
    if not isinstance(request, PortfolioBuildRequest):
        raise ReactiveContractError(
            "portfolio build requires PortfolioBuildRequest")
    if not isinstance(request.policy, PortfolioPolicy):
        raise ReactiveContractError("portfolio build requires a policy")
    candidates = tuple(request.candidates)
    evaluations = tuple(request.evaluations)
    if any(not isinstance(item, CandidateOutput) for item in candidates):
        raise ReactiveContractError("portfolio candidates must be typed")
    if any(not isinstance(item, CandidateEvaluation) for item in evaluations):
        raise ReactiveContractError("portfolio evaluations must be typed")
    candidate_map = {item.candidate_id: item for item in candidates}
    evaluation_map = {item.candidate_ref: item for item in evaluations}
    if len(candidate_map) != len(candidates) or len(evaluation_map) != len(
            evaluations):
        raise ReactiveContractError(
            "portfolio candidate and evaluation identities must be unique")
    if set(evaluation_map) - set(candidate_map):
        raise ReactiveContractError(
            "portfolio evaluation references an unknown candidate")
    if request.policy.view is PortfolioView.ALL_ATTEMPTED:
        attempted = []
        for candidate in candidates:
            evaluation = evaluation_map.get(candidate.candidate_id)
            if evaluation is None:
                attempted.append((candidate, "", 0.0, (),
                                  "attempted without evaluation"))
            else:
                derived, dimensions = _score(evaluation, request.policy)
                attempted.append((candidate, evaluation.evaluation_id,
                                  derived, dimensions,
                                  f"attempted with {evaluation.verdict.value} "
                                  "evaluation"))
        attempted.sort(key=lambda item: (
            item[0].generated_at, item[0].candidate_id))
        selected_attempts = attempted[:request.policy.maximum_results]
        entries = tuple(PortfolioEntry(
            candidate.candidate_id, evaluation_ref, index,
            round(score, 12), dimensions, reason)
            for index, (candidate, evaluation_ref, score, dimensions, reason)
            in enumerate(selected_attempts, start=1))
        omitted = tuple(item[0].candidate_id
                        for item in attempted[request.policy.maximum_results:])
        return OutputPortfolioSnapshot(
            request.series_id, request.topic_ref, request.portfolio_version,
            request.policy.policy_id, request.policy.version,
            request.policy.content_digest, request.policy.view,
            request.input_watermark, request.generated_at, entries,
            tuple(item.candidate_id for item in candidates), omitted)
    eligible = []
    rejected = []
    for candidate in candidates:
        evaluation = evaluation_map.get(candidate.candidate_id)
        if evaluation is None:
            rejected.append(candidate.candidate_id)
            continue
        if request.policy.view is PortfolioView.VERIFIED_TOP_K \
                and evaluation.verdict is not CandidateVerdict.VERIFIED:
            rejected.append(candidate.candidate_id)
            continue
        if evaluation.verdict in {
                CandidateVerdict.REJECTED, CandidateVerdict.RETRACTED,
                CandidateVerdict.SUPERSEDED}:
            rejected.append(candidate.candidate_id)
            continue
        derived, dimensions = _score(evaluation, request.policy)
        eligible.append((candidate, evaluation, derived, dimensions))
    eligible.sort(key=lambda item: (-item[2], item[0].candidate_id))
    ranked = (_pareto_frontier(eligible, request.policy)
              if request.policy.view is PortfolioView.PARETO else eligible)
    ranked.sort(key=lambda item: (-item[2], item[0].candidate_id))
    selected = ranked[:request.policy.maximum_results]
    selected_ids = {item[0].candidate_id for item in selected}
    rejected.extend(item[0].candidate_id for item in eligible
                    if item[0].candidate_id not in selected_ids)
    entries = tuple(PortfolioEntry(
        candidate.candidate_id, evaluation.evaluation_id, index,
        round(score, 12), dimensions,
        f"selected by {request.policy.view.value}")
        for index, (candidate, evaluation, score, dimensions)
        in enumerate(selected, start=1))
    return OutputPortfolioSnapshot(
        request.series_id, request.topic_ref, request.portfolio_version,
        request.policy.policy_id, request.policy.version,
        request.policy.content_digest, request.policy.view,
        request.input_watermark,
        request.generated_at, entries,
        tuple(item.candidate_id for item in candidates),
        tuple(sorted(set(rejected))))


@dataclass(frozen=True)
class OutputQuery:
    """Read-only portfolio request that never implies producer activation."""

    series_id: str
    topic_ref: str
    view: PortfolioView | str
    maximum_results: int = 10
    as_of_portfolio_version: int | None = None
    minimum_derived_score: float = 0.0

    def __post_init__(self) -> None:
        _identity("series_id", self.series_id)
        _identity("topic_ref", self.topic_ref)
        object.__setattr__(
            self, "view", _enum(self.view, PortfolioView, "query view"))
        if (not isinstance(self.maximum_results, int)
                or isinstance(self.maximum_results, bool)
                or self.maximum_results < 1):
            raise ReactiveContractError(
                "query maximum_results must be positive")
        if (self.as_of_portfolio_version is not None
                and (not isinstance(self.as_of_portfolio_version, int)
                     or isinstance(self.as_of_portfolio_version, bool)
                     or self.as_of_portfolio_version < 1)):
            raise ReactiveContractError(
                "as-of portfolio version must be positive")
        _bounded_score("minimum_derived_score", self.minimum_derived_score)


__all__ = (
    "CandidateEvaluation", "CandidateOutput", "ConfidenceVector",
    "OutputPortfolioSnapshot", "OutputQuery", "PortfolioBuildRequest",
    "PortfolioEntry", "build_output_portfolio",
)
