# Delta-rule associative memory

Stores key-value pairs in a matrix and retrieves a value by multiplying the matrix with its key. The delta rule writes only the part of a value the memory currently gets wrong. It is compared with the Hebbian rule, which only adds, and with the minimum-norm memory that reproduces every pair.

## When to use it

- Test a fast-weight memory, a linear-attention state or a key-value cache model for interference between stored items.
- Show how correlated keys corrupt retrieval under an additive rule and how an error-correcting rule fixes the latest write.
- Get a reference memory (`least_squares_memory`) to compare an iterative scheme against.

## Formula

    delta rule:     M <- M + rate (v - M k) k^T
    Hebbian rule:   M <- M + rate v k^T
    retrieval:      v_hat = M k
    reference:      M* = V (K^T K)^-1 K^T     (keys as the columns of K, values as the columns of V)

- With `rate * ||k||^2 = 1`, the write stores `(k, v)` exactly (`normalize_by_key_norm` divides the rate by `||k||^2`).
- A write with a key orthogonal to `k` does not change the retrieval of `k`.
- With unit keys and rate 1, repeated sweeps are the Kaczmarz method. From `M = 0` they converge to `M*` when the keys are independent.
- The update is stable for `0 < rate * ||k||^2 < 2`. Divergence raises `ValueError`.

## Assumptions and what it does not establish

- Keys and values are fixed-length real vectors. `store_pairs` starts from a zero memory.
- More pairs than key dimensions cannot all be stored. Sweeps then cycle without converging.
- The tool measures storage and interference. It says nothing about how a trained model chooses its keys.

## Parameters

| Name | Meaning |
|---|---|
| `memory` | value_size by key_size matrix |
| `key`, `value` | vectors of the key and value sizes |
| `keys`, `values` | rows of keys and the matching rows of values |
| `rate` | positive step size |
| `sweeps` | passes over all pairs, 1 to 100000 |
| `rule` | `"delta"` (default) or `"hebbian"` |
| `normalize_by_key_norm` | divide the rate by `||k||^2` at each write |

## Example

```python
from delta_rule_associative_memory import store_pairs

keys, values = [[1, 0], [0.6, 0.8]], [[1], [0]]
store_pairs(keys, values)["errors"]                    # [0.36, 0.0]: the latest pair is exact
store_pairs(keys, values, rule="hebbian")["errors"]    # [0.0, 0.6]: crosstalk on the latest pair
store_pairs(keys, values, sweeps=200)["memory"]        # [[1.0, -0.75]], the interpolating memory
```

Command line:

```bash
echo '{"call": "store_pairs", "arguments": {"keys": [[1, 0], [0, 1]], "values": [[3, 4], [5, 6]]}}' | python3 delta_rule_associative_memory.py
```

## Limits

- Dense matrices for small sizes (tens to a few hundred).
- Nearly parallel keys make sweeps converge slowly.
- No decay, gating or forgetting terms.

## Files

- `delta_rule_associative_memory.py`: the functions and the JSON command line.
- `numerics.py`, `atom_cli.py`, `schema_lite.py`: shared helpers.
- `test_delta_rule_associative_memory.py`, `test_package.py`: run with `python3 -m unittest`.
