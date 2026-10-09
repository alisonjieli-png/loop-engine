"""Two non-orientable surfaces embedded in R^4 without self-intersection: the Klein bottle and the Veronese RP^2.

Klein bottle: K(u, v) = ((R + r cos v) cos u, (R + r cos v) sin u, r sin v cos(u/2), r sin v sin(u/2)). Going once
around u flips (z, w), which equals v -> -v, so the grid closes with the Klein identification (u + 2 pi, v) ~ (u, -v).
Dropping w gives the familiar 3D Klein bottle, which crosses itself along u = pi, where the two sheets differ only
in w. Veronese surface: (x, y, z) on S^2 -> (xy, xz, yz, (x^2 - y^2)/2) identifies antipodes (a real projective
plane) and is injective. Dropping the last coordinate gives Steiner's Roman surface
X^2 Y^2 + Y^2 Z^2 + Z^2 X^2 = X Y Z, which crosses itself along three segments. The module builds both as
quotient triangle meshes, checks Euler characteristics (0 and 1), non-orientability by orientation propagation,
the 4D embedding and the 3D self-intersection, and writes both shadows coloured by the dropped coordinate.

    python klein_bottle_veronese.py --out klein_and_roman.gltf
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict, deque

import fourd


def klein(u, v, big=2.0, small=1.0):
    """The Klein bottle point in R^4."""
    ring = big + small * math.cos(v)
    return (ring * math.cos(u), ring * math.sin(u), small * math.sin(v) * math.cos(u / 2.0),
            small * math.sin(v) * math.sin(u / 2.0))


def klein_mesh(columns=48, rows=24, big=2.0, small=1.0):
    """(points4, triangles) of the Klein bottle on a columns x rows grid, glued with (u + 2 pi, v) ~ (u, -v)."""
    if columns < 4 or rows < 4 or columns % 2:
        raise ValueError("columns is an even number of 4 or more and rows is 4 or more")
    points = [klein(2.0 * math.pi * i / columns, 2.0 * math.pi * j / rows, big, small)
              for i in range(columns) for j in range(rows)]
    index = lambda i, j: i * rows + (j % rows)
    triangles = []
    for i in range(columns):
        for j in range(rows):
            if i + 1 < columns:
                a, b, c, d = index(i, j), index(i + 1, j), index(i + 1, j + 1), index(i, j + 1)
            else:
                a, b, c, d = index(i, j), index(0, -j), index(0, -(j + 1)), index(i, j + 1)
            triangles += [(a, b, c), (a, c, d)]
    return points, triangles


def veronese(point):
    """(x, y, z) on the unit sphere -> (xy, xz, yz, (x^2 - y^2)/2)."""
    x, y, z = point
    return (x * y, x * z, y * z, (x * x - y * y) / 2.0)


def veronese_mesh(subdivisions=3):
    """(points4, triangles) of RP^2: an icosphere with antipodal vertices and faces identified, then mapped."""
    sphere = fourd.sphere_mesh((0.0, 0.0, 0.0), 1.0, None, subdivisions)
    vertices = sphere["positions"]
    key = {fourd.point_key(vertex, 9): index for index, vertex in enumerate(vertices)}
    representative = {}
    classes = []
    for index, vertex in enumerate(vertices):
        twin = key[fourd.point_key(fourd.scale(vertex, -1.0), 9)]
        if twin in representative:
            representative[index] = representative[twin]
        else:
            representative[index] = len(classes)
            classes.append(index)
    triangles, seen = [], set()
    faces = [tuple(sphere["indices"][k:k + 3]) for k in range(0, len(sphere["indices"]), 3)]
    for face in faces:
        mapped = tuple(representative[v] for v in face)
        if frozenset(mapped) in seen:
            continue
        seen.add(frozenset(mapped))
        triangles.append(mapped)
    return [veronese(vertices[index]) for index in classes], triangles


def euler_characteristic(points, triangles):
    """V - E + F of a triangle mesh given by vertex indices."""
    edges = {tuple(sorted(pair)) for a, b, c in triangles for pair in ((a, b), (b, c), (c, a))}
    used = {vertex for triangle in triangles for vertex in triangle}
    return len(used) - len(edges) + len(triangles)


def is_orientable(triangles):
    """Propagate an orientation across shared edges; False when a conflict proves the surface non-orientable."""
    by_edge = defaultdict(list)
    for index, (a, b, c) in enumerate(triangles):
        for first, second in ((a, b), (b, c), (c, a)):
            by_edge[frozenset((first, second))].append((index, first, second))
    sign = [0] * len(triangles)
    for start in range(len(triangles)):
        if sign[start]:
            continue
        sign[start] = 1
        queue = deque([start])
        while queue:
            current = queue.popleft()
            a, b, c = triangles[current]
            for first, second in ((a, b), (b, c), (c, a)):
                for other, other_first, other_second in by_edge[frozenset((first, second))]:
                    if other == current:
                        continue
                    same_direction = (other_first, other_second) == (first, second)
                    wanted = -sign[current] if same_direction else sign[current]
                    if sign[other] == 0:
                        sign[other] = wanted
                        queue.append(other)
                    elif sign[other] != wanted:
                        return False
    return True


def closest_far_pair(points, triangles, dimensions=4, hops=3):
    """Smallest distance (in the first `dimensions` coordinates) between vertices more than `hops` edges apart."""
    neighbours = defaultdict(set)
    for a, b, c in triangles:
        neighbours[a] |= {b, c}
        neighbours[b] |= {a, c}
        neighbours[c] |= {a, b}
    best = math.inf
    for start in range(len(points)):
        near = {start}
        frontier = {start}
        for _ in range(hops):
            frontier = {n for vertex in frontier for n in neighbours[vertex]} - near
            near |= frontier
        p = points[start][:dimensions]
        for other in range(start + 1, len(points)):
            if other not in near:
                value = math.dist(p, points[other][:dimensions])
                if value < best:
                    best = value
    return best


def roman_residual(points):
    """Largest |X^2 Y^2 + Y^2 Z^2 + Z^2 X^2 - X Y Z| over the 3D shadow (X, Y, Z) of the Veronese points."""
    return max(abs(x * x * y * y + y * y * z * z + z * z * x * x - x * y * z) for x, y, z, _w in points)


def shadow_mesh(points, triangles, scale_to=1.0):
    """Flat-shaded triangles of the 3D shadow (first three coordinates), coloured by the fourth coordinate."""
    reach = max(math.sqrt(p[0] ** 2 + p[1] ** 2 + p[2] ** 2) for p in points) or 1.0
    colours = fourd.depth_colors([p[3] for p in points])
    flat = [tuple(value * scale_to / reach for value in p[:3]) for p in points]
    positions, normals, indices, vertex_colours = [], [], [], []
    for a, b, c in triangles:
        corners = [flat[a], flat[b], flat[c]]
        normal = fourd.cross3(fourd.sub(corners[1], corners[0]), fourd.sub(corners[2], corners[0]))
        if fourd.norm(normal) <= 1e-15:
            continue
        normal = fourd.normalize(normal)
        base = len(positions)
        positions += corners
        normals += [normal] * 3
        vertex_colours += [colours[a], colours[b], colours[c]]
        indices += [base, base + 1, base + 2]
    return {"positions": positions, "normals": normals, "indices": indices, "colors": vertex_colours, "mode": 4}


def export(path, columns=32, rows=12, subdivisions=3, gap=2.6):
    """Both shadows side by side, Klein bottle left and Roman surface right, each scaled to radius 1."""
    klein_points, klein_triangles = klein_mesh(columns, rows)
    roman_points, roman_triangles = veronese_mesh(subdivisions)
    meshes = [dict(shadow_mesh(klein_points, klein_triangles), name="klein_bottle_shadow", translation=(-gap / 2.0, 0.0, 0.0)),
              dict(shadow_mesh(roman_points, roman_triangles), name="roman_surface_shadow", translation=(gap / 2.0, 0.0, 0.0))]
    document = fourd.gltf_document(meshes, generator="klein_bottle_veronese.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    klein_points, klein_triangles = klein_mesh(24, 12)
    roman_points, roman_triangles = veronese_mesh(2)
    torus = [(i, j) for i in range(8) for j in range(6)]
    torus_triangles = []
    for i in range(8):
        for j in range(6):
            a, b, c, d = i * 6 + j, ((i + 1) % 8) * 6 + j, ((i + 1) % 8) * 6 + (j + 1) % 6, i * 6 + (j + 1) % 6
            torus_triangles += [(a, b, c), (a, c, d)]
    return {"klein_euler_characteristic": euler_characteristic(klein_points, klein_triangles),
            "klein_orientable": is_orientable(klein_triangles),
            "klein_embedded_in_r4": closest_far_pair(klein_points, klein_triangles, 4) > 0.3,
            "klein_shadow_self_intersects": closest_far_pair(klein_points, klein_triangles, 3) < 1e-9,
            "klein_seam_identification": max(math.dist(klein(u + 2.0 * math.pi, v), klein(u, -v))
                                             for u, v in ((0.3, 0.7), (1.9, 2.5), (4.0, 5.1))) < 1e-12,
            "rp2_euler_characteristic": euler_characteristic(roman_points, roman_triangles),
            "rp2_orientable": is_orientable(roman_triangles),
            "rp2_embedded_in_r4": closest_far_pair(roman_points, roman_triangles, 4) > 0.02,
            "roman_shadow_self_intersects": closest_far_pair(roman_points, roman_triangles, 3) < 1e-9,
            "roman_equation_residual": round(roman_residual(roman_points), 12),
            "torus_control_orientable": is_orientable(torus_triangles),
            "torus_control_euler": euler_characteristic(torus, torus_triangles)}


def controls():
    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    points, triangles = klein_mesh(12, 6)
    flipped = [triangles[0][::-1]] + triangles[1:]
    open_strip = [(0, 1, 2), (1, 3, 2)]
    sphere = fourd.sphere_mesh((0.0, 0.0, 0.0), 1.0, None, 1)
    sphere_triangles = [tuple(sphere["indices"][k:k + 3]) for k in range(0, len(sphere["indices"]), 3)]
    bumped = list(veronese_mesh(1)[0])
    largest = max(range(len(bumped)), key=lambda k: abs(bumped[k][0] * bumped[k][1] * bumped[k][2]))
    bumped[largest] = tuple(1.3 * value for value in bumped[largest])
    return {"odd_columns_refused": refused(lambda: klein_mesh(7, 6)),
            "sphere_is_orientable": is_orientable(sphere_triangles),
            "one_flipped_face_still_nonorientable": not is_orientable(flipped),
            "open_strip_has_euler_one": euler_characteristic([0, 1, 2, 3], open_strip) == 1,
            "bumped_point_breaks_roman_equation": roman_residual(bumped) > 1e-3}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="klein_bottle_veronese.py",
                                     description="Write the 3D shadows of the Klein bottle and the Veronese surface.")
    parser.add_argument("--columns", type=int, default=32, help="Klein bottle grid steps along u (even)")
    parser.add_argument("--rows", type=int, default=12, help="Klein bottle grid steps along v")
    parser.add_argument("--subdivisions", type=int, default=3, help="icosphere subdivisions for the Veronese surface")
    parser.add_argument("--gap", type=float, default=2.6, help="distance between the two models")
    parser.add_argument("--out", required=True, help="output .gltf")
    args = parser.parse_args(argv)
    if not 0 <= args.subdivisions <= 4 or args.gap <= 0:
        parser.error("subdivisions is 0 to 4 and gap is positive")
    try:
        summary = export(args.out, args.columns, args.rows, args.subdivisions, args.gap)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
