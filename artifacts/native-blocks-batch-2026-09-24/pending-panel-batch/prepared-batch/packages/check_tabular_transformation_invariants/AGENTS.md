# Check Tabular Transformation Invariants

## Purpose
Verify that a transformation of a tabular dataset preserves specific invariants: ID set integrity, field preservation (type-strict equality), allowed mutations, and integer sum consistency.

## First Action
Run the `tools/check_tabular_transformation_invariants.py` tool with a JSON payload via `stdin` to validate a specific transformation logic.

## Helper Invocation
```bash
cat example_input.json | python3 tools/check_tabular_transformation_invariants.py
```

## Contract & Refusal Rules
- **ID Integrity**: The set of unique, non-empty string IDs in `before` must exactly match the set in `after`.
- **Preserved Fields**: Values in `preserved_fields` must be identical in `before` and `after` using JSON-type-aware equality (e.g., `true` != `1`).
- **Allowed Changes**: Only fields listed in `allowed_changed_fields` may differ.
- **Integer Totals**: Fields in `integer_total_fields` must contain only integers (no booleans, no floats). The sum of these fields must be identical in `before` and `after`.
- **Refusals**:
    - Duplicate keys in input JSON.
    - Non-finite numbers (NaN, Inf).
    - Missing IDs or non-string IDs.
    - Sum mismatch or non-integer values in total fields.
    - Unlisted field mutations.
    - Input size > 1MiB.

