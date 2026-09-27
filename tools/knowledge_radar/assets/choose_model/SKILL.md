---
name: radar-choose-model
description: Choose the model with the lowest listed output price per published intelligence index point that meets your constraints (tool calling, structured output, reasoning, context size, price ceiling, licence), from the dated model table this package carries. Use when a harness must pick a model under a budget and wants a reproducible choice from dated data. It reads only its own files and makes no network call.
license: MIT
metadata:
  asset_version: "1.0.0"
  data_file: "references/models-table.json"
---

# Choose a model from the dated radar table

## What it returns

The models that meet every constraint you give, ordered by the listed output
price per published intelligence index point, lowest first. Ties go to the
lower output price, then to the name. The answer names the table's as-of and
valid-until days. After the valid-until day the helper refuses to choose and
answers `table_expired`, because an old table must not look current.

The rule uses published list prices and published index values. It is not a
cost per accepted task on your own work. Check the chosen model against the
step's own acceptance test before relying on it.

## How to call it

Pass one JSON object as the only argument, or `-` to read it from standard input:

```text
python scripts/choose_model.py '{"needs_tool_calling": true, "needs_structured_output": true, "minimum_context": 100000, "maximum_output_price": 2, "count": 3}'
```

Every field is optional. The fields and their defaults are in
[contracts/input.schema.json](contracts/input.schema.json).

## Output fields

`state` is `chosen`, `no_eligible_option` or `table_expired`. `chosen` lists
each model's title, address, output and input price in US dollars per
million tokens, price provider and price date, intelligence index, price per
index point, context size and licence. `rejected` counts the models left out,
by reason. The full contract is in
[contracts/output.schema.json](contracts/output.schema.json).

A value the table does not know never counts as support: a model whose tool
calling is unknown is not chosen when tool calling is required.

## Effects

It reads [references/models-table.json](references/models-table.json) from
this package and starts one Python process. It makes no network call and
writes nothing.

## Source and attribution

The table is built daily by the Baltor knowledge radar from the Baltor model
directory, which records OpenRouter prices with their dates and Artificial
Analysis index values as published. Each row keeps its address and dates.

## Limits

- Prices change often; the table is valid only until its valid-until day.
- Index values measure general ability, not your task.
- Reasoning effort settings and their cost are not in the table.

## How to check it

Run `python scripts/test_choose_model.py` from the package folder. It uses the
fixed table in [verification/fixture-table.json](verification/fixture-table.json)
and the cases in [verification/cases.json](verification/cases.json), including
known-wrong answers the helper must not give, and needs no network.
