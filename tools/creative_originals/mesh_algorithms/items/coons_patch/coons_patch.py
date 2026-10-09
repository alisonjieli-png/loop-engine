"""Coons patch: a surface spanning four boundary curves by bilinearly blended interpolation.

Command line: python3 coons_patch.py --output coons.gltf --boundary saddle --resolution 24
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "boundary", "type": "str", "default": "saddle", "unit": "name", "choices": ["saddle", "pillow", "flat"],
     "meaning": "Demonstration set of four boundary curves."},
    {"name": "resolution", "type": "int", "default": 24, "unit": "cells", "minimum": 1, "maximum": 4096,
     "meaning": "Grid cells per side; the patch has (resolution + 1)^2 vertices."},
]


def coons_point(bottom, top, left, right, u, v):
    """S(u, v) = ruled(u) + ruled(v) - bilinear corners, for boundary functions of one parameter in [0, 1]:
    bottom(u) = S(u, 0), top(u) = S(u, 1), left(v) = S(0, v), right(v) = S(1, v); the corners must agree."""
    b, t, l, r = bottom(u), top(u), left(v), right(v)
    p00, p10, p01, p11 = bottom(0.0), bottom(1.0), top(0.0), top(1.0)
    return tuple((1 - v) * b[k] + v * t[k] + (1 - u) * l[k] + u * r[k]
                 - ((1 - u) * (1 - v) * p00[k] + u * (1 - v) * p10[k] + (1 - u) * v * p01[k] + u * v * p11[k])
                 for k in range(3))


def polyline_function(points):
    """A boundary function t -> point that follows a polyline by arc length (t = 0 first point, 1 last)."""
    pts = [tuple(float(c) for c in p) for p in points]
    lengths = [meshkit.vdistance(a, b) for a, b in zip(pts, pts[1:])]
    total = math.fsum(lengths)

    def evaluate(t):
        target = min(max(t, 0.0), 1.0) * total
        walked = 0.0
        for k, length in enumerate(lengths):
            if walked + length >= target or k == len(lengths) - 1:
                w = 0.0 if length == 0 else (target - walked) / length
                return meshkit.vlerp(pts[k], pts[k + 1], min(1.0, w))
            walked += length
        return pts[-1]
    return evaluate


def demo_boundary(name="saddle"):
    """(bottom, top, left, right) boundary functions over a 2 x 2 square in XZ."""
    if name == "flat":
        return (lambda u: (2 * u - 1, 0.0, 1.0), lambda u: (2 * u - 1, 0.0, -1.0),
                lambda v: (-1.0, 0.0, 1 - 2 * v), lambda v: (1.0, 0.0, 1 - 2 * v))
    if name == "saddle":
        return (lambda u: (2 * u - 1, 0.5 * math.sin(math.pi * u), 1.0), lambda u: (2 * u - 1, 0.5 * math.sin(math.pi * u), -1.0),
                lambda v: (-1.0, -0.5 * math.sin(math.pi * v), 1 - 2 * v), lambda v: (1.0, -0.5 * math.sin(math.pi * v), 1 - 2 * v))
    if name == "pillow":
        return (lambda u: (2 * u - 1, 0.0, 1.0 + 0.3 * math.sin(math.pi * u)), lambda u: (2 * u - 1, 0.0, -1.0 - 0.3 * math.sin(math.pi * u)),
                lambda v: (-1.0 - 0.3 * math.sin(math.pi * v), 0.0, 1 - 2 * v), lambda v: (1.0 + 0.3 * math.sin(math.pi * v), 0.0, 1 - 2 * v))
    raise meshkit.MeshError("boundary_unknown", str(name))


def coons_patch(boundary, resolution=24):
    """A (resolution + 1)^2 grid mesh of the Coons patch with normals from the mesh; boundary vertices lie
    exactly on the boundary curves. ``boundary`` is (bottom, top, left, right), each a function of one
    parameter in [0, 1] or a polyline (followed by arc length). Faces wind so the normal follows
    (dS/dv) x (dS/du), which points +Y for the demonstration squares."""
    bottom, top, left, right = (part if callable(part) else polyline_function(part) for part in boundary)
    n = int(resolution)
    if n < 1:
        raise meshkit.MeshError("resolution_invalid", "at least one cell")
    vertices = [coons_point(bottom, top, left, right, i / n, j / n) for j in range(n + 1) for i in range(n + 1)]
    faces = [tuple(reversed(f)) for f in meshkit.grid_faces(n + 1, n + 1)]
    mesh = meshkit.Mesh(vertices, faces, name="coons_patch",
                        material=meshkit.material("coons", (0.95, 0.75, 0.45, 1.0), double_sided=True))
    mesh.normals = meshkit.vertex_normals(mesh)
    return mesh


def build(boundary="saddle", resolution=24):
    """The demonstration patch, coloured by height."""
    mesh = coons_patch(demo_boundary(boundary), resolution)
    low, high = meshkit.bounding_box(mesh)
    span = max(high[1] - low[1], 1e-9)
    mesh.colors = [(0.35 + 0.6 * (v[1] - low[1]) / span, 0.55, 0.95 - 0.6 * (v[1] - low[1]) / span, 1.0) for v in mesh.vertices]
    return mesh


def main(argv=None):
    """Command line: write the patch (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
