"""Chaikin corner cutting: repeated quarter-point subdivision that rounds a polygon or polyline toward a
quadratic B-spline.

Command line: python3 chaikin_corner_cutting.py --output chaikin.gltf --iterations 4
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "iterations", "type": "int", "default": 4, "unit": "count", "minimum": 0, "maximum": 16,
     "meaning": "Rounds of corner cutting; each doubles the point count of a closed polygon."},
    {"name": "ratio", "type": "float", "default": 0.25, "unit": "fraction", "minimum": 0.01, "maximum": 0.49,
     "meaning": "Where each edge is cut, as a fraction from each end (0.25 is Chaikin's rule)."},
]
DEMO_SHAPE = [(0.0, 1.4), (0.5, 0.5), (1.4, 0.4), (0.7, -0.2), (0.9, -1.2), (0.0, -0.6), (-0.9, -1.2), (-0.7, -0.2),
              (-1.4, 0.4), (-0.5, 0.5)]


def chaikin(points, iterations=1, closed=True, ratio=0.25):
    """Each round replaces every edge (a, b) by the points (1 - r) a + r b and r a + (1 - r) b. A closed
    polygon of n points has n * 2^k points after k rounds; an open polyline keeps both end points and has
    2n points after one round. With r = 1/4 the limit is the uniform quadratic B-spline of the input."""
    pts = [tuple(float(c) for c in p) for p in points]
    if len(pts) < (3 if closed else 2):
        raise meshkit.MeshError("too_few_points", "three points for a polygon, two for a polyline")
    for _ in range(int(iterations)):
        count = len(pts)
        edges = [(pts[k], pts[(k + 1) % count]) for k in range(count if closed else count - 1)]
        cut = []
        for a, b in edges:
            cut.append(tuple((1.0 - ratio) * x + ratio * y for x, y in zip(a, b)))
            cut.append(tuple(ratio * x + (1.0 - ratio) * y for x, y in zip(a, b)))
        pts = cut if closed else [pts[0]] + cut + [pts[-1]]
    return pts


def build(iterations=4, ratio=0.25):
    """The rounded demonstration star as a flat plate in the XZ plane, with the input polygon as a thin outline tube."""
    smooth = chaikin(DEMO_SHAPE, iterations, True, ratio)
    plate = meshkit.Mesh([meshkit.plane_to_3d(p) for p in smooth], meshkit.triangulate_polygon_2d(smooth),
                         normals=[(0.0, 1.0, 0.0)] * len(smooth), name="chaikin_plate",
                         material=meshkit.material("chaikin", (0.62, 0.70, 0.95, 1.0), double_sided=True))
    outline = meshkit.polyline_tube([meshkit.plane_to_3d(p, 0.01) for p in DEMO_SHAPE], 0.015, 6, closed=True,
                                    name="control_polygon", material=meshkit.material("control", (0.95, 0.85, 0.5, 1.0)))
    return [plate, outline]


def main(argv=None):
    """Command line: write the plate and outline (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
