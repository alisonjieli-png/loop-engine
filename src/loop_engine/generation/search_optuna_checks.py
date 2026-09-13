"""Actual optional-optimizer controls on deterministic, disclosed objectives.

These checks exercise the installed optimizer implementations when available
and test an explicit refusal otherwise. They never contact a model provider.
"""
from __future__ import annotations

from dataclasses import replace
from importlib.metadata import PackageNotFoundError, version

from .model.fragments import GenerationError
from .search import propose_configurations
from .search_checks import fixtures, observation
from .search_records import SearchObjective, SearchServices
from .search_optuna import (
    OptunaSearchAdapter, BayesianSearchSettings, EvolutionarySearchSettings,
    CovarianceSearchSettings)
from .space import ConfigurationAxis, ConfigurationSpace, content_digest


INSTALLED_CONTROLS = tuple(
    [method + suffix for method in ("BayesianSearchSettings", "EvolutionarySearchSettings",
                                    "CovarianceSearchSettings")
     for suffix in ("_proposes_valid_distinct_candidates", "_rebuild_is_reproducible",
                    "_binds_exact_task_evidence")]
    + ["bayesian_history_does_not_mix_raw_scores_from_other_tasks",
       "bayesian_measurements_change_the_proposals",
       "BayesianSearchSettings_supports_multiple_objectives",
       "EvolutionarySearchSettings_supports_multiple_objectives",
       "covariance_refuses_unordered_categories",
       "optimizers_do_not_execute_or_accept_task_outputs"])


def run_checks():
    tests = []

    def check(name, value):
        tests.append({"name": name, "passed": bool(value)})

    request = replace(fixtures(), space=ConfigurationSpace("optimizer-control", "1.0.0", (
        ConfigurationAxis("x", "integer_range", minimum=0, maximum=9),
        ConfigurationAxis("y", "integer_range", minimum=0, maximum=9))))
    request = replace(request, observations=tuple(observation(request, "control-" + str(i), i,
        values=(float((i // 10 - 3) ** 2 + (i % 10 - 7) ** 2),))
        for i in (0, 11, 22, 33, 44, 55)))
    try:
        installed = version("optuna")
    except PackageNotFoundError:
        installed = None
    if installed != "5.0.0":
        try:
            adapter = OptunaSearchAdapter(BayesianSearchSettings(3, 24))
            next(adapter.propose(request, (), {}))
            check("unavailable_optimizer_refuses_without_a_substitute", False)
        except GenerationError:
            check("unavailable_optimizer_refuses_without_a_substitute", True)
        # The controls that did not run stay visible in the aggregate as
        # not tested, with the dependency that would exercise them, instead
        # of vanishing from the count.
        for name in INSTALLED_CONTROLS:
            missing = ["optuna"] + (["cmaes"] if name.startswith(("Covariance", "covariance")) else [])
            tests.append({"name": name, "passed": True, "not_tested": True,
                          "outcome": "NOT_APPLICABLE", "missing_optional_dependencies": missing,
                          "detail": "optional optimizer not installed; control not exercised"})
        return {"tests": tests, "optimizer_qualification": "unavailable_not_exercised"}

    def propose(parameters, selected=request):
        return propose_configurations(selected, SearchServices(
            OptunaSearchAdapter(parameters), lambda record: True))["value"]

    parameters = (BayesianSearchSettings(3, 24),
                  EvolutionarySearchSettings(2, 0.9, 0.2),
                  CovarianceSearchSettings(3, None))
    for settings in parameters:
        method = type(settings).__name__
        first, again = propose(settings), propose(settings)
        check(method + "_proposes_valid_distinct_candidates",
              len(first["proposals"]) == 3
              and len({v["configuration_index"] for v in first["proposals"]}) == 3
              and all(0 <= v["configuration_index"] < 100 for v in first["proposals"]))
        check(method + "_rebuild_is_reproducible", first == again)
        check(method + "_binds_exact_task_evidence",
              first["proposals"][0]["parent_trial_ids"] == [v.trial_id for v in request.observations])
    other_task = replace(request, task=replace(request.task,
        task_id="different", task_digest=content_digest("different")))
    cold = propose(parameters[0], other_task)
    check("bayesian_history_does_not_mix_raw_scores_from_other_tasks",
          all(v["parent_trial_ids"] == [] for v in cold["proposals"]))
    reversed_values = replace(request, observations=tuple(
        replace(v, values=(-v.values[0],)) for v in request.observations))
    original, changed = propose(parameters[0]), propose(parameters[0], reversed_values)
    check("bayesian_measurements_change_the_proposals",
          [v["configuration_index"] for v in original["proposals"]]
          != [v["configuration_index"] for v in changed["proposals"]])
    for settings in parameters[:2]:
        objectives = (SearchObjective("loss@1.0.0", "minimize"),
                      SearchObjective("quality@1.0.0", "maximize"))
        multi = replace(request, objectives=objectives, observations=tuple(
            replace(v, objectives=objectives, values=(v.values[0], float(v.configuration_index)))
            for v in request.observations))
        check(type(settings).__name__ + "_supports_multiple_objectives",
              len(propose(settings, multi)["proposals"]) == 3)
    unsupported = replace(request, space=ConfigurationSpace("mixed", "1.0.0", (
        ConfigurationAxis("kind", "categorical", ('"one"', '"two"')),
        ConfigurationAxis("x", "integer_range", minimum=0, maximum=9))))
    try:
        next(OptunaSearchAdapter(parameters[2]).propose(unsupported, (), {}))
        check("covariance_refuses_unordered_categories", False)
    except GenerationError:
        check("covariance_refuses_unordered_categories", True)
    check("optimizers_do_not_execute_or_accept_task_outputs",
          not original["task_execution_performed"] and not original["promotion_performed"])
    return {"tests": tests, "optimizer_qualification": "Optuna 5.0.0 deterministic controls"}
