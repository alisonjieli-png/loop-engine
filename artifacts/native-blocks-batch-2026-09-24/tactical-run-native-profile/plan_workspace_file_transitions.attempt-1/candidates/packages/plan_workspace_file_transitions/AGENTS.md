# Plan Workspace File Transitions

## Task
Given three inventories (base, current, desired) representing the state of a workspace at different points in time, calculate the set of atomic file operations required to move from `current` to `desired`, respecting the constraints imposed by `base`.

## Contract
- **Input**: A JSON object containing `base`, `current`, and `desired` inventories. Each inventory is a map of `path` (string) to `digest` (SHA256 string). Missing files are represented by `null`.
- **Output**: A JSON object indicating `status` ("success" or "refused") and either `transitions` (list of operations) or `error` (code and message).
- **Operations**:
    - `create`: `base` is null, `current` is null, `desired` is value.
    - `update`: `base` is value, `current` is value, `desired` is different value.
    - `delete`: `base` is value, `current` is value, `desired` is null.
    - `noop`: `current` is value, `desired` is same value (regardless of `base`).
    - `conflict`: Any state where `current` has changed from `base` but is not the `desired` state, or where `current` is a different value than `base` when an update/delete was expected.
- **Safety Rules**:
    - Paths must be safe (no `..`, no absolute, no empty).
    - No case-fold collisions (e.g., `File.txt` and `file.txt` in same dir).
    - No file-directory collisions.
    - `current` must equal `base` for any `update` or `delete`. If `current != base` and `current != desired`, it is a `conflict`.

## First Action
1. Read 1MiB from `stdin`.
2. Parse JSON with strict checks (no duplicates, no non-finite numbers, no booleans where integers expected).
3. Validate schema.
4. Compute transitions.
5. Emit JSON.

## Refusal Codes
- `INVALID_JSON`: Malformed syntax.
- `DUPLICATE_KEY`: JSON contains duplicate keys.
- `NON_FINITE_NUMBER`: Contains `NaN` or `Infinity`.
- `SCHEMA_VIOLATION`: Missing keys or wrong types.
- `UNSAFE_PATH`: Path contains `..`, `/`, or is empty.
- `COLLISION`: Case-fold or file/dir collisions.
- `TYPE_MISMATCH`: Boolean used where integer/string expected.
