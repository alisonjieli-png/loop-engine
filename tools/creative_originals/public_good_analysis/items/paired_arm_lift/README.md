# Paired arm lift of an evaluation

Measure how much a treatment arm changes scores against a baseline arm, item by item: judges averaged per answer, items paired per model, then per model and overall the arm means, the mean and median lift, and counts of pairs improved, worsened and unchanged.

## What it does

The judges' scores of one model's answer to one item under one arm are averaged first, so an item graded by three judges counts once. Every item a model answered under both arms is a pair, and its lift is the treatment mean minus the baseline mean. Per model and over every pair of every model, the summary gives the paired items, both arm means over those items, the mean and median lift and how many pairs improved, worsened or stayed equal. Items answered under one arm only are counted per model, and rows of other arms (a third arm of the same evaluation) are ignored and counted. The arithmetic is exact with fractions until the result is rounded to six decimals.

## Run it

As a library:

```python
from paired_arm_lift import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 paired_arm_lift.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `rows` (array of object, required): one judge's score of one model's answer to one item under one arm
- `baseline_arm` (string, required): the arm the lift is measured from
- `treatment_arm` (string, required): the arm the lift is measured to

## Output

- `baseline_arm` (string, required)
- `treatment_arm` (string, required)
- `models` (array of object, required): one summary per model, in model name order
- `overall` (object, required): every (model, item) pair of every model together
- `other_arm_rows` (integer, required): rows of arms other than the two compared

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `same_arm`: the baseline and treatment arms are the same arm
- `arm_not_found`: no row carries the baseline or the treatment arm
- `duplicate_grade`: one judge scored one model, arm and item twice

## Checks

`examples/known_good.json` and the 4 cases of `examples/known_answers.json` hold inputs with answers worked out by hand; `examples/known_wrong.json` holds an input the function refuses. `test_package.py` runs the known-good and known-wrong examples through the function and the command line, and every known answer through the function.

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `paired_arm_lift.py` | executable_tool |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `examples/known_answers.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## Source and SDG basis

The DueCare harness benchmark grades, which the owner published on Kaggle under CC BY 4.0 from the Gemma 4 Good Hackathon: 85,417 grades of eight models' answers under three arms (baseline, harness_core, harness_full) by a three-judge panel. Its headline, gemma4:31b going from 48.4 to 89.1 with the core harness, is this function's mean of baseline and treatment arms over paired prompts.

Built for:

- [`taylorsamarel/duecare-harness-benchmark-grades`](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades)

Dataset shape: panel_grades.csv: model, arm, prompt_id, judge, score_0_100 (prompt_id is the item and score_0_100 the score).

Proposed goals 5, 8, 16; targets 5.2, 8.7, 16.2. Inherited from the dataset it was built for, which grades model answers to labour-exploitation and trafficking prompts (targets 8.7, 16.2 and 5.2). The function itself is a general evaluation step. The association is a proposal for reviewers, not a grant.

## Limits

The lift is a plain paired difference of judge means; it carries no confidence interval or significance test, and every judge counts equally whatever its reliability (judge_agreement measures that). Items a model answered under one arm only are counted but not used. Scores are taken on one scale, so mixing rubrics in one input makes the means meaningless. Arm, model, item and judge names compare exactly.

This item is a candidate component. Generating it did not approve or qualify it.
