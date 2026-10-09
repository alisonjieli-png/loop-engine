# Equal-cohort comparison with separate coverage

Compares candidates on the rows that every candidate scored, and reports separately how much of the declared universe each candidate covered. A missing score stays missing: it is never set to zero and never quietly dropped for one candidate only.

## When to use it

- Two agents, models or configurations ran on a benchmark and some runs crashed, timed out or refused.
- You want a quality comparison that cannot be won by skipping hard rows, and a coverage number that cannot be hidden inside the quality number.
- You need the list of rows that kept a comparison from using the whole universe.

## Formula

    eligible(c) = rows where candidate c has a finite score
    cohort      = intersection of eligible(c) over all candidates
    mean(c)     = average of c's scores over the cohort
    coverage(c) = |eligible(c)| / |universe|
    paired difference(c) = average over the cohort of score(c) - score(reference)

## Assumptions and what it does not establish

- A missing score carries no value. It is not a zero, a failure grade or a pass.
- Cohort rows are comparable across candidates: same input and same scoring rule.
- The cohort can be a biased subset (for example, only the easy rows every candidate finished). Read coverage next to the means.
- No interval or test is computed. Use a paired test on the cohort rows for that.

## Parameters

| Name | Meaning |
|---|---|
| `scores` | `{candidate: {row_id: number or null}}` |
| `universe` | optional list of declared row ids; default is every row id that appears |
| `higher_is_better` | ranking direction, true by default |
| `reference` | optional candidate for paired differences |

The result holds `cohort`, `cohort_size`, `comparable`, `means`, `coverage`, `ranking`, `excluded_rows` (row to the candidates that miss it) and `paired_differences`.

## Example

```python
from equal_cohort_comparison import compare_on_common_cohort

scores = {"a": {"r1": 0.9, "r2": 0.8, "r3": None},
          "b": {"r1": 0.7, "r2": 0.6, "r3": 0.1, "r4": 0.2}}
result = compare_on_common_cohort(scores)
result["means"]       # {"a": 0.85, "b": 0.65} on rows r1 and r2
result["coverage"]    # a: 2 of 4 rows, b: 4 of 4 rows
```

Averaging each candidate over its own rows would report 0.85 against 0.40. Counting missing rows as zero would report 0.425 for `a`.

Command line:

```bash
echo '{"call": "compare_on_common_cohort", "arguments": {"scores": {"a": {"r1": 1, "r2": null}, "b": {"r1": 0, "r2": 1}}}}' | python3 equal_cohort_comparison.py
```

## Limits

- Row ids must match exactly across candidates.
- A cohort of a few rows gives fragile means. The tool reports the size; it does not refuse small cohorts.

## Files

- `equal_cohort_comparison.py`: the function and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_equal_cohort_comparison.py`, `test_package.py`: run with `python3 -m unittest`.
