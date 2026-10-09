"""Ramer-Douglas-Peucker polyline simplification in 2D or 3D, with a measure of the largest deviation.

Command line: python3 douglas_peucker.py --output simplified.gltf --tolerance 0.05
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "tolerance", "type": "float", "default": 0.05, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Largest allowed distance from a removed point to the simplified polyline."},
    {"name": "samples", "type": "int", "default": 400, "unit": "count", "minimum": 2, "maximum": 1000000,
     "meaning": "Points in the demonstration curve before simplification."},
]


def _segment_distance(p, a, b):
    ab = [y - x for x, y in zip(a, b)]
    ap = [y - x for x, y in zip(a, p)]
    length2 = math.fsum(c * c for c in ab)
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, math.fsum(x * y for x, y in zip(ap, ab)) / length2))
    return math.sqrt(math.fsum((x + t * d - y) ** 2 for x, d, y in zip(a, ab, p)))


def simplify(points, tolerance=0.05):
    """The kept points, in order: both ends, and recursively the point farthest from the current chord segment
    while that distance exceeds ``tolerance``. Iterative (no recursion limit). O(n log n) typical, O(n^2) worst."""
    pts = [tuple(float(c) for c in p) for p in points]
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        first, last = stack.pop()
        best, index = -1.0, -1
        for k in range(first + 1, last):
            distance = _segment_distance(pts[k], pts[first], pts[last])
            if distance > best:
                best, index = distance, k
        if index >= 0 and best > tolerance:
            keep[index] = True
            stack.append((first, index))
            stack.append((index, last))
    return [p for p, kept in zip(pts, keep) if kept]


def max_deviation(original, simplified):
    """Largest distance from any original point to the simplified polyline (0 when nothing was removed)."""
    simple = [tuple(float(c) for c in p) for p in simplified]
    return max(min(_segment_distance(tuple(map(float, p)), a, b) for a, b in zip(simple, simple[1:])) for p in original)


def demo_curve(samples=400):
    """A 3D test curve: a spiral with a superimposed wobble."""
    points = []
    for k in range(samples):
        t = 4.0 * math.pi * k / (samples - 1)
        points.append((0.15 * t * math.cos(t), 0.25 * math.sin(5.0 * t), -0.15 * t * math.sin(t)))
    return points


def build(tolerance=0.05, samples=400):
    """Two tubes: the original curve (thin, grey) and its simplification (thicker, coloured)."""
    original = demo_curve(samples)
    simplified = simplify(original, tolerance)
    return [meshkit.polyline_tube(original, 0.015, 6, name="original", material=meshkit.material("original", (0.6, 0.6, 0.62, 1.0))),
            meshkit.polyline_tube(simplified, 0.035, 8, name="simplified", material=meshkit.material("simplified", (0.95, 0.45, 0.35, 1.0)))]


def main(argv=None):
    """Command line: write both tubes (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
