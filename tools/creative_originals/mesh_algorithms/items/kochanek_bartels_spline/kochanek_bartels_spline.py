"""Kochanek-Bartels (TCB) splines: cubic Hermite segments whose tangents are shaped by tension, continuity
and bias at every key.

Command line: python3 kochanek_bartels_spline.py --output tcb.gltf --tension 0 --continuity 0 --bias 0
"""
from __future__ import annotations

import meshkit

PARAMETERS = [
    {"name": "tension", "type": "float", "default": 0.0, "unit": "ratio", "minimum": -1.0, "maximum": 1.0,
     "meaning": "Tangent length: 1 gives straight segments, -1 rounder curves."},
    {"name": "continuity", "type": "float", "default": 0.0, "unit": "ratio", "minimum": -1.0, "maximum": 1.0,
     "meaning": "Difference between incoming and outgoing tangents: away from 0 makes corners."},
    {"name": "bias", "type": "float", "default": 0.0, "unit": "ratio", "minimum": -1.0, "maximum": 1.0,
     "meaning": "Tangent direction: positive leans toward the previous key (overshoot), negative toward the next."},
    {"name": "samples_per_segment", "type": "int", "default": 16, "unit": "count", "minimum": 1, "maximum": 10000,
     "meaning": "Points per segment."},
]
DEMO_KEYS = [(-2.0, 0.0, 0.5), (-1.2, 0.9, -0.4), (-0.4, -0.2, 0.6), (0.4, 1.1, -0.2), (1.2, 0.1, 0.7),
             (2.0, 0.8, -0.5)]


def hermite(p0, p1, m0, m1, t):
    """Cubic Hermite point from p0 (t = 0) to p1 (t = 1) with end tangents m0 and m1."""
    t2, t3 = t * t, t * t * t
    h00, h10, h01, h11 = 2 * t3 - 3 * t2 + 1, t3 - 2 * t2 + t, -2 * t3 + 3 * t2, t3 - t2
    return tuple(h00 * a + h10 * c + h01 * b + h11 * d for a, b, c, d in zip(p0, p1, m0, m1))


def tcb_tangents(previous, current, following, tension=0.0, continuity=0.0, bias=0.0):
    """(incoming, outgoing) tangents at ``current`` from the Kochanek-Bartels formulas."""
    before = [c - p for c, p in zip(current, previous)]
    after = [f - c for f, c in zip(following, current)]
    t, c, b = tension, continuity, bias
    outgoing = tuple((1 - t) * (1 + b) * (1 + c) / 2 * x + (1 - t) * (1 - b) * (1 - c) / 2 * y for x, y in zip(before, after))
    incoming = tuple((1 - t) * (1 + b) * (1 - c) / 2 * x + (1 - t) * (1 - b) * (1 + c) / 2 * y for x, y in zip(before, after))
    return incoming, outgoing


def tcb_spline(keys, tension=0.0, continuity=0.0, bias=0.0, samples_per_segment=16):
    """Points through every key (open curve; the end keys repeat their neighbour difference). With all three
    parameters 0 the curve is the uniform Catmull-Rom spline; with tension 1 every segment is straight."""
    pts = [tuple(float(c) for c in p) for p in keys]
    if len(pts) < 2:
        raise meshkit.MeshError("too_few_keys", "a spline needs two keys")
    padded = ([tuple(2 * a - b for a, b in zip(pts[0], pts[1]))] + pts
              + [tuple(2 * a - b for a, b in zip(pts[-1], pts[-2]))])
    tangents = [tcb_tangents(padded[k - 1], padded[k], padded[k + 1], tension, continuity, bias)
                for k in range(1, len(padded) - 1)]
    result = []
    for k in range(len(pts) - 1):
        for j in range(samples_per_segment):
            result.append(hermite(pts[k], pts[k + 1], tangents[k][1], tangents[k + 1][0], j / samples_per_segment))
    result.append(pts[-1])
    return result


def build(tension=0.0, continuity=0.0, bias=0.0, samples_per_segment=16):
    """Tubes for the chosen setting (gold) and, for comparison, tension 0.8 (blue) through the same keys."""
    main_curve = meshkit.polyline_tube(tcb_spline(DEMO_KEYS, tension, continuity, bias, samples_per_segment), 0.04,
                                       10, name="tcb", material=meshkit.material("tcb", (0.92, 0.72, 0.32, 1.0)))
    tight = meshkit.polyline_tube(tcb_spline(DEMO_KEYS, 0.8, continuity, bias, samples_per_segment), 0.025, 8,
                                  name="tension_0_8", material=meshkit.material("tight", (0.45, 0.62, 0.95, 1.0)))
    return [main_curve, tight]


def main(argv=None):
    """Command line: write the spline tubes (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
