"""Duoprisms {p}x{q}: the product of a p-gon in the xy plane and a q-gon in the zw plane.

Vertex (i, j) is (r1 cos 2 pi i/p, r1 sin 2 pi i/p, r2 cos 2 pi j/q, r2 sin 2 pi j/q). Edges step i or j by one,
squares step both, and the p q-gons {(i, j) : j} and q p-gons {(i, j) : i} complete the faces. The cells form
two rings: p q-gonal prisms between consecutive q-gons, and q p-gonal prisms between consecutive p-gons. The counts
are V = pq, E = 2pq, F = pq + p + q, C = p + q, so V - E + F - C = 0 for every p and q. With the uniform radii
r = 1/(2 sin(pi/n)) every edge has length 1; the hypervolume is the product of the two polygon areas. The {4}x{4}
duoprism turned 45 degrees in the xy and zw planes is the tesseract of edge 1.

    python duoprism.py --p 5 --q 7 --style cells --out duoprism_5_7.gltf
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys

import fourd


def radii(p, q, uniform=True):
    """Polygon radii: unit edges when uniform, otherwise both 1."""
    if p < 3 or q < 3:
        raise ValueError("p and q are 3 or more")
    if uniform:
        return 1.0 / (2.0 * math.sin(math.pi / p)), 1.0 / (2.0 * math.sin(math.pi / q))
    return 1.0, 1.0


def polytope(p=5, q=7, uniform=True):
    """The {p}x{q} duoprism; vertex (i, j) has index i*q + j. Cells: p q-gonal prisms then q p-gonal prisms."""
    r1, r2 = radii(p, q, uniform)
    index = lambda i, j: (i % p) * q + (j % q)
    points = [(r1 * math.cos(2 * math.pi * i / p), r1 * math.sin(2 * math.pi * i / p),
               r2 * math.cos(2 * math.pi * j / q), r2 * math.sin(2 * math.pi * j / q)) for i in range(p) for j in range(q)]
    edges = sorted({tuple(sorted((index(i, j), index(i + 1, j)))) for i in range(p) for j in range(q)}
                   | {tuple(sorted((index(i, j), index(i, j + 1)))) for i in range(p) for j in range(q)})
    squares = [[index(i, j), index(i + 1, j), index(i + 1, j + 1), index(i, j + 1)] for i in range(p) for j in range(q)]
    q_gons = [[index(i, j) for j in range(q)] for i in range(p)]
    p_gons = [[index(i, j) for i in range(p)] for j in range(q)]
    faces = squares + q_gons + p_gons
    square_at = lambda i, j: (i % p) * q + (j % q)
    q_offset, p_offset = p * q, p * q + p
    cells = [[q_offset + i, q_offset + (i + 1) % p] + [square_at(i, j) for j in range(q)] for i in range(p)]
    cells += [[p_offset + j, p_offset + (j + 1) % q] + [square_at(i, j) for i in range(p)] for j in range(q)]
    return {"vertices": points, "edges": edges, "faces": faces, "cells": cells}


def polygon_area(n, radius):
    """Area of the regular n-gon of circumradius radius."""
    return 0.5 * n * radius * radius * math.sin(2.0 * math.pi / n)


def expected_counts(p, q):
    """(V, E, F, C) = (pq, 2pq, pq + p + q, p + q)."""
    return (p * q, 2 * p * q, p * q + p + q, p + q)


def is_uniform(shape, tolerance=1e-9):
    """True when every edge has the same length."""
    lengths = [fourd.distance(shape["vertices"][a], shape["vertices"][b]) for a, b in shape["edges"]]
    return max(lengths) - min(lengths) <= tolerance


def tesseract_check():
    """The uniform {4}x{4} turned 45 degrees in xy and zw equals the vertex set {+-1/2}^4."""
    shape = polytope(4, 4, True)
    turned = fourd.rotate_points(fourd.rotation_matrix("xy=45deg,zw=45deg"), shape["vertices"])
    target = {fourd.point_key(point) for point in itertools.product((-0.5, 0.5), repeat=4)}
    return {fourd.point_key(point) for point in turned} == target


def mesh(p=5, q=7, uniform=True, rotation="xw=0.5,yz=0.3", projection="perspective", eye=2.6, style="cells",
         shrink=0.86, tube=0.025, cells="front"):
    """Exploded prisms facing the 4D eye (or all; q-gonal ring warm, p-gonal ring cool), tubes or LINES."""
    shape = polytope(p, q, uniform)
    rotated = fourd.rotate_points(fourd.rotation_matrix(rotation), shape["vertices"])
    reach = max(fourd.norm(point) for point in shape["vertices"])
    projected = fourd.project_points(rotated, projection, eye_distance=eye * reach)
    if style == "cells":
        warm = [fourd.lerp((0.98, 0.62, 0.22), (0.92, 0.3, 0.42), i / max(1, p - 1)) + (1.0,) for i in range(p)]
        cool = [fourd.lerp((0.2, 0.55, 0.98), (0.3, 0.9, 0.7), j / max(1, q - 1)) + (1.0,) for j in range(q)]
        chosen = fourd.facing_cells(shape, rotated, projection, eye * reach) if cells == "front" \
            else list(range(p + q))
        return fourd.cell_mesh(projected, shape, shrink, [(warm + cool)[index] for index in chosen], cells=chosen)
    colours = fourd.depth_colors([point[3] for point in rotated])
    if style == "lines":
        return fourd.line_mesh(projected, shape["edges"], colours)
    if style == "tubes":
        return fourd.wireframe_mesh(projected, shape["edges"], tube * reach, None, 8, colours)
    raise ValueError("style is cells, tubes or lines")


def export(path, p=5, q=7, uniform=True, rotation="xw=0.5,yz=0.3", projection="perspective", eye=2.6, style="cells",
           shrink=0.86, tube=0.025, cells="front"):
    if str(path).endswith(".json"):
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(fourd.polytope_record(polytope(p, q, uniform), f"duoprism {p}x{q}"), stream, indent=1)
            stream.write("\n")
        return {"path": str(path)}
    document = fourd.gltf_document([dict(mesh(p, q, uniform, rotation, projection, eye, style, shrink, tube, cells),
                                         name=f"duoprism_{p}_{q}")], generator="duoprism.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    pairs = [(3, 3), (4, 4), (5, 7), (3, 8), (6, 10)]
    shapes = {f"{p}x{q}": polytope(p, q) for p, q in pairs}
    five_seven = shapes["5x7"]
    r1, r2 = radii(3, 3)
    return {"f_vectors": {name: list(fourd.f_vector(shape)) for name, shape in shapes.items()},
            "formula_matches": all(fourd.f_vector(polytope(p, q)) == expected_counts(p, q)
                                   for p in range(3, 9) for q in range(3, 9)),
            "euler_characteristics": sorted({fourd.euler_characteristic(shape) for shape in shapes.values()}),
            "structure_problems": sum(len(fourd.polytope_problems(shape)) for shape in shapes.values()),
            "hypervolume_3x3": fourd.hypervolume(shapes["3x3"]),
            "hypervolume_3x3_formula": polygon_area(3, r1) * polygon_area(3, r2),
            "hypervolume_4x4": fourd.hypervolume(shapes["4x4"]),
            "uniform_5x7": is_uniform(five_seven), "edge_length_5x7": fourd.distance(*[five_seven["vertices"][v]
                                                                                       for v in five_seven["edges"][0]]),
            "prism_rings_5x7": [sum(1 for cell in five_seven["cells"] if len(cell) == 9),
                                sum(1 for cell in five_seven["cells"] if len(cell) == 7)],
            "pq44_is_tesseract": tesseract_check()}


def controls():
    shape = polytope(5, 7)
    moved = dict(shape, vertices=[fourd.add(shape["vertices"][0], (0.02, 0.0, 0.0, 0.0))] + shape["vertices"][1:])

    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    return {"digon_refused": refused(lambda: polytope(2, 5)),
            "equal_radii_not_uniform": not is_uniform(polytope(3, 8, uniform=False)),
            "moved_vertex_not_uniform": not is_uniform(moved),
            "dropped_square_detected": bool(fourd.polytope_problems(dict(shape, faces=shape["faces"][1:]))),
            "dropped_cell_breaks_euler": fourd.euler_characteristic(dict(shape, cells=shape["cells"][1:])) != 0}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="duoprism.py", description="Write a {p}x{q} duoprism.")
    parser.add_argument("--p", type=int, default=5, help="sides of the polygon in the xy plane (3 or more)")
    parser.add_argument("--q", type=int, default=7, help="sides of the polygon in the zw plane (3 or more)")
    parser.add_argument("--radii", choices=("uniform", "equal"), default="uniform",
                        help="uniform: unit edges; equal: both radii 1 (vertices on a Clifford torus)")
    parser.add_argument("--rotate", default="xw=0.5,yz=0.3", help="plane rotations applied in order")
    parser.add_argument("--project", choices=fourd.PROJECTIONS, default="perspective", help="4D to 3D projection")
    parser.add_argument("--eye", type=float, default=2.6, help="4D eye distance in circumradii")
    parser.add_argument("--style", choices=("cells", "tubes", "lines"), default="cells", help="output style")
    parser.add_argument("--shrink", type=float, default=0.86, help="cell scale toward its own centroid")
    parser.add_argument("--tube", type=float, default=0.025, help="tube radius in circumradii")
    parser.add_argument("--cells", choices=("front", "all"), default="front",
                        help="cells style: only prisms facing the 4D eye (no overlap) or all prisms")
    parser.add_argument("--out", required=True, help=".gltf model or .json polytope record")
    args = parser.parse_args(argv)
    if args.p < 3 or args.q < 3 or args.p * args.q > 4096 or args.eye <= 0 or not 0 < args.shrink <= 1:
        parser.error("p and q are 3 or more with p*q at most 4096; eye is positive; shrink is in (0, 1]")
    try:
        summary = export(args.out, args.p, args.q, args.radii == "uniform", args.rotate, args.project, args.eye,
                         args.style, args.shrink, args.tube, args.cells)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
