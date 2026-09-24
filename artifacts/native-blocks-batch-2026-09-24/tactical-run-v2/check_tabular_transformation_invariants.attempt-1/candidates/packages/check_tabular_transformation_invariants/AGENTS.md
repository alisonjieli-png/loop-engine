# Check Tabular Transformation Invariants

## Task
Verify that a transformation from a 'before' dataset to an 'after' dataset adheres to a strict contract regarding identity preservation, field stability, and numeric integrity.

## First Action
1. Read the JSON payload from `stdin`.
2. Validate the payload against the input schema.
3. Execute the invariant checks:
    - ID Set Integrity (Uniqueness, Non-empty, Cardinality).
    - Preserved Fields (Recursive JSON equality).
    - Allowed Changes (Field-specific mutation).
    - Integer Totals (Summation and type strictness).

## Helper Invocation
The tool is invoked as a standalone Python process:
`echo '<json_payload>' | python3 tools/check_tabular_transformation_invariants.py`

## Contract Rules
- **ID Field**: Must be a unique, non-empty string. The set of IDs in 'before' must exactly match 'after'.
- **Preserved Fields**: Values must be identical in type and value (e.g., `true` != `1`).
- **Allowed Changes**: Only fields explicitly listed in `allowed_changes` may differ.
- **Integer Totals**: Fields in `integer_totals` must be integers (no booleans, no floats). The sum of these fields in 'before' must equal the sum in 'after'.

## Refusal Rules
- Reject if `id` is missing or duplicated.
- Reject if a `preserved` field changed.
- Reject if an `integer_total` field changed its sum or contains a non-integer.
- Reject if a field changed that was not in `allowed_changes`.
- Reject if the input exceeds 1MiB or contains duplicate keys.
