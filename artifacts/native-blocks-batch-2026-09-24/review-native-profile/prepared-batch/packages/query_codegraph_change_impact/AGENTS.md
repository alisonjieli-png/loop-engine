# Agent Instructions: query_codegraph_change_impact

## Task
Calculate the impact of symbol changes in a code graph by performing a reverse breadth-first traversal from changed symbols to their consumers.

## First Action
1. Inspect `contracts/input.schema.json` to understand the required graph structure.
2. Review `tools/query_codegraph_change_impact.py` for the core logic implementation.

## Helper Invocation
The tool is invoked via `python3 tools/query_codegraph_change_impact.py` reading a JSON payload from `stdin`.

## Contract & Refusal Rules
- **Input**: A JSON object containing `symbols`, `files`, `edges`, `changed_symbol_ids`, and `limits`.
- **Output**: A JSON object with `status` ("success" or "refused"), `results` (on success), or `error` (on refusal).
- **Refusals**:
    - Duplicate keys in input JSON.
    - Non-finite numbers.
    - Booleans where integers are expected.
    - Dangling edges (edge refers to a non-existent symbol).
    - Malformed hashes or negative source ranges.
    - Exceeding `max_nodes` or `max_depth` (must report `truncated: true`).
- **Constraints**: Python 3.10+ standard library only. No `eval`, no `exec`, no network, no filesystem mutation.
