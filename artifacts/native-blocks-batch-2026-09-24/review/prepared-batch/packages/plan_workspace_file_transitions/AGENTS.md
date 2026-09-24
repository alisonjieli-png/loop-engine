# Plan Workspace File Transitions

## Purpose
Calculate the set of file system operations (create, update, delete, noop, conflict) required to move a workspace from a `current` state to a `desired` state, given a `base` state for change detection.

## First Action
Invoke the tool with a JSON payload containing three dictionaries: `base`, `current`, and `desired`. Each dictionary maps a relative path (string) to a SHA256 digest (string). Missing files must be represented as `null`.

## Contract
- **Input**: A JSON object with `base`, `current`, and `desired` keys.
- **Output**: A JSON object containing either a `success` list of transitions or a `refused` object with an error code and message.
- **Transitions**:
    - `create`: `base` is null, `current` is null, `desired` is a value.
    - `update`: `base` is A, `current` is A, `desired` is B.
    - `delete`: `base` is A, `current` is A, `desired` is null.
    - `noop`: `current` is equal to `desired` (regardless of `base`).
    - `conflict`: 
        - `base` is A, `current` is B, `desired` is C (divergent change).
        - `base` is null, `current` is B, `desired` is C (untracked file vs new file).
        - `base` is A, `current` is B, `desired` is B (noop/stale).
        - `base` is A, `current` is B, `desired` is A (stale current).
        - *Note*: A file is a conflict if `current != base` AND `current != desired` AND `base != desired`.
        - *Note*: A file is a conflict if `current != base` AND `desired != null` AND `base != null` AND `current != desired`.
        - *Strict Rule*: Updates/Deletes are only permitted if `current == base`. If `current != base`, it is a `conflict` unless `current == desired` (which is a `noop`).

## Refusal Rules
- **Path Safety**: Reject paths with `..`, absolute paths, or empty strings.
- **Collisions**: Reject if a path is treated as both a file and a directory (implied by path structure) or case-fold collisions (e.g., `File.txt` and `file.txt` on case-insensitive systems).
- **Types**: Reject booleans where integers or strings are expected.
- **Size**: Reject JSON input > 1MiB.
- **JSON Integrity**: Reject duplicate keys or non-finite numbers.

