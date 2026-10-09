"""Offset a simple 2D polygon by a signed distance with miter, round or bevel joins.

Command line: python3 polygon_offset_2d.py --output offset.gltf --distance 0.25 --join round
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "distance", "type": "float", "default": 0.25, "unit": "m", "minimum": -1000000.0, "maximum": 1000000.0,
     "meaning": "Offset distance: positive grows the polygon, negative shrinks it."},
    {"name": "join", "type": "str", "default": "round", "unit": "name", "choices": ["round", "miter", "bevel"],
     "meaning": "How offset edges meet at corners that open a gap."},
    {"name": "arc_segments", "type": "int", "default": 8, "unit": "count", "minimum": 1, "maximum": 4096,
     "meaning": "Segments per 90 degrees of a round join."},
]
DEMO_SHAPE = [(-1.0, -0.8), (1.2, -0.8), (1.2, 0.0), (0.2, 0.0), (0.2, 0.9), (-1.0, 0.9)]


def _intersect(p, d, q, e):
    denominator = d[0] * e[1] - d[1] * e[0]
    if abs(denominator) < 1e-15:
        return None
    t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / denominator
    return (p[0] + d[0] * t, p[1] + d[1] * t)


def _crosses(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0) and 0 not in (o1, o2, o3, o4)


def offset_polygon(polygon, distance, join="round", arc_segments=8, miter_limit=4.0):
    """The offset outline, counter-clockwise. Each edge moves ``distance`` along its outward normal; where the
    moved edges overlap (a corner turning against the offset) they meet at their line intersection, and where
    they open a gap the ``join`` fills it: the line intersection (miter, limited to miter_limit * |distance|,
    beyond which it bevels), an arc around the corner (round) or the straight gap (bevel). Raises MeshError
    when an edge would vanish or turn around (offset_collapses) or the result would cross itself
    (offset_self_intersects)."""
    pts = [(float(p[0]), float(p[1])) for p in polygon]
    if len(pts) < 3:
        raise meshkit.MeshError("too_few_points", "a polygon needs three points")
    if meshkit.polygon_area_2d(pts) < 0:
        pts.reverse()
    if distance == 0:
        return pts
    count = len(pts)
    edges = []
    for k in range(count):
        a, b = pts[k], pts[(k + 1) % count]
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        direction = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
        normal = (direction[1], -direction[0])
        edges.append(((a[0] + normal[0] * distance, a[1] + normal[1] * distance),
                      (b[0] + normal[0] * distance, b[1] + normal[1] * distance), direction, normal))
    result, starts = [], []
    for k in range(count):
        starts.append(len(result))
        before, after = edges[k - 1], edges[k]
        corner = pts[k]
        turn = before[2][0] * after[2][1] - before[2][1] * after[2][0]
        opens_gap = (turn > 0) if distance > 0 else (turn < 0)
        if abs(turn) < 1e-15:
            result.append(after[0])
            continue
        if not opens_gap:
            point = _intersect(before[1], before[2], after[0], after[2])
            result.append(point if point is not None else after[0])
            continue
        if join == "miter":
            point = _intersect(before[1], before[2], after[0], after[2])
            if point is not None and math.hypot(point[0] - corner[0], point[1] - corner[1]) <= miter_limit * abs(distance):
                result.append(point)
                continue
            result += [before[1], after[0]]
        elif join == "bevel":
            result += [before[1], after[0]]
        elif join == "round":
            a0 = math.atan2(before[1][1] - corner[1], before[1][0] - corner[0])
            a1 = math.atan2(after[0][1] - corner[1], after[0][0] - corner[0])
            sweep = (a1 - a0 + math.pi) % (2.0 * math.pi) - math.pi
            steps = max(1, int(math.ceil(abs(sweep) / (0.5 * math.pi) * arc_segments - 1e-9)))
            for j in range(steps + 1):
                t = a0 + sweep * j / steps
                result.append((corner[0] + abs(distance) * math.cos(t), corner[1] + abs(distance) * math.sin(t)))
        else:
            raise meshkit.MeshError("join_unknown", str(join))
    total = len(result)
    for k in range(count):
        a, b = result[(starts[(k + 1) % count] - 1) % total], result[starts[(k + 1) % count] % total]
        direction = edges[k][2]
        if (b[0] - a[0]) * direction[0] + (b[1] - a[1]) * direction[1] <= 0:
            raise meshkit.MeshError("offset_collapses", "an edge vanishes or turns around at this distance")
    for i in range(total):
        for j in range(i + 2, total):
            if i == 0 and j == total - 1:
                continue
            if _crosses(result[i], result[(i + 1) % total], result[j], result[(j + 1) % total]):
                raise meshkit.MeshError("offset_self_intersects", "the offset is too large for this shape")
    if meshkit.polygon_area_2d(result) <= 0:
        raise meshkit.MeshError("offset_collapses", "the offset polygon has no area left")
    return result


def build(distance=0.25, join="round", arc_segments=8):
    """A flat band between the demonstration polygon and its offset (the offset outside, or inside when the
    distance is negative), in the XZ plane facing +Y."""
    shape = DEMO_SHAPE
    grown = offset_polygon(shape, distance, join, arc_segments)
    outer, inner = (grown, shape) if distance > 0 else (shape, grown)
    vertices = [meshkit.plane_to_3d(p) for p in outer + inner]
    faces = meshkit.triangulate_polygon_2d(outer, [inner])
    return meshkit.Mesh(vertices, faces, normals=[(0.0, 1.0, 0.0)] * len(vertices), name="offset_band",
                        material=meshkit.material("offset", (0.95, 0.60, 0.45, 1.0), double_sided=True))


def main(argv=None):
    """Command line: write the offset band (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
