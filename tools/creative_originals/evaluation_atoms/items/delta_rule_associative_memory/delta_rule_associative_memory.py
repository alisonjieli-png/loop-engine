"""Delta-rule associative memory: store key-value pairs in a matrix by error-correcting outer-product updates.

    delta rule:   M <- M + rate (v - M k) k^T      (writes only the part of v the memory gets wrong)
    Hebbian rule: M <- M + rate v k^T              (adds, and accumulates crosstalk between keys)
    retrieval:    v_hat = M k

With rate * ||k||^2 = 1 an update stores the current pair exactly. Pairs with orthogonal keys do not disturb each
other. With unit keys and rate 1, repeated sweeps are the Kaczmarz method: starting from M = 0 they converge to the
minimum-norm memory that reproduces every pair when the keys are linearly independent. The update stays stable for
0 < rate * ||k||^2 < 2.

    echo '{"call": "store_pairs", "arguments": {"keys": [[1, 0], [0, 1]], "values": [[3, 4], [5, 6]]}}' | python3 delta_rule_associative_memory.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics

RULES = ("delta", "hebbian")


def _memory(memory, key_size=None, value_size=None):
    m = numerics.matrix(memory, "memory")
    if key_size is not None and len(m[0]) != key_size:
        raise ValueError(f"memory must have {key_size} columns (the key length)")
    if value_size is not None and len(m) != value_size:
        raise ValueError(f"memory must have {value_size} rows (the value length)")
    return m


def _step(m, key, value, rate, rule, normalize):
    if normalize:
        length = numerics.dot(key, key)
        if length == 0:
            raise ValueError("a key of length zero cannot be normalized")
        rate = rate / length
    target = value if rule == "hebbian" else [v - r for v, r in zip(value, numerics.matvec(m, key))]
    return [[m[i][j] + rate * target[i] * key[j] for j in range(len(key))] for i in range(len(m))]


def _rate(rate):
    rate = numerics.finite_number(rate, "rate")
    if rate <= 0:
        raise ValueError("rate must be positive")
    return rate


def delta_update(memory, key, value, rate=1.0, normalize_by_key_norm=False):
    """One delta-rule write: M + rate (v - M k) k^T (rate divided by ||k||^2 when normalize_by_key_norm)."""
    k = numerics.vector(key, "key")
    v = numerics.vector(value, "value")
    m = _memory(memory, len(k), len(v))
    return _step(m, k, v, _rate(rate), "delta", bool(normalize_by_key_norm))


def hebbian_update(memory, key, value, rate=1.0):
    """One Hebbian write: M + rate v k^T, shown for comparison; it does not correct existing crosstalk."""
    k = numerics.vector(key, "key")
    v = numerics.vector(value, "value")
    m = _memory(memory, len(k), len(v))
    return _step(m, k, v, _rate(rate), "hebbian", False)


def retrieve(memory, key):
    """The retrieved value M k."""
    k = numerics.vector(key, "key")
    return numerics.matvec(_memory(memory, len(k)), k)


def store_pairs(keys, values, rate=1.0, sweeps=1, rule="delta", normalize_by_key_norm=False):
    """Write every (key, value) pair in order, ``sweeps`` times, into a memory that starts at zero.

    Returns {"memory", "retrievals", "errors" (Euclidean error per pair), "max_error"}."""
    key_rows = numerics.matrix(keys, "keys")
    value_rows = numerics.matrix(values, "values")
    if len(key_rows) != len(value_rows):
        raise ValueError("keys and values must have the same number of rows")
    if rule not in RULES:
        raise ValueError(f"rule is one of {RULES}")
    sweeps = numerics.integer(sweeps, "sweeps", minimum=1, maximum=100000)
    rate = _rate(rate)
    m = numerics.zeros(len(value_rows[0]), len(key_rows[0]))
    for _sweep in range(sweeps):
        for key, value in zip(key_rows, value_rows):
            m = _step(m, key, value, rate, rule, bool(normalize_by_key_norm))
            if any(not math.isfinite(entry) or abs(entry) > 1e150 for row in m for entry in row):
                raise ValueError("the memory diverged; use rate * ||key||^2 below 2")
    retrievals = [numerics.matvec(m, key) for key in key_rows]
    errors = [numerics.vector_norm([r - v for r, v in zip(got, value)]) for got, value in zip(retrievals, value_rows)]
    return {"memory": m, "retrievals": retrievals, "errors": errors, "max_error": max(errors)}


def least_squares_memory(keys, values):
    """The minimum-norm memory M = V (K^T K)^-1 K^T reproducing every pair, for linearly independent keys.

    K holds the keys as columns and V the values as columns."""
    key_rows = numerics.matrix(keys, "keys")
    value_rows = numerics.matrix(values, "values")
    if len(key_rows) != len(value_rows):
        raise ValueError("keys and values must have the same number of rows")
    gram = [[numerics.dot(a, b) for b in key_rows] for a in key_rows]
    try:
        coefficients = numerics.solve(gram, value_rows)  # rows: (K^T K)^-1 V^T
    except ValueError:
        raise ValueError("keys must be linearly independent") from None
    size_value, size_key = len(value_rows[0]), len(key_rows[0])
    return [[math.fsum(coefficients[n][i] * key_rows[n][j] for n in range(len(key_rows))) for j in range(size_key)]
            for i in range(size_value)]


FUNCTIONS = {"delta_update": delta_update, "hebbian_update": hebbian_update, "retrieve": retrieve,
             "store_pairs": store_pairs, "least_squares_memory": least_squares_memory}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["RULES", "delta_update", "hebbian_update", "retrieve", "store_pairs", "least_squares_memory", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
