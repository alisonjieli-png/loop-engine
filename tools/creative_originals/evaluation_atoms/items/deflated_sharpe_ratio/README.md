# Probabilistic and deflated Sharpe ratio

Computes the probability that a strategy's true Sharpe ratio exceeds a benchmark, given its sample length, skewness and kurtosis. The deflated version raises the benchmark to the Sharpe ratio that the best of many pure-luck trials would be expected to reach, which corrects for picking the best configuration out of a search.

## When to use it

- You ran a hyperparameter or strategy search and want to report the winner's Sharpe ratio, or any mean-over-volatility score, without selection bias.
- You want a significance-like number that accounts for skewed or fat-tailed returns.
- You need to show how much of an apparent edge the number of trials explains.

## Formula

    PSR(SR*) = Phi( (SR - SR*) sqrt(T - 1) / sqrt(1 - g3 SR + ((g4 - 1) / 4) SR^2) )
    E[max]   ~ sqrt(V) ((1 - gamma) Phi^-1(1 - 1/N) + gamma Phi^-1(1 - 1/(N e)))
    DSR      = PSR(E[max])

`SR` is the per-period Sharpe ratio (mean over sample standard deviation), `g3` the skewness, `g4` the non-excess kurtosis (population moment ratios), `T` the number of observations, `N` the number of trials, `V` the variance of their Sharpe ratios, and `gamma` the Euler-Mascheroni constant. `expected_maximum_of_normals` gives the exact Gaussian expected maximum by quadrature for comparison.

## Assumptions and what it does not establish

- Returns are i.i.d. with a finite fourth moment. The PSR uses the asymptotic distribution of the estimated Sharpe ratio.
- `N` counts effectively independent trials, all of them, including discarded ones.
- In the seeded test, the best of 20 pure-noise strategies has PSR above 0.95 in more than 30 percent of runs and DSR above 0.95 in less than 10 percent.
- A high DSR does not rule out look-ahead bias, leakage or regime change.

## Parameters

| Name | Meaning |
|---|---|
| `returns` | per-period returns, at least 3, non-zero variance |
| `sharpe`, `observations`, `skewness`, `kurtosis`, `benchmark` | inputs of the PSR (per period; kurtosis non-excess, 3 for normal returns) |
| `trials`, `variance` / `trial_sharpe_variance` | number of trials (at least 2) and the variance of their Sharpe ratios |

## Example

```python
from deflated_sharpe_ratio import deflated_sharpe_ratio

returns = [0.01, -0.005, 0.02, 0.0, 0.015, -0.01, 0.012, 0.007]
result = deflated_sharpe_ratio(returns, trials=20, trial_sharpe_variance=0.04)
result["undeflated"], result["deflated"]      # 0.920 against zero, 0.694 against the best-of-20 benchmark
```

Command line:

```bash
echo '{"call": "probabilistic_sharpe_ratio", "arguments": {"sharpe": 0.1, "observations": 101, "skewness": -1, "kurtosis": 6}}' | python3 deflated_sharpe_ratio.py
```

## Limits

- Asymptotic and approximate for short or dependent series.
- The number of trials and their variance must be supplied honestly.

## Files

- `deflated_sharpe_ratio.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_deflated_sharpe_ratio.py`, `test_package.py`: run with `python3 -m unittest`.
