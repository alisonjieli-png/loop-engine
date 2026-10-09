"""NURBS curves: rational de Boor evaluation in homogeneous coordinates, with exact circles and conic arcs.

Command line: python3 nurbs_curve.py --output nurbs_circle.gltf --radius 1 --samples 48
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "radius", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius of the exact NURBS circle that the command line draws."},
    {"name": "samples", "type": "int", "default": 48, "unit": "count", "minimum": 3, "maximum": 100000,
     "meaning": "Points sampled along each curve for the display tubes."},
]


def _span(knots, degree, count, t):
    if t >= knots[count]:
        return count - 1
    span = degree
    while span < count - 1 and knots[span + 1] <= t:
        span += 1
    return span


def nurbs_point(controls, weights, degree, knots, t):
    """Point of the rational B-spline at t: de Boor on (w x, w y, w z, w), then divide by w."""
    count = len(controls)
    span = _span(knots, degree, count, t)
    points = []
    for j in range(degree + 1):
        i = span - degree + j
        w = float(weights[i])
        points.append([w * float(c) for c in controls[i]] + [w])
    for r in range(1, degree + 1):
        for j in range(degree, r - 1, -1):
            left = knots[span - degree + j]
            right = knots[span + 1 + j - r]
            alpha = 0.0 if right == left else (t - left) / (right - left)
            points[j] = [(1.0 - alpha) * a + alpha * b for a, b in zip(points[j - 1], points[j])]
    homogeneous = points[degree]
    return tuple(c / homogeneous[-1] for c in homogeneous[:-1])


def circle(radius=1.0, center=(0.0, 0.0, 0.0)):
    """The exact circle in the XZ plane as a degree-2 NURBS: nine control points on a square (corner weights
    sqrt(2) / 2) and knots 0 0 0 1/4 1/4 1/2 1/2 3/4 3/4 1 1 1. Returns (controls, weights, degree, knots)."""
    corner = math.sqrt(0.5)
    square = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0)]
    controls = [(center[0] + radius * x, center[1], center[2] - radius * y) for x, y in square]
    weights = [1.0 if k % 2 == 0 else corner for k in range(9)]
    knots = [0.0, 0.0, 0.0, 0.25, 0.25, 0.5, 0.5, 0.75, 0.75, 1.0, 1.0, 1.0]
    return controls, weights, 2, knots


def conic_arc(start, control, end, weight):
    """A single rational quadratic arc: weight < 1 ellipse, 1 parabola, > 1 hyperbola, through start and end with
    tangents toward ``control``. Returns (controls, weights, degree, knots)."""
    return [tuple(start), tuple(control), tuple(end)], [1.0, float(weight), 1.0], 2, [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]


def sample_nurbs(curve, samples=128, closed=False):
    """``samples`` points evenly spaced in the parameter (the last one left out for a closed curve)."""
    controls, weights, degree, knots = curve
    low, high = knots[degree], knots[len(controls)]
    steps = samples if closed else samples - 1
    return [nurbs_point(controls, weights, degree, knots, low + (high - low) * k / steps) for k in range(samples)]


def build(radius=1.0, samples=48):
    """Tubes along the exact circle and three conic arcs (ellipse, parabola, hyperbola) beside it."""
    ring = meshkit.polyline_tube(sample_nurbs(circle(radius), samples, True), 0.04 * radius, 10, closed=True,
                                 name="nurbs_circle", material=meshkit.material("circle", (0.40, 0.75, 0.55, 1.0)))
    parts = [ring]
    colors = ((0.95, 0.55, 0.35, 1.0), (0.95, 0.85, 0.40, 1.0), (0.55, 0.60, 0.95, 1.0))
    for number, weight in enumerate((0.5, 1.0, 2.0)):
        x = radius * (1.6 + 0.9 * number)
        arc = conic_arc((x, 0.0, radius), (x + 0.8 * radius, 0.0, 0.0), (x, 0.0, -radius), weight)
        tube = meshkit.polyline_tube(sample_nurbs(arc, samples), 0.03 * radius, 8, name=f"conic_{weight:g}",
                                     material=meshkit.material(f"conic_{number}", colors[number]))
        parts.append(tube)
    return parts


def main(argv=None):
    """Command line: write the circle and conic tubes (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
