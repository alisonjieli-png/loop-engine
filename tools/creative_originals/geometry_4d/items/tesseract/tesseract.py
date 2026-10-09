"""Tesseract (8-cell, Schlafli symbol {4,3,3}) built exactly from 4-bit vertex labels.

Vertex k has coordinate (size / 2)(2 b_i - 1) on axis i, where b_i is bit i of k. Two vertices share an edge when
their labels differ in one bit; a square face frees two bits and fixes two; a cubic cell fixes one bit. No distance
search is involved. The module also gives the reflected Gray code Hamiltonian cycle on the 16 vertices and the two
inscribed 16-cells (the labels of even and of odd bit parity), and it writes a rotated, projected tube wireframe
as glTF (coloured by 4D depth) or the polytope as a fourd_polytope/v1 JSON record.

    python tesseract.py --rotate xw=0.6,yz=0.3 --project perspective --out tesseract.gltf
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys

import fourd


def vertices(size=2.0):
    """The 16 vertices; vertex k has coordinate (size/2)(2 b_i - 1) on axis i for the bits b_i of k."""
    half = size / 2.0
    return [tuple(half * (2 * ((label >> axis) & 1) - 1) for axis in range(4)) for label in range(16)]


def polytope(size=2.0):
    """Vertices, edges (labels one bit apart), 24 square faces as cycles and 8 cubic cells as face lists."""
    if size <= 0:
        raise ValueError("size is positive")
    edges = sorted((label, label | (1 << axis)) for label in range(16) for axis in range(4)
                   if not label & (1 << axis))
    faces = []
    for first, second in itertools.combinations(range(4), 2):
        others = [axis for axis in range(4) if axis not in (first, second)]
        for fixed in range(4):
            base = sum(((fixed >> position) & 1) << axis for position, axis in enumerate(others))
            faces.append([base, base | (1 << first), base | (1 << first) | (1 << second), base | (1 << second)])
    cells = []
    for axis in range(4):
        for bit in (0, 1):
            cells.append([index for index, face in enumerate(faces)
                          if all(((label >> axis) & 1) == bit for label in face)])
    return {"vertices": vertices(size), "edges": edges, "faces": faces, "cells": cells}


def gray_cycle():
    """The reflected binary Gray code: a Hamiltonian cycle of vertex labels, one bit flipped per step."""
    return [index ^ (index >> 1) for index in range(16)]


def is_hamiltonian_cycle(cycle, edges):
    """True when the labels visit all 16 vertices once and every step, including the last, is an edge."""
    edge_set = {tuple(sorted(edge)) for edge in edges}
    return (len(cycle) == 16 and len(set(cycle)) == 16
            and all((min(a, b), max(a, b)) in edge_set for a, b in zip(cycle, cycle[1:] + cycle[:1])))


def half_tesseracts():
    """Labels of even and of odd bit parity; each set is the vertex set of an inscribed 16-cell."""
    even = [label for label in range(16) if bin(label).count("1") % 2 == 0]
    odd = [label for label in range(16) if bin(label).count("1") % 2 == 1]
    return even, odd


def is_sixteen_cell(points, tolerance=1e-9):
    """True for 8 points that each have one antipode at 2R and six neighbours at R sqrt(2) (R the circumradius)."""
    if len(points) != 8:
        return False
    middle = fourd.centroid(points)
    radius = fourd.distance(points[0], middle)
    for point in points:
        distances = sorted(fourd.distance(point, other) for other in points if other is not point)
        if any(abs(value - radius * 2 ** 0.5) > tolerance for value in distances[:6]) or \
                abs(distances[6] - 2.0 * radius) > tolerance:
            return False
    return True


def wireframe(size=2.0, rotation="xw=0.6,yz=0.3", projection="perspective", eye=2.5, style="tubes", radius=None,
              sides=8):
    """The rotated tesseract projected to 3D as a tube (or LINES) mesh coloured by rotated w."""
    shape = polytope(size)
    circumradius = size
    radius = 0.035 * size if radius is None else radius
    return fourd.projected_wireframe(shape["vertices"], shape["edges"], fourd.rotation_matrix(rotation), projection,
                                     eye * circumradius, radius, sides, style)


def export(path, size=2.0, rotation="xw=0.6,yz=0.3", projection="perspective", eye=2.5, style="tubes", radius=None,
           sides=8):
    """Write a .gltf wireframe or a .json polytope record; returns a summary."""
    if str(path).endswith(".json"):
        record = fourd.polytope_record(polytope(size), "tesseract")
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(record, stream, indent=1)
            stream.write("\n")
        return {"path": str(path), "f_vector": list(fourd.f_vector(polytope(size)))}
    mesh = wireframe(size, rotation, projection, eye, style, radius, sides)
    document = fourd.gltf_document([dict(mesh, name="tesseract")], generator="tesseract.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    """Computed values the contract declares."""
    shape = polytope()
    report = fourd.regularity_report(shape)
    even, odd = half_tesseracts()
    points = shape["vertices"]
    counts = fourd.f_vector(shape)
    return {"vertices": counts[0], "edges": counts[1], "faces": counts[2], "cells": counts[3],
            "euler_characteristic": fourd.euler_characteristic(shape), "circumradius": report["circumradius"],
            "edge_length": report["edge_length"], "regular": report["regular"],
            "schlafli": list(fourd.schlafli_symbol(shape)), "hypervolume": fourd.hypervolume(shape),
            "surface_volume": sum(fourd.cell_volume(shape, index) for index in range(counts[3])),
            "vertex_degree": report["degrees"][0],
            "gray_cycle_is_hamiltonian": is_hamiltonian_cycle(gray_cycle(), shape["edges"]),
            "inscribed_16cells": [is_sixteen_cell([points[i] for i in even]), is_sixteen_cell([points[i] for i in odd])],
            "edges_match_minimum_distance": fourd.edges_by_length(points) == shape["edges"]}


def controls():
    """Known-wrong inputs and the check that must refuse each."""
    shape = polytope()
    moved = dict(shape, vertices=[fourd.add(shape["vertices"][0], (0.05, 0.0, 0.0, 0.0))] + shape["vertices"][1:])
    swapped = gray_cycle()
    swapped[3], swapped[4] = swapped[4], swapped[3]
    even, odd = half_tesseracts()
    mixed = [shape["vertices"][label] for label in even[:7] + odd[:1]]

    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    return {"moved_vertex_not_regular": not fourd.regularity_report(moved)["regular"],
            "swapped_gray_steps_not_a_cycle": not is_hamiltonian_cycle(swapped, shape["edges"]),
            "mixed_parity_not_a_16cell": not is_sixteen_cell(mixed),
            "unknown_plane_refused": refused(lambda: fourd.rotation_matrix("xq=1")),
            "eye_inside_refused": refused(lambda: wireframe(eye=0.5))}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tesseract.py", description="Write a rotated, projected tesseract.")
    parser.add_argument("--size", type=float, default=2.0, help="edge length (default 2)")
    parser.add_argument("--rotate", default="xw=0.6,yz=0.3",
                        help="plane rotations applied in order, radians or deg, like xw=0.6,yz=30deg")
    parser.add_argument("--project", choices=fourd.PROJECTIONS, default="perspective", help="4D to 3D projection")
    parser.add_argument("--eye", type=float, default=2.5, help="4D eye distance in circumradii (perspective)")
    parser.add_argument("--style", choices=("tubes", "lines"), default="tubes", help="tube mesh or LINES primitive")
    parser.add_argument("--radius", type=float, default=None, help="tube radius (default 0.035 x size)")
    parser.add_argument("--sides", type=int, default=8, help="sides of each tube (3 or more)")
    parser.add_argument("--out", required=True, help=".gltf wireframe or .json polytope record")
    args = parser.parse_args(argv)
    if args.size <= 0 or args.sides < 3 or args.eye <= 0:
        parser.error("size and eye are positive, sides is 3 or more")
    try:
        summary = export(args.out, args.size, args.rotate, args.project, args.eye, args.style, args.radius, args.sides)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
