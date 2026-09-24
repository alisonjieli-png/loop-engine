# Algorithm: Exact Package Dependency Closure

## Overview
The tool resolves a dependency graph where every node is uniquely identified by a combination of `id`, `revision`, and `digest`. Unlike standard package managers that might allow version ranges, this tool requires exact matches, making it suitable for deterministic build environments.

## Algorithm Steps
1. **Inventory Mapping**: The `available_packages` dictionary is indexed by `id@rev` for $O(1)$ lookup.
2. **Recursive Traversal (DFS)**:
   - Starting from each `requested_identity`, perform a Depth-First Search.
   - **Cycle Detection**: Maintain a stack of the current traversal path. If a node is revisited within the same path, a `CYCLE_DETECTED` error is raised.
   - **Identity Collision**: If a node with the same `id` but a different `digest` is encountered during the resolution of the requested set, an `IDENTITY_COLLISION` is raised.
   - **Version Conflict**: If the graph requires two different `rev` values for the same `id`, it is treated as a collision/conflict.
3. **Topological Sort**: Nodes are added to the result list only after all their dependencies have been visited (Post-order traversal). This ensures that dependencies appear before the consumers in the output list.
4. **Aggregation**:
   - **Size**: Sum the `size` attribute of all unique resolved packages.
   - **Effects**: Collect the union of all `effects` strings from all resolved packages.

## Constraints & Bounds
- **Input Size**: Maximum 1MiB UTF-8 JSON.
- **Complexity**: $O(V + E)$ where $V$ is the number of packages and $E$ is the number of dependency links.
- **Memory**: $O(V)$ to store the resolved graph and identity maps.
- **No Side Effects**: The tool never touches the filesystem or network; it operates purely on the provided JSON inventory.

## Known-Wrong Approaches to Avoid
- **Using `set()` for topological sort**: A simple set of visited nodes does not guarantee the "dependencies before consumers" order.
- **Ignoring Effects**: Forgetting to aggregate effects from sub-dependencies.
- **Permissive Versioning**: Allowing `A@1` and `A@2` to coexist in the same resolved graph (this tool enforces a single version per identity).

