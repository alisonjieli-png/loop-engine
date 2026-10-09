# Agreement between pairs of judges

Measure how closely each pair of judges scores the same answers: shared units, mean absolute difference, the share of units within a tolerance and Pearson's correlation, so an evaluation sees which judges disagree before it averages them.

## What it does

A unit is one model's answer to one item under one arm. For every pair of judges, on the units both scored, the function reports how many there are, the mean absolute difference of their scores, the share of units whose scores differ by at most the tolerance (10 by default, ten points on a 0 to 100 rubric) and Pearson's correlation. The correlation is null with fewer than three shared units or when one judge gives every shared unit the same score. A pair that shares no unit is listed with null statistics, so a missing comparison is visible.

## Run it

As a library:

```python
from judge_agreement import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 judge_agreement.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `rows` (array of object, required): one judge's score of one model's answer to one item under one arm
- `tolerance` (number): largest score difference counted as agreement (default 10)

## Output

- `tolerance` (number, required)
- `judges` (array of object, required): each judge with the units it scored, in judge name order
- `pairs` (array of object, required): one row per pair of judges, in name order

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_grade`: one judge scored one model, arm and item twice
- `fewer_than_two_judges`: agreement needs at least two judges

## Checks

`examples/known_good.json` and the 4 cases of `examples/known_answers.json` hold inputs with answers worked out by hand; `examples/known_wrong.json` holds an input the function refuses. `test_package.py` runs the known-good and known-wrong examples through the function and the command line, and every known answer through the function.

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `judge_agreement.py` | executable_tool |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `examples/known_answers.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## Source and SDG basis

The DueCare harness benchmark grades (CC BY 4.0, Gemma 4 Good Hackathon), where three judge models grade every answer; their agreement decides how much an averaged score can be trusted.

Built for:

- [`taylorsamarel/duecare-harness-benchmark-grades`](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades)

Dataset shape: panel_grades.csv: model, arm, prompt_id, judge, score_0_100 graded by three judges.

Proposed goals 5, 8, 16; targets 5.2, 8.7, 16.2. Inherited from the dataset it was built for, which grades model answers to labour-exploitation and trafficking prompts (targets 8.7, 16.2 and 5.2). The function itself is a general evaluation step. The association is a proposal for reviewers, not a grant.

## Limits

Pearson's correlation measures linear agreement only and is null below three shared units or without spread; it ignores a constant offset, which the mean absolute difference shows. No chance-corrected statistic (Cohen's or Fleiss' kappa, Krippendorff's alpha) is computed. A unit is (model, arm, item), compared exactly.

This item is a candidate component. Generating it did not approve or qualify it.
