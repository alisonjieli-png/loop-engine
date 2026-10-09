"""Fillet the corners of a 2D polygon or polyline with circular arcs tangent to both edges.

Command line: python3 fillet_polyline_2d.py --output fillet.gltf --radius 0.3 --arc-segments 8
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "radius", "type": "float", "default": 0.3, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Fillet radius; reduced at a corner whose edges are too short to hold it."},
    {"name": "arc_segments", "type": "int", "default": 8, "unit": "count", "minimum": 1, "maximum": 4096,
     "meaning": "Straight segments per arc."},
]
DEMO_SHAPE = [(-1.5, -1.0), (1.5, -1.0), (1.5, 0.2), (0.4, 0.2), (0.4, 1.0), (-1.5, 1.0)]


def fillet(points, radius=0.3, arc_segments=8, closed=True):
    """Points of the polygon (or open polyline) with each corner replaced by ``arc_segments`` + 1 points of an
    arc of ``radius`` tangent to both edges. The tangent points sit radius / tan(angle / 2) from the corner,
    limited to half of each edge (the radius shrinks to fit). Straight corners are kept as they are."""
    pts = [(float(p[0]), float(p[1])) for p in points]
    count = len(pts)
    if count < 3 if closed else count < 2:
        raise meshkit.MeshError("too_few_points", "three points for a polygon, two for a polyline")
    result = []

    def add(point):
        if not result or math.hypot(point[0] - result[-1][0], point[1] - result[-1][1]) > 1e-12:
            result.append(point)

    for i in range(count):
        if not closed and i in (0, count - 1):
            add(pts[i])
            continue
        prev, cur, nxt = pts[i - 1], pts[i], pts[(i + 1) % count]
        a = (prev[0] - cur[0], prev[1] - cur[1])
        b = (nxt[0] - cur[0], nxt[1] - cur[1])
        la, lb = math.hypot(*a), math.hypot(*b)
        if la == 0 or lb == 0 or radius <= 0:
            add(cur)
            continue
        da, db = (a[0] / la, a[1] / lb * la / la), (b[0] / lb, b[1] / lb)
        da = (a[0] / la, a[1] / la)
        cosine = max(-1.0, min(1.0, da[0] * db[0] + da[1] * db[1]))
        angle = math.acos(cosine)
        if angle > math.pi - 1e-9 or angle < 1e-9:
            add(cur)
            continue
        reach = min(radius / math.tan(angle / 2.0), 0.5 * la, 0.5 * lb)
        fitted = reach * math.tan(angle / 2.0)
        start = (cur[0] + da[0] * reach, cur[1] + da[1] * reach)
        end = (cur[0] + db[0] * reach, cur[1] + db[1] * reach)
        bisector = meshkit.vnormalize((da[0] + db[0], da[1] + db[1], 0.0))
        distance = fitted / math.sin(angle / 2.0)
        center = (cur[0] + bisector[0] * distance, cur[1] + bisector[1] * distance)
        a0 = math.atan2(start[1] - center[1], start[0] - center[0])
        a1 = math.atan2(end[1] - center[1], end[0] - center[0])
        sweep = (a1 - a0 + math.pi) % (2.0 * math.pi) - math.pi
        for k in range(arc_segments + 1):
            t = a0 + sweep * k / arc_segments
            add((center[0] + fitted * math.cos(t), center[1] + fitted * math.sin(t)))
    if closed and len(result) > 1 and math.hypot(result[0][0] - result[-1][0], result[0][1] - result[-1][1]) <= 1e-12:
        result.pop()
    return result


def perimeter(points, closed=True):
    """Length of the polygon (or polyline)."""
    pairs = list(zip(points, points[1:])) + ([(points[-1], points[0])] if closed else [])
    return math.fsum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in pairs)


def build(radius=0.3, arc_segments=8):
    """The filleted demonstration outline as a flat plate in the XZ plane facing +Y."""
    outline = fillet(DEMO_SHAPE, radius, arc_segments)
    vertices = [meshkit.plane_to_3d(p) for p in outline]
    faces = meshkit.triangulate_polygon_2d(outline)
    return meshkit.Mesh(vertices, faces, normals=[(0.0, 1.0, 0.0)] * len(vertices), name="filleted_outline",
                        material=meshkit.material("fillet", (0.55, 0.80, 0.70, 1.0), double_sided=True))


def main(argv=None):
    """Command line: write the filleted outline (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
