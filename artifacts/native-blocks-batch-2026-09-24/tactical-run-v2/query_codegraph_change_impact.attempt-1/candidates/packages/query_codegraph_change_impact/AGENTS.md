# Query Code Graph Change Impact

## Focused Task
Given a bounded graph snapshot of unique symbol IDs, source file digests/ranges, and directed `depends_on` edges (consumer $\to$ dependency), report reverse-reachable consumers of changed symbols using breadth-first traversal.

## First Action
1. Read exactly one JSON object from `stdin` (max 1MiB).
2. Validate schema, types (reject booleans where integers are expected), and data integrity (no duplicate keys, no non-finite numbers).
3. Perform BFS on the inverted graph to find all consumers affected by the provided `changed_symbols`.

## Contract & Refusal Rules
- **Input**: A JSON object containing `symbols`, `files`, `edges`, `depth_limit`, and `node_limit`.
- **Output**: A JSON object with `status` ("success" or "refused"), `impacted_symbols` (list of objects), and `metadata` (incompleteness flags).
- **Refusal**: If input is malformed, exceeds limits, or contains dangling edges, return `status: "refused"` with a stable `error_code`.
- **Incompleteness**: If the traversal hits `depth_limit` or `node_limit`, mark `is_complete: false`. Do not claim a complete impact if truncated.
- **Deterministic Path**: For each impacted symbol, provide exactly one shortest witness path (sequence of symbol IDs) and the edge evidence.
- **Constraints**: Python 3.10+ standard library only. No `eval`, `exec`, or external network/FS calls.

## Helper Invocation
The tool is invoked via `python3 tools/query_codegraph_change_impact.py < input.json`.
