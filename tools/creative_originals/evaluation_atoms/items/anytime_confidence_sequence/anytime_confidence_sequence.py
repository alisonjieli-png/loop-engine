"""Anytime-valid confidence sequences for the mean of bounded observations: valid at every time at once.

A fixed-sample interval checked after every new observation ("peeking") misses the mean far more often than its
nominal level. A confidence sequence (CS) holds simultaneously for all t:  P(for all t: mu in CI_t) >= 1 - alpha,
so it may be monitored continuously and stopped at any data-dependent time. Two constructions for data in [a, b]:

- hoeffding: CI_t = mean_t +- (b - a) sqrt(log(2 t (t + 1) / alpha) / (2 t)). Hoeffding's inequality at each t with
  level alpha / (t (t + 1)) and a union bound over t (the levels sum to alpha).
- betting: the hedged capital process of Waudby-Smith and Ramdas. For a candidate mean m, a bettor wagers on
  X_t - m with predictable stakes; K_t(m) = max(K_t^+(m), K_t^-(m)) / 2 with
  K_t^+(m) = prod(1 + min(lam_i, c/m) (X_i - m)) and K_t^-(m) = prod(1 - min(lam_i, c/(1 - m)) (X_i - m)).
  Under mu = m the average of the two products is a non-negative martingale, so by Ville's inequality
  P(exists t: K_t(mu) >= 1/alpha) <= alpha. CI_t = {m : K_t(m) < 1/alpha}. K^+ falls and K^- rises with m, so CI_t
  is an interval; it is bracketed on a grid of cell centres (reporting the first rejected centre, which is
  conservative) and the final interval is refined by bisection.

Both sequences are reported as running intersections, which keeps the simultaneous guarantee.

    echo '{"call": "hoeffding_sequence", "arguments": {"observations": [1, 0, 1, 1, 0, 1], "alpha": 0.1}}' | python3 anytime_confidence_sequence.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics

METHODS = ("hoeffding", "betting", "pointwise_wilson")


def _data(observations, lower_bound, upper_bound):
    low = numerics.finite_number(lower_bound, "lower_bound")
    high = numerics.finite_number(upper_bound, "upper_bound")
    if high <= low:
        raise ValueError("upper_bound must exceed lower_bound")
    values = numerics.vector(observations, "observations", maximum_length=200000)
    if any(value < low or value > high for value in values):
        raise ValueError("every observation must lie in [lower_bound, upper_bound]")
    return [(value - low) / (high - low) for value in values], low, high


def _alpha(alpha):
    return numerics.probability(alpha, "alpha", open_low=True, open_high=True)


def _intersect(lowers, uppers):
    """Running intersection; once it would be empty the raw intervals are reported and the time is recorded."""
    out_low, out_high, empty_at = [], [], None
    current_low, current_high = 0.0, 1.0
    for step, (low, high) in enumerate(zip(lowers, uppers), start=1):
        new_low, new_high = max(current_low, low), min(current_high, high)
        if new_low > new_high and empty_at is None:
            empty_at = step
        if empty_at is None:
            current_low, current_high = new_low, new_high
        else:
            current_low, current_high = low, high
        out_low.append(current_low)
        out_high.append(current_high)
    return out_low, out_high, empty_at


def _scaled(result, low, high):
    span = high - low
    for key in ("lower", "upper"):
        result[key] = [low + span * value for value in result[key]]
    result["final"] = [low + span * value for value in result["final"]]
    result["means"] = [low + span * value for value in result["means"]]
    return result


def hoeffding_sequence(observations, alpha, lower_bound=0.0, upper_bound=1.0):
    """The Hoeffding union-bound confidence sequence, as running intersections for t = 1 .. n.

    Returns {"lower", "upper", "means", "final", "empty_at" (null unless the intersection emptied), "method"}."""
    values, low, high = _data(observations, lower_bound, upper_bound)
    alpha = _alpha(alpha)
    lowers, uppers, means, total = [], [], [], 0.0
    for step, value in enumerate(values, start=1):
        total += value
        mean = total / step
        radius = math.sqrt(math.log(2.0 * step * (step + 1) / alpha) / (2.0 * step))
        lowers.append(max(0.0, mean - radius))
        uppers.append(min(1.0, mean + radius))
        means.append(mean)
    lower, upper, empty_at = _intersect(lowers, uppers)
    return _scaled({"lower": lower, "upper": upper, "means": means, "final": [lower[-1], upper[-1]],
                    "empty_at": empty_at, "method": "hoeffding"}, low, high)


def _stakes(values, alpha, cap):
    """Predictable plug-in stakes: lam_t uses only X_1 .. X_(t-1)."""
    stakes, total, squares = [], 0.0, 0.25
    for step, value in enumerate(values, start=1):
        variance = squares / step  # (1/4 + sum_(i<t) (X_i - mu_i)^2) / t
        stakes.append(min(cap, math.sqrt(2.0 * math.log(2.0 / alpha) / (variance * step * math.log(1.0 + step)))))
        total += value
        running_mean = (0.5 + total) / (step + 1)
        squares += (value - running_mean) ** 2
    return stakes


def _log_capital(values, stakes, m, cap):
    plus = minus = 0.0
    up, down = cap / m, cap / (1.0 - m)
    for value, stake in zip(values, stakes):
        plus += math.log1p(min(stake, up) * (value - m))
        minus += math.log1p(-min(stake, down) * (value - m))
    return plus, minus


def betting_sequence(observations, alpha, lower_bound=0.0, upper_bound=1.0, grid=200, cap=0.5):
    """The hedged-capital betting confidence sequence (running intersections) with a bisection-refined final interval.

    grid: number of cells on [0, 1] (20 to 2000); cap: the stake truncation c in (0, 1).
    Returns {"lower", "upper", "means", "final", "empty_at", "method"}."""
    values, low, high = _data(observations, lower_bound, upper_bound)
    alpha = _alpha(alpha)
    grid = numerics.integer(grid, "grid", minimum=20, maximum=2000)
    cap = numerics.probability(cap, "cap", open_low=True, open_high=True)
    centres = [(index + 0.5) / grid for index in range(grid)]
    stakes = _stakes(values, alpha, cap)
    threshold = math.log(1.0 / alpha) + math.log(2.0)  # max(K+, K-)/2 >= 1/alpha
    plus, minus = [0.0] * grid, [0.0] * grid
    lowers, uppers, means, total = [], [], [], 0.0
    for step, (value, stake) in enumerate(zip(values, stakes), start=1):
        total += value
        means.append(total / step)
        for index, m in enumerate(centres):
            plus[index] += math.log1p(min(stake, cap / m) * (value - m))
            minus[index] += math.log1p(-min(stake, cap / (1.0 - m)) * (value - m))
        kept = [index for index in range(grid) if max(plus[index], minus[index]) < threshold]
        if kept:
            lowers.append(0.0 if kept[0] == 0 else centres[kept[0] - 1])
            uppers.append(1.0 if kept[-1] == grid - 1 else centres[kept[-1] + 1])
        else:
            lowers.append(lowers[-1] if lowers else 0.0)
            uppers.append(uppers[-1] if uppers else 1.0)
    lower, upper, empty_at = _intersect(lowers, uppers)

    def rejected_low(m):
        return _log_capital(values, stakes, m, cap)[0] >= threshold

    def rejected_high(m):
        return _log_capital(values, stakes, m, cap)[1] >= threshold

    refined_low, refined_high = 0.0, 1.0
    if values:
        a, b = 1e-12, max(lower[-1], 1e-12)
        if rejected_low(b):
            a, b = b, min(upper[-1], 1.0 - 1e-12)
        if rejected_low(a):
            for _ in range(80):
                middle = (a + b) / 2.0
                a, b = (middle, b) if rejected_low(middle) else (a, middle)
            refined_low = a
        a, b = min(upper[-1], 1.0 - 1e-12), 1.0 - 1e-12
        if rejected_high(a):
            a, b = max(lower[-1], 1e-12), a
        if rejected_high(b):
            for _ in range(80):
                middle = (a + b) / 2.0
                a, b = (a, middle) if rejected_high(middle) else (middle, b)
            refined_high = b
    final = [max(lower[-1], refined_low), min(upper[-1], refined_high)]
    if final[0] > final[1]:
        final = [lower[-1], upper[-1]]
    return _scaled({"lower": lower, "upper": upper, "means": means, "final": final, "empty_at": empty_at,
                    "method": "betting"}, low, high)


def pointwise_wilson_sequence(observations, alpha, lower_bound=0.0, upper_bound=1.0):
    """The fixed-sample Wilson score interval recomputed at every t, for 0/1 observations.

    Shown as the known-wrong comparison: each interval has about 1 - alpha coverage at one pre-chosen t, but checking
    it after every observation misses the mean at some t far more often than alpha."""
    values, low, high = _data(observations, lower_bound, upper_bound)
    z = numerics.normal_quantile(1.0 - _alpha(alpha) / 2.0)
    lowers, uppers, means, total = [], [], [], 0.0
    for step, value in enumerate(values, start=1):
        total += value
        mean = total / step
        centre = (mean + z * z / (2.0 * step)) / (1.0 + z * z / step)
        radius = z * math.sqrt(max(mean * (1.0 - mean), 0.0) / step + z * z / (4.0 * step * step)) / (1.0 + z * z / step)
        lowers.append(max(0.0, centre - radius))
        uppers.append(min(1.0, centre + radius))
        means.append(mean)
    return _scaled({"lower": lowers, "upper": uppers, "means": means, "final": [lowers[-1], uppers[-1]],
                    "empty_at": None, "method": "pointwise_wilson"}, low, high)


def coverage_simulation(method, mean, length, replications, alpha, seed, grid=100):
    """Fraction of seeded Bernoulli(mean) sequences in which the true mean leaves the reported interval at any t.

    Returns {"method", "miscoverage", "within_alpha" (miscoverage <= alpha), "replications", "length"}."""
    if method not in METHODS:
        raise ValueError(f"method is one of {METHODS}")
    mean = numerics.probability(mean, "mean")
    length = numerics.integer(length, "length", minimum=1, maximum=5000)
    replications = numerics.integer(replications, "replications", minimum=1, maximum=5000)
    alpha = _alpha(alpha)
    generator = numerics.seeded_random(seed)
    misses = 0
    for _ in range(replications):
        data = [1.0 if generator.random() < mean else 0.0 for _ in range(length)]
        if method == "hoeffding":
            result = hoeffding_sequence(data, alpha)
        elif method == "betting":
            result = betting_sequence(data, alpha, grid=grid)
        else:
            result = pointwise_wilson_sequence(data, alpha)
        if any(not (low <= mean <= high) for low, high in zip(result["lower"], result["upper"])):
            misses += 1
    rate = misses / replications
    return {"method": method, "miscoverage": rate, "within_alpha": rate <= alpha, "replications": replications,
            "length": length}


FUNCTIONS = {"hoeffding_sequence": hoeffding_sequence, "betting_sequence": betting_sequence,
             "pointwise_wilson_sequence": pointwise_wilson_sequence, "coverage_simulation": coverage_simulation}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["METHODS", "hoeffding_sequence", "betting_sequence", "pointwise_wilson_sequence", "coverage_simulation",
           "main"]

if __name__ == "__main__":
    raise SystemExit(main())
