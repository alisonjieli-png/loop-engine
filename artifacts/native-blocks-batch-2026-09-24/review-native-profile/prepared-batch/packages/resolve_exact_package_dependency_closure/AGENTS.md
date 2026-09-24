# Resolve Exact Package Dependency Closure

## Task
Resolve a bounded dependency graph from a set of provided package records based on requested identities.

## First Action
1. Read up to 1MiB of UTF-8 JSON from `stdin`.
2. Validate JSON structure, duplicate keys, and non-finite numbers.
3. Validate against `contracts/input.schema.json`.

## Helper Invocation
The tool is a standalone Python script: `tools/resolve_exact_package_dependency_closure.py`.
It accepts JSON via `stdin` and emits a single JSON object to `stdout`.

## Contract & Refusal Rules
- **Identity Collision**: If two records have the same `id` but different `digest`, refuse.
- **Version Conflict**: If the graph requires two different `revision` values for the same `id`, refuse.
- **Missing Dependency**: If a required `id` is not in the provided `records`, refuse.
- **Cycles**: If the dependency graph contains a cycle, refuse.
- **Type Strictness**: Reject booleans where integers are expected (e.g., `size`).
- **Effect Aggregation**: The output must include the union of all `effects` from the resolved dependency chain, even if the root request only specifies a subset.
- **Ordering**: Return the resolved list in a stable topological order (dependencies before consumers).

## Refusal Codes
- `INVALID_JSON`: Malformed JSON or size limit exceeded.
- `SCHEMA_VIOLATION`: Input does not match `input.schema.json`.
- `MISSING_RECORD`: A required dependency is not in the provided records.
- `DIGEST_MISMATCH`: Same ID found with different digests.
- `VERSION_CONFLICT`: Same ID found with different revisions.
- `CYCLE_DETECTED`: Circular dependency found.
- `TYPE_ERROR`: e.g., boolean used where integer was expected.
