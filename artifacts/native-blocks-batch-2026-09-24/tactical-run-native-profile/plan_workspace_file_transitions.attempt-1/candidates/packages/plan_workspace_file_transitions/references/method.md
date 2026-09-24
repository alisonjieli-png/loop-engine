# Algorithm: Plan Workspace File Transitions

## Overview
The tool computes the delta between a `current` state and a `desired` state, using a `base` state to detect if files were modified independently (conflicts).

## Transition Logic
For every path $p$ in the union of all inventories:

1.  **Noop**: If $current(p) == desired(p)$, the operation is `noop`.
    - *Note*: This takes precedence even if $base(p) \neq current(p)$.
2.  **Create**: If $base(p) = \text{null}$, $current(p) = \text{null}$, and $desired(p) \neq \text{null}$, the operation is `create`.
3.  **Update**: If $base(p) = current(p)$ and $current(p) \neq desired(p)$ (and $desired(p) \neq \text{null}$), the operation is `update`.
4.  **Delete**: If $base(p) = current(p)$ and $desired(p) = \text{null}$, the operation is `delete`.
5.  **Conflict**: If none of the above apply:
    - If $current(p) \neq base(p)$, the file was modified since the base was recorded.
    - If $base(p) = \text{null}$ but $current(p) \neq \text{null}$, an unexpected file exists.

## Constraints
- **Path Safety**: No `..`, no absolute paths, no empty strings.
- **Collisions**: 
    - Case-insensitive collisions (e.g., `A.txt` and `a.txt`) are rejected.
    - File/Directory collisions are rejected (though this tool treats all paths as files in a flat map).
- **Strictness**: 
    - JSON must not contain duplicate keys.
    - JSON must not contain `NaN` or `Infinity`.
    - Booleans are not allowed where strings or integers are expected.

## Complexity
- **Time**: $O(N \log N)$ where $N$ is the number of unique paths (due to sorting for deterministic output).
- **Space**: $O(N)$ to store the inventories and the result.

## Limitations
- Does not perform actual filesystem IO.
- Assumes all paths are relative to the workspace root.
- Does not distinguish between file types (all are treated as blobs).
