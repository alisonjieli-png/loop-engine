---
name: radar-choose-model
description: Shortlist the models that openly licensed catalogues (models.dev and the LiteLLM price map) mark as supporting structured output, cheapest estimated cost per call first, under your constraints (tool calling, reasoning, context size, price ceilings, providers), from the dated table this package carries. Use when a step extracts typed fields from text and should try the cheapest candidates first; then run your own acceptance check on your own route. It reads only its own files and makes no network call.
license: MIT
metadata:
  asset_version: "2.0.0"
  data_file: "references/models-table.json"
---

# Shortlist models for structured extraction from the dated radar table

## What it returns

The models that meet every constraint you give, ordered by the estimated
listed cost of one call: the listed input price times your expected input
tokens plus the listed output price times your expected output tokens. Ties
go to the lower output price, then to the name. The answer names the table's
as-of and valid-until days. After the valid-until day the helper refuses to
choose and answers `table_expired`, because an old table must not look
current.

This is a shortlist, not a result. A catalogue that says a route supports
structured output has not shown that the route honours your schema: Ollama's
own documentation has said since April 22, 2026 that its cloud does not
support structured outputs. Run your acceptance check (for example field
accuracy of at least 0.95 on held-out records and valid JSON after at most
one repair) on your own route before relying on any candidate.

## How to call it

Pass one JSON object as the only argument, or `-` to read it from standard input:

```text
python scripts/choose_model.py '{"needs_tool_calling": true, "minimum_context": 32000, "expected_input_tokens": 1500, "expected_output_tokens": 200, "count": 3}'
```

Every field is optional. The fields and their defaults are in
[contracts/input.schema.json](contracts/input.schema.json).

## Output fields

`state` is `chosen`, `no_eligible_option` or `table_expired`. `chosen` lists
each model's title, address, provider, model identifier, input and output
price in US dollars per million tokens, context size, capability flags,
retirement date and estimated cost per call. `rejected` counts the models
left out, by reason. The full contract is in
[contracts/output.schema.json](contracts/output.schema.json).

A value the table does not know never counts as support: a model whose
structured output support is unknown is not chosen when it is required. A
model whose retirement date has passed is never chosen.

## Effects

It reads `references/models-table.json`, which the daily package adds, from
this package and starts one Python process. It makes no network call and
writes nothing.

## Source and attribution

The table is built daily by the Baltor knowledge radar from models.dev (MIT)
and the LiteLLM price map (MIT). Each row keeps its address and dates.
Values from OpenRouter and Artificial Analysis are not in the table, because
their terms do not allow storing them in a served file.

## Limits

- Prices change often; the table is valid only until its valid-until day.
- Listed prices are not a measured cost per accepted task.
- Reasoning effort settings and their cost are not in the table.

## How to check it

Run `python scripts/test_choose_model.py` from the package folder. It uses the
fixed table in [verification/fixture-table.json](verification/fixture-table.json)
and the cases in [verification/cases.json](verification/cases.json), including
known-wrong answers the helper must not give, and needs no network.
