"""Passive finite-distribution and observed information-update evidence.

This module owns exact categorical probability checks plus Shannon entropy,
Shannon surprisal, and Bayesian surprise calculations. It performs no model
call, belief update, retrieval, state mutation, or promotion.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass

from .information_evidence_contracts import (
    InformationTheoryEvidenceError,
    _number,
    _text,
)

INFORMATION_UPDATE_SCHEMA = "information_update_evidence/v1"
FORECAST_SCORE_SCHEMA = "categorical_forecast_score/v1"


@dataclass(frozen=True)
class CategoricalDistribution:
    """One normalized finite distribution over named discrete outcomes."""

    distribution_id: str
    variable_ref: str
    probabilities: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        _text(self.distribution_id, "distribution_id")
        _text(self.variable_ref, "variable_ref")
        try:
            rows = tuple(self.probabilities)
        except TypeError as exc:
            raise InformationTheoryEvidenceError(
                "probabilities must be a sequence"
            ) from exc
        if not rows:
            raise InformationTheoryEvidenceError("a distribution cannot be empty")
        normalized: list[tuple[str, float]] = []
        for row in rows:
            if not isinstance(row, tuple) or len(row) != 2:
                raise InformationTheoryEvidenceError(
                    "probabilities need (label, probability) pairs"
                )
            label = _text(row[0], "probability label")
            probability = _number(row[1], "probability", minimum=0.0)
            if probability > 1.0:
                raise InformationTheoryEvidenceError("probability cannot exceed one")
            normalized.append((label, probability))
        if len({label for label, _value in normalized}) != len(normalized):
            raise InformationTheoryEvidenceError("distribution labels cannot repeat")
        total = math.fsum(value for _label, value in normalized)
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise InformationTheoryEvidenceError(
                "distribution probabilities must sum to one"
            )
        object.__setattr__(
            self,
            "probabilities",
            tuple(sorted((label, value / total) for label, value in normalized)),
        )

    @property
    def entropy_bits(self) -> float:
        return -math.fsum(
            probability * math.log2(probability)
            for _label, probability in self.probabilities
            if probability > 0.0
        )

    def probability(self, label: str) -> float:
        selected = _text(label, "outcome label")
        return dict(self.probabilities).get(selected, 0.0)

    def to_dict(self) -> dict[str, object]:
        return {
            "distribution_id": self.distribution_id,
            "variable_ref": self.variable_ref,
            "probabilities": [
                {"label": label, "probability": probability}
                for label, probability in self.probabilities
            ],
            "entropy_bits": self.entropy_bits,
        }


def _kl_bits(
    posterior: CategoricalDistribution,
    prior: CategoricalDistribution,
) -> tuple[float | None, bool]:
    if posterior.variable_ref != prior.variable_ref:
        raise InformationTheoryEvidenceError(
            "prior and posterior must describe the same belief variable"
        )
    posterior_values = dict(posterior.probabilities)
    prior_values = dict(prior.probabilities)
    if set(posterior_values) != set(prior_values):
        raise InformationTheoryEvidenceError(
            "prior and posterior must use the same support"
        )
    if any(
        posterior_values[label] > 0.0 and prior_values[label] == 0.0
        for label in posterior_values
    ):
        return None, True
    value = math.fsum(
        posterior_values[label]
        * (math.log2(posterior_values[label]) - math.log2(prior_values[label]))
        for label in posterior_values
        if posterior_values[label] > 0.0
    )
    return (max(0.0, value), False) if math.isfinite(value) else (None, True)


@dataclass(frozen=True)
class InformationUpdateEvidence:
    """Shannon and Bayesian surprise for one observed update."""

    update_id: str
    observation_ref: str
    evidence_ref: str
    observed_outcome: str
    predictive_distribution: CategoricalDistribution
    prior_beliefs: CategoricalDistribution
    posterior_beliefs: CategoricalDistribution
    record_type: str = INFORMATION_UPDATE_SCHEMA

    def __post_init__(self) -> None:
        for name in ("update_id", "observation_ref", "evidence_ref"):
            _text(getattr(self, name), name)
        _text(self.observed_outcome, "observed_outcome")
        if self.record_type != INFORMATION_UPDATE_SCHEMA:
            raise InformationTheoryEvidenceError(
                "information update record type is unsupported"
            )
        for name in (
            "predictive_distribution",
            "prior_beliefs",
            "posterior_beliefs",
        ):
            if not isinstance(getattr(self, name), CategoricalDistribution):
                raise InformationTheoryEvidenceError(
                    f"{name} must use CategoricalDistribution"
                )
        _kl_bits(self.posterior_beliefs, self.prior_beliefs)

    @property
    def shannon_surprisal_bits(self) -> float | None:
        probability = self.predictive_distribution.probability(self.observed_outcome)
        return None if probability == 0.0 else -math.log2(probability)

    @property
    def shannon_surprisal_infinite(self) -> bool:
        return self.predictive_distribution.probability(self.observed_outcome) == 0.0

    @property
    def bayesian_surprise(self) -> tuple[float | None, bool]:
        return _kl_bits(self.posterior_beliefs, self.prior_beliefs)

    def to_dict(self) -> dict[str, object]:
        bayesian_bits, bayesian_infinite = self.bayesian_surprise
        return {
            "record_type": self.record_type,
            "update_id": self.update_id,
            "observation_ref": self.observation_ref,
            "evidence_ref": self.evidence_ref,
            "observed_outcome": self.observed_outcome,
            "predictive_distribution": self.predictive_distribution.to_dict(),
            "prior_beliefs": self.prior_beliefs.to_dict(),
            "posterior_beliefs": self.posterior_beliefs.to_dict(),
            "shannon_surprisal_bits": self.shannon_surprisal_bits,
            "shannon_surprisal_infinite": self.shannon_surprisal_infinite,
            "bayesian_surprise_bits": bayesian_bits,
            "bayesian_surprise_infinite": bayesian_infinite,
            "gradient_surprise_measured": False,
            "measurement_specification_bound": False,
            "population_and_evaluator_bound": False,
            "issued_measurement": False,
            "grants_authority": False,
        }


@dataclass(frozen=True, init=False)
class CategoricalForecastScore:
    """Recomputed proper losses for one candidate forecast and observation.

    These values evaluate probability accuracy, not entropy reduction or
    decision utility. The input references are not canonically resolved, and
    forecast-before-outcome ordering is not established by this calculator.
    """

    update_id: str
    forecast_digest: str
    variable_ref: str
    observation_ref: str
    evidence_ref: str
    observed_outcome: str
    support_size: int
    multiclass_brier_loss: float
    normalized_brier_loss: float
    log_loss_bits: float | None
    log_loss_infinite: bool

    def __init__(self, *args, **kwargs):
        raise TypeError("use score_categorical_forecast to recompute the score")

    def to_dict(self) -> dict[str, object]:
        return {
            "record_type": FORECAST_SCORE_SCHEMA,
            "update_id": self.update_id,
            "forecast_digest": self.forecast_digest,
            "variable_ref": self.variable_ref,
            "observation_ref": self.observation_ref,
            "evidence_ref": self.evidence_ref,
            "observed_outcome": self.observed_outcome,
            "support_size": self.support_size,
            "multiclass_brier_loss": self.multiclass_brier_loss,
            "normalized_brier_loss": self.normalized_brier_loss,
            "normalization": "multiclass_brier_loss_divided_by_two",
            "log_loss_bits": self.log_loss_bits,
            "log_loss_infinite": self.log_loss_infinite,
            "metric_direction": "lower_is_better",
            "measurement_specification_bound": False,
            "population_and_evaluator_bound": False,
            "forecast_precedes_outcome_verified": False,
            "calibration_established": False,
            "issued_measurement": False,
            "grants_authority": False,
        }


def score_categorical_forecast(
    update: InformationUpdateEvidence,
) -> CategoricalForecastScore:
    """Score a declared finite predictive distribution against its outcome.

    Quadratic loss is sum((p[k] - indicator(k == outcome)) ** 2), in [0, 2].
    Division by two preserves propriety and gives [0, 1] bounded loss.
    Log loss uses bits and represents zero-probability events explicitly as
    infinite, never as JSON Infinity or a silently clipped finite value.
    """
    if not isinstance(update, InformationUpdateEvidence):
        raise TypeError("forecast scoring needs InformationUpdateEvidence")
    supplied = update.predictive_distribution
    distribution = CategoricalDistribution(
        supplied.distribution_id, supplied.variable_ref, supplied.probabilities)
    outcome = _text(update.observed_outcome, "observed_outcome")
    values = dict(distribution.probabilities)
    if outcome not in values:
        raise InformationTheoryEvidenceError(
            "forecast outcome must belong to the declared categorical support")
    brier = math.fsum(
        (probability - float(label == outcome)) ** 2
        for label, probability in distribution.probabilities)
    realized_probability = values[outcome]
    forecast_digest = hashlib.sha256(json.dumps(
        distribution.to_dict(), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()
    result = object.__new__(CategoricalForecastScore)
    fields = {
        "update_id": _text(update.update_id, "update_id"),
        "forecast_digest": forecast_digest,
        "variable_ref": distribution.variable_ref,
        "observation_ref": _text(update.observation_ref, "observation_ref"),
        "evidence_ref": _text(update.evidence_ref, "evidence_ref"),
        "observed_outcome": outcome,
        "support_size": len(values),
        "multiclass_brier_loss": brier,
        "normalized_brier_loss": brier / 2.0,
        "log_loss_bits": (None if realized_probability == 0.0
                          else -math.log2(realized_probability)),
        "log_loss_infinite": realized_probability == 0.0,
    }
    for name, value in fields.items():
        object.__setattr__(result, name, value)
    return result


__all__ = (
    "INFORMATION_UPDATE_SCHEMA",
    "CategoricalDistribution",
    "CategoricalForecastScore",
    "InformationUpdateEvidence",
    "score_categorical_forecast",
)
