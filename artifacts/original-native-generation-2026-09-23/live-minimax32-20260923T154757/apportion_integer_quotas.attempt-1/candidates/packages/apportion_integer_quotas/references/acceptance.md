# Reference: apportion_integer_quotas

## 1. Mathematical contract

Given a target `T ∈ ℕ₀` and weights `w : ID → ℕ₀` with `id ∈ ID` unique
nonempty strings and `∑ w > 0` whenever `T > 0`, the algorithm returns
`a : ID → ℕ₀` such that:

1. **Existence:** `a(id) ≥ 0` for every `id`.
2. **Global invariant:** `∑_id a(id) == T`.
3. **Hamilton optimality:** no group `i` with strictly positive remainder can
   receive less than any group `j` with strictly smaller or equal remainder
   unless `i` and `j` share the remainder; ties are broken by ascending `id`.

The implementation uses `fractions.Fraction` so `ideal_i = T·w_i / W` is
exact; the floor and remainder are then derived without floating-point error.

## 2. Limitations

* This is **an integer allocation algorithm**, not a rounding audit. It does
  *not* attempt to attribute or propagate pre-existing floating-point error
  from upstream instrumentation. (That is the role of
  `trace-numeric-rounding`; this method is narrower.)
* `target` and weight values are capped at `2^53 − 1` so the output remains
  portable JSON. Inputs above this range are refused with `E_TARGET` or
  `E_WEIGHT_VALUE`.
* The whole stdin payload is capped at 1 MiB. Larger inputs are refused with
  `E_INPUT_BYTES`.

## 3. Independent worked examples

### 3.1 Classic 5-group textbook example

Weights `{p:6, q:6, r:5, s:3, t:1}` summing to 21, target `T=20`.

| id | w | ideal = 20·w/21 | floor | remainder |
|----|---|------------------|-------|-----------|
| p  | 6 |  5.714285…       | 5     | 0.714285… |
| q  | 6 |  5.714285…       | 5     | 0.714285… |
| r  | 5 |  4.761904…       | 4     | 0.761904… |
| s  | 3 |  2.857142…       | 2     | 0.857142… |
| t  | 1 |  0.952380…       | 0     | 0.952380… |

Floors sum to 16; the 4 remaining slots go to (t, s, r, q) in that order,
breaking the p/q tie by ascending id. Final allocations:
`{p:6, q:6, r:4, s:3, t:1}`.

### 3.2 One-shot small example

Weights `{a:1, b:2, c:3, d:4}` summing to 10, target `T=7`.

| id | w | ideal = 7·w/10    | floor | remainder |
|----|---|-------------------|-------|-----------|
| a  | 1 | 0.7               | 0     | 0.7       |
| b  | 2 | 1.4               | 1     | 0.4       |
| c  | 3 | 2.1               | 2     | 0.1       |
| d  | 4 | 2.8               | 2     | 0.8       |

Floors sum to 5; the 2 remaining slots go to (d, a). Final allocations:
`{a:1, b:1, c:2, d:3}`.

## 4. Nearest prior distinction

`trace-numeric-rounding` is a *general* numeric-rounding audit. It inspects
existing numerical computations and reports where rounding changed values.

`apportion_integer_quotas` is **not** a rounding audit. It is a *constructive*
allocation algorithm that produces an integer vector satisfying a global sum
invariant. The two methods share a concern with integer-ness, but
`apportion_integer_quotas` requires no prior trace and adds no rounding
attribution; its output is the allocation itself, exact and reproducible.

## 5. Refusal codes

| Code                  | Meaning                                                              |
| --------------------- | -------------------------------------------------------------------- |
| `E_INPUT_BYTES`       | Stdin exceeded 1 MiB.                                                |
| `E_INPUT_SHAPE`       | Input was not exactly one JSON object, or contained duplicate keys.  |
| `E_TARGET`            | `target` missing, non-integer, negative, boolean, or non-finite.      |
| `E_WEIGHTS`           | `weights` missing, not an object, or empty.                          |
| `E_WEIGHT_VALUE`      | A weight is not a non-negative integer.                              |
| `E_WEIGHT_ID`         | A weight key is missing, empty, or not a string.                     |
| `E_WEIGHTS_ALL_ZERO`  | Every weight is zero while `target > 0`.                             |
| `E_INTERNAL`          | Defensive catch-all (no traceback is ever printed).                  |

All refusals are returned as a single JSON object on stdout with a stable
`error.code` string; the host can branch on the code without parsing prose.
