# Typed work result with six outcomes

A JSON Schema and a validator for the one result a bounded unit of agent work returns. Each result is exactly one of six outcomes, so a caller never has to guess whether "done" meant finished, skipped, blocked or out of budget.

## When to use it

- A harness hands a task to a worker (a subagent, a tool run, a model call) and needs a result it can route without reading prose.
- You want "completed" to always carry evidence, and "blocked" to always say what would unblock it.
- You want an out-of-budget stop to leave a checkpoint and a list of what is still owed.

## Contract

| Outcome | Required fields | Finished |
|---|---|---|
| `completed` | `artifact` (a reference), `evidence` (at least one) | yes |
| `no_change_needed` | `evidence` (at least one) | yes |
| `needs_input` | `required_fields` (name, description, optional type and choices) | no |
| `needs_scope_expansion` | `reason`, `proposed_scope` (`add`, optional `remove`) | no |
| `unsupported` | `reason` | yes |
| `budget_exhausted` | `checkpoint` (a reference), `remaining_obligations`, optional `consumed` | no |

Every result has `record_type: "work_result/v1"` and `outcome`, and may carry `notes`. A reference is `{kind, locator, sha256?}` with kind `file`, `commit`, `record`, `message` or `address`. Evidence is `{claim, method, reference}` with method `test`, `measurement`, `inspection`, `citation` or `external_confirmation`. Fields of another outcome are refused (`additionalProperties: false` in each branch).

Rules the validator adds beyond the schema:

- The artifact is not evidence for itself: a completed result cites at least one reference other than the artifact.
- `needs_input` field names are unique. A field of type `choice` lists `choices`, and only such a field does.
- `remaining_obligations` are unique.
- A scope expansion does not add and remove the same item, and does not repeat items.

## Assumptions and what it does not establish

- The validator checks shape and consistency. It does not open references, rerun tests or decide whether the evidence supports the claim.
- A valid `completed` result is a claim with citations, not an accepted result. Acceptance is a separate, independent step.

## Parameters

| Function | Arguments | Returns |
|---|---|---|
| `validate_work_result` | `result` | `{valid, outcome, terminal, errors}` |
| `classify_work_result` | a valid `result` | `{outcome, terminal, next_step}`; `ValueError` when invalid |
| `make_work_result` | `outcome`, `fields` | the full result; `ValueError` when invalid |

## Example

```python
from work_result_type import make_work_result, classify_work_result

result = make_work_result("budget_exhausted", {
    "checkpoint": {"kind": "commit", "locator": "a1b2c3d"},
    "remaining_obligations": ["migrate table b", "update docs"],
})
classify_work_result(result)["terminal"]   # False: resume from the checkpoint or record the obligations as open
```

Command line:

```bash
echo '{"call": "validate_work_result", "arguments": {"result": {"record_type": "work_result/v1", "outcome": "unsupported", "reason": "needs a GPU"}}}' | python3 work_result_type.py
```

## Limits

- Six fixed outcomes. A new outcome needs a new record type.
- Text fields hold at most 2000 characters. Field names are lower-case identifiers.
- `schema.json` is the declarative contract; `work_result_type.py` embeds an identical copy so it reads no file, and the tests check the two match.

## Files

- `schema.json`: the JSON Schema (draft 2020-12).
- `work_result_type.py`: the validator, constructor, classifier and JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers (`schema_lite` validates the schema subset).
- `test_work_result_type.py`, `test_package.py`: run with `python3 -m unittest`.
