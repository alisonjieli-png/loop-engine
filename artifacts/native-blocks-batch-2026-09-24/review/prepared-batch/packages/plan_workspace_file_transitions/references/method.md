# Algorithm: Workspace File Transitions

## Logic Flow
For every unique path $P$ present in `base`, `current`, or `desired`:

1.  **Identify States**: Let $B = base[P]$, $C = current[P]$, $D = desired[P]$.
2.  **Noop Check**: If $C == D$, the action is `noop`. The current state already matches the goal.
3.  **Conflict Check**: If $C \neq B$ (the file has been modified locally) AND $C \neq D$ (the modification doesn't match the goal), the action is `conflict`.
4.  **Clean Transitions**: If $C == B$ (no local changes):
    - If $B$ is null and $D$ is not null $\rightarrow$ `create`.
    - If $B$ is not null and $D$ is null $\rightarrow$ `delete`.
    - If $B$ is not null and $D$ is not null and $D \neq B \rightarrow$ `update`.
    - If $B$ is not null and $D$ is not null and $D == B \rightarrow$ `noop` (already covered by step 2).

## Constraints
- **Path Safety**: Paths must not contain `..`, absolute roots, or empty segments.
- **Case Sensitivity**: On a single run, paths like `a.txt` and `A.txt` are considered a collision.
- **Type Strictness**: Booleans are not integers. `true` is not `1`.
- **Memory**: Input is capped at 1MiB.

## Known-Wrong Approach
A common mistake is to assume that if `base != desired`, an `update` must occur. This ignores the `current` state. If `current` has diverged from `base` in a way that doesn't match `desired`, it is a `conflict`, not an `update`.
