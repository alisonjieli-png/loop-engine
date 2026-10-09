# Leakage of related rows across dataset splits

Find groups of related rows (a prompt cluster, a lineage family, a source document) whose rows fall in more than one of the train, validation and test splits, with the splits and row counts of each leaking group, so held-out scores are not inflated by near-copies.

## What it does

Each row carries an id, a split and grouping fields. For each grouping field the input names, the function counts the field's values, lists every value seen in more than one split with its rows per split, counts the rows those values hold and the rows without a value, and says whether anything leaks. Ids are checked for repeats first, because a repeated id makes rows impossible to tell apart.

## Run it

As a library:

```python
from split_leakage_check import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 split_leakage_check.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `rows` (array of object, required): one row per example: its id, its split and its grouping fields
- `group_fields` (array of string, required): the fields whose values must stay inside one split

## Output

- `leaking` (boolean, required)
- `rows` (integer, required)
- `splits` (object, required): rows per split
- `fields` (array of object, required): one row per grouping field, in input order

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_id`: two rows share an id
- `group_field_missing`: no row holds a grouping field

## Checks

`examples/known_good.json` and the 3 cases of `examples/known_answers.json` hold inputs with answers worked out by hand; `examples/known_wrong.json` holds an input the function refuses. `test_package.py` runs the known-good and known-wrong examples through the function and the command line, and every known answer through the function.

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `split_leakage_check.py` | executable_tool |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `examples/known_answers.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## Source and SDG basis

The DueCare measured response training corpus (CC BY 4.0, Gemma 4 Good Hackathon), whose training lanes carry a split and two grouping keys, prompt_cluster_id and lineage_family_id.

Built for:

- [`taylorsamarel/duecare-measured-response-training-corpus`](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus)

Dataset shape: the corpus's training lanes: id, split, prompt_cluster_id, lineage_family_id.

Proposed goals 5, 8, 16; targets 5.2, 8.7, 16.2. Inherited from the dataset it was built for, a training corpus of graded answers to labour-exploitation and trafficking prompts (targets 8.7, 16.2 and 5.2). The function itself is a general data-quality step. The association is a proposal for reviewers, not a grant.

## Limits

Only the grouping fields named are checked; near-duplicates that share no field value are not found (duplicate_record_finder compares content). Values compare exactly, so two spellings of one group id are two groups. Up to 100 leaking values are listed per field and the counts cover all of them.

This item is a candidate component. Generating it did not approve or qualify it.
