# Algorithm: Bounded Instruction Section Assembly

## Overview
The goal is to select a subset of text sections that satisfy a budget constraint while respecting mandatory requirements and precedence constraints.

## Steps
1. **Parsing**: Read JSON from stdin. Detect duplicate keys and non-finite numbers. Ensure `cost` and `priority` are integers, not booleans.
2. **Graph Construction**: Build a directed graph where an edge $u \to v$ exists if $u$ is a predecessor of $v$.
3. **Validation**:
   - Check for unknown dependencies.
   - Check for cycles using DFS.
4. **Mandatory Selection**:
   - Identify all sections marked `mandatory`.
   - For each mandatory section, compute its transitive closure of predecessors.
   - Sum the costs of all unique sections in this mandatory set.
   - If `sum > budget`, refuse with `ERR_MANDATORY_OVER_BUDGET`.
5. **Greedy Optional Selection**:
   - Identify optional sections not in the mandatory closure.
   - Sort them by `priority` (descending) and then by their original index in the input array (ascending).
   - For each candidate, compute its required closure (all predecessors).
   - If the cost of the *new* sections introduced by this closure fits in the remaining budget, add them to the selected set.
6. **Topological Sort**:
   - Perform a topological sort on the selected set.
   - To ensure stability, when multiple nodes have an in-degree of 0, select the one that appeared earliest in the original input list.
7. **Output Generation**:
   - Concatenate the text of selected sections in topological order.
   - Calculate the UTF-8 byte offsets for each section.

## Complexity
- Time: $O(N \cdot (N + E))$ where $N$ is number of sections and $E$ is number of dependencies.
- Space: $O(N + E)$.

## Limitations
- Does not attempt to optimize the budget via knapsack; uses a greedy priority-based approach.
- Assumes all costs are positive integers.
