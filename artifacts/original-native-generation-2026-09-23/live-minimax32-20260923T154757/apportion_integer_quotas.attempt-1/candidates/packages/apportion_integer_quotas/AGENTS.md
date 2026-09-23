# AGENTS.md — apportion_integer_quotas

This package contains **one** native tool: `tools/apportion_integer_quotas.py`. It is a
self-contained, read-only, bounded CLI used to allocate an integer target sample
count across groups whose weights are nonnegative integers. The host already
provides all permissions it needs (it reads stdin and writes stdout). Nothing in
this package grants itself extra authority.

The host invokes this tool to plan a stratified sample. The tool never reads
files, opens sockets, runs subprocesses, or evaluates user-supplied code.

---

## 1. First action

Put a UTF-8 JSON object on stdin describing the groups and the target sample
count. The tool reads **exactly one** such object, prints **exactly one** JSON
object on stdout, then exits.

### Minimal example (bash)

```bash
printf '%s' '{"target":2,"weights":{"a":1,"b":1,"c":1}}' \
  | python3 tools/apportion_integer_quotas.py
# -> {"status":"ok","sum":2,"allocations":{"a":1,"b":1,"c":0}}
```

### Example showing ties broken by ID

```bash
printf '%s' '{"target":3,"weights":{"b":2,"a":2,"c":2}}' \
  | python3 tools/apportion_integer_quotas.py
# -> {"status":"ok","sum":3,"allocations":{"a":1,"b":1,"c":1}}
```

If the input is invalid the tool instead prints
`{"status":"refused","error":{"code":"...","message":"..."}}` and exits
non-zero.

---

## 2. Algorithm (Hamilton's largest-remainders method)

Let groups be indexed by unique nonempty IDs with nonnegative integer weights
`w_i`. Define

```
sum_w = sum(w_i)                 # exact, using Python ints
ideal_i = target * w_i / sum_w   # exact, using Fraction
floor_i = floor(ideal_i)         # exact integer
frac_i  = ideal_i - floor_i      # exact Fraction in [0, 1)
```

1. Start each group at `floor_i` so the partial sum is at most `target`.
2. Sort the remaining `(target - sum(floor_i))` slots to award by:
   - descending `frac_i`, then
   - ascending group ID.
3. Increment chosen groups by 1 each.

This guarantees `sum(allocations) == target` whenever `target >= 0`.

### Refusal cases (stable error codes)

| Code                  | Trigger                                                                            |
| --------------------- | ---------------------------------------------------------------------------------- |
| `E_INPUT_BYTES`       | The single stdin object exceeds 1 MiB (1 048 576 bytes) of UTF-8 text.              |
| `E_INPUT_SHAPE`       | Not a single JSON object, or extra outer JSON tokens.                              |
| `E_TARGET`            | `target` absent, non-integer, finite-negative, `null`, true/false, or non-finite.  |
| `E_WEIGHTS`           | `weights` absent, not an object, empty, has duplicate keys in JSON, etc.          |
| `E_WEIGHT_VALUE`      | A weight is non-integer, negative, `null`, true/false, or non-finite.             |
| `E_WEIGHT_ID`         | An ID is empty or not a string.                                                    |
| `E_WEIGHTS_ALL_ZERO`  | All weights are zero while `target > 0`.                                           |
| `E_INTERNAL`          | Catch-all for the host to surface an unexpected failure without traceback.        |

The tool never echoes the input or values back as part of an error message.

---

## 3. Contract summary

- Input: `{"target": int >= 0, "weights": { non-empty string -> int >= 0 }}`
  - Target must satisfy `0 <= target <= 2^53 - 1` to keep output JSON portable.
  - Weights must satisfy `0 <= w <= 2^53 - 1` for the same reason.
  - IDs must be unique nonempty strings with no JSON duplicate keys.
  - The entire stdin payload must be at most 1 048 576 UTF-8 bytes.
- Success output: `{"status":"ok","sum":int,"allocations":{id:int,...}}`.
- `sum` always equals `target` on success (0 returns 0 allocations).

See `contracts/input.schema.json` and `contracts/output.schema.json` for the
closed JSON Schemas covering input and output (success + refused).

---

## 4. Tests

`tests/test_apportion_integer_quotas.py` exercises the bundled CLI using
`unittest` plus `subprocess`. No third-party packages are installed and no
network is touched. Run with the repository root as the working directory:

```bash
python3 -m unittest tests/test_apportion_integer_quotas.py -v
```

The suite covers:

- the supplied acceptance examples (`a=1,b=1,c=1` with `target=2`,
  `b=2,a=2,c=2` with `target=3`),
- `target=0` returning `{"a":0,"b":0,"c":0}`,
- refusal of `target=-1`, non-integer weight, boolean weight, and duplicate IDs,
- the 1 MiB stdin ceiling,
- independent constructed examples with hand-computed expected allocations,
- a known-wrong reference algorithm (round-to-nearest) that violates
  `sum == target`, included only to document the distinction and never used by
  the CLI.

---

## 5. Resource and safety guarantees

- Reads **only** stdin. No `open()` of user paths.
- Writes **only** stdout. No filesystem mutation.
- No `subprocess`, no `socket`, no `urllib`, no `http.client`.
- No `eval`, no `exec`, no dynamic imports.
- No tracebacks printed. Refusals are structured JSON with a stable code.
- Exact arithmetic via `fractions.Fraction`; the algorithm is an exact,
  integer-preserving apportionment, not a rounding audit.

The host owns effect authority: this package does not grant itself permissions
or claim independent approval. All material here still requires the host's
independent review and qualification before production use.
