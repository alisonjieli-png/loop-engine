"""Schlegel diagrams of convex 4-polytopes: every cell seen through one chosen cell.

Pick a cell F with outward unit normal n and hyperplane n . p = h. Place the eye e = c + t n just outside F (c the
centroid of F), with t at half the largest value for which e stays inside every other cell's half-space
(n_g . e < h_g), so F is the only cell the eye sees from outside. Each vertex v is projected centrally from e onto
F's hyperplane: p = e + s (v - e) with s = (h - n . e)/(n . (v - e)). The image is a 3D polyhedral complex inside F:
F's own vertices stay fixed and every other vertex lands inside F. Coordinates are taken in the hyperplane basis
around c. Built-in polytopes come from the Coxeter group orbits (fourd); any fourd_polytope/v1 record also works.

    python schlegel_diagram.py --polytope 24cell --style tubes --out schlegel_24cell.gltf
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from functools import lru_cache

import fourd

BUILT_IN = {"5cell": ("A4", 0), "tesseract": ("B4", 0), "16cell": ("B4", 3), "24cell": ("F4", 0),
            "120cell": ("H4", 0), "600cell": ("H4", 3)}


@lru_cache(maxsize=8)
def _built(name):
    group, node = BUILT_IN[name]
    roots = fourd.simple_roots(group)
    vertices = fourd.orbit(fourd.wythoff_point(roots, {node}), roots)
    # A regular polytope ringed at an end node has its cells orthogonal to the images of the far end's weight.
    normals = fourd.orbit(fourd.normalize(fourd.fundamental_weights(roots)[3 - node]), roots)
    return fourd.polytope_from_facets(vertices, normals)


def load_polytope(source):
    """A built-in name (5cell, tesseract, 16cell, 24cell, 120cell, 600cell) or a fourd_polytope/v1 JSON path."""
    if source in BUILT_IN:
        shape = _built(source)
        return {key: list(value) for key, value in shape.items()}
    with open(source, "r", encoding="utf-8") as stream:
        return fourd.polytope_from_record(json.load(stream))


def eye_point(shape, cell=0):
    """(eye, normal, offset, centre): the viewpoint just outside the chosen cell."""
    if not 0 <= cell < len(shape["cells"]):
        raise ValueError(f"cell is 0 to {len(shape['cells']) - 1}")
    normals = fourd.cell_normals(shape)
    sets = fourd.cell_vertex_sets(shape)
    vertices = shape["vertices"]
    offsets = [fourd.dot(normals[index], vertices[min(members)]) for index, members in enumerate(sets)]
    normal, offset = normals[cell], offsets[cell]
    centre = fourd.centroid([vertices[index] for index in sets[cell]])
    limit = math.inf
    for index, (other, height) in enumerate(zip(normals, offsets)):
        along = fourd.dot(other, normal)
        if index != cell and along > 1e-12:
            limit = min(limit, (height - fourd.dot(other, centre)) / along)
    step = 0.5 * limit if math.isfinite(limit) else offset
    return fourd.add(centre, fourd.scale(normal, step)), normal, offset, centre


def project(shape, cell=0):
    """3D Schlegel coordinates of every vertex (hyperplane basis of the chosen cell, origin at its centroid)."""
    eye, normal, offset, centre = eye_point(shape, cell)
    basis = fourd.hyperplane_basis(normal)
    points = []
    for vertex in shape["vertices"]:
        direction = fourd.sub(vertex, eye)
        denominator = fourd.dot(normal, direction)
        if denominator >= -1e-12:
            raise ValueError("a vertex is not behind the chosen cell's hyperplane as seen from the eye")
        hit = fourd.add(eye, fourd.scale(direction, (offset - fourd.dot(normal, eye)) / denominator))
        points.append(tuple(fourd.dot(fourd.sub(hit, centre), axis) for axis in basis))
    return points


def outer_faces(shape, points, cell=0):
    """Planes (unit normal, offset) of the outer cell's faces in Schlegel coordinates, normals pointing outward."""
    middle = fourd.centroid([points[index] for index in fourd.cell_vertex_sets(shape)[cell]])
    planes = []
    for face_index in shape["cells"][cell]:
        corners = [points[index] for index in shape["faces"][face_index]]
        normal = fourd.normalize(fourd.polygon_normal(corners))
        if fourd.dot(normal, fourd.sub(fourd.centroid(corners), middle)) < 0.0:
            normal = fourd.scale(normal, -1.0)
        planes.append((normal, fourd.dot(normal, corners[0])))
    return planes


def inside_outer_cell(shape, points, cell=0, tolerance=1e-9):
    """True when every projected vertex lies inside or on the outer cell."""
    planes = outer_faces(shape, points, cell)
    return all(fourd.dot(normal, point) <= offset + tolerance * max(1.0, abs(offset))
               for point in points for normal, offset in planes)


