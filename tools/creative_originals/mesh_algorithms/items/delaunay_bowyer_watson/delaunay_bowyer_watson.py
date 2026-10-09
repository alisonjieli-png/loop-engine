"""2D Delaunay triangulation by Bowyer-Watson insertion with exact fallback predicates and a final Lawson pass.

Command line: python3 delaunay_bowyer_watson.py --output delaunay.gltf --count 160 --layout random --seed 11
"""
from __future__ import annotations

import math
import random
from fractions import Fraction

import meshkit

PARAMETERS = [
    {"name": "count", "type": "int", "default": 160, "unit": "count", "minimum": 3, "maximum": 20000,
     "meaning": "Number of input points."},
    {"name": "layout", "type": "str", "default": "random", "unit": "name", "choices": ["random", "jittered_grid", "rings"],
     "meaning": "How the demonstration points are placed in the unit square."},
    {"name": "seed", "type": "int", "default": 11, "unit": "integer", "minimum": 0, "maximum": 2147483647,
     "meaning": "Random seed; the same seed gives the same points."},
]


def _orient(a, b, c):
    left = (a[0] - c[0]) * (b[1] - c[1])
    right = (a[1] - c[1]) * (b[0] - c[0])
    value = left - right
    if abs(value) > 1e-12 * (abs(left) + abs(right)):
        return value
    fa, fb, fc = [Fraction(x) for x in a], [Fraction(x) for x in b], [Fraction(x) for x in c]
    return float((fa[0] - fc[0]) * (fb[1] - fc[1]) - (fa[1] - fc[1]) * (fb[0] - fc[0]))


def _incircle(a, b, c, d):
    """Positive when d is strictly inside the circle through counter-clockwise a, b, c."""
    adx, ady = a[0] - d[0], a[1] - d[1]
    bdx, bdy = b[0] - d[0], b[1] - d[1]
    cdx, cdy = c[0] - d[0], c[1] - d[1]
    alift, blift, clift = adx * adx + ady * ady, bdx * bdx + bdy * bdy, cdx * cdx + cdy * cdy
    value = adx * (bdy * clift - cdy * blift) - ady * (bdx * clift - cdx * blift) + alift * (bdx * cdy - bdy * cdx)
    permanent = (abs(adx) * (abs(bdy) * clift + abs(cdy) * blift) + abs(ady) * (abs(bdx) * clift + abs(cdx) * blift)
                 + alift * (abs(bdx * cdy) + abs(bdy * cdx)))
    if abs(value) > 1e-11 * permanent:
        return value
    ax, ay = Fraction(a[0]) - Fraction(d[0]), Fraction(a[1]) - Fraction(d[1])
    bx, by = Fraction(b[0]) - Fraction(d[0]), Fraction(b[1]) - Fraction(d[1])
    cx, cy = Fraction(c[0]) - Fraction(d[0]), Fraction(c[1]) - Fraction(d[1])
    al, bl, cl = ax * ax + ay * ay, bx * bx + by * by, cx * cx + cy * cy
    return float(ax * (by * cl - cy * bl) - ay * (bx * cl - cx * bl) + al * (bx * cy - by * cx))


def _boundary(triangles):
    directed = set()
    for a, b, c in triangles:
        directed.update(((a, b), (b, c), (c, a)))
    return {a: b for (a, b) in directed if (b, a) not in directed}


def delaunay(points):
    """Delaunay triangulation of 2D points: {"points", "triangles", "hull"}.

    ``triangles`` are counter-clockwise index triples into ``points``; ``hull`` is the counter-clockwise
    boundary loop. Exact duplicates are used once (later copies stay unused). Raises MeshError for fewer than
    three distinct points or points that are all collinear. Insertion scans all triangles: O(n^2)."""
    pts = [(float(p[0]), float(p[1])) for p in points]
    first, order = {}, []
    for index, p in enumerate(pts):
        if p not in first:
            first[p] = index
            order.append(index)
    if len(order) < 3:
        raise meshkit.MeshError("degenerate_input", "three distinct points are needed")
    if all(_orient(pts[order[0]], pts[order[1]], pts[i]) == 0 for i in order[2:]):
        raise meshkit.MeshError("degenerate_input", "the points are collinear")
    xs, ys = [pts[i][0] for i in order], [pts[i][1] for i in order]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-12)
    mx, my = (max(xs) + min(xs)) / 2.0, (max(ys) + min(ys)) / 2.0
    big = 64.0 * span
    extended = pts + [(mx - 2.0 * big, my - big), (mx + 2.0 * big, my - big), (mx, my + 2.0 * big)]
    n = len(pts)
    triangles = [(n, n + 1, n + 2)]
    for i in order:
        p = extended[i]
        bad, keep = [], []
        for t in triangles:
            (bad if _incircle(extended[t[0]], extended[t[1]], extended[t[2]], p) > 0 else keep).append(t)
        edges = set()
        for a, b, c in bad:
            edges.update(((a, b), (b, c), (c, a)))
        cavity = [(a, b) for (a, b) in sorted(edges) if (b, a) not in edges]
        triangles = keep + [(a, b, i) for a, b in cavity]
    triangles = [t for t in triangles if max(t) < n]
    changed = True
    while changed:
        changed = False
        following = _boundary(triangles)
        for v, w in sorted(following.items()):
            u = next(k for k, value in following.items() if value == v)
            if _orient(pts[u], pts[v], pts[w]) < 0:
                triangles.append((u, w, v))
                changed = True
                break
    triangles = _legalize(pts, triangles)
    following = _boundary(triangles)
    start = min(following)
    hull, current = [start], following[start]
    while current != start:
        hull.append(current)
        current = following[current]
    return {"points": pts, "triangles": sorted(_canonical(t) for t in triangles), "hull": hull}


