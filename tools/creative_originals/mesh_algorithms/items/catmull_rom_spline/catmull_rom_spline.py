"""Catmull-Rom splines with uniform, centripetal or chordal knot spacing (Barry-Goldman pyramid evaluation).

Command line: python3 catmull_rom_spline.py --output catmull_rom.gltf --alpha 0.5 --closed true
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "alpha", "type": "float", "default": 0.5, "unit": "exponent", "minimum": 0.0, "maximum": 1.0,
     "meaning": "Knot spacing exponent: 0 uniform, 0.5 centripetal (no cusps or self-loops), 1 chordal."},
    {"name": "closed", "type": "bool", "default": True, "unit": "flag",
     "meaning": "Join the last control point back to the first."},
    {"name": "samples_per_segment", "type": "int", "default": 16, "unit": "count", "minimum": 1, "maximum": 10000,
     "meaning": "Points per segment between consecutive control points."},
]
DEMO_POINTS = [(1.6, 0.0, 0.0), (0.9, 0.5, -1.1), (0.0, -0.3, -0.5), (-0.8, 0.6, -1.3), (-1.7, 0.0, 0.0),
               (-0.6, -0.5, 1.2), (0.05, 0.4, 0.15), (0.8, -0.2, 1.4)]


def _knot(a, b, alpha):
    return math.sqrt(math.fsum((x - y) ** 2 for x, y in zip(a, b))) ** alpha


def catmull_rom_point(p0, p1, p2, p3, t, alpha=0.5):
    """Point between p1 (t = 0) and p2 (t = 1) of the Catmull-Rom segment with knot spacing |dp|^alpha,
    by the Barry-Goldman pyramid of linear interpolations."""
    t0 = 0.0
    t1 = t0 + max(_knot(p0, p1, alpha), 1e-12)
    t2 = t1 + max(_knot(p1, p2, alpha), 1e-12)
    t3 = t2 + max(_knot(p2, p3, alpha), 1e-12)
    s = t1 + (t2 - t1) * t

    def mix(a, b, ta, tb):
        w = (s - ta) / (tb - ta)
        return tuple((1.0 - w) * x + w * y for x, y in zip(a, b))

    a1, a2, a3 = mix(p0, p1, t0, t1), mix(p1, p2, t1, t2), mix(p2, p3, t2, t3)
    b1, b2 = mix(a1, a2, t0, t2), mix(a2, a3, t1, t3)
    point = mix(b1, b2, t1, t2)
    if t == 0.0:
        return tuple(float(c) for c in p1)
    if t == 1.0:
        return tuple(float(c) for c in p2)
    return point


def catmull_rom(points, alpha=0.5, closed=False, samples_per_segment=16):
    """Points of the spline through every control point; each segment contributes ``samples_per_segment``
    points starting at its first control point, and an open spline ends exactly on the last point. Open ends
    use a reflected neighbour (2 p0 - p1) so the end tangents follow the first and last segments."""
    pts = [tuple(float(c) for c in p) for p in points]
    if len(pts) < 2:
        raise meshkit.MeshError("too_few_points", "a spline needs two points")
    if closed:
        extended = [pts[-1]] + pts + pts[:2]
        segments = len(pts)
    else:
        extended = ([tuple(2 * a - b for a, b in zip(pts[0], pts[1]))] + pts
                    + [tuple(2 * a - b for a, b in zip(pts[-1], pts[-2]))])
        segments = len(pts) - 1
    result = []
    for k in range(segments):
        p0, p1, p2, p3 = extended[k], extended[k + 1], extended[k + 2], extended[k + 3]
        for j in range(samples_per_segment):
            result.append(catmull_rom_point(p0, p1, p2, p3, j / samples_per_segment, alpha))
    if not closed:
        result.append(pts[-1])
    return result


def build(alpha=0.5, closed=True, samples_per_segment=16):
    """A tube through the demonstration control points plus small markers at each control point."""
    curve = catmull_rom(DEMO_POINTS, alpha, closed, samples_per_segment)
    parts = [meshkit.polyline_tube(curve, 0.045, 10, closed=closed, name="catmull_rom",
                                   material=meshkit.material("curve", (0.85, 0.45, 0.65, 1.0)))]
    for number, point in enumerate(DEMO_POINTS):
        marker = meshkit.translated(meshkit.with_normals(meshkit.box((0.12, 0.12, 0.12))), point)
        marker.name = f"control_{number}"
        marker.material = meshkit.material("control", (0.95, 0.90, 0.80, 1.0))
        parts.append(marker)
    return [parts[0], meshkit.combine(parts[1:], "controls")]


def main(argv=None):
    """Command line: write the spline tube and control markers (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
