# Silent concept-shift twin datasets

Generates two datasets that are identical in every marginal: the same input rows and the same targets, as multisets. The relationship between inputs and targets is reversed in the second one. A drift monitor that reads only inputs, or only targets, sees no change at all.

## When to use it

- Test whether a monitoring or evaluation pipeline can detect a change in the input-output relationship, not only in the inputs.
- Show a reader why input drift statistics are not a guarantee that a model still works.
- Build a fixture for a "retrain or not" decision procedure.

## Formula

Draw inputs `x_i` (standard normal, dimension `d`), a slope `w` and noise `e_i1, e_i2 ~ N(0, s^2)`:

    reference rows:  (x_i,  w.x_i + e_i1)   and   (-x_i, -w.x_i + e_i2)
    shifted rows:    (x_i, -w.x_i + e_i2)   and   (-x_i,  w.x_i + e_i1)       then shuffled

Per pair, both datasets contain the inputs `{x_i, -x_i}` and the targets `{w.x_i + e_i1, -w.x_i + e_i2}`, so the multisets match exactly. Input means are exactly 0, and each shifted product `x * y` is the negative of a reference product, so every input-target covariance flips sign exactly.

## Assumptions and what it does not establish

- The twins are a constructed fixture. They show that input-only statistics cannot detect this kind of change. They do not estimate how often such changes occur.
- The construction needs inputs symmetric under negation and a linear relationship.
- Seeded draws use `random.Random.random()` only, so a seed gives the same twins on every Python version.

## Parameters

| Name | Meaning |
|---|---|
| `n_pairs` | number of antithetic pairs; each dataset has `2 n_pairs` rows |
| `dimension` | input width, 1 to 100 |
| `seed` | non-negative integer |
| `noise` | noise standard deviation, default 0.5 |
| `slope` | optional fixed `w`; a seeded unit vector otherwise |
| `labels` | turn targets into `1{y > 0}` |

## Example

```python
from silent_concept_shift_twins import silent_shift_report

report = silent_shift_report(n_pairs=50, dimension=2, seed=3)
report["input_max_ks"], report["target_ks"]          # 0.0, 0.0
report["joint_covariance_reference"]                  # [-0.698, -0.107]
report["joint_covariance_shifted"]                    # [0.698, 0.107]
```

Command line:

```bash
echo '{"call": "silent_shift_report", "arguments": {"n_pairs": 50, "dimension": 2, "seed": 3}}' | python3 silent_concept_shift_twins.py
```

## Limits

- Linear relationship, Gaussian inputs and noise.
- Up to 50,000 pairs per call.

## Files

- `silent_concept_shift_twins.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_silent_concept_shift_twins.py`, `test_package.py`: run with `python3 -m unittest`.
