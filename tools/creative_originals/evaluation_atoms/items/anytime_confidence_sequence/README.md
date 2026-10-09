# Anytime-valid confidence sequence for a bounded mean

Computes confidence intervals for the mean of bounded observations that hold at every time simultaneously. You can update the interval after every run, look at it as often as you like, and stop whenever you want, and the error probability stays below `alpha`.

## When to use it

- An evaluation runs one task at a time and you want to stop as soon as the pass rate is pinned down.
- A dashboard shows a running success rate with an interval, and people look at it after every run.
- You need to show that the usual fixed-sample interval, checked repeatedly, is not valid.

## Formula

Observations are rescaled from `[a, b]` to `[0, 1]`.

Hoeffding sequence:

    CI_t = mean_t +- sqrt(log(2 t (t + 1) / alpha) / (2 t))

Each `t` uses Hoeffding's inequality at level `alpha / (t (t + 1))`. These levels sum to `alpha`, so a union bound over all `t` gives the simultaneous guarantee.

Betting sequence (hedged capital):

    K_t^+(m) = prod_i (1 + min(lam_i, c / m) (X_i - m))
    K_t^-(m) = prod_i (1 - min(lam_i, c / (1 - m)) (X_i - m))
    CI_t = { m : max(K_t^+(m), K_t^-(m)) / 2 < 1 / alpha }

The stakes `lam_i = min(c, sqrt(2 log(2 / alpha) / (sigma2_(i-1) i log(1 + i))))` use only earlier observations. At the true mean, `(K^+ + K^-) / 2` is a non-negative martingale, so by Ville's inequality it reaches `1 / alpha` with probability at most `alpha`. `K^+` falls and `K^-` rises with `m`, so `CI_t` is an interval. It is bracketed on a grid and the final interval is refined by bisection.

Both sequences are reported as running intersections.

## Assumptions and what it does not establish

- Observations lie in known bounds and have a common conditional mean given the past, for example i.i.d. draws.
- `alpha` is chosen before seeing the data.
- Under drift there is no single mean to cover, and the guarantee does not apply.
- `pointwise_wilson_sequence` is included only as the counterexample: in the seeded simulation, a 90 percent interval checked after every observation misses the mean at some time in about two thirds of the runs.

## Parameters

| Name | Meaning |
|---|---|
| `observations` | numbers in `[lower_bound, upper_bound]` |
| `alpha` | error level in `(0, 1)` |
| `lower_bound`, `upper_bound` | known bounds, default `[0, 1]` |
| `grid`, `cap` | betting grid cells (20 to 2000, default 200) and stake cap `c` (default 0.5) |
| `method`, `mean`, `length`, `replications`, `seed` | coverage simulation on Bernoulli(`mean`) data |

Each sequence returns `lower`, `upper` and `means` for every `t`, the `final` interval and `empty_at`.

## Example

```python
from anytime_confidence_sequence import hoeffding_sequence, betting_sequence, coverage_simulation

data = [1, 0] * 50
hoeffding_sequence(data, 0.05)["final"]    # [0.2499, 0.7541]
betting_sequence(data, 0.05)["final"]      # [0.3575, 0.6455]
coverage_simulation("pointwise_wilson", 0.3, 200, 200, 0.1, 3)["miscoverage"]   # 0.66
```

Command line:

```bash
echo '{"call": "hoeffding_sequence", "arguments": {"observations": [1, 0, 1, 1, 0, 1], "alpha": 0.1}}' | python3 anytime_confidence_sequence.py
```

## Limits

- The bounds must be known in advance.
- The betting sequence costs `grid x n` operations: a few thousand observations are fine.
- Grid reporting widens intervals by at most one cell.

## Files

- `anytime_confidence_sequence.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_anytime_confidence_sequence.py`, `test_package.py`: run with `python3 -m unittest`.
