"""Cubic Bezier curves: de Casteljau evaluation, splitting, Gauss-Legendre arc length and resampling by length.

Command line: python3 bezier_curve_arc_length.py --output bezier.gltf --path wave --spacing 0.05
"""
from __future__ import annotations

import bisect
import math

import meshkit

PARAMETERS = [
    {"name": "path", "type": "str", "default": "wave", "unit": "name", "choices": ["wave", "loop", "quarter_circle"],
     "meaning": "Demonstration path made of cubic segments."},
    {"name": "spacing", "type": "float", "default": 0.05, "unit": "m", "minimum": 0.001, "maximum": 1000.0,
     "meaning": "Arc-length spacing of the resampled points the tube follows."},
    {"name": "tube_radius", "type": "float", "default": 0.04, "unit": "m", "minimum": 0.0001, "maximum": 1000.0,
     "meaning": "Radius of the display tube."},
]
_NODES = (-0.9061798459386640, -0.5384693101056831, 0.0, 0.5384693101056831, 0.9061798459386640)
_WEIGHTS = (0.2369268850561891, 0.4786286704993665, 0.5688888888888889, 0.4786286704993665, 0.2369268850561891)


def _lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def bezier_point(controls, t):
    """Point at parameter t in [0, 1] by de Casteljau's repeated linear interpolation (any dimension)."""
    points = [tuple(float(c) for c in p) for p in controls]
    while len(points) > 1:
        points = [_lerp(points[k], points[k + 1], t) for k in range(len(points) - 1)]
    return points[0]


def bezier_derivative(controls, t):
    """Velocity dB/dt of a cubic at t: 3 [(1-t)^2 (P1-P0) + 2 (1-t) t (P2-P1) + t^2 (P3-P2)]."""
    p0, p1, p2, p3 = ([float(c) for c in p] for p in controls)
    u = 1.0 - t
    return tuple(3.0 * (u * u * (p1[k] - p0[k]) + 2.0 * u * t * (p2[k] - p1[k]) + t * t * (p3[k] - p2[k]))
                 for k in range(len(p0)))


def split_bezier(controls, t=0.5):
    """The two cubics that trace the parts before and after t (de Casteljau's intermediate points)."""
    p0, p1, p2, p3 = (tuple(float(c) for c in p) for p in controls)
    a, b, c = _lerp(p0, p1, t), _lerp(p1, p2, t), _lerp(p2, p3, t)
    d, e = _lerp(a, b, t), _lerp(b, c, t)
    f = _lerp(d, e, t)
    return [p0, a, d, f], [f, e, c, p3]


def _speed(controls, t):
    return math.sqrt(math.fsum(c * c for c in bezier_derivative(controls, t)))


def _gauss(controls, a, b):
    half, middle = (b - a) / 2.0, (a + b) / 2.0
    return math.fsum(w * half * _speed(controls, middle + half * x) for x, w in zip(_NODES, _WEIGHTS))


def arc_length(controls, t0=0.0, t1=1.0, pieces=16):
    """Length of a cubic between t0 and t1: five-point Gauss-Legendre quadrature of the speed on ``pieces``
    equal sub-intervals (error falls like the tenth power of the piece size for smooth speed)."""
    return math.fsum(_gauss(controls, t0 + (t1 - t0) * k / pieces, t0 + (t1 - t0) * (k + 1) / pieces)
                     for k in range(pieces))


def length_table(controls, pieces=32):
    """Cumulative arc length at t = k / pieces for k = 0 .. pieces (the lookup table for inversion)."""
    table = [0.0]
    for k in range(pieces):
        table.append(table[-1] + _gauss(controls, k / pieces, (k + 1) / pieces))
    return table


def parameter_at_length(controls, length, table=None):
    """The t whose arc length from 0 equals ``length``: find the table piece, then Newton steps inside it."""
    table = table or length_table(controls)
    pieces = len(table) - 1
    target = min(max(length, 0.0), table[-1])
    k = min(max(bisect.bisect_right(table, target) - 1, 0), pieces - 1)
    t0, t1 = k / pieces, (k + 1) / pieces
    span = table[k + 1] - table[k]
    t = t0 + (target - table[k]) / span * (t1 - t0) if span > 0 else t0
    for _ in range(12):
        speed = _speed(controls, t)
        if speed <= 1e-15:
            break
        step = (table[k] + _gauss(controls, t0, t) - target) / speed
        t = min(t1, max(t0, t - step))
        if abs(step) < 1e-15:
            break
    return t


def resample_by_length(segments, spacing):
    """Points along a path of cubic segments spaced ``spacing`` apart in arc length, plus the final end point.

    ``segments`` is a list of 4-point control lists (each starts where the previous one ends)."""
    if spacing <= 0:
        raise meshkit.MeshError("spacing_invalid", "spacing must be positive")
    tables = [length_table(segment) for segment in segments]
    lengths = [table[-1] for table in tables]
    total = math.fsum(lengths)
    count = int(math.floor(total / spacing + 1e-9))
    points, index, before = [], 0, 0.0
    for k in range(count + 1):
        s = k * spacing
        while index < len(segments) - 1 and s > before + lengths[index]:
            before += lengths[index]
            index += 1
        points.append(bezier_point(segments[index], parameter_at_length(segments[index], s - before, tables[index])))
    end = tuple(float(c) for c in segments[-1][-1])
    if meshkit.vdistance(points[-1], end) > 1e-9 * max(1.0, total):
        points.append(end)
    return points


def demo_path(name="wave"):
    """Cubic segments of a demonstration path: 'wave' (four arches), 'loop' (closed) or 'quarter_circle'."""
    k = 4.0 / 3.0 * (math.sqrt(2.0) - 1.0)
    if name == "quarter_circle":
        return [[(1.0, 0.0, 0.0), (1.0, 0.0, -k), (k, 0.0, -1.0), (0.0, 0.0, -1.0)]]
    if name == "wave":
        segments = []
        for i in range(4):
            x0, sign = i * 1.0 - 2.0, 1.0 if i % 2 == 0 else -1.0
            segments.append([(x0, 0.0, 0.0), (x0 + 0.33, 0.6 * sign, -0.2 * sign), (x0 + 0.67, 0.6 * sign, 0.2 * sign),
                             (x0 + 1.0, 0.0, 0.0)])
        return segments
    if name == "loop":
        corners = [(1.0, 0.0, 0.0), (0.0, 0.5, -1.0), (-1.0, 0.0, 0.0), (0.0, -0.5, 1.0)]
        segments = []
        for i in range(4):
            a, b = corners[i], corners[(i + 1) % 4]
            ta = meshkit.vsub(corners[(i + 1) % 4], corners[i - 1])
            tb = meshkit.vsub(corners[(i + 2) % 4], corners[i])
            segments.append([a, meshkit.vadd(a, meshkit.vscale(ta, 0.25)), meshkit.vsub(b, meshkit.vscale(tb, 0.25)), b])
        return segments
    raise meshkit.MeshError("path_unknown", str(name))


def build(path="wave", spacing=0.05, tube_radius=0.04):
    """A tube through the path resampled at even arc length (what the command line writes)."""
    points = resample_by_length(demo_path(path), spacing)
    return meshkit.polyline_tube(points, tube_radius, 10, closed=(path == "loop"), name="bezier_path",
                                 material=meshkit.material("bezier", (0.36, 0.62, 0.92, 1.0)))


def main(argv=None):
    """Command line: write the resampled path as a tube (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
