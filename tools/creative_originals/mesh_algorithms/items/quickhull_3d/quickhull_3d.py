"""3D convex hull by quickhull, with coplanar triangles merged into convex polygon faces.

Command line: python3 quickhull_3d.py --output hull.gltf --count 300 --distribution ball --seed 5
"""
from __future__ import annotations

import math
import random

import meshkit

PARAMETERS = [
    {"name": "count", "type": "int", "default": 300, "unit": "count", "minimum": 4, "maximum": 100000,
     "meaning": "Number of random input points."},
    {"name": "distribution", "type": "str", "default": "ball", "unit": "name",
     "choices": ["ball", "cube", "sphere", "gaussian"], "meaning": "Where the random points are drawn."},
    {"name": "seed", "type": "int", "default": 5, "unit": "integer", "minimum": 0, "maximum": 2147483647,
     "meaning": "Random seed; the same seed gives the same points."},
]


def _plane(points, a, b, c):
    normal = meshkit.vcross(meshkit.vsub(points[b], points[a]), meshkit.vsub(points[c], points[a]))
    normal = meshkit.vnormalize(normal)
    return normal, meshkit.vdot(normal, points[a])


def convex_hull(points, merge_coplanar=True, tolerance=None):
    """The convex hull of 3D points as a closed mesh with outward faces.

    Vertices are the hull's extreme points in input order (exact duplicates count once). Faces are triangles, or
    with ``merge_coplanar`` the convex polygons formed by coplanar neighbouring triangles. ``tolerance`` is the
    distance a point must exceed to count as outside a face (default 1e-9 times the bounding-box diagonal).
    Raises MeshError for fewer than four points or points that are all collinear or coplanar.
    Expected O(n log n), worst case O(n^2)."""
    unique, seen = [], {}
    for p in points:
        key = (float(p[0]), float(p[1]), float(p[2]))
        if key not in seen:
            seen[key] = len(unique)
            unique.append(key)
    if len(unique) < 4:
        raise meshkit.MeshError("degenerate_input", "a hull needs four distinct points")
    low, high = meshkit.bounding_box(unique)
    scale = meshkit.vdistance(low, high)
    eps = tolerance if tolerance is not None else 1e-9 * scale
    n = len(unique)
    extremes = []
    for axis in range(3):
        extremes.append(min(range(n), key=lambda i: (unique[i][axis], i)))
        extremes.append(max(range(n), key=lambda i: (unique[i][axis], -i)))
    i0, i1 = max(((a, b) for a in extremes for b in extremes if a < b),
                 key=lambda pair: (meshkit.vdistance(unique[pair[0]], unique[pair[1]]), -pair[0], -pair[1]))
    direction = meshkit.vnormalize(meshkit.vsub(unique[i1], unique[i0]))

    def line_distance(i):
        offset = meshkit.vsub(unique[i], unique[i0])
        return meshkit.vlength(meshkit.vsub(offset, meshkit.vscale(direction, meshkit.vdot(offset, direction))))

    i2 = max(range(n), key=lambda i: (line_distance(i), -i))
    if line_distance(i2) <= eps:
        raise meshkit.MeshError("degenerate_input", "the points are collinear")
    normal, offset = _plane(unique, i0, i1, i2)
    i3 = max(range(n), key=lambda i: (abs(meshkit.vdot(normal, unique[i]) - offset), -i))
    if abs(meshkit.vdot(normal, unique[i3]) - offset) <= eps:
        raise meshkit.MeshError("degenerate_input", "the points are coplanar")
    inside = meshkit.vscale(meshkit.vadd(meshkit.vadd(unique[i0], unique[i1]), meshkit.vadd(unique[i2], unique[i3])), 0.25)
    faces = {}
    owner = {}
    counter = [0]

    def add_face(a, b, c):
        normal, offset = _plane(unique, a, b, c)
        if meshkit.vdot(normal, inside) - offset > 0:
            a, b = b, a
            normal, offset = _plane(unique, a, b, c)
        number = counter[0]
        counter[0] += 1
        faces[number] = {"corners": (a, b, c), "normal": normal, "offset": offset, "outside": [], "far": -1,
                         "far_distance": 0.0}
        for edge in ((a, b), (b, c), (c, a)):
            owner[edge] = number
        return number

    def assign(candidates, targets):
        for i in candidates:
            for number in targets:
                face = faces[number]
                distance = meshkit.vdot(face["normal"], unique[i]) - face["offset"]
                if distance > eps:
                    face["outside"].append(i)
                    if distance > face["far_distance"]:
                        face["far_distance"], face["far"] = distance, i
                    break

    start = [add_face(i0, i1, i2), add_face(i0, i1, i3), add_face(i0, i2, i3), add_face(i1, i2, i3)]
    assign([i for i in range(n) if i not in (i0, i1, i2, i3)], start)
    while True:
        pending = [number for number in sorted(faces) if faces[number]["outside"]]
        if not pending:
            break
        apex = faces[pending[0]]["far"]
        visible, stack = set(), [pending[0]]
        while stack:
            number = stack.pop()
            if number in visible:
                continue
            visible.add(number)
            a, b, c = faces[number]["corners"]
            for edge in ((b, a), (c, b), (a, c)):
                neighbor = owner.get(edge)
                if neighbor is not None and neighbor not in visible:
                    face = faces[neighbor]
                    if meshkit.vdot(face["normal"], unique[apex]) - face["offset"] > eps:
                        stack.append(neighbor)
        horizon = []
        orphans = []
        for number in sorted(visible):
            a, b, c = faces[number]["corners"]
            for edge in ((a, b), (b, c), (c, a)):
                if owner.get((edge[1], edge[0])) not in visible:
                    horizon.append(edge)
            orphans.extend(i for i in faces[number]["outside"] if i != apex)
        for number in visible:
            a, b, c = faces[number]["corners"]
            for edge in ((a, b), (b, c), (c, a)):
                if owner.get(edge) == number:
                    del owner[edge]
            del faces[number]
        created = []
        for a, b in horizon:
            number = counter[0]
            counter[0] += 1
            normal, offset = _plane(unique, a, b, apex)
            faces[number] = {"corners": (a, b, apex), "normal": normal, "offset": offset, "outside": [], "far": -1,
                             "far_distance": 0.0}
            for edge in ((a, b), (b, apex), (apex, a)):
                owner[edge] = number
            created.append(number)
        assign(orphans, created)
    used = sorted({i for face in faces.values() for i in face["corners"]})
    remap = {old: new for new, old in enumerate(used)}
    triangles = [tuple(remap[i] for i in faces[number]["corners"]) for number in sorted(faces)]
    vertices = [unique[i] for i in used]
    mesh = meshkit.Mesh(vertices, triangles, name="convex_hull")
    return _merge_coplanar(mesh, eps) if merge_coplanar else mesh


