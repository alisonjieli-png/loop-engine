# Resolve Exact Package Dependency Closure

## Algorithm
1. **Input Parsing**: Read UTF-8 JSON from `stdin`. Use a custom `object_pairs_hook` to detect duplicate keys during parsing. Validate that no number is `NaN` or `Inf`.
2. **Validation**: Ensure the input matches the schema.
3. **Graph Traversal**:
   - Perform a Depth-First Search (DFS) starting from each `requested_id`.
   - Maintain a `path` set to detect cycles (if a node is revisited in the current recursion stack).
   - Maintain a `visited` set to avoid redundant processing and ensure topological order.
4. **Topological Sort**: Append nodes to the `resolved_dependencies` list *after* their children have been visited. This ensures dependencies appear before consumers.
5. **Aggregation**:
   - Sum the `size` of all unique packages in the resolved set.
   - Collect all unique `effects` strings from the resolved set.
6. **Error Handling**:
   - If a dependency is missing from `records` $\rightarrow$ `MISSING_RECORD`.
   - If a cycle is found $\rightarrow$ `CYCLE_DETECTED`.
   - If a `size` is a `bool` instead of `int` $\rightarrow$ `TYPE_ERROR`.

## Conventions
- **Stability**: The output order is determined by the input order of `requested_ids` and the DFS traversal.
- **Bounds**: Input is capped at 1MiB.
- **Strictness**: Types are checked strictly (e.g., `1` is an integer, `True` is a boolean and will fail if an integer is expected).

## Known-Wrong Approach
A common mistake is to use a simple `set` for the output list, which loses the topological order required for installation/resolution. Another mistake is to only include effects declared by the root package, ignoring the transitive effects of dependencies.

## Limitations
- Does not perform network or filesystem operations.
- Does not resolve version ranges; it requires exact identity matches.
- Does not verify the actual content of the files, only the metadata provided in the `records` object.
