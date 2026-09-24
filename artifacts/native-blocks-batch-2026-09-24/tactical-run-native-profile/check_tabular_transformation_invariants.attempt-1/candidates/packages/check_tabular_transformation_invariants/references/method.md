# Algorithm: Tabular Invariant Checker

## Overview
The tool performs a deterministic validation of a transformation between two datasets (`before` and `after`) based on a provided `contract`. It ensures that the transformation is "safe" according to specific business rules.

## Invariants Checked
1.  **ID Set Integrity**:
    - Every row must have a unique, non-empty string `id`.
    - The set of IDs in `before` must be identical to the set of IDs in `after`.
2.  **Field Preservation**:
    - Fields listed in `preserved_fields` must retain their exact value.
    - Equality is type-strict (JSON-style): `1` is not `true`, `"1"` is not `1`.
3.  **Mutation Control**:
    - Any field that changes value or is removed must be explicitly listed in `allowed_changed_fields`.
4.  **Integer Summation**:
    - Fields in `integer_total_fields` must contain only `int` types (no `bool`, no `float`).
    - The sum of these fields across all rows must be identical in both datasets.

## Complexity & Bounds
- **Time**: $O(N \times F)$ where $N$ is number of rows and $F$ is number of fields.
- **Space**: $O(N)$ to store the row maps.
- **Input Limit**: 1 MiB UTF-8 JSON.

## Known Limitations
- Does not check for schema evolution (e.g., new fields not in `before` but in `after` are treated as unauthorized mutations if not in `allowed_changed_fields`).
- Does not perform deep semantic validation of the data content itself, only the declared invariants.

## Known-Wrong Approach to Avoid
- Using `eval()` for numeric parsing.
- Using `==` in Python for equality where `True == 1` would pass (must use `type(a) is type(b)`).
- Using floating point for sums (must use `decimal.Decimal` or arbitrary precision integers to avoid precision drift).

