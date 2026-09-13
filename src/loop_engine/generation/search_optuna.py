"""Optional Optuna proposal adapters, with no independent persistent store.

Each batch rebuilds an in-memory study from host-validated observations for
the exact task. Optuna proposes parameters; the canonical search boundary
still checks applicability and duplication. Rebuilding is an explicit new
seeded proposal computation, not exact resumption of an earlier optimizer.
No task code, provider, database, or external effect is executed here.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from importlib.metadata import PackageNotFoundError, version
import json
import math

from .model.fragments import GenerationError


def _positive(value, name):
    if type(value) is not int or value < 1:
        raise GenerationError(name + " must be a positive integer")


@dataclass(frozen=True)
class BayesianSearchSettings:
    """Tree-structured Parzen estimation settings, supplied explicitly."""

    startup_trials: int
    acquisition_candidates: int

    def __post_init__(self):
        _positive(self.startup_trials, "startup trials")
        _positive(self.acquisition_candidates, "acquisition candidates")


@dataclass(frozen=True)
class EvolutionarySearchSettings:
    """Non-dominated sorting genetic search settings."""

    population_size: int
    crossover_probability: float
    mutation_probability: float | None

    def __post_init__(self):
        if type(self.population_size) is not int or self.population_size < 2:
            raise GenerationError("genetic population size must be at least two")
        for name in ("crossover_probability", "mutation_probability"):
            value = getattr(self, name)
            if value is None and name == "mutation_probability":
                continue
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise GenerationError(name + " must be a finite probability")


@dataclass(frozen=True)
class CovarianceSearchSettings:
    """Covariance matrix adaptation over declared ordered coordinates."""

    startup_trials: int
    initial_sigma: float | None

    def __post_init__(self):
        _positive(self.startup_trials, "startup trials")
        if self.initial_sigma is not None and (
                type(self.initial_sigma) not in (int, float)
                or not math.isfinite(self.initial_sigma) or self.initial_sigma <= 0):
            raise GenerationError("initial sigma must be positive or unspecified")


@dataclass(frozen=True)
class OptunaSearchAdapter:
    """A version-pinned optimizer adapter, not a task executor or authority."""

    parameters: BayesianSearchSettings | EvolutionarySearchSettings | CovarianceSearchSettings
    required_version: str = "5.0.0"

    def __post_init__(self):
        if not isinstance(self.parameters, (BayesianSearchSettings,
                EvolutionarySearchSettings, CovarianceSearchSettings)):
            raise GenerationError("Optuna requires typed algorithm settings")
        if self.required_version != "5.0.0":
            raise GenerationError("this adapter qualifies only Optuna 5.0.0")

    @property
    def adapter_ref(self):
        name = ("bayesian" if isinstance(self.parameters, BayesianSearchSettings) else
                "evolutionary" if isinstance(self.parameters, EvolutionarySearchSettings) else
                "covariance_adaptation")
        return f"generation.optuna.{name}@{self.required_version}"

    def settings(self):
        return {"adapter_ref": self.adapter_ref, **asdict(self.parameters),
                "state_policy": "rebuild_from_validated_exact_task_history",
                "storage": "in_memory_projection_only"}

    def propose(self, request, observations, state):
        try:
            installed = version("optuna")
        except PackageNotFoundError as exc:
            raise GenerationError("Optuna optimizer unavailable; install the optimization extra") from exc
        if installed != self.required_version:
            raise GenerationError("installed optimizer version differs from its declared binding")
        if request.seed >= 2 ** 32:
            raise GenerationError("Optuna seed must fit its unsigned 32-bit seed contract")
        if request.shard_count != 1:
            raise GenerationError("Optuna does not bind exact-enumeration shards; use separate trial leases")
        import optuna
        parameters = self.parameters
        if isinstance(parameters, BayesianSearchSettings):
            sampler = optuna.samplers.TPESampler(seed=request.seed,
                n_startup_trials=parameters.startup_trials,
                n_ei_candidates=parameters.acquisition_candidates,
                multivariate=True, constant_liar=True)
        elif isinstance(parameters, EvolutionarySearchSettings):
            sampler = optuna.samplers.NSGAIISampler(seed=request.seed,
                population_size=parameters.population_size,
                crossover_prob=parameters.crossover_probability,
                mutation_prob=parameters.mutation_probability)
        else:
            if len(request.objectives) != 1:
                raise GenerationError("covariance adaptation requires a single objective")
            if any(a.value_kind not in ("integer_range", "ordinal", "float_values")
                   for a in request.space.axes):
                raise GenerationError("covariance adaptation needs explicitly ordered numeric axes")
            if sum(a.cardinality > 1 for a in request.space.axes) < 2:
                raise GenerationError("covariance adaptation needs at least two varying coordinates")
            try:
                if version("cmaes") != "0.12.0":
                    raise GenerationError("covariance adaptation requires cmaes 0.12.0")
            except PackageNotFoundError as exc:
                raise GenerationError("covariance adapter dependency unavailable") from exc
            sampler = optuna.samplers.CmaEsSampler(seed=request.seed,
                n_startup_trials=parameters.startup_trials, sigma0=parameters.initial_sigma)
        # No persistent Optuna database is created. Run History remains the
        # source of trial observations and the engine owns proposal records.
        study = optuna.create_study(sampler=sampler,
            directions=[objective.direction for objective in request.objectives])
        covariance = isinstance(parameters, CovarianceSearchSettings)
        distributions = {}
        for axis in request.space.axes:
            if axis.value_kind == "integer_range":
                if max(abs(axis.minimum), abs(axis.maximum)) > 2 ** 53 - 1:
                    raise GenerationError("optimizer numeric coordinates cannot represent this range exactly")
                distributions[axis.dimension_id] = optuna.distributions.IntDistribution(axis.minimum, axis.maximum)
            elif covariance:
                values = [json.loads(v) for v in axis.encoded_values]
                if (any(type(v) not in (int, float) for v in values)
                        or values != sorted(values)):
                    raise GenerationError("covariance coordinates must have declared numeric order")
                distributions[axis.dimension_id] = optuna.distributions.IntDistribution(0, axis.cardinality - 1)
            else:
                # Strict JSON labels distinguish False, 0, null, and complex
                # bindings without inventing an ordering on categorical data.
                distributions[axis.dimension_id] = optuna.distributions.CategoricalDistribution(axis.encoded_values)

        def encode(index):
            config = request.space.configuration_at(index)
            return {axis.dimension_id: (
                config[axis.dimension_id] if axis.value_kind == "integer_range" else
                axis.offset_of(config[axis.dimension_id]) if covariance else
                axis.encoded_values[axis.offset_of(config[axis.dimension_id])])
                for axis in request.space.axes}

        def decode(params):
            config = json.loads(request.space.context_json)
            for axis in request.space.axes:
                value = params[axis.dimension_id]
                config[axis.dimension_id] = (value if axis.value_kind == "integer_range" else
                    axis.value_at(value) if covariance else json.loads(value))
            return request.space.index_of(config)

        used = []
        for observation in observations:
            if observation.task.identity_digest != request.task.identity_digest:
                continue
            used.append(observation.trial_id)
            study.enqueue_trial(encode(observation.configuration_index))
            trial = study.ask(fixed_distributions=distributions)
            if observation.state == "completed" and all(v is not None for v in observation.values):
                study.tell(trial, list(observation.values))
            elif observation.state != "running":
                study.tell(trial, state=optuna.trial.TrialState.FAIL)
        for _ in range(request.draw_limit):
            trial = study.ask(fixed_distributions=distributions)
            index = decode(trial.params)
            if request.space.exclusions(index):
                study.tell(trial, state=optuna.trial.TrialState.FAIL)
            # Pending proposals remain pending in this batch. They are not
            # labeled successes or assigned fabricated objective values.
            yield index, tuple(used), "optimizer proposal from exact-task measurements; evaluation still required"


def self_test() -> dict:
    from .search_optuna_checks import run_checks
    return run_checks()