def depth(shape, cell=0):
    """Distance of each vertex below the chosen cell's hyperplane (0 for the cell's own vertices)."""
    _eye, normal, offset, _centre = eye_point(shape, cell)
    return [offset - fourd.dot(normal, vertex) for vertex in shape["vertices"]]


def meshes(shape, cell=0, style="tubes", radius=None, sides=6, shell=True):
    """The Schlegel wireframe (tubes or LINES, coloured from outer amber to inner blue) and the outer cell as a shell."""
    points = project(shape, cell)
    reach = max(fourd.norm(point) for point in points)
    radius = 0.012 * reach if radius is None else radius
    colours = fourd.depth_colors([-value for value in depth(shape, cell)])
    if style == "lines":
        wire = dict(fourd.line_mesh(points, shape["edges"], colours), unlit=True)
    elif style == "tubes":
        wire = fourd.wireframe_mesh(points, shape["edges"], radius, None, sides, colours)
    else:
        raise ValueError("style is tubes or lines")
    result = [dict(wire, name="schlegel")]
    if shell:
        faces = [shape["faces"][index] for index in shape["cells"][cell]]
        planes = outer_faces(shape, points, cell)
        oriented = []
        for face, (normal, _offset) in zip(faces, planes):
            corners = [points[index] for index in face]
            oriented.append(list(face) if fourd.dot(fourd.polygon_normal(corners), normal) > 0.0 else list(reversed(face)))
        result.append(dict(fourd.polygon_mesh(points, oriented), name="outer_cell", color=(0.75, 0.8, 0.95, 0.18)))
    return result


def export(path, source="24cell", cell=0, style="tubes", radius=None, sides=6, shell=True):
    shape = load_polytope(source)
    document = fourd.gltf_document(meshes(shape, cell, style, radius, sides, shell), generator="schlegel_diagram.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    result = {}
    for name in BUILT_IN:
        shape = load_polytope(name)
        points = project(shape)
        own = fourd.cell_vertex_sets(shape)[0]
        depths = depth(shape)
        fixed = all(abs(depths[index]) < 1e-9 for index in own)
        distinct = len({fourd.point_key(point, 7) for point in points}) == len(points)
        result[name] = [inside_outer_cell(shape, points), fixed, distinct]
    tesseract = load_polytope("tesseract")
    points = project(tesseract)
    sets = fourd.cell_vertex_sets(tesseract)
    opposite = [index for index, members in enumerate(sets) if not members & sets[0]][0]
    inner = [points[index] for index in sets[opposite]]
    outer = [points[index] for index in sets[0]]
    inner_extent = sorted(round(max(p[axis] for p in inner) - min(p[axis] for p in inner), 9) for axis in range(3))
    outer_extent = sorted(round(max(p[axis] for p in outer) - min(p[axis] for p in outer), 9) for axis in range(3))
    centred = all(abs(value) < 1e-9 for value in fourd.centroid(inner))
    return {"inside_fixed_distinct": result,
            "tesseract_inner_cell_is_centred_cube": centred and inner_extent[0] == inner_extent[2],
            "tesseract_inner_to_outer_ratio": round(inner_extent[0] / outer_extent[0], 9),
            "cells_120cell": len(load_polytope("120cell")["cells"])}


def controls():
    shape = load_polytope("tesseract")
    points = project(shape)
    pushed = list(points)
    pushed[0] = fourd.scale(pushed[0], 3.0)

    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    return {"pushed_vertex_detected_outside": not inside_outer_cell(shape, pushed),
            "bad_cell_refused": refused(lambda: eye_point(shape, 99)),
            "unknown_style_refused": refused(lambda: meshes(shape, style="dots")),
            "broken_record_refused": refused(lambda: fourd.polytope_from_record({"record_type": "fourd_polytope/v1",
                                                                                 "vertices": [[0, 0, 0, 0]],
                                                                                 "edges": [[0, 3]]}))}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="schlegel_diagram.py", description="Write the Schlegel diagram of a 4-polytope.")
    parser.add_argument("--polytope", default="24cell",
                        help="built-in name (5cell, tesseract, 16cell, 24cell, 120cell, 600cell) or a polytope JSON path")
    parser.add_argument("--cell", type=int, default=0, help="index of the cell to look through")
    parser.add_argument("--style", choices=("tubes", "lines"), default="tubes", help="tube mesh or LINES primitive")
    parser.add_argument("--radius", type=float, default=None, help="tube radius (default 1.2 percent of the size)")
    parser.add_argument("--sides", type=int, default=6, help="sides of each tube")
    parser.add_argument("--shell", choices=("on", "off"), default="on", help="draw the outer cell as a translucent shell")
    parser.add_argument("--out", required=True, help="output .gltf")
    args = parser.parse_args(argv)
    if args.sides < 3 or (args.radius is not None and args.radius <= 0):
        parser.error("sides is 3 or more and radius is positive")
    try:
        summary = export(args.out, args.polytope, args.cell, args.style, args.radius, args.sides, args.shell == "on")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
