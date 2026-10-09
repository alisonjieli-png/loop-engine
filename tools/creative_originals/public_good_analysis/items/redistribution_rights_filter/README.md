# Rows whose own rights fields allow redistribution or training

Keep the rows of a corpus whose own licence is on an allowed list and whose permission flags allow public redistribution and, when asked, training use; every other row is excluded with its first failing reason, so a derived release carries only rows it may carry.

## What it does

Each row is checked in a fixed order: a licence is named, the licence is one of the allowed licences (exact match after trimming spaces), public redistribution is allowed when required (the default) and training use is allowed when required. The first failing check is the row's reason; kept ids and excluded rows keep the input order, and the counts cover every reason. A missing or null flag is not true.

## Run it

As a library:

```python
from redistribution_rights_filter import run
result = run(payload)  # payload: a dict shaped like the input schema
```

From a shell, with a JSON input document on standard input:

```bash
python3 redistribution_rights_filter.py < input.json
```

The `input` object of `examples/known_good.json` is a working input. Exit status 0 prints the result; exit status 2 prints `{"refused": true, "reason": ..., "detail": ...}`.

## Input

- `rows` (array of object, required): one row per record with its own licence and permission flags
- `allowed_licences` (array of string, required): licence identifiers a kept row may carry, such as CC-BY-4.0
- `require_redistribution` (boolean): keep only rows allowing public redistribution (default true)
- `require_training_use` (boolean): keep only rows allowing training use (default false)

## Output

- `kept` (array of string, required): ids of kept rows, in input order
- `excluded` (array of object, required): excluded rows in input order, each with its first failing reason
- `counts` (object, required)

## Refusals

- `input_invalid`: the input does not match the input schema
- `input_not_json`: standard input is not a JSON document
- `duplicate_id`: two rows share an id

## Checks

`examples/known_good.json` and the 3 cases of `examples/known_answers.json` hold inputs with answers worked out by hand; `examples/known_wrong.json` holds an input the function refuses. `test_package.py` runs the known-good and known-wrong examples through the function and the command line, and every known answer through the function.

## Files

| File | Role |
| --- | --- |
| `README.md` | other |
| `redistribution_rights_filter.py` | executable_tool |
| `examples/known_good.json` | other |
| `examples/known_wrong.json` | other |
| `examples/known_answers.json` | other |
| `kit_schema.py` | shared JSON Schema subset validator and command line runner |
| `test_package.py` | shared package tests |

## Source and SDG basis

The DueCare measured response training corpus (CC BY 4.0, Gemma 4 Good Hackathon), where every row states its licence, its rights holder and whether it may be redistributed or used for training.

Built for:

- [`taylorsamarel/duecare-measured-response-training-corpus`](https://www.kaggle.com/datasets/taylorsamarel/duecare-measured-response-training-corpus)

Dataset shape: the corpus rows: id, license, allow_public_redistribution, allow_training_use, rights_basis.

Proposed goals 5, 8, 16; targets 5.2, 8.7, 16.2. Inherited from the dataset it was built for, a corpus about labour exploitation and trafficking whose rows carry their own licence and permission flags (targets 8.7, 16.2 and 5.2). The function itself is a general release step. The association is a proposal for reviewers, not a grant.

## Limits

The filter trusts each row's own licence and flags; it does not verify them against the original source or decide what a licence allows. Licence identifiers compare exactly after trimming, so CC-BY-4.0 and CC BY 4.0 differ. A missing or null flag is never true. Legal review of the allowed list stays with the person releasing the data.

This item is a candidate component. Generating it did not approve or qualify it.
