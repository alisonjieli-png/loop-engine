# Algorithm: Reverse BFS for Change Impact

## Overview
Given a directed graph where edges represent `consumer -> dependency`, we want to find all nodes reachable from a set of `changed_symbol_ids` by traversing edges in the **reverse** direction.

## Algorithm Steps
1. **Graph Inversion**: Construct an adjacency list where each key is a `dependency` and the value is a list of its `consumers`.
2. **Breadth-First Search (BFS)**:
   - Initialize a queue with the `changed_symbol_ids`.
   - Maintain a `visited` map storing `(distance, shortest_witness_path)`.
   - For each node popped from the queue:
     - If `distance < max_depth`, iterate through its consumers.
     - If a consumer hasn't been visited, add it to the queue and mark its distance and path.
3. **Termination**:
   - Stop if the number of nodes processed exceeds `max_nodes`.
   - Stop exploring a branch if `distance == max_depth`.
4. **Output**:
   - Return all visited nodes that were not in the original `changed_symbol_ids`.
   - If `max_nodes` was exceeded, set `truncated: true`.

## Complexity
- **Time**: $O(V + E)$ where $V$ is number of symbols and $E$ is number of edges.
- **Space**: $O(V)$ to store the adjacency list and visited map.

## Constraints & Refusals
- **Dangling Edges**: If an edge refers to a symbol ID not present in the `symbols` dictionary, the entire request is refused.
- **Types**: Strict checking for `int` vs `bool` to prevent JSON ambiguity.
- **Determinism**: Shortest path is guaranteed by BFS; tie-breaking for output is done by symbol ID.
