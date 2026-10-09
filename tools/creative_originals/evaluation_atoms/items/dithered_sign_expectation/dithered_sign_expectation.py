"""Dithered sign expectation: the mean of sign(x + noise) as a smooth, invertible function of x.

A one-bit reading sign(x) loses the magnitude of x. Adding independent noise before taking the sign keeps the
magnitude in the average:

    Gaussian dither N(0, sigma^2):   E[sign(x + sigma Z)] = 2 Phi(x / sigma) - 1 = erf(x / (sigma sqrt 2))
    uniform dither U(-a, a):         E[sign(x + a U)]     = x / a for |x| <= a, sign(x) beyond

so the average of many dithered signs estimates a known function of x, which can be inverted (recover_offset). A
seeded Monte Carlo estimate checks the closed form; each draw is +1 or -1, so its standard error is
sqrt((1 - m^2) / N) with m the exact mean.

    echo '{"call": "sign_expectation", "arguments": {"x": 1, "sigma": 1}}' | python3 dithered_sign_expectation.py
"""
from __future__ import annotations

import math

import atom_cli
import numerics

DITHERS = ("gaussian", "uniform")


def _inputs(x, sigma, dither):
    x = numerics.finite_number(x, "x")
    sigma = numerics.finite_number(sigma, "sigma")
    if sigma <= 0:
        raise ValueError("sigma must be positive")
    if dither not in DITHERS:
        raise ValueError(f"dither is one of {DITHERS}")
    return x, sigma


def sign_expectation(x, sigma, dither="gaussian"):
    """E[sign(x + noise)] for Gaussian noise with standard deviation sigma, or uniform noise on [-sigma, sigma]."""
    x, sigma = _inputs(x, sigma, dither)
    if dither == "gaussian":
        return math.erf(x / (sigma * math.sqrt(2.0)))
    return max(-1.0, min(1.0, x / sigma))


def _sign(value):
    return 1.0 if value > 0 else (-1.0 if value < 0 else 0.0)


def monte_carlo_sign_expectation(x, sigma, samples, seed, dither="gaussian"):
    """The average of ``samples`` seeded draws of sign(x + noise), next to the exact value.

    Returns {"estimate", "exact", "standard_error", "z_score" (null when the standard error is 0), "samples"}."""
    x, sigma = _inputs(x, sigma, dither)
    samples = numerics.integer(samples, "samples", minimum=1, maximum=2_000_000)
    generator = numerics.seeded_random(seed)
    if dither == "gaussian":
        noise = [sigma * value for value in numerics.standard_normals(generator, samples)]
    else:
        noise = [sigma * (2.0 * value - 1.0) for value in numerics.uniforms(generator, samples)]
    estimate = math.fsum(_sign(x + value) for value in noise) / samples
    exact = sign_expectation(x, sigma, dither)
    error = math.sqrt(max(0.0, 1.0 - exact * exact) / samples)
    return {"estimate": estimate, "exact": exact, "standard_error": error,
            "z_score": (estimate - exact) / error if error > 0 else None, "samples": samples}


def recover_offset(mean_sign, sigma, dither="gaussian"):
    """Invert the expectation: the x whose dithered sign has mean ``mean_sign``.

    Gaussian: sigma * Phi^-1((m + 1) / 2) for m in (-1, 1); uniform: sigma * m for m in [-1, 1]."""
    m = numerics.finite_number(mean_sign, "mean_sign")
    _x, sigma = _inputs(0.0, sigma, dither)
    if dither == "gaussian":
        if not -1.0 < m < 1.0:
            raise ValueError("mean_sign must lie strictly between -1 and 1 for a Gaussian dither")
        return sigma * numerics.normal_quantile((m + 1.0) / 2.0)
    if not -1.0 <= m <= 1.0:
        raise ValueError("mean_sign must lie in [-1, 1]")
    return sigma * m


FUNCTIONS = {"sign_expectation": sign_expectation, "monte_carlo_sign_expectation": monte_carlo_sign_expectation,
             "recover_offset": recover_offset}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["DITHERS", "sign_expectation", "monte_carlo_sign_expectation", "recover_offset", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
