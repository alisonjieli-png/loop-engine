# Algorithm: Bounded Instruction Assembly

## Overview
The tool assembles a subset of text sections that fit within a specified integer budget. It prioritizes mandatory sections and then adds optional sections based on a descending priority and input order.

## Constraints
1. **Mandatory Closure**: If a section is marked `mandatory`, all its `predecessors` must also be included. If the total cost of a mandatory section and its required predecessors exceeds the budget, the entire operation is refused.
2. **Acyclic Precedence**: The dependency graph must be a Directed Acyclic Graph (DAG). Cycles result in `ERR_CYCLIC_DEPENDENCY`.
3. **Priority Selection**: Optional sections are considered in descending order of `priority`. If priorities are equal, the section appearing earlier in the input list is preferred.
4. **Prerequisite Closure for Optionals**: An optional section can only be added if its entire prerequisite closure (all ancestors in the dependency graph) can fit within the remaining budget.
5. **Topological Ordering**: The final output must be a stable topological sort of the selected sections. "Stable" means that among all valid topological sorts, the one that respects the original input order is chosen.

## Complexity & Bounds
- **Input Size**: Maximum 1MiB UTF-8 JSON.
- **Time Complexity**: $O(N + E)$ where $N$ is the number of sections and $E$ is the number of dependency edges, primarily due to topological sorting and cycle detection.
- **Space Complexity**: $O(N + E)$ to store the graph and selection sets.

## Known Limitations
- The tool does not perform "knapsack-style" optimization for optional sections; it uses a greedy approach based on priority and input order.
- Unit counts are treated as integer estimates of complexity/cost, not exact token counts.
