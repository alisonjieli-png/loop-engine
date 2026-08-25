"""Test-driven and optimization regimes.

Two families of what-is-next answer that are not "add a node":

- **test_driven** — "we don't know enough to choose; run a test and ask again."
  The answer is a ``run_tests`` move; only its results let the loop decide.
- **optimization** — once a working graph exists, the expert stops adding nodes
  and starts *searching*: mutate the incumbent, start a random-configuration
  optimization plan, ensemble diverse candidates, or (on a plateau) hand off to
  the logjam breakers.

These read the Knowledge facts (``candidate_count``, ``diversity``, ``plateau``,
``close_candidates``) and results, and stay deterministic so the loop can decide
most of them with no model call.
"""

from __future__ import annotations

from ...strings.knowledge import Knowledge
from ...loop.moves import answer, move


def insufficient_results_probe(k: Knowledge):
    """test_driven: a model exists but too few results to trust a choice — run a
    cross-validation probe first."""
    if k.fact("has_model") and len(k.results) < 3:
        return answer("insufficient_results_probe", "test_driven",
                      [move("run_tests", "cv_probe:5fold",
                            mechanism="fewer than three results — probe before "
                            "committing to a model choice", confidence=0.8)], 0.8)
    return None


def tie_break_probe(k: Knowledge):
    """test_driven: two candidates are within noise — run a discriminating test
    rather than guess."""
    close = k.fact("close_candidates")
    if close and len(close) >= 2:
        return answer("tie_break_probe", "test_driven",
                      [move("run_tests", f"discriminate:{'|'.join(close[:2])}",
                            mechanism="top candidates are within noise — a "
                            "discriminating test decides", confidence=0.78)], 0.78)
    return None


def calibration_probe(k: Knowledge):
    """test_driven: a probabilistic metric with no calibration check — probe it."""
    if (k.fact("metric_family") == "probabilistic_classification"
            and not k.fact("calibration_checked") and k.fact("has_model")):
        return answer("calibration_probe", "test_driven",
                      [move("run_tests", "calibration_reliability_curve",
                            mechanism="a probabilistic metric rewards calibration "
                            "— check it before tuning", confidence=0.72)], 0.72)
    return None


def start_optimization_plan(k: Knowledge):
    """optimization: a working graph exists and the search space is barely
    explored — start a random-configuration optimization plan."""
    if (k.fact("has_model") and len(k.results) >= 3
            and k.fact("candidate_count", 0) < 5 and not k.fact("plateau")
            and not k.fact("near_perfect")):
        return answer("start_optimization_plan", "custom_special",
                      [move("optimize", "random_config_search:successive_halving",
                            mechanism="a working graph with an under-explored "
                            "search space — begin an optimization plan",
                            confidence=0.75)], 0.75, detail="optimization")
    return None


def mutate_incumbent(k: Knowledge):
    """optimization: try a bounded mutation of the current best."""
    if (k.fact("has_model") and len(k.results) >= 3 and not k.fact("near_perfect")
            and k.fact("candidate_count", 0) >= 1):
        return answer("mutate_incumbent", "custom_special",
                      [move("mutate", "incumbent:swap_estimator_family",
                            mechanism="a working incumbent — a bounded mutation "
                            "may find a complementary member", confidence=0.7)],
                      0.7, detail="optimization")
    return None


def ensemble_when_diverse(k: Knowledge):
    """optimization: enough diverse, individually-good candidates exist —
    ensemble them (only when they are genuinely diverse, not near-clones)."""
    if k.fact("candidate_count", 0) >= 3 and k.fact("diversity"):
        return answer("ensemble_when_diverse", "custom_special",
                      [move("ensemble", "blend:diverse_candidates",
                            mechanism="three or more genuinely diverse candidates "
                            "— blend them and compare to the best single member",
                            confidence=0.8)], 0.8, detail="optimization")
    return None


def break_plateau(k: Knowledge):
    """optimization: the search has plateaued — hand off to the logjam breaker
    portfolio rather than keep grinding."""
    if k.fact("plateau"):
        return answer("break_plateau", "custom_special",
                      [move("understand_graph", "run_logjam_breaker_portfolio",
                            mechanism="frontier has plateaued — diagnose and "
                            "propose breakers (see logjam_breaker_portfolio)",
                            confidence=0.85)], 0.85, detail="plateau")
    return None


SPECS = [
    ("insufficient_results_probe", "test_driven", insufficient_results_probe, {}),
    ("tie_break_probe", "test_driven", tie_break_probe, {}),
    ("calibration_probe", "test_driven", calibration_probe, {}),
    ("start_optimization_plan", "custom_special", start_optimization_plan,
     {"cost": 1.0}),
    ("mutate_incumbent", "custom_special", mutate_incumbent, {"cost": 1.1}),
    ("ensemble_when_diverse", "custom_special", ensemble_when_diverse,
     {"cost": 0.9}),
    ("break_plateau", "custom_special", break_plateau, {"cost": 0.5}),
]
