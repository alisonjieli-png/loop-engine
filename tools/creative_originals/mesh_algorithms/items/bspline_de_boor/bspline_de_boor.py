"""B-spline curves of any degree: clamped and periodic knot vectors, de Boor evaluation, Cox-de Boor basis
functions and Boehm knot insertion.

Command line: python3 bspline_de_boor.py --output bspline.gltf --degree 3 --closed false
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "degree", "type": "int", "default": 3, "unit": "degree", "minimum": 1, "maximum": 7,
     "meaning": "Polynomial degree of the curve."},
    {"name": "closed", "type": "bool", "default": False, "unit": "flag",
     "meaning": "Periodic curve through the control polygon's loop instead of a clamped open curve."},
    {"name": "samples", "type": "int", "default": 160, "unit": "count", "minimum": 2, "maximum": 100000,
     "meaning": "Points sampled along the curve for the display tube."},
]
DEMO_CONTROLS = [(-2.0, 0.0, 0.0), (-1.5, 1.2, -0.6), (-0.5, -0.4, -1.0), (0.3, 1.4, 0.4), (1.2, -0.2, 1.0),
                 (2.0, 1.0, 0.2), (2.4, 0.0, -0.8)]


def clamped_knots(count, degree):
    """Clamped uniform knot vector in [0, 1] for ``count`` control points: degree + 1 repeated end knots."""
    if count <= degree:
        raise meshkit.MeshError("too_few_controls", "a B-spline needs more control points than its degree")
    inner = count - degree - 1
    return [0.0] * (degree + 1) + [k / (inner + 1) for k in range(1, inner + 1)] + [1.0] * (degree + 1)


def _span(knots, degree, count, t):
    if t >= knots[count]:
        return count - 1
    low, high = degree, count
    while high - low > 1:
        middle = (low + high) // 2
        if t < knots[middle]:
            high = middle
        else:
            low = middle
    return low


def de_boor(controls, degree, knots, t):
    """Curve point at t by de Boor's triangular scheme (the stable form of the B-spline sum)."""
    count = len(controls)
    span = _span(knots, degree, count, t)
    points = [list(map(float, controls[span - degree + j])) for j in range(degree + 1)]
    for r in range(1, degree + 1):
        for j in range(degree, r - 1, -1):
            left = knots[span - degree + j]
            right = knots[span + 1 + j - r]
            alpha = 0.0 if right == left else (t - left) / (right - left)
            points[j] = [(1.0 - alpha) * a + alpha * b for a, b in zip(points[j - 1], points[j])]
    return tuple(points[degree])


def basis_functions(degree, knots, count, t):
    """All ``count`` basis function values N_i,degree(t) by the Cox-de Boor recursion; they sum to 1 on the domain."""
    span = _span(knots, degree, count, t)
    values = [0.0] * count
    for j, value in enumerate(_cox(degree, knots, span, t)):
        values[span - degree + j] = value
    return values


def _cox(degree, knots, span, t):
    values = [1.0]
    for p in range(1, degree + 1):
        nxt = [0.0] * (p + 1)
        for j in range(p):
            i = span - p + 1 + j
            denominator = knots[i + p] - knots[i]
            weight = (t - knots[i]) / denominator if denominator > 0 else 0.0
            nxt[j + 1] += values[j] * weight
            nxt[j] += values[j] * (1.0 - weight)
        values = nxt
    return values


def insert_knot(controls, degree, knots, t):
    """Boehm knot insertion: (new controls, new knots) describing the same curve with one more control point."""
    count = len(controls)
    span = _span(knots, degree, count, t)
    new_controls = []
    for i in range(count + 1):
        if i <= span - degree:
            new_controls.append(tuple(map(float, controls[i])))
        elif i > span:
            new_controls.append(tuple(map(float, controls[i - 1])))
        else:
            alpha = (t - knots[i]) / (knots[i + degree] - knots[i])
            new_controls.append(tuple((1.0 - alpha) * a + alpha * b for a, b in zip(controls[i - 1], controls[i])))
    return new_controls, knots[:span + 1] + [float(t)] + knots[span + 1:]


def sample_curve(controls, degree=3, samples=160, closed=False):
    """``samples`` points along a clamped curve (ends on the first and last control points) or, when closed, a
    uniform periodic curve through the wrapped control loop (no repeated end point)."""
    if closed:
        loop = [tuple(map(float, p)) for p in controls] + [tuple(map(float, p)) for p in controls[:degree]]
        count = len(loop)
        knots = [float(k) for k in range(count + degree + 1)]
        low, high = knots[degree], knots[count]
        return [de_boor(loop, degree, knots, low + (high - low) * k / samples) for k in range(samples)]
    knots = clamped_knots(len(controls), degree)
    return [de_boor(controls, degree, knots, k / (samples - 1)) for k in range(samples)]


def build(degree=3, closed=False, samples=160):
    """A tube along the demonstration curve plus line segments of its control polygon."""
    points = sample_curve(DEMO_CONTROLS, degree, samples, closed)
    tube = meshkit.polyline_tube(points, 0.05, 10, closed=closed, name="bspline",
                                 material=meshkit.material("bspline", (0.95, 0.62, 0.30, 1.0)))
    start = len(tube.vertices)
    tube.vertices.extend(DEMO_CONTROLS)
    tube.normals.extend([(0.0, 1.0, 0.0)] * len(DEMO_CONTROLS))
    count = len(DEMO_CONTROLS)
    tube.lines = [(start + k, start + (k + 1) % count) for k in range(count if closed else count - 1)]
    return tube


def main(argv=None):
    """Command line: write the curve tube and control polygon (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