def _merge_coplanar(mesh, eps):
    vertices = mesh.vertices
    normals = [meshkit.face_normal(vertices, face) for face in mesh.faces]
    adjacency = meshkit.edge_faces(mesh)
    parent = list(range(len(mesh.faces)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b), owners in adjacency.items():
        if len(owners) != 2:
            continue
        f, g = owners
        if meshkit.vdot(normals[f], normals[g]) < 1.0 - 1e-12:
            continue
        if all(abs(meshkit.vdot(normals[f], meshkit.vsub(vertices[i], vertices[mesh.faces[f][0]]))) <= eps
               for i in mesh.faces[g]):
            parent[find(g)] = find(f)
    groups = {}
    for number in range(len(mesh.faces)):
        groups.setdefault(find(number), []).append(number)
    faces = []
    for members in groups.values():
        if len(members) == 1:
            faces.append(mesh.faces[members[0]])
            continue
        directed = {}
        for number in members:
            face = mesh.faces[number]
            for k in range(3):
                directed[(face[k], face[(k + 1) % 3])] = number
        following = {}
        for (a, b) in directed:
            if (b, a) not in directed:
                following[a] = b
        start = min(following)
        loop, current = [start], following[start]
        while current != start:
            loop.append(current)
            current = following[current]
        faces.append(tuple(loop))
    return meshkit.Mesh(vertices, faces, name=mesh.name)


def sphere_points(count=60, radius=1.0):
    """``count`` points spread evenly on a sphere by the golden-angle (Fibonacci) spiral; every point is extreme."""
    golden = math.pi * (3.0 - math.sqrt(5.0))
    points = []
    for k in range(count):
        y = 1.0 - 2.0 * (k + 0.5) / count
        ring = math.sqrt(max(0.0, 1.0 - y * y))
        angle = golden * k
        points.append((radius * ring * math.cos(angle), radius * y, -radius * ring * math.sin(angle)))
    return points


def random_points(count=300, distribution="ball", seed=5):
    """Seeded random points in the unit ball, the cube [-1, 1]^3, on the unit sphere, or Gaussian (sigma 0.5)."""
    generator = random.Random(seed)
    points = []
    while len(points) < count:
        if distribution == "gaussian":
            points.append(tuple(generator.gauss(0.0, 0.5) for _ in range(3)))
            continue
        p = tuple(generator.uniform(-1.0, 1.0) for _ in range(3))
        length = meshkit.vlength(p)
        if distribution == "cube":
            points.append(p)
        elif distribution == "ball" and length <= 1.0:
            points.append(p)
        elif distribution == "sphere" and 0.05 < length <= 1.0:
            points.append(meshkit.vscale(p, 1.0 / length))
        elif distribution not in ("ball", "sphere"):
            raise meshkit.MeshError("distribution_unknown", str(distribution))
    return points


def build(count=300, distribution="ball", seed=5):
    """The faceted hull of seeded random points that the command line writes."""
    hull = meshkit.flat_shaded(convex_hull(random_points(count, distribution, seed)))
    hull.material = meshkit.material("convex_hull", (0.55, 0.78, 0.74, 1.0))
    return hull


def main(argv=None):
    """Command line: write the hull of random points as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
