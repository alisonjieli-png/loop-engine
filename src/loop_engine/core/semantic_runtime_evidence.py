"""Reliability envelopes and execution-strategy evidence for semantic Loops.

These records summarize measured fixture outcomes. They are passive evidence,
not runtime authority, qualification by themselves, or model confidence.
"""
from __future__ import annotations

from dataclasses import dataclass

from .semantic_runtime_records import (
    SemanticRuntimeContractError, _digest, _identifier, _names)


@dataclass(frozen=True)
class SemanticReliabilityEnvelope:
    envelope_id: str
    contract_digest: str
    realization_binding_digest: str
    interpreter_profile_digest: str
    fixture_population_digest: str
    fixture_count: int
    accepted_count: int
    rejected_count: int
    abstained_count: int
    false_accept_count: int
    unsafe_commit_count: int
    model_calls: int
    verifier_profile_digest: str
    qualified: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _identifier("envelope_id", self.envelope_id)
        for label in (
                "contract_digest", "realization_binding_digest",
                "interpreter_profile_digest", "fixture_population_digest",
                "verifier_profile_digest"):
            _digest(label, getattr(self, label))
        counts = (
            self.fixture_count, self.accepted_count, self.rejected_count,
            self.abstained_count, self.false_accept_count,
            self.unsafe_commit_count, self.model_calls)
        if (any(not isinstance(value, int) or value < 0 for value in counts)
                or self.accepted_count + self.rejected_count
                + self.abstained_count != self.fixture_count
                or not isinstance(self.qualified, bool)):
            raise SemanticRuntimeContractError(
                "semantic reliability counts are inconsistent")
        object.__setattr__(
            self, "evidence_refs",
            _names("evidence_refs", self.evidence_refs, required=True))

    @property
    def observed_unsafe_commit_rate_ppm(self) -> int:
        if not self.fixture_count:
            return 1_000_000
        return int(1_000_000 * self.unsafe_commit_count / self.fixture_count)


@dataclass(frozen=True)
class SemanticStrategyMeasurement:
    strategy: str
    success: bool
    false_accepts: int
    unsafe_commits: int
    abstained: bool
    model_calls: int
    prompt_tokens: int | None
    output_tokens: int | None
    cost: float | None
    latency_ms: float


@dataclass(frozen=True)
class SemanticStrategyBenchmark:
    benchmark_id: str
    contract_digest: str
    population_digest: str
    measurements: tuple[SemanticStrategyMeasurement, ...]

    def __post_init__(self) -> None:
        _identifier("benchmark_id", self.benchmark_id)
        _digest("contract_digest", self.contract_digest)
        _digest("population_digest", self.population_digest)
        values = tuple(self.measurements)
        if (not values or any(not isinstance(
                item, SemanticStrategyMeasurement) for item in values)
                or len({item.strategy for item in values}) != len(values)):
            raise SemanticRuntimeContractError(
                "semantic benchmark needs unique strategy measurements")
        object.__setattr__(self, "measurements", values)


__all__ = (
    "SemanticReliabilityEnvelope", "SemanticStrategyBenchmark",
    "SemanticStrategyMeasurement",
)
