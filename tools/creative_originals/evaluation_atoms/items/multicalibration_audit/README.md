# Multicalibration audit by prediction bin and group

Reports, for every declared group and for the whole population, the mean of outcome minus prediction in each prediction bin, and flags cells beyond a tolerance. A predictor can look calibrated overall while over-predicting for one group and under-predicting for another; this audit shows both. `multicalibrate` repairs the flagged cells by iterative patching.

## When to use it

- A model or judge outputs probabilities, and the population is a mix of task types, languages, sources or user groups.
- An overall reliability diagram looks fine, and you need to know whether that holds inside each group.
- You want a simple post-processing step that removes group-level calibration gaps on a calibration set.

## Formula

For group `g` (or `all`) and bin `b` (equal width on `[0, 1]`):

    residual(g, b) = mean over rows in g with prediction in b of (outcome - prediction)
    mass(g, b)     = rows in the cell / all rows
    flagged        = count >= minimum_count and |residual| > tolerance

Patching: while a cell is flagged, take the one with the largest `|residual| x mass`, add its residual to its predictions (clipped to `[0, 1]`) and re-bin. Each patch lowers the squared error by at least `minimum_count x tolerance^2`, so the loop ends.

## Assumptions and what it does not establish

- Only the declared groups are audited. A group you did not declare can still be miscalibrated.
- Small cells are noisy. No interval is computed; use `minimum_count` to avoid flagging noise.
- Patched predictions fit the audit data. Check them on fresh data before relying on them.

## Parameters

| Name | Meaning |
|---|---|
| `predictions`, `outcomes` | numbers in `[0, 1]`, one per row |
| `groups` | `{name: [row indices]}`; groups may overlap; `all` is reserved |
| `bins` | number of equal-width bins, default 10 |
| `tolerance` | largest allowed absolute residual, default 0.05 |
| `minimum_count` | smallest cell that can be flagged, default 1 |
| `max_rounds` | patching limit for `multicalibrate`, default 1000 |

## Example

```python
from multicalibration_audit import multicalibration_audit

predictions = [0.5] * 20
outcomes = [1] * 7 + [0] * 3 + [1] * 3 + [0] * 7
groups = {"g1": list(range(10)), "g2": list(range(10, 20))}
audit = multicalibration_audit(predictions, outcomes, groups)
audit["calibrated_overall"], audit["multicalibrated"]   # True, False: residuals +0.2 and -0.2 cancel overall
```

Command line:

```bash
echo '{"call": "multicalibrate", "arguments": {"predictions": [0.5, 0.5, 0.5, 0.5], "outcomes": [1, 1, 0, 0], "groups": {"g": [0, 1]}}}' | python3 multicalibration_audit.py
```

## Limits

- Equal-width bins only.
- Groups are given as row index lists, at most a few thousand rows per call for comfortable run time.

## Files

- `multicalibration_audit.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_multicalibration_audit.py`, `test_package.py`: run with `python3 -m unittest`.
