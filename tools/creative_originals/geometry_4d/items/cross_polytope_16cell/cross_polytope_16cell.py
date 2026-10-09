"""The 16-cell (4D cross-polytope, Schlafli symbol {3,3,4}) built from signed axes.

The vertices are +-r e_i. Two vertices share an edge unless they are antipodal; a face picks three different axes
and a sign for each; a cell picks a sign for every one of the four axes, so the 16 cells are the 16 sign vectors.
Nothing is found by search. The edge graph is the cocktail party graph K_{2,2,2,2}: its complement is the perfect
matching of antipodes. The 16-cell is the dual of the tesseract (the tesseract's cell centres are +-e_i) and the
bipyramid over the octahedron (8 cells meet each apex +-e_4). Exports: exploded cells coloured by sign vector, a
tube wireframe, LINES, or the polytope record.

    python cross_polytope_16cell.py --style cells --rotate xw=0.3,zw=0.2,yz=0.5 --out 16cell.gltf
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys

import fourd


def vertices(radius=1.0):
    """+-radius on each axis, ordered (+x, -x, +y, -y, +z, -z, +w, -w): vertex 2a + s is axis a with sign (-1)^s."""
    if radius <= 0:
        raise ValueError("radius is positive")
    points = []
    for axis in range(4):
        for sign in (1.0, -1.0):
            points.append(tuple(sign * radius if index == axis else 0.0 for index in range(4)))
    return points


def polytope(radius=1.0):
    """Edges between non-antipodal vertices, faces from three signed axes, cells from the 16 sign vectors."""
    edges = [(a, b) for a, b in itertools.combinations(range(8), 2) if a // 2 != b // 2]
    faces, face_of = [], {}
    for axes in itertools.combinations(range(4), 3):
        for signs in itertools.product((0, 1), repeat=3):
            face = [2 * axis + sign for axis, sign in zip(axes, signs)]
            face_of[tuple(face)] = len(faces)
            faces.append(face)
    cells = []
    for signs in itertools.product((0, 1), repeat=4):
        members = [2 * axis + sign for axis, sign in enumerate(signs)]
        cells.append([face_of[tuple(sorted(triple))] for triple in itertools.combinations(members, 3)])
    return {"vertices": vertices(radius), "edges": edges, "faces": faces, "cells": cells}


def is_cocktail_party(edges, count=8):
    """True when the complement of the edge graph is a perfect matching (every vertex misses exactly one other)."""
    present = {tuple(sorted(edge)) for edge in edges}
    missing = [pair for pair in itertools.combinations(range(count), 2) if pair not in present]
    covered = [vertex for pair in missing for vertex in pair]
    return len(missing) == count // 2 and sorted(covered) == list(range(count))


def tesseract_cell_centres(size=2.0):
    """Centroids of the eight cubic cells of the tesseract with vertices (+-size/2)^4: the points +-(size/2) e_i."""
    half = size / 2.0
    corners = [tuple(point) for point in itertools.product((-half, half), repeat=4)]
    centres = []
    for axis in range(4):
        for value in (half, -half):
            members = [corner for corner in corners if corner[axis] == value]
            centres.append(fourd.centroid(members))
    return centres


def apex_cells(shape, apex):
    """The cells containing a vertex: the bipyramid half over the octahedron of the other six vertices."""
    faces = shape["faces"]
    return [index for index, cell in enumerate(shape["cells"]) if any(apex in faces[face] for face in cell)]


def mesh(radius=1.0, rotation="xw=0.3,zw=0.2,yz=0.5", projection="perspective", eye=2.6, style="cells", tube=0.025,
         shrink=0.6, cells="front"):
    """Exploded cells (those facing the 4D eye, or all; 16 colours), a tube wireframe or LINES."""
    shape = polytope(radius)
    rotated = fourd.rotate_points(fourd.rotation_matrix(rotation), shape["vertices"])
    projected = fourd.project_points(rotated, projection, eye_distance=eye * radius)
    if style == "cells":
        chosen = fourd.facing_cells(shape, rotated, projection, eye * radius) if cells == "front" else list(range(16))
        return fourd.cell_mesh(projected, shape, shrink, [fourd.palette(16)[index] for index in chosen], cells=chosen)
    colours = fourd.depth_colors([point[3] for point in rotated])
    if style == "lines":
        return fourd.line_mesh(projected, shape["edges"], colours)
    if style == "tubes":
        return fourd.wireframe_mesh(projected, shape["edges"], tube * radius, None, 8, colours)
    raise ValueError("style is cells, tubes or lines")


def export(path, radius=1.0, rotation="xw=0.3,zw=0.2,yz=0.5", projection="perspective", eye=2.6, style="cells", tube=0.025,
           shrink=0.6, cells="front"):
    if str(path).endswith(".json"):
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(fourd.polytope_record(polytope(radius), "16-cell"), stream, indent=1)
            stream.write("\n")
        return {"path": str(path)}
    document = fourd.gltf_document([dict(mesh(radius, rotation, projection, eye, style, tube, shrink, cells),
                                         name="16cell")],
                                   generator="cross_polytope_16cell.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    shape = polytope()
    report = fourd.regularity_report(shape)
    counts = fourd.f_vector(shape)
    centres = tesseract_cell_centres()
    dual = sorted(fourd.point_key(point) for point in centres) == sorted(fourd.point_key(point)
                                                                            for point in vertices(1.0))
    return {"vertices": counts[0], "edges": counts[1], "faces": counts[2], "cells": counts[3],
            "euler_characteristic": fourd.euler_characteristic(shape), "circumradius": report["circumradius"],
            "edge_length": report["edge_length"], "regular": report["regular"],
            "schlafli": list(fourd.schlafli_symbol(shape)), "hypervolume": fourd.hypervolume(shape),
            "vertex_degree": report["degrees"][0], "edge_graph_is_cocktail_party": is_cocktail_party(shape["edges"]),
            "dual_of_tesseract": dual, "cells_at_each_apex": len(apex_cells(shape, 6)),
            "edges_match_minimum_distance": fourd.edges_by_length(shape["vertices"]) == shape["edges"]}


def controls():
    shape = polytope()
    moved = dict(shape, vertices=[fourd.add(shape["vertices"][0], (0.0, 0.03, 0.0, 0.0))] + shape["vertices"][1:])
    with_antipodal = shape["edges"] + [(0, 1)]
    without_one = shape["edges"][1:]

    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    return {"moved_vertex_not_regular": not fourd.regularity_report(moved)["regular"],
            "antipodal_edge_breaks_cocktail_party": not is_cocktail_party(with_antipodal),
            "missing_edge_breaks_cocktail_party": not is_cocktail_party(without_one),
            "negative_radius_refused": refused(lambda: vertices(-1.0))}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="cross_polytope_16cell.py", description="Write the 16-cell.")
    parser.add_argument("--radius", type=float, default=1.0, help="circumradius")
    parser.add_argument("--rotate", default="xw=0.3,zw=0.2,yz=0.5", help="plane rotations applied in order")
    parser.add_argument("--project", choices=fourd.PROJECTIONS, default="perspective", help="4D to 3D projection")
    parser.add_argument("--eye", type=float, default=2.6, help="4D eye distance in circumradii")
    parser.add_argument("--style", choices=("cells", "tubes", "lines"), default="cells", help="output style")
    parser.add_argument("--tube", type=float, default=0.025, help="tube radius in circumradii (tubes style)")
    parser.add_argument("--shrink", type=float, default=0.6, help="cell scale toward its own centroid (cells style)")
    parser.add_argument("--cells", choices=("front", "all"), default="front",
                        help="cells style: only cells facing the 4D eye (no overlap) or all cells")
    parser.add_argument("--out", required=True, help=".gltf model or .json polytope record")
    args = parser.parse_args(argv)
    if args.radius <= 0 or args.eye <= 0 or not 0 < args.shrink <= 1 or args.tube <= 0:
        parser.error("radius, eye and tube are positive; shrink is in (0, 1]")
    try:
        summary = export(args.out, args.radius, args.rotate, args.project, args.eye, args.style, args.tube, args.shrink,
                         args.cells)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
