"""Transient amplification profile: the spectral norms ||A^h||_2 of a linear update over a horizon.

A linear recurrence x_(h+1) = A x_h with spectral radius below 1 decays eventually, yet a non-normal A can amplify
some states by a large factor first. The profile shows that hump: ||A^h||_2 for h = 0 .. horizon, its peak, the step
after which the norm stays below 1, the spectral radius and the bound rho(A) <= min_h ||A^h||^(1/h).

The spectral norm of each power B = A^h is found by power iteration on B^T B from two deterministic starting
vectors (the larger result is kept), with the Rayleigh quotient as the estimate. The spectral radius comes from the
characteristic polynomial (Faddeev-LeVerrier) and simultaneous root iteration (Durand-Kerner).

Example: A = [[0.8, 4], [0, 0.8]] has spectral radius 0.8, but ||A^4||_2 is about 8.21.

    echo '{"call": "transient_profile", "arguments": {"matrix": [[0.8, 4], [0, 0.8]], "horizon": 30}}' | python3 transient_amplification_profile.py
"""
from __future__ import annotations

import cmath
import math

import atom_cli
import numerics

MAXIMUM_SIZE_FOR_EIGENVALUES = 8


def _square(matrix_rows, name="matrix"):
    return numerics.matrix(matrix_rows, name, square=True, maximum_rows=60)


def _power_iteration(b, start, iterations, tolerance):
    bt = numerics.transpose(b)
    vector = start
    length = numerics.vector_norm(vector)
    vector = [value / length for value in vector]
    estimate, previous = 0.0, -1.0
    for step in range(1, iterations + 1):
        image = numerics.matvec(bt, numerics.matvec(b, vector))
        estimate = numerics.dot(vector, image)
        size = numerics.vector_norm(image)
        if size == 0.0:
            return 0.0, step, True
        vector = [value / size for value in image]
        if abs(estimate - previous) <= tolerance * max(estimate, 1e-300):
            return estimate, step, True
        previous = estimate
    return estimate, iterations, False


def spectral_norm(matrix, iterations=2000, tolerance=1e-15):
    """The largest singular value of a square or rectangular matrix by power iteration on B^T B.

    Returns {"norm", "iterations", "converged"}. Two deterministic starts are used (a spread vector and the column of
    largest norm), so a start orthogonal to the top singular vector cannot hide it."""
    b = numerics.matrix(matrix, "matrix")
    iterations = numerics.integer(iterations, "iterations", minimum=1)
    tolerance = numerics.finite_number(tolerance, "tolerance")
    width = len(b[0])
    spread = [1.0 + math.sqrt(2.0) * index % 1.0 for index in range(width)]
    columns = numerics.transpose(b)
    largest = max(range(width), key=lambda index: numerics.vector_norm(columns[index]))
    basis = [1.0 if index == largest else 0.0 for index in range(width)]
    runs = [_power_iteration(b, start, iterations, tolerance) for start in (spread, basis)]
    value, steps, converged = max(runs, key=lambda run: run[0])
    return {"norm": math.sqrt(max(value, 0.0)), "iterations": steps, "converged": converged}


def _characteristic_polynomial(a):
    size = len(a)
    coefficients = [1.0]
    m = numerics.zeros(size, size)
    for k in range(1, size + 1):
        product = numerics.matmul(a, m)
        m = [[product[i][j] + (coefficients[-1] if i == j else 0.0) for j in range(size)] for i in range(size)]
        coefficients.append(-numerics.trace(numerics.matmul(a, m)) / k)
    return coefficients


def _polynomial_roots(coefficients):
    degree = len(coefficients) - 1
    bound = 1.0 + max(abs(value) for value in coefficients[1:])
    roots = [bound * cmath.exp(complex(0.0, 2.0 * math.pi * k / degree + 0.4)) for k in range(degree)]

    def evaluate(point):
        total = complex(0.0, 0.0)
        for value in coefficients:
            total = total * point + value
        return total

    for _ in range(5000):
        updated = []
        for i, root in enumerate(roots):
            denominator = complex(1.0, 0.0)
            for j, other in enumerate(roots):
                if i != j:
                    denominator *= (root - other) if root != other else complex(1e-300, 0.0)
            updated.append(root - evaluate(root) / denominator)
        change = max(abs(p - q) for p, q in zip(updated, roots))
        roots = updated
        if change <= 1e-15 * bound:
            break
    return roots


def spectral_radius(matrix):
    """The spectral radius and eigenvalues ([real, imaginary] pairs) of a square matrix of size at most 8.

    Eigenvalues are roots of the characteristic polynomial; a repeated eigenvalue is accurate to about 1e-8."""
    a = _square(matrix)
    if len(a) > MAXIMUM_SIZE_FOR_EIGENVALUES:
        raise ValueError(f"spectral_radius accepts at most {MAXIMUM_SIZE_FOR_EIGENVALUES} rows")
    if len(a) == 1:
        return {"radius": abs(a[0][0]), "eigenvalues": [[a[0][0], 0.0]]}
    roots = _polynomial_roots(_characteristic_polynomial(a))
    scale = max(1.0, max(abs(root) for root in roots))
    pairs = sorted(([root.real, 0.0 if abs(root.imag) <= 1e-12 * scale else root.imag] for root in roots),
                   key=lambda pair: (-math.hypot(pair[0], pair[1]), -pair[0], -pair[1]))
    return {"radius": max(math.hypot(real, imaginary) for real, imaginary in pairs), "eigenvalues": pairs}


def transient_profile(matrix, horizon):
    """||A^h||_2 for h = 0 .. horizon, with the peak, the settling step and spectral information.

    Returns {"norms", "peak_norm", "peak_step", "amplifies" (peak above 1), "settles_below_one_at" (the first step
    from which every norm up to the horizon is below 1, or null), "spectral_radius" (null above size 8),
    "gelfand_bound" (min over h >= 1 of ||A^h||^(1/h), an upper bound on the spectral radius), "converged"}."""
    a = _square(matrix)
    horizon = numerics.integer(horizon, "horizon", minimum=1, maximum=5000)
    power = numerics.identity(len(a))
    norms, converged = [1.0], True
    for _step in range(horizon):
        power = numerics.matmul(power, a)
        result = spectral_norm(power)
        norms.append(result["norm"])
        converged = converged and result["converged"]
    peak_step = max(range(len(norms)), key=lambda index: (norms[index], -index))
    settles = None
    for step in range(len(norms) - 1, -1, -1):
        if norms[step] >= 1.0:
            break
        settles = step
    bound = min(norm ** (1.0 / step) for step, norm in enumerate(norms) if step >= 1)
    radius = spectral_radius(a)["radius"] if len(a) <= MAXIMUM_SIZE_FOR_EIGENVALUES else None
    return {"norms": norms, "peak_norm": norms[peak_step], "peak_step": peak_step,
            "amplifies": norms[peak_step] > 1.0 + 1e-12, "settles_below_one_at": settles,
            "spectral_radius": radius, "gelfand_bound": bound, "converged": converged}


FUNCTIONS = {"transient_profile": transient_profile, "spectral_norm": spectral_norm,
             "spectral_radius": spectral_radius}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["MAXIMUM_SIZE_FOR_EIGENVALUES", "transient_profile", "spectral_norm", "spectral_radius", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
