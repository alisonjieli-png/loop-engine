"""Deflated Sharpe ratio: the probability that a strategy's true Sharpe ratio beats the best one luck alone would
produce among the configurations tried.

Probabilistic Sharpe ratio (non-annualized SR from T observations with skewness g3 and non-excess kurtosis g4):

    PSR(SR*) = Phi( (SR - SR*) sqrt(T - 1) / sqrt(1 - g3 SR + ((g4 - 1) / 4) SR^2) )

Expected maximum of N independent trial Sharpe ratios with variance V when every true Sharpe ratio is 0:

    E[max] ~ sqrt(V) ((1 - gamma) Phi^-1(1 - 1/N) + gamma Phi^-1(1 - 1/(N e))),   gamma = Euler-Mascheroni

    DSR = PSR(E[max])

Assumptions: returns i.i.d. with finite fourth moment (the PSR uses the asymptotic distribution of the Sharpe
ratio); N is the number of effectively independent trials; the trial Sharpe ratios are roughly Gaussian. The
expected-maximum formula is an approximation (expected_maximum_of_normals gives the exact value by quadrature).

    echo '{"call": "probabilistic_sharpe_ratio", "arguments": {"sharpe": 0.1, "observations": 101}}' | python3 deflated_sharpe_ratio.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics

EULER_GAMMA = 0.5772156649015329


def sharpe_moments(returns):
    """Per-period Sharpe ratio (mean / sample standard deviation), skewness and non-excess kurtosis.

    Skewness and kurtosis are population moment ratios m3 / m2^1.5 and m4 / m2^2. Returns {"sharpe", "skewness",
    "kurtosis", "observations"}."""
    values = numerics.vector(returns, "returns", minimum_length=3)
    n = len(values)
    centre = numerics.mean(values)
    deviations = [value - centre for value in values]
    m2 = math.fsum(d * d for d in deviations) / n
    if m2 == 0:
        raise ValueError("returns have zero variance")
    m3 = math.fsum(d ** 3 for d in deviations) / n
    m4 = math.fsum(d ** 4 for d in deviations) / n
    return {"sharpe": centre / math.sqrt(numerics.variance(values, 1)), "skewness": m3 / m2 ** 1.5,
            "kurtosis": m4 / (m2 * m2), "observations": n}


def probabilistic_sharpe_ratio(sharpe, observations, skewness=0.0, kurtosis=3.0, benchmark=0.0):
    """PSR: the probability that the true Sharpe ratio exceeds ``benchmark`` (all in per-period units)."""
    sr = numerics.finite_number(sharpe, "sharpe")
    t = numerics.integer(observations, "observations", minimum=2)
    g3 = numerics.finite_number(skewness, "skewness")
    g4 = numerics.finite_number(kurtosis, "kurtosis")
    target = numerics.finite_number(benchmark, "benchmark")
    variance = 1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr * sr
    if variance <= 0:
        raise ValueError("1 - skewness * sharpe + (kurtosis - 1) / 4 * sharpe^2 must be positive")
    return numerics.normal_cdf((sr - target) * math.sqrt(t - 1) / math.sqrt(variance))


def expected_maximum_sharpe(trials, variance):
    """The approximate expected maximum of ``trials`` independent zero-mean Gaussian Sharpe ratios of variance V."""
    n = numerics.integer(trials, "trials", minimum=2)
    v = numerics.finite_number(variance, "variance")
    if v < 0:
        raise ValueError("variance must be non-negative")
    return math.sqrt(v) * ((1.0 - EULER_GAMMA) * numerics.normal_quantile(1.0 - 1.0 / n)
                           + EULER_GAMMA * numerics.normal_quantile(1.0 - 1.0 / (n * math.e)))


def expected_maximum_of_normals(count):
    """E[max of ``count`` i.i.d. standard normals] by Simpson's rule on [-12, 12] (for checking the approximation)."""
    n = numerics.integer(count, "count", minimum=1, maximum=100000)
    steps, low, high = 4000, -12.0, 12.0
    width = (high - low) / steps
    total = 0.0
    for index in range(steps + 1):
        x = low + index * width
        density = n * numerics.normal_pdf(x) * numerics.normal_cdf(x) ** (n - 1)
        total += (1 if index in (0, steps) else (4 if index % 2 else 2)) * x * density
    return total * width / 3.0


def deflated_sharpe_ratio(returns, trials, trial_sharpe_variance):
    """DSR for a return series selected as the best of ``trials`` configurations whose Sharpe ratios have variance V.

    Returns {"sharpe", "skewness", "kurtosis", "observations", "expected_maximum", "deflated", "undeflated"}, where
    undeflated is PSR(0) for comparison."""
    moments = sharpe_moments(returns)
    threshold = expected_maximum_sharpe(trials, trial_sharpe_variance)
    arguments = (moments["sharpe"], moments["observations"], moments["skewness"], moments["kurtosis"])
    return {**moments, "expected_maximum": threshold,
            "deflated": probabilistic_sharpe_ratio(*arguments, threshold),
            "undeflated": probabilistic_sharpe_ratio(*arguments, 0.0)}


FUNCTIONS = {"sharpe_moments": sharpe_moments, "probabilistic_sharpe_ratio": probabilistic_sharpe_ratio,
             "expected_maximum_sharpe": expected_maximum_sharpe,
             "expected_maximum_of_normals": expected_maximum_of_normals, "deflated_sharpe_ratio": deflated_sharpe_ratio}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["EULER_GAMMA", "sharpe_moments", "probabilistic_sharpe_ratio", "expected_maximum_sharpe",
           "expected_maximum_of_normals", "deflated_sharpe_ratio", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
