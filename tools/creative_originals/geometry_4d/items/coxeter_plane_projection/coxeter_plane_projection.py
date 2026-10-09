"""Orthogonal projection of a 4-polytope onto the Coxeter plane of its symmetry group (SVG and glTF).

The Coxeter element c = s1 s2 s3 s4 (the product of the four simple reflections) is a rotation of order h, the
Coxeter number: 5 for A4, 8 for B4, 12 for F4, 30 for H4. In one invariant plane it turns by 2 pi/h; that plane
is the eigenspace of (c + c^T)/2 for the eigenvalue cos(2 pi/h), found here as a null space. Projected onto it, the
vertices fall on concentric rings of h points with h-fold rotational symmetry, and the outer ring traces the
Petrie polygon. Vertices come from the Wythoff construction of the group (any ringing); edges join vertices at the
edge length, which is 1 for every Wythoff polytope.

    python coxeter_plane_projection.py --polytope 600cell --out coxeter_600cell.svg
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from functools import lru_cache

import fourd

NAMED = {"5cell": ("A4", "1000"), "tesseract": ("B4", "1000"), "16cell": ("B4", "0001"), "24cell": ("F4", "1000"),
         "600cell": ("H4", "0001"), "120cell": ("H4", "1000")}


def reflection_matrix(root):
    """The 4x4 matrix of the reflection in the hyperplane orthogonal to root."""
    unit = fourd.normalize(root)
    return tuple(tuple((1.0 if i == j else 0.0) - 2.0 * unit[i] * unit[j] for j in range(4)) for i in range(4))


def coxeter_element(group):
    """The product of the four simple reflections, in node order."""
    result = fourd.identity(4)
    for root in fourd.simple_roots(group):
        result = fourd.matmul(result, reflection_matrix(root))
    return result


def element_order(matrix, limit=100):
    """The smallest k with matrix^k = identity."""
    power = matrix
    for k in range(1, limit + 1):
        if all(abs(power[i][j] - (1.0 if i == j else 0.0)) < 1e-9 for i in range(4) for j in range(4)):
            return k
        power = fourd.matmul(power, matrix)
    raise ValueError("order above limit")


def coxeter_plane(group):
    """An orthonormal basis (u, v) of the plane in which the Coxeter element turns by 2 pi/h."""
    element = coxeter_element(group)
    number = fourd.COXETER_NUMBERS[group]
    symmetric = [[(element[i][j] + element[j][i]) / 2.0 - (math.cos(2.0 * math.pi / number) if i == j else 0.0)
                  for j in range(4)] for i in range(4)]
    basis = fourd.null_space(symmetric, 1e-9)
    if len(basis) != 2:
        raise ValueError("the Coxeter plane is not 2-dimensional")
    u = fourd.normalize(basis[0])
    v = fourd.normalize(fourd.sub(basis[1], fourd.scale(u, fourd.dot(basis[1], u))))
    return u, v


@lru_cache(maxsize=16)
def _polytope(group, rings):
    roots = fourd.simple_roots(group)
    ringed = {index for index, mark in enumerate(rings) if mark == "1"}
    vertices = fourd.orbit(fourd.wythoff_point(roots, ringed), roots, 3000)
    return vertices, fourd.edges_by_length(vertices, 1.0)


def named_polytope(name_or_group, rings=None):
    """(group, vertices, edges) for a named regular polytope or a group with a ringing like '1100'."""
    if rings is None:
        if name_or_group not in NAMED:
            raise ValueError(f"name is one of {sorted(NAMED)}, or give a group and a ringing")
        group, rings = NAMED[name_or_group]
    else:
        group = name_or_group
        if group not in fourd.COXETER_DIAGRAMS or len(rings) != 4 or set(rings) - {"0", "1"} or "1" not in rings:
            raise ValueError("group is A4, B4, D4, F4 or H4 and rings is four characters of 0 and 1")
    vertices, edges = _polytope(group, rings)
    return group, list(vertices), list(edges)


def project(group, vertices):
    """2D Coxeter plane coordinates of the vertices."""
    u, v = coxeter_plane(group)
    return [(fourd.dot(point, u), fourd.dot(point, v)) for point in vertices]


def rings(points, tolerance=1e-7):
    """[(radius, count)] of the concentric rings, smallest radius first."""
    radii = sorted(math.hypot(x, y) for x, y in points)
    groups = []
    for radius in radii:
        if groups and radius - groups[-1][0] <= tolerance:
            groups[-1][1] += 1
        else:
            groups.append([radius, 1])
    return [(round(radius, 9), count) for radius, count in groups]


def is_symmetric(points, order, tolerance=1e-7):
    """True when turning the points by 2 pi/order maps the set onto itself."""
    angle = 2.0 * math.pi / order
    keys = {(round(x / tolerance), round(y / tolerance)) for x, y in points}
    def near(x, y):
        bx, by = round(x / tolerance), round(y / tolerance)
        return any((bx + dx, by + dy) in keys for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    return all(near(x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle))
               for x, y in points)


def svg(points, edges, size=640, margin=24):
    """An SVG drawing: edges coloured by the mean ring of their ends, vertices as dots."""
    reach = max(math.hypot(x, y) for x, y in points) or 1.0
    factor = (size / 2.0 - margin) / reach
    radii = sorted({round(math.hypot(x, y), 6) for x, y in points})
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">',
             f'<rect width="{size}" height="{size}" fill="#0e1016"/>']
    for a, b in edges:
        (xa, ya), (xb, yb) = points[a], points[b]
        level = (radii.index(round(math.hypot(xa, ya), 6)) + radii.index(round(math.hypot(xb, yb), 6))) / max(1, 2 * (len(radii) - 1))
        r, g, bl, _alpha = fourd.depth_color(level)
        colour = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(bl * 255))
        lines.append(f'<line x1="{size / 2 + xa * factor:.3f}" y1="{size / 2 - ya * factor:.3f}" '
                     f'x2="{size / 2 + xb * factor:.3f}" y2="{size / 2 - yb * factor:.3f}" stroke="{colour}" '
                     f'stroke-width="0.8" stroke-opacity="0.85"/>')
    for x, y in points:
        lines.append(f'<circle cx="{size / 2 + x * factor:.3f}" cy="{size / 2 - y * factor:.3f}" r="1.6" fill="#f2f4f8"/>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def meshes(points, edges, style="lines", radius=0.008, dot=0.016):
    """The drawing in the glTF xy plane (z = 0): edges as LINES (or thin tubes) and vertices as small spheres,
    both coloured by distance from the centre."""
    reach = max(math.hypot(x, y) for x, y in points) or 1.0
    flat = [(x / reach, y / reach, 0.0) for x, y in points]
    colours = fourd.depth_colors([math.hypot(x, y) for x, y in points])
    if style == "lines":
        wire = dict(fourd.line_mesh(flat, edges, colours), unlit=True)
    elif style == "tubes":
        wire = fourd.tube_mesh(flat, edges, radius, 4, colours)
    else:
        raise ValueError("style is lines or tubes")
    dots = fourd.merge_meshes([fourd.sphere_mesh(point, dot, colour) for point, colour in zip(flat, colours)])
    return [dict(wire, name="edges"), dict(dots, name="vertices")]


def export(path, name="600cell", group=None, ringing=None, style="lines"):
    """Write the projection as .svg or .gltf."""
    chosen_group, vertices, edges = named_polytope(group, ringing) if group else named_polytope(name)
    points = project(chosen_group, vertices)
    if str(path).endswith(".svg"):
        text = svg(points, edges)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(text)
        return {"path": str(path), "vertices": len(points), "edges": len(edges), "rings": rings(points)}
    document = fourd.gltf_document(meshes(points, edges, style), generator="coxeter_plane_projection.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), "rings": rings(points), **fourd.gltf_summary(document)}


def invariants():
    result = {"coxeter_numbers": {group: element_order(coxeter_element(group)) for group in ("A4", "B4", "F4", "H4")}}
    ring_counts, symmetric, orbits = {}, {}, {}
    for name in NAMED:
        group, vertices, _edges = named_polytope(name)
        points = project(group, vertices)
        ring_counts[name] = [count for _radius, count in rings(points)]
        symmetric[name] = is_symmetric(points, fourd.COXETER_NUMBERS[group])
        orbits[name] = len(points) // fourd.COXETER_NUMBERS[group] if all(math.hypot(x, y) > 1e-9 for x, y in points) else None
    result["ring_counts"] = ring_counts
    result["rotation_orbits"] = orbits
    result["h_fold_symmetric"] = symmetric
    group, vertices, edges = named_polytope("tesseract")
    result["tesseract_edges"] = len(edges)
    u, v = coxeter_plane("H4")
    result["plane_orthonormal"] = abs(fourd.dot(u, v)) < 1e-12 and abs(fourd.norm(u) - 1.0) < 1e-12
    return result


def controls():
    group, vertices, _edges = named_polytope("tesseract")
    points = project(group, vertices)
    shifted = [(x + 0.05, y) for x, y in points]

    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    return {"shifted_points_not_symmetric": not is_symmetric(shifted, 8),
            "wrong_order_not_symmetric": not is_symmetric(points, 7),
            "unknown_name_refused": refused(lambda: named_polytope("dodecahedron")),
            "bad_ringing_refused": refused(lambda: named_polytope("B4", "0000"))}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="coxeter_plane_projection.py",
                                     description="Project a 4-polytope onto the Coxeter plane of its group.")
    parser.add_argument("--polytope", default="600cell", help="5cell, tesseract, 16cell, 24cell, 600cell or 120cell")
    parser.add_argument("--group", default=None, help="Coxeter group for a Wythoff ringing instead of a name")
    parser.add_argument("--rings", default=None, help="ringing with --group, like 1100")
    parser.add_argument("--style", choices=("lines", "tubes"), default="lines", help="glTF edges as LINES or thin tubes")
    parser.add_argument("--out", required=True, help=".svg drawing or .gltf model")
    args = parser.parse_args(argv)
    if (args.group is None) != (args.rings is None):
        parser.error("--group and --rings go together")
    try:
        summary = export(args.out, args.polytope, args.group, args.rings, args.style)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
