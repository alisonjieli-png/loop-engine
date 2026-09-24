# Algorithm: Reverse BFS Impact Analysis

## Overview
The tool calculates the "blast radius" of a change in a dependency graph. Given a set of symbols that have changed, it traverses the graph in reverse (from dependency to consumer) to find all symbols that depend on the changed ones.

## Algorithm Steps
1. **Inversion**: The input provides `consumer -> dependency` edges. We first construct an adjacency list of `dependency -> [consumers]`.
2. **Breadth-First Search (BFS)**:
   - Initialize a queue with the `changed_symbols`.
   - Maintain a `visited` map: `symbol_id -> (distance, path, evidence_list)`.
   - For each node popped from the queue:
     - If `distance < depth_limit`, expand its neighbors.
     - If a neighbor has not been visited, record its shortest distance, the path taken, and the edge evidence used.
3. **Termination**:
   - The search terminates when the queue is empty or `node_limit` is reached.
   - If `depth_limit` is reached, the traversal stops expanding further, and `is_complete` is set to `false`.
   - Cycles are naturally handled by the `visited` check.

## Complexity
- **Time**: $O(V + E)$ where $V$ is the number of symbols and $E$ is the number of edges.
- **Space**: $O(V + E)$ to store the inverted graph and the visited set.

## Constraints & Bounds
- **Depth Limit**: Prevents infinite or overly large traversals in deep graphs.
- **Node Limit**: Prevents memory exhaustion in extremely dense graphs.
- **Determinism**: Shortest path is guaranteed by BFS. If multiple shortest paths exist, the first one encountered in the adjacency list order is chosen.

## Known-Wrong Approach (Avoid)
- **DFS**: Depth-First Search does not guarantee the shortest path and can easily get stuck in cycles without complex bookkeeping.
- **Inference**: Do not assume a symbol exists if it is mentioned in an edge but not in the `symbols` dictionary; this is a `DANGLING_EDGE` error.
- **Recursive BFS**: Using recursion can lead to `RecursionError` on deep graphs; an iterative queue-based approach is preferred.
