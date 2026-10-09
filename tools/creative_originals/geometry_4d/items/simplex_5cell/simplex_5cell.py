"""The 5-cell (regular 4-simplex, Schlafli symbol {3,3,3}) from the standard simplex of R^5.

The five unit vectors e_1..e_5 of R^5 are the vertices of a regular simplex in the hyperplane x_1 + ... + x_5 = 1.
The Helmert vectors h_k = (1, ..., 1, -k, 0, ...)/sqrt(k(k+1)), k = 1..4, are an orthonormal basis of the
hyperplane through the origin, so the coordinates (e_i . h_1, ..., e_i . h_4) place the simplex in R^4 with its
centroid at the origin. Every pair of vertices is an edge, every triple a face and every quadruple a cell; the
combinatorics need no search. The module also converts points to barycentric coordinates (inside means all five
are non-negative), samples uniform points inside, checks the full permutation symmetry, and writes a wireframe or
an exploded-cell glTF.

    python simplex_5cell.py --style cells --rotate xw=3.0,yz=0.4 --out 5cell.gltf
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import sys

import fourd


def helmert_basis():
    """The four orthonormal Helmert vectors of R^5 spanning the hyperplane where the coordinates sum to zero."""
    basis = []
    for k in range(1, 5):
        scale = 1.0 / math.sqrt(k * (k + 1))
        basis.append(tuple([scale] * k + [-k * scale] + [0.0] * (4 - k)))
    return basis


def vertices(edge=1.0):
    """The five vertices in R^4, centroid at the origin, all edges of the given length."""
    if edge <= 0:
        raise ValueError("edge is positive")
    factor = edge / math.sqrt(2.0)
    basis = helmert_basis()
    return [tuple(factor * axis[index] for axis in basis) for index in range(5)]


def polytope(edge=1.0):
    """All 10 pairs as edges, all 10 triples as faces, the 5 quadruples as cells."""
    faces = [list(triple) for triple in itertools.combinations(range(5), 3)]
    cells = []
    for quadruple in itertools.combinations(range(5), 4):
        cells.append([index for index, face in enumerate(faces) if set(face) <= set(quadruple)])
    return {"vertices": vertices(edge), "edges": list(itertools.combinations(range(5), 2)), "faces": faces,
            "cells": cells}


def barycentric(point, edge=1.0):
    """Five weights w with sum 1 and point = sum w_i v_i (solved through the affine map of the simplex)."""
    corners = vertices(edge)
    columns = [fourd.sub(corner, corners[4]) for corner in corners[:4]]
    first = fourd.solve(fourd.transpose(columns), fourd.sub(point, corners[4]))
    return tuple(first) + (1.0 - sum(first),)


def contains(point, edge=1.0, tolerance=1e-12):
    """True when every barycentric weight is non-negative."""
    return all(weight >= -tolerance for weight in barycentric(point, edge))


def sample_points(count, seed=1, edge=1.0):
    """Uniform random points inside: weights are the gaps between sorted uniform numbers (Dirichlet(1,...,1))."""
    generator = random.Random(seed)
    corners = vertices(edge)
    points = []
    for _ in range(count):
        cuts = sorted(generator.random() for _ in range(4))
        weights = [b - a for a, b in zip([0.0] + cuts, cuts + [1.0])]
        points.append(tuple(sum(weight * corner[axis] for weight, corner in zip(weights, corners)) for axis in range(4)))
    return points


def symmetry_count(edge=1.0, tolerance=1e-9):
    """How many of the 120 vertex permutations preserve every pairwise distance (all of them, for a regular simplex)."""
    corners = vertices(edge)
    distances = {(a, b): fourd.distance(corners[a], corners[b]) for a in range(5) for b in range(5)}
    return sum(1 for permutation in itertools.permutations(range(5))
               if all(abs(distances[(a, b)] - distances[(permutation[a], permutation[b])]) <= tolerance
                      for a in range(5) for b in range(5)))


def dihedral_angle(edge=1.0):
    """Angle between two adjacent cells (pi minus the angle between their outward normals)."""
    corners = vertices(edge)
    normals = [fourd.normalize(fourd.scale(corner, -1.0)) for corner in corners]
    return math.pi - fourd.angle_between(normals[0], normals[1])


def mesh(edge=1.0, rotation="xw=3.0,yz=0.4", projection="perspective", eye=3.0, style="cells", radius=None, shrink=0.62,
         cells="front"):
    """A projected wireframe (tubes or lines) or exploded cells (those facing the 4D eye, or all), one colour each."""
    shape = polytope(edge)
    rotated = fourd.rotate_points(fourd.rotation_matrix(rotation), shape["vertices"])
    circumradius = fourd.norm(shape["vertices"][0])
    projected = fourd.project_points(rotated, projection, eye_distance=eye * circumradius)
    colours = fourd.palette(5)
    if style == "cells":
        chosen = fourd.facing_cells(shape, rotated, projection, eye * circumradius) if cells == "front" \
            else list(range(5))
        return fourd.cell_mesh(projected, shape, shrink, [colours[index] for index in chosen], cells=chosen)
    if style == "lines":
        return fourd.line_mesh(projected, shape["edges"], colours)
    if style == "tubes":
        return fourd.wireframe_mesh(projected, shape["edges"], 0.03 * edge if radius is None else radius, None, 8,
                                    colours)
    raise ValueError("style is cells, tubes or lines")


def export(path, edge=1.0, rotation="xw=3.0,yz=0.4", projection="perspective", eye=3.0, style="cells", radius=None,
           shrink=0.62, cells="front"):
    """Write the glTF (or the polytope record for a .json path)."""
    if str(path).endswith(".json"):
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(fourd.polytope_record(polytope(edge), "5-cell"), stream, indent=1)
            stream.write("\n")
        return {"path": str(path)}
    document = fourd.gltf_document([dict(mesh(edge, rotation, projection, eye, style, radius, shrink, cells),
                                         name="5cell")],
                                   generator="simplex_5cell.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    shape = polytope()
    report = fourd.regularity_report(shape)
    counts = fourd.f_vector(shape)
    basis = helmert_basis()
    orthonormal = all(abs(fourd.dot(a, b) - (1.0 if i == j else 0.0)) < 1e-12
                      for i, a in enumerate(basis) for j, b in enumerate(basis))
    samples = sample_points(200)
    return {"vertices": counts[0], "edges": counts[1], "faces": counts[2], "cells": counts[3],
            "euler_characteristic": fourd.euler_characteristic(shape), "circumradius": report["circumradius"],
            "edge_length": report["edge_length"], "regular": report["regular"],
            "schlafli": list(fourd.schlafli_symbol(shape)), "hypervolume": fourd.hypervolume(shape),
            "helmert_orthonormal": orthonormal, "symmetry_order": symmetry_count(),
            "dihedral_angle_degrees": math.degrees(dihedral_angle()),
            "samples_inside": all(contains(point) for point in samples),
            "centroid_weights": [round(weight, 12) for weight in barycentric((0.0, 0.0, 0.0, 0.0))]}


def controls():
    shape = polytope()
    moved = dict(shape, vertices=[fourd.add(shape["vertices"][0], (0.02, 0.0, 0.0, 0.0))] + shape["vertices"][1:])
    outside = fourd.scale(shape["vertices"][0], 1.2)

    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    return {"moved_vertex_not_regular": not fourd.regularity_report(moved)["regular"],
            "outside_point_not_contained": not contains(outside),
            "zero_edge_refused": refused(lambda: vertices(0.0)),
            "unknown_style_refused": refused(lambda: mesh(style="ribbons"))}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="simplex_5cell.py", description="Write the regular 5-cell.")
    parser.add_argument("--edge", type=float, default=1.0, help="edge length")
    parser.add_argument("--rotate", default="xw=3.0,yz=0.4", help="plane rotations applied in order")
    parser.add_argument("--project", choices=fourd.PROJECTIONS, default="perspective", help="4D to 3D projection")
    parser.add_argument("--eye", type=float, default=3.0, help="4D eye distance in circumradii")
    parser.add_argument("--style", choices=("cells", "tubes", "lines"), default="cells",
                        help="exploded cells, tube wireframe or LINES")
    parser.add_argument("--radius", type=float, default=None, help="tube radius (default 0.03 x edge)")
    parser.add_argument("--shrink", type=float, default=0.62, help="cell scale toward its centroid (cells style)")
    parser.add_argument("--cells", choices=("front", "all"), default="front",
                        help="cells style: only cells facing the 4D eye (no overlap) or all cells")
    parser.add_argument("--out", required=True, help=".gltf model or .json polytope record")
    args = parser.parse_args(argv)
    if args.edge <= 0 or args.eye <= 0 or not 0 < args.shrink <= 1:
        parser.error("edge and eye are positive; shrink is in (0, 1]")
    try:
        summary = export(args.out, args.edge, args.rotate, args.project, args.eye, args.style, args.radius, args.shrink,
                         args.cells)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
