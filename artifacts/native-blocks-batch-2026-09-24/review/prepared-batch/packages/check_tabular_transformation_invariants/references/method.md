# Algorithm: Tabular Transformation Invariant Checker

## Overview
The tool performs a deterministic validation of data transformations. It ensures that the mapping from a source state to a target state respects a set of logical invariants defined in a contract.

## Core Logic
1. **Input Parsing**: Reads a JSON object from `stdin`. The object must contain `before`, `after`, and `contract`.
2. **Identity Validation**:
   - Extracts the `id_field`.
   - Ensures every row has a unique, non-empty string ID.
   - Ensures the set of IDs in `before` is identical to the set of IDs in `after`.
3. **Field Stability**:
   - For every ID, it iterates through `preserved_fields`.
   - Uses recursive type-aware equality (e.g., `True` is not `1`).
   - Checks that any field not in `preserved_fields` or `allowed_changes` remains unchanged.
4. **Numeric Integrity**:
   - For every field in `integer_totals`, it verifies all values are strictly `int` (rejecting `bool` and `float`).
   - It calculates the sum of these fields in both datasets using `decimal.Decimal` for arbitrary precision.
   - Rejects if `sum(before) != sum(after)`.

## Known Limitations
- Does not validate the semantic meaning of data (e.g., it doesn't know if a name change is "correct", only if it was "allowed").
- Does not perform schema validation on the rows themselves, only on the contract and the transformation invariants.
- Memory usage is proportional to the input size (max 1MiB).

## Complexity
- **Time**: $O(N \times F)$ where $N$ is number of rows and $F$ is number of fields.
- **Space**: $O(N)$ to store the row maps for comparison.