def _canonical(t):
    k = t.index(min(t))
    return t[k:] + t[:k]


def _legalize(pts, triangles):
    """Lawson flips until every interior edge is locally Delaunay."""
    triangles = [tuple(t) for t in triangles]
    owner = {}
    for number, (a, b, c) in enumerate(triangles):
        for edge in ((a, b), (b, c), (c, a)):
            owner[edge] = number
    stack = sorted(owner)
    while stack:
        a, b = stack.pop()
        if (a, b) not in owner or (b, a) not in owner:
            continue
        first, second = owner[(a, b)], owner[(b, a)]
        t1, t2 = triangles[first], triangles[second]
        c = next(v for v in t1 if v not in (a, b))
        d = next(v for v in t2 if v not in (a, b))
        if _incircle(pts[a], pts[b], pts[c], pts[d]) <= 0:
            continue
        for x, y, z in (t1, t2):
            for edge in ((x, y), (y, z), (z, x)):
                del owner[edge]
        triangles[first], triangles[second] = (c, a, d), (d, b, c)
        for number in (first, second):
            x, y, z = triangles[number]
            for edge in ((x, y), (y, z), (z, x)):
                owner[edge] = number
        stack.extend(((a, d), (d, b), (b, c), (c, a)))
    return triangles


def random_points(count=160, layout="random", seed=11):
    """Seeded demonstration points in the unit square: uniform 'random', 'jittered_grid' or concentric 'rings'."""
    generator = random.Random(seed)
    if layout == "random":
        return [(generator.random(), generator.random()) for _ in range(count)]
    if layout == "jittered_grid":
        side = max(2, int(math.ceil(math.sqrt(count))))
        cells = [(i, j) for j in range(side) for i in range(side)][:count]
        return [((i + 0.5 + 0.7 * (generator.random() - 0.5)) / side, (j + 0.5 + 0.7 * (generator.random() - 0.5)) / side)
                for i, j in cells]
    if layout == "rings":
        points, ring = [(0.5, 0.5)], 1
        while len(points) < count:
            around = 6 * ring
            twist = generator.random()
            for k in range(around):
                if len(points) == count:
                    break
                angle = 2.0 * math.pi * (k + twist) / around
                points.append((0.5 + 0.08 * ring * math.cos(angle), 0.5 + 0.08 * ring * math.sin(angle)))
            ring += 1
        return points
    raise meshkit.MeshError("layout_unknown", str(layout))


def triangulation_mesh(result, height=0.0):
    """A flat glTF-ready mesh of a triangulation: one colour per triangle, the plane facing +Y."""
    vertices, faces, colors = [], [], []
    for number, (a, b, c) in enumerate(result["triangles"]):
        shade = meshkit.hash_integers(number, seed=97)
        color = (0.45 + 0.4 * ((shade & 255) / 255.0), 0.55 + 0.35 * (((shade >> 8) & 255) / 255.0),
                 0.65 + 0.3 * (((shade >> 16) & 255) / 255.0), 1.0)
        start = len(vertices)
        for index in (a, b, c):
            vertices.append(meshkit.plane_to_3d(result["points"][index], height))
            colors.append(color)
        faces.append((start, start + 1, start + 2))
    return meshkit.Mesh(vertices, faces, normals=[(0.0, 1.0, 0.0)] * len(vertices), colors=colors,
                        name="delaunay", material=meshkit.material("delaunay", (1.0, 1.0, 1.0, 1.0), double_sided=True))


def build(count=160, layout="random", seed=11):
    """The coloured triangulation of seeded points that the command line writes."""
    return triangulation_mesh(delaunay(random_points(count, layout, seed)))


def main(argv=None):
    """Command line: write the triangulation as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
