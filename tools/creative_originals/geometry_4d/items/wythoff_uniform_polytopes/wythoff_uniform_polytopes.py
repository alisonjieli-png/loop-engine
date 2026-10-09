"""Uniform 4-polytopes by the Wythoff construction for the Coxeter groups A4, B4, D4, F4 and H4.

A ringing such as "1100" marks Coxeter diagram nodes. The generating point lies on the mirror of every unringed
node and at distance 1/2 from every ringed mirror (fourd.wythoff_point), so all its reflections in ringed mirrors
are at distance 1: the vertices are its orbit under the reflection group and every edge has length 1. Each facet
of a Wythoff polytope is orthogonal to an image of a fundamental weight (the direction fixed by all mirrors but
one), so the orbits of the four weights are the candidate facet normals; fourd.polytope_from_facets keeps those
whose face is 3-dimensional and derives faces and edges from them. Cells are grouped into types by their vertex
and face counts. Node 0 is the first mirror of the Schlafli symbol: B4 "1000" is the tesseract {4,3,3}, "0001"
the 16-cell, F4 "1000" the 24-cell, H4 "1000" the 120-cell and "0001" the 600-cell.

    python wythoff_uniform_polytopes.py --group B4 --rings 1100 --style cells --out truncated_tesseract.gltf
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

import fourd

GROUPS = ("A4", "B4", "D4", "F4", "H4")
NAMES = {
    "A4": {"1000": "5-cell", "0100": "rectified 5-cell", "1100": "truncated 5-cell", "1010": "cantellated 5-cell",
           "1001": "runcinated 5-cell", "0110": "bitruncated 5-cell", "1110": "cantitruncated 5-cell",
           "1101": "runcitruncated 5-cell", "1111": "omnitruncated 5-cell"},
    "B4": {"1000": "tesseract", "0001": "16-cell", "0100": "rectified tesseract", "0010": "24-cell (rectified 16-cell)",
           "1100": "truncated tesseract", "0011": "truncated 16-cell", "1010": "cantellated tesseract",
           "0101": "rectified 24-cell (cantellated 16-cell)", "1001": "runcinated tesseract",
           "0110": "bitruncated tesseract", "1110": "cantitruncated tesseract",
           "0111": "truncated 24-cell (cantitruncated 16-cell)", "1101": "runcitruncated tesseract",
           "1011": "runcitruncated 16-cell", "1111": "omnitruncated tesseract"},
    "F4": {"1000": "24-cell", "0100": "rectified 24-cell", "1100": "truncated 24-cell", "1010": "cantellated 24-cell",
           "1001": "runcinated 24-cell", "0110": "bitruncated 24-cell", "1110": "cantitruncated 24-cell",
           "1101": "runcitruncated 24-cell", "1111": "omnitruncated 24-cell"},
    "H4": {"1000": "120-cell", "0001": "600-cell", "0100": "rectified 120-cell", "0010": "rectified 600-cell",
           "1100": "truncated 120-cell", "0011": "truncated 600-cell"},
}
MAXIMUM_VERTICES = 1500


def parse_rings(rings):
    """'1100' -> {0, 1}; four characters of 0 and 1 with at least one 1."""
    if not isinstance(rings, str) or len(rings) != 4 or set(rings) - {"0", "1"} or "1" not in rings:
        raise ValueError("rings is four characters of 0 and 1 with at least one 1, like 1100")
    return {index for index, mark in enumerate(rings) if mark == "1"}


def name(group, rings):
    """A common name for the ringing (mirror-symmetric diagrams read both ways), or a Coxeter-Dynkin label."""
    table = NAMES.get(group, {})
    if rings in table:
        return table[rings]
    if group in ("A4", "F4") and rings[::-1] in table:
        return table[rings[::-1]]
    return f"{group} {rings}"


def construct(group, rings, limit=MAXIMUM_VERTICES):
    """The uniform polytope with unit edges, as a fourd polytope with the group and ringing attached."""
    if group not in GROUPS:
        raise ValueError(f"group is one of {GROUPS}")
    roots = fourd.simple_roots(group)
    point = fourd.wythoff_point(roots, parse_rings(rings), edge=1.0)
    vertices = fourd.orbit(point, roots, limit)
    normals = []
    for weight in fourd.fundamental_weights(roots):
        normals += fourd.orbit(fourd.normalize(weight), roots, 20000)
    shape = fourd.polytope_from_facets(vertices, normals)
    shape["group"], shape["rings"] = group, rings
    return shape


def cell_types(shape):
    """[[cell vertices, cell faces, how many], ...] sorted: the kinds of cells and their counts."""
    faces = shape["faces"]
    counter = Counter((len({vertex for face in cell for vertex in faces[face]}), len(cell)) for cell in shape["cells"])
    return sorted([vertices, face_count, count] for (vertices, face_count), count in counter.items())


def edge_lengths(shape):
    """(shortest, longest) edge."""
    lengths = [fourd.distance(shape["vertices"][a], shape["vertices"][b]) for a, b in shape["edges"]]
    return min(lengths), max(lengths)


def mesh(shape, rotation="xw=0.2,yz=0.3", projection="perspective", eye=2.6, style="cells", shrink=0.84, tube=0.03,
         cells="front"):
    """Exploded cells facing the 4D eye (or all) coloured by cell type, tubes or LINES coloured by depth."""
    rotated = fourd.rotate_points(fourd.rotation_matrix(rotation), shape["vertices"])
    reach = max(fourd.norm(point) for point in shape["vertices"])
    projected = fourd.project_points(rotated, projection, eye_distance=eye * reach)
    if style == "cells":
        kinds = cell_types(shape)
        palette = fourd.palette(len(kinds))
        faces = shape["faces"]
        lookup = {(row[0], row[1]): palette[index] for index, row in enumerate(kinds)}
        colours = [lookup[(len({v for face in cell for v in faces[face]}), len(cell))] for cell in shape["cells"]]
        chosen = fourd.facing_cells(shape, rotated, projection, eye * reach) if cells == "front" \
            else list(range(len(shape["cells"])))
        return fourd.cell_mesh(projected, shape, shrink, [colours[index] for index in chosen], cells=chosen)
    colours = fourd.depth_colors([point[3] for point in rotated])
    if style == "lines":
        return fourd.line_mesh(projected, shape["edges"], colours)
    if style == "tubes":
        return fourd.wireframe_mesh(projected, shape["edges"], tube, None, 6, colours)
    raise ValueError("style is cells, tubes or lines")


def export(path, group="B4", rings="1100", rotation="xw=0.2,yz=0.3", projection="perspective", eye=2.6, style="cells",
           shrink=0.84, tube=0.03, cells="front"):
    shape = construct(group, rings)
    if str(path).endswith(".json"):
        record = fourd.polytope_record(shape, name(group, rings))
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=1)
            stream.write("\n")
        return {"path": str(path), "f_vector": list(fourd.f_vector(shape))}
    document = fourd.gltf_document([dict(mesh(shape, rotation, projection, eye, style, shrink, tube, cells),
                                         name=name(group, rings).replace(" ", "_"))],
                                   generator="wythoff_uniform_polytopes.py")
    return {"path": str(path), "name": name(group, rings), "f_vector": list(fourd.f_vector(shape)),
            "cell_types": cell_types(shape), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


CHECKED = (("A4", "1000"), ("A4", "0100"), ("A4", "1100"), ("A4", "1001"), ("A4", "1111"), ("B4", "1000"),
           ("B4", "0100"), ("B4", "1100"), ("B4", "1001"), ("B4", "0110"), ("B4", "1010"), ("B4", "0011"),
           ("B4", "1111"), ("F4", "0100"), ("F4", "1100"), ("H4", "0001"))


def invariants():
    shapes = {f"{group} {rings}": construct(group, rings) for group, rings in CHECKED}
    unit = all(abs(low - 1.0) < 1e-9 and abs(high - 1.0) < 1e-9 for low, high in map(edge_lengths, shapes.values()))
    return {"f_vectors": {key: list(fourd.f_vector(shape)) for key, shape in shapes.items()},
            "euler_characteristics": sorted({fourd.euler_characteristic(shape) for shape in shapes.values()}),
            "structure_problems": sum(len(fourd.polytope_problems(shape)) for shape in shapes.values()),
            "unit_edges": unit,
            "vertex_transitive_degrees": all(len(fourd.regularity_report(shape)["degrees"]) == 1
                                             for shape in shapes.values()),
            "truncated_tesseract_cells": cell_types(shapes["B4 1100"]),
            "runcinated_tesseract_cells": cell_types(shapes["B4 1001"]),
            "omnitruncated_5cell_cells": cell_types(shapes["A4 1111"]),
            "names": [name("B4", "1100"), name("F4", "0010"), name("H4", "0001")]}


def controls():
    shape = construct("B4", "1100")
    moved = dict(shape, vertices=[fourd.add(shape["vertices"][0], (0.05, 0.0, 0.0, 0.0))] + shape["vertices"][1:])
    low, high = edge_lengths(moved)

    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    return {"empty_ringing_refused": refused(lambda: parse_rings("0000")),
            "malformed_ringing_refused": refused(lambda: parse_rings("11a0")),
            "unknown_group_refused": refused(lambda: construct("E8", "1000")),
            "oversized_orbit_refused": refused(lambda: construct("H4", "1111")),
            "moved_vertex_breaks_unit_edges": high - low > 1e-3,
            "dropped_cell_breaks_euler": fourd.euler_characteristic(dict(shape, cells=shape["cells"][1:])) != 0}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="wythoff_uniform_polytopes.py",
                                     description="Write a uniform 4-polytope from a Coxeter group and a ringing.")
    parser.add_argument("--group", choices=GROUPS, default="B4", help="Coxeter group")
    parser.add_argument("--rings", default="1100", help="ringed nodes, four characters of 0 and 1 (node 0 first)")
    parser.add_argument("--rotate", default="xw=0.2,yz=0.3", help="plane rotations applied in order")
    parser.add_argument("--project", choices=fourd.PROJECTIONS, default="perspective", help="4D to 3D projection")
    parser.add_argument("--eye", type=float, default=2.6, help="4D eye distance in circumradii")
    parser.add_argument("--style", choices=("cells", "tubes", "lines"), default="cells", help="output style")
    parser.add_argument("--shrink", type=float, default=0.84, help="cell scale toward its own centroid")
    parser.add_argument("--tube", type=float, default=0.03, help="tube radius (edges have length 1)")
    parser.add_argument("--cells", choices=("front", "all"), default="front",
                        help="cells style: only cells facing the 4D eye (no overlap) or all cells")
    parser.add_argument("--out", required=True, help=".gltf model or .json polytope record")
    args = parser.parse_args(argv)
    if args.eye <= 0 or not 0 < args.shrink <= 1 or args.tube <= 0:
        parser.error("eye and tube are positive; shrink is in (0, 1]")
    try:
        summary = export(args.out, args.group, args.rings, args.rotate, args.project, args.eye, args.style,
                         args.shrink, args.tube, args.cells)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
