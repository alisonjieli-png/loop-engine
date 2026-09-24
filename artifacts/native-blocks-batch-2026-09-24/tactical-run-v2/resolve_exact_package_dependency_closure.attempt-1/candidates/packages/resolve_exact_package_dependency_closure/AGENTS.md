# Agent Instructions: resolve_exact_package_dependency_closure

## Primary Objective
Resolve a closed dependency graph from a set of provided package records based on a list of requested identities. Ensure topological ordering, version consistency, and effect aggregation.

## First Action
Invoke the helper `tools/resolve_exact_package_dependency_closure.py` by piping a JSON payload (conforming to `contracts/input.schema.json`) into its `stdin`.

## Contract & Refusal Rules
- **Input**: A JSON object containing `available_packages` (the inventory) and `requested_identities` (the roots).
- **Success**: Returns a topologically sorted list of dependencies (leaves first), total unique file size, and the union of all required effects.
- **Refusal (Error Codes)**:
    - `MISSING_RECORD`: A requested identity or a dependency's identity is not in the inventory.
    - `DIGEST_MISMATCH`: The provided digest for a package does not match the inventory's record for that identity/revision.
    - `IDENTITY_COLLISION`: The same identity is provided with different digests in the same request.
    - `VERSION_CONFLICT`: The graph requires two different revisions of the same identity.
    - `CYCLE_DETECTED`: The dependency graph contains a circular reference.
    - `INVALID_INPUT`: JSON syntax errors, duplicate keys, non-finite numbers, or type mismatches (e.g., boolean where integer expected).
- **Effect Rule**: If any package in the resolved graph requires an effect (e.g., `network`), it must be included in the output even if the root request only specifies `reads_fs`.

## Helper Invocation Example
```bash
cat examples/input.json | python3 tools/resolve_exact_package_dependency_closure.py
```
