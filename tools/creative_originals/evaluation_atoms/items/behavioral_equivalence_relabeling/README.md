# Method-blind relabeling and behavioral equivalence

Replaces candidate names with neutral, seeded labels and keeps the key apart, so whoever judges the outputs cannot see which method produced them. It also groups candidates that produce identical outputs on the same probe inputs, so behaviorally identical variants are not counted as separate results.

## When to use it

- A person or a model judges outputs of several methods and must not know which is which.
- A configuration sweep produced many variants, and some of them behave identically on every probe.
- You want a stable fingerprint of a candidate's behaviour on a probe set.

## Formula

- Labels: sort the names, shuffle with a seeded Fisher-Yates shuffle, and give the i-th name `candidate_` plus `i + 1`, zero-padded.
- Classes: round every number to `decimals` places (when given), serialize each candidate's outputs as canonical JSON, and group equal serializations. The fingerprint is the SHA-256 of that serialization.

Rounding keeps equality transitive. A tolerance would not: `0.0 ~ 0.008` and `0.008 ~ 0.016` within 0.01, but `0.0` and `0.016` are not.

## Assumptions and what it does not establish

- All candidates ran on the same probes in the same order.
- Equal outputs on the probes say nothing about inputs outside the probe set.
- Blind labels hide names, not recognizable output styles.

## Parameters

| Name | Meaning |
|---|---|
| `names` | unique text or integer names |
| `seed` | non-negative integer |
| `outputs` | `{candidate: [output per probe]}`, JSON values, equal lengths |
| `decimals` | optional rounding for numbers, 0 to 15 |

## Example

```python
from behavioral_equivalence_relabeling import equivalence_classes, blind_report

equivalence_classes({"A": [1, 2, 3], "B": [1, 2, 3], "C": [1, 2, 4]})["class_count"]   # 2
equivalence_classes({"x": [0.1 + 0.2], "y": [0.3]}, decimals=9)["class_count"]        # 1
blind_report({"A": [1, 2, 3], "B": [1, 2, 3], "C": [1, 2, 4]}, seed=5)["key"]        # candidate_1 is A, ...
```

Command line:

```bash
echo '{"call": "blind_labels", "arguments": {"names": ["ours", "baseline", "ablation"], "seed": 3}}' | python3 behavioral_equivalence_relabeling.py
```

## Limits

- Values that straddle a rounding boundary can land in different classes.
- Outputs must be JSON data: numbers, text, booleans, null, lists and objects.

## Files

- `behavioral_equivalence_relabeling.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_behavioral_equivalence_relabeling.py`, `test_package.py`: run with `python3 -m unittest`.
