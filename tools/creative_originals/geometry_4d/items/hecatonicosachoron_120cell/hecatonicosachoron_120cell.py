"""The 120-cell (Schlafli symbol {5,3,3}) from its seven coordinate classes.

With phi the golden ratio, the 600 vertices of circumradius 2 sqrt(2) are all permutations of
(0, 0, +-2, +-2), (+-1, +-1, +-1, +-sqrt5), (+-phi^-2, +-phi, +-phi, +-phi), (+-phi^-1, +-phi^-1, +-phi^-1, +-phi^2)
and the even permutations of (0, +-phi^-2, +-1, +-phi^2), (0, +-phi^-1, +-phi, +-sqrt5), (+-phi^-1, +-1, +-phi, +-2);
they are scaled here to circumradius 1. The 120 dodecahedral cells face the 120 icosians (the vertices of the
dual 600-cell: +-1, +-i, +-j, +-k, (+-1 +-i +-j +-k)/2 and the even permutations of (+-phi, +-1, +-phi^-1, 0)/2).
Faces are the pentagons shared by two cells. Read as quaternions, the vertices are permuted by left
multiplication with icosians; the five orbits are five disjoint inscribed 600-cells. Cells whose centres lie on
one great decagon of the dual form a ring of ten dodecahedra joined face to face.

    python hecatonicosachoron_120cell.py --rotate xw=0.3,yz=0.15 --out 120cell.gltf
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from functools import lru_cache

import fourd

PHI = (1.0 + math.sqrt(5.0)) / 2.0
ROOT5 = math.sqrt(5.0)


def even_permutations():
    """The 12 even permutations of four positions (counted by inversions)."""
    result = []
    for permutation in itertools.permutations(range(4)):
        inversions = sum(1 for a, b in itertools.combinations(permutation, 2) if a > b)
        if inversions % 2 == 0:
            result.append(permutation)
    return result


def _expand(base, permutations):
    points = set()
    for signs in itertools.product((-1.0, 1.0), repeat=4):
        signed = tuple(sign * value for sign, value in zip(signs, base))
        for permutation in permutations:
            points.add(fourd.point_key(tuple(signed[index] for index in permutation), 12))
    return sorted(points)


def coordinate_classes():
    """The seven vertex classes of circumradius 2 sqrt(2), as lists of points."""
    every = list(itertools.permutations(range(4)))
    even = even_permutations()
    bases = [((0.0, 0.0, 2.0, 2.0), every), ((1.0, 1.0, 1.0, ROOT5), every), ((PHI ** -2, PHI, PHI, PHI), every),
             ((1.0 / PHI, 1.0 / PHI, 1.0 / PHI, PHI ** 2), every), ((0.0, PHI ** -2, 1.0, PHI ** 2), even),
             ((0.0, 1.0 / PHI, PHI, ROOT5), even), ((1.0 / PHI, 1.0, PHI, 2.0), even)]
    return [_expand(base, permutations) for base, permutations in bases]


def icosians():
    """The 120 unit icosians as quaternions (a, b, c, d), from their coordinate rule."""
    points = set()
    for axis in range(4):
        for sign in (-1.0, 1.0):
            points.add(fourd.point_key(tuple(sign if index == axis else 0.0 for index in range(4)), 12))
    for signs in itertools.product((-0.5, 0.5), repeat=4):
        points.add(fourd.point_key(signs, 12))
    for point in _expand((PHI / 2.0, 0.5, 0.5 / PHI, 0.0), even_permutations()):
        points.add(point)
    return sorted(points)


@lru_cache(maxsize=1)
def _polytope():
    scale = 1.0 / (2.0 * math.sqrt(2.0))
    points = [fourd.scale(point, scale) for group in coordinate_classes() for point in group]
    return fourd.polytope_from_facets(points, [fourd.quaternion_to_point(q) for q in icosians()])


def polytope():
    """The 120-cell with circumradius 1: 600 vertices, 1200 edges, 720 pentagons, 120 dodecahedra."""
    shape = _polytope()
    return {"vertices": list(shape["vertices"]), "edges": list(shape["edges"]), "faces": list(shape["faces"]),
            "cells": list(shape["cells"])}


def inscribed_600cells():
    """Orbits of the vertices under left multiplication by the icosians: five sets of 120 vertex indices."""
    shape = _polytope()
    index = {fourd.point_key(point, 7): position for position, point in enumerate(shape["vertices"])}
    group = icosians()
    seen, orbits = set(), []
    for position, point in enumerate(shape["vertices"]):
        if position in seen:
            continue
        quaternion = fourd.point_to_quaternion(point)
        members = sorted({index[fourd.point_key(fourd.quaternion_to_point(fourd.quat_mul(g, quaternion)), 7)]
                          for g in group})
        seen.update(members)
        orbits.append(members)
    return orbits


def is_600cell(points, tolerance=1e-7):
    """120 points on one sphere, each with 12 neighbours at the circumradius over phi."""
    if len(points) != 120:
        return False
    radius = fourd.norm(points[0])
    target = radius / PHI
    return all(sum(1 for other in points if abs(fourd.distance(point, other) - target) <= tolerance) == 12
               for point in points)


def cell_ring(start=(1.0, 0.0, 0.0, 0.0)):
    """Ten cells whose centres are g, g q, g q^2, ... for an icosian g and the order-10 icosian q = (phi, 1, 1/phi, 0)/2:
    consecutive points of a great decagon of the dual 600-cell, so consecutive cells share a pentagon. With g = 1
    and g = k the two rings lie in absolutely orthogonal planes and link like a Hopf link."""
    shape = _polytope()
    sets = fourd.cell_vertex_sets(shape)
    centres = [fourd.normalize(fourd.centroid([shape["vertices"][v] for v in members])) for members in sets]
    step = (PHI / 2.0, 0.5, 0.5 / PHI, 0.0)
    current = tuple(start)
    ring = []
    for _ in range(10):
        target = fourd.quaternion_to_point(current)
        ring.append(min(range(len(centres)), key=lambda index: fourd.distance(centres[index], target)))
        current = fourd.quat_mul(current, step)
    return ring


def meshes(rotation="xw=0.3,yz=0.15", projection="perspective", eye=2.2, shrink=0.94, edge_colours="plain"):
    """Two linked rings of ten dodecahedra (warm and cool) and all edges as LINES, plain or coloured by inscribed
    600-cell."""
    shape = _polytope()
    rotated = fourd.rotate_points(fourd.rotation_matrix(rotation), shape["vertices"])
    projected = fourd.project_points(rotated, projection, eye_distance=eye)
    colours = [(0.5, 0.53, 0.62, 1.0)] * len(projected)
    if edge_colours == "orbits":
        for number, orbit in enumerate(inscribed_600cells()):
            for member in orbit:
                colours[member] = fourd.palette(5, 0.45, 0.9)[number]
    warm = [fourd.lerp((0.98, 0.7, 0.25), (0.93, 0.32, 0.36), k / 9.0) + (1.0,) for k in range(10)]
    cool = [fourd.lerp((0.25, 0.6, 0.98), (0.35, 0.92, 0.75), k / 9.0) + (1.0,) for k in range(10)]
    ring = fourd.cell_mesh(projected, shape, shrink, warm + cool,
                           cells=cell_ring() + cell_ring((0.0, 0.0, 0.0, 1.0)))
    lines = fourd.line_mesh(projected, shape["edges"], colours)
    return [dict(ring, name="cell_ring"), dict(lines, name="edges", unlit=True)]


def export(path, rotation="xw=0.3,yz=0.15", projection="perspective", eye=2.2, shrink=0.94, edge_colours="plain"):
    if str(path).endswith(".json"):
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(fourd.polytope_record(polytope(), "120-cell"), stream, indent=1)
            stream.write("\n")
        return {"path": str(path)}
    document = fourd.gltf_document(meshes(rotation, projection, eye, shrink, edge_colours),
                                   generator="hecatonicosachoron_120cell.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    shape = _polytope()
    report = fourd.regularity_report(shape)
    counts = fourd.f_vector(shape)
    orbits = inscribed_600cells()
    ring = cell_ring()
    sets = fourd.cell_vertex_sets(shape)
    adjacent = all(len(sets[a] & sets[b]) == 5 for a, b in zip(ring, ring[1:] + ring[:1]))
    return {"vertices": counts[0], "edges": counts[1], "faces": counts[2], "cells": counts[3],
            "euler_characteristic": fourd.euler_characteristic(shape), "circumradius": report["circumradius"],
            "edge_length": report["edge_length"], "regular": report["regular"],
            "schlafli": list(fourd.schlafli_symbol(shape)),
            "hypervolume_per_edge4": fourd.hypervolume(shape) / report["edge_length"] ** 4,
            "vertex_degree": report["degrees"][0], "coordinate_classes": [len(group) for group in coordinate_classes()],
            "cell_vertices": sorted({len(members) for members in sets}), "icosians": len(icosians()),
            "inscribed_600cells": len(orbits),
            "orbits_are_600cells": all(is_600cell([shape["vertices"][v] for v in orbit]) for orbit in orbits),
            "cell_ring_length": len(set(ring)), "ring_cells_share_pentagons": adjacent,
            "linked_rings_disjoint": not set(ring) & set(cell_ring((0.0, 0.0, 0.0, 1.0)))}


def controls():
    shape = polytope()
    moved = dict(shape, vertices=[fourd.add(shape["vertices"][0], (0.004, 0.0, 0.0, 0.0))] + shape["vertices"][1:])
    orbit = inscribed_600cells()[0]
    mixed = [shape["vertices"][v] for v in orbit[:119] + [inscribed_600cells()[1][0]]]
    odd = [permutation for permutation in itertools.permutations(range(4)) if permutation not in even_permutations()]
    wrong_class = _expand((0.0, PHI ** -2, 1.0, PHI ** 2), odd)
    scale = 1.0 / (2.0 * math.sqrt(2.0))
    true_set = {fourd.point_key(point, 6) for point in shape["vertices"]}
    return {"moved_vertex_not_regular": not fourd.regularity_report(moved)["regular"],
            "mixed_orbit_not_a_600cell": not is_600cell(mixed),
            "odd_permutations_are_not_vertices": not any(fourd.point_key(fourd.scale(point, scale), 6) in true_set
                                                         for point in wrong_class),
            "ring_breaks_when_shuffled": not all(len(fourd.cell_vertex_sets(shape)[a] & fourd.cell_vertex_sets(shape)[b]) == 5
                                                 for a, b in zip(cell_ring()[::2], cell_ring()[1::2][::-1]))}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hecatonicosachoron_120cell.py", description="Write the 120-cell.")
    parser.add_argument("--rotate", default="xw=0.3,yz=0.15", help="plane rotations applied in order")
    parser.add_argument("--project", choices=fourd.PROJECTIONS, default="perspective", help="4D to 3D projection")
    parser.add_argument("--eye", type=float, default=2.2, help="4D eye distance (circumradius is 1)")
    parser.add_argument("--shrink", type=float, default=0.94, help="scale of each ring cell toward its centroid")
    parser.add_argument("--edges", choices=("plain", "orbits"), default="plain",
                        help="edge colours: plain grey, or one colour per inscribed 600-cell")
    parser.add_argument("--out", required=True, help=".gltf model or .json polytope record")
    args = parser.parse_args(argv)
    if args.eye <= 0 or not 0 < args.shrink <= 1:
        parser.error("eye is positive; shrink is in (0, 1]")
    try:
        summary = export(args.out, args.rotate, args.project, args.eye, args.shrink, args.edges)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
