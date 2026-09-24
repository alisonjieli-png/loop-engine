# Algorithm: Traceable Evidence Selection

## Overview
The selection process is a deterministic two-stage pipeline:
1. **Integrity Check**: Validates that every record in the `evidence_pool` exists in the `registry` and that its `span` is contained within the registry's recorded `bounds`.
2. **Budgeted Selection**: Sorts valid records by `required` status, then `priority` (descending), then input order. It greedily adds records until the `byte_budget` is reached.

## Conventions
- **Byte Calculation**: Uses UTF-8 encoding length of the `content` string.
- **Contradiction Handling**: A `contradiction_group` is a list of IDs. If exactly one ID from a group is present in the `selected_records`, the remaining IDs in that group are added to `unresolved_contradictions`.
- **Stability**: When priorities are equal, the original order in the `evidence_pool` is preserved.

## Bounds
- **Input Size**: Max 1MiB JSON.
- **Complexity**: $O(N \log N)$ where $N$ is the number of records in the pool (due to sorting).

## First Actions
1. Validate JSON structure and types.
2. Filter pool against registry.
3. Sort and select within budget.
4. Identify unresolved contradictions.

## Known-Wrong Approach
An approach that uses a LLM to decide which records to select is "wrong" for this specific helper. The helper must be **deterministic**. The LLM's role is to decide *relevance* (which IDs to mark as `required_ids`), but the helper's role is to ensure the selection is *traceable* and *within budget*.

## Limitations
- Does not perform semantic deduplication (if two records have the same content, they are treated as distinct).
- Does not validate the actual text content of the `content` field against the registry; it only validates the `span` indices.
