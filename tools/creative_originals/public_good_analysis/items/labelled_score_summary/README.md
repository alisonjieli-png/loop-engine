# Scores of each arm broken down by an item label

Join score rows with label rows on the item and summarize each arm per value of one chosen label (category, corridor, difficulty): count, mean, median, minimum and maximum, with scored items that have no label and labels that have no score counted and listed.

## What it does

Score rows (item, arm, score) are joined with label rows (an item and any label fields) on the item. For the one label field the input names, every (label value, arm) gets its count, mean, median, minimum and maximum. A label row that lacks the field, or holds null there, puts its item under the value null, listed first. Scores of items without a label row are left out and counted, with up to 20 listed by name, and so are label rows no score uses.

## Run it

As a library:

```python
from labelled_score_summary import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 labelled_score_summary.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `scores` (array of object, required): one score of one item under one arm
- `labels` (array of object, required): one row per item: the item and its label fields
- `label_field` (string, required): the label the scores are broken down by

## Output

- `label_field` (string, required)
- `groups` (array of object, required): one row per label value and arm, null value first
- `scores_used` (integer, required)
- `items_without_label` (integer, required): distinct scored items with no label row
- `items_without_label_examples` (array of string, required)
- `labels_without_scores` (integer, required): label rows no score row uses
- `labels_without_scores_examples` (array of string, required)

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_label`: two label rows name the same item
- `label_field_missing`: no label row holds the label field

## Checks

`examples/known_good.json` and the 4 cases of `examples/known_answers.json` hold inputs with answers worked out by hand; `examples/known_wrong.json` holds an input the function refuses. `test_package.py` runs the known-good and known-wrong examples through the function and the command line, and every known answer through the function.

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `labelled_score_summary.py` | executable_tool |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `examples/known_answers.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## Source and SDG basis

The DueCare harness benchmark grades (CC BY 4.0, Gemma 4 Good Hackathon), whose prompt metadata labels each prompt with a category of exploitation, a migration corridor such as Nepal->Qatar and a difficulty.

Built for:

- [`taylorsamarel/duecare-harness-benchmark-grades`](https://www.kaggle.com/datasets/taylorsamarel/duecare-harness-benchmark-grades)

Dataset shape: prompt_metadata.csv: prompt_id, category, corridor, difficulty, source, joined to panel_grades.csv on prompt_id.

Proposed goals 5, 8, 16; targets 5.2, 8.7, 16.2. Inherited from the dataset it was built for, whose prompt labels name forms of labour exploitation and migration corridors (targets 8.7, 16.2 and 5.2). The function itself is a general summary step. The association is a proposal for reviewers, not a grant.

## Limits

One label field per call; a breakdown by two fields needs a combined label. Items without a label row are left out of every group, so a group's count can be lower than the item count. Label values compare as JSON values: the text 1 and the number 1 are two values. Up to 20 unmatched items are listed by name and the counts cover all of them.

This item is a candidate component. Generating it did not approve or qualify it.
