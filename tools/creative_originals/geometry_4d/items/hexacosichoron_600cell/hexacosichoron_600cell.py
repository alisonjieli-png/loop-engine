"""The 600-cell (Schlafli symbol {3,3,5}) as the binary icosahedral group of 120 unit quaternions.

The quaternions s = (1 + i + j + k)/2 (order 6) and t = (phi + i/phi + j)/2 (order 10) satisfy
s^3 = t^5 = (st)^2 = -1, the presentation of the binary icosahedral group 2I; closing {s, t} under
multiplication gives its 120 elements, the vertices of the 600-cell with circumradius 1. Edges join vertices at
distance 1/phi (12 per vertex); faces are the 1200 triangles and cells the 600 tetrahedra of the edge graph,
found as 3- and 4-cliques. Two subgroup structures are exported:

- the cyclic group <t> of order 10 has 12 left cosets g<t>; each is a regular decagon on a great circle and the
  12 circles are fibres of a Hopf fibration (Clifford parallels);
- the binary tetrahedral group 2T (the 24 Hurwitz units) has 5 left cosets, five disjoint inscribed 24-cells.

The glTF holds the 12 decagons as coloured tubes and all 720 edges as LINES.

    python hexacosichoron_600cell.py --rotate xw=0.35,yz=0.2 --out 600cell.gltf
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
S = (0.5, 0.5, 0.5, 0.5)
T = (PHI / 2.0, 1.0 / (2.0 * PHI), 0.5, 0.0)


def closure(generators, limit=200):
    """All products of unit quaternion generators; refused when not unit or when the group exceeds the limit."""
    for generator in generators:
        if abs(fourd.norm(generator) - 1.0) > 1e-9:
            raise ValueError("generators are unit quaternions")
    found = {fourd.point_key((1.0, 0.0, 0.0, 0.0)): (1.0, 0.0, 0.0, 0.0)}
    frontier = list(found.values())
    while frontier:
        fresh = []
        for element in frontier:
            for generator in generators:
                product = fourd.quat_mul(element, generator)
                key = fourd.point_key(product)
                if key not in found:
                    found[key] = product
                    fresh.append(product)
                    if len(found) > limit:
                        raise ValueError(f"the generated group exceeds {limit} elements")
        frontier = fresh
    return [found[key] for key in sorted(found)]


@lru_cache(maxsize=1)
def _icosians():
    return tuple(closure((S, T)))


def icosians():
    """The 120 elements of the binary icosahedral group, as quaternions (a, b, c, d)."""
    return list(_icosians())


def order(element, limit=200):
    """The multiplicative order of a unit quaternion (refused above the limit)."""
    power, count = element, 1
    while fourd.distance(power, (1.0, 0.0, 0.0, 0.0)) > 1e-9:
        power = fourd.quat_mul(power, element)
        count += 1
        if count > limit:
            raise ValueError("order above limit")
    return count


def clique_polytope(points, length):
    """Edges at the given length; faces and cells as the 3- and 4-cliques of the edge graph."""
    edges = fourd.edges_by_length(points, length)
    neighbours = {index: set() for index in range(len(points))}
    for a, b in edges:
        neighbours[a].add(b)
        neighbours[b].add(a)
    faces = sorted((a, b, c) for a, b in edges for c in neighbours[a] & neighbours[b] if c > b)
    face_index = {face: index for index, face in enumerate(faces)}
    cells = []
    for a, b, c in faces:
        for d in sorted(neighbours[a] & neighbours[b] & neighbours[c]):
            if d > c:
                quad = (a, b, c, d)
                cells.append([face_index[triple] for triple in itertools.combinations(quad, 3)])
    return {"vertices": list(points), "edges": edges, "faces": [list(face) for face in faces], "cells": cells}


@lru_cache(maxsize=1)
def _polytope():
    points = [fourd.quaternion_to_point(element) for element in _icosians()]
    return clique_polytope(points, 1.0 / PHI)


def polytope():
    """The 600-cell with circumradius 1 and edge 1/phi."""
    shape = _polytope()
    return {"vertices": list(shape["vertices"]), "edges": list(shape["edges"]), "faces": list(shape["faces"]),
            "cells": list(shape["cells"])}


def left_cosets(subgroup):
    """Left cosets g H of a subgroup H in the 120 icosians, each sorted, in order of first appearance."""
    seen, result = set(), []
    for element in _icosians():
        if fourd.point_key(element) in seen:
            continue
        coset = sorted((fourd.quat_mul(element, member) for member in subgroup), key=fourd.point_key)
        seen.update(fourd.point_key(member) for member in coset)
        result.append(coset)
    return result


def hopf_decagons():
    """The 12 left cosets of <t>, each ordered g, g t, g t^2, ... around its great circle."""
    powers = [(1.0, 0.0, 0.0, 0.0)]
    for _ in range(9):
        powers.append(fourd.quat_mul(powers[-1], T))
    seen, result = set(), []
    for element in _icosians():
        if fourd.point_key(element) in seen:
            continue
        ring = [fourd.quat_mul(element, power) for power in powers]
        seen.update(fourd.point_key(member) for member in ring)
        result.append(ring)
    return result


def is_regular_decagon(ring, tolerance=1e-9):
    """Ten points on one great circle with equal consecutive steps of 36 degrees."""
    if len(ring) != 10:
        return False
    steps = [fourd.angle_between(a, b) for a, b in zip(ring, ring[1:] + ring[:1])]
    plane = fourd.rank([fourd.sub(point, (0.0, 0.0, 0.0, 0.0)) for point in ring], 1e-9)
    return plane == 2 and all(abs(step - math.pi / 5.0) <= tolerance for step in steps)


def hurwitz_subgroup():
    """The 24 icosians with all coordinates in {0, +-1/2, +-1}: the binary tetrahedral group 2T."""
    return [element for element in _icosians() if all(min(abs(abs(v) - 0.5), abs(v), abs(abs(v) - 1.0)) < 1e-9
                                                      for v in element)]


def is_24cell(points, tolerance=1e-9):
    """24 points on the unit sphere, each with exactly 8 neighbours at distance 1."""
    if len(points) != 24 or any(abs(fourd.norm(point) - 1.0) > tolerance for point in points):
        return False
    return all(sum(1 for other in points if abs(fourd.distance(point, other) - 1.0) <= tolerance) == 8
               for point in points)


def meshes(rotation="xw=0.35,yz=0.2", projection="perspective", eye=2.4, radius=0.012, sides=6):
    """Two meshes: the 12 Hopf decagons as coloured tubes, every edge as grey LINES."""
    matrix = fourd.rotation_matrix(rotation)
    shape = _polytope()
    projected = fourd.project_points(fourd.rotate_points(matrix, shape["vertices"]), projection, eye_distance=eye)
    index = {fourd.point_key(point): position for position, point in enumerate(shape["vertices"])}
    colours = [None] * len(projected)
    ring_edges = []
    for ring_number, ring in enumerate(hopf_decagons()):
        members = [index[fourd.point_key(fourd.quaternion_to_point(element))] for element in ring]
        for member in members:
            colours[member] = fourd.palette(12)[ring_number]
        ring_edges += list(zip(members, members[1:] + members[:1]))
    tubes = fourd.wireframe_mesh(projected, ring_edges, radius, radius * 1.6, sides, colours)
    lines = fourd.line_mesh(projected, shape["edges"], [(0.62, 0.64, 0.7, 1.0)] * len(projected))
    return [dict(tubes, name="hopf_decagons"), dict(lines, name="edges", unlit=True)]


def export(path, rotation="xw=0.35,yz=0.2", projection="perspective", eye=2.4, radius=0.012, sides=6):
    if str(path).endswith(".json"):
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(fourd.polytope_record(polytope(), "600-cell"), stream, indent=1)
            stream.write("\n")
        return {"path": str(path)}
    document = fourd.gltf_document(meshes(rotation, projection, eye, radius, sides), generator="hexacosichoron_600cell.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    shape = _polytope()
    report = fourd.regularity_report(shape)
    counts = fourd.f_vector(shape)
    rings = hopf_decagons()
    tetrahedral = hurwitz_subgroup()
    cosets = left_cosets(tetrahedral)
    group = _icosians()
    keys = {fourd.point_key(element) for element in group}
    closed = all(fourd.point_key(fourd.quat_mul(a, b)) in keys for a in group for b in group)
    return {"vertices": counts[0], "edges": counts[1], "faces": counts[2], "cells": counts[3],
            "euler_characteristic": fourd.euler_characteristic(shape), "circumradius": report["circumradius"],
            "edge_length": report["edge_length"], "regular": report["regular"],
            "schlafli": list(fourd.schlafli_symbol(shape)), "hypervolume": fourd.hypervolume(shape),
            "vertex_degree": report["degrees"][0], "group_order": len(group), "group_closed": closed,
            "generator_orders": [order(S), order(T), order(fourd.quat_mul(S, T))],
            "hopf_decagons": len(rings), "decagons_regular": all(is_regular_decagon(ring) for ring in rings),
            "decagon_edges_are_edges": all(abs(fourd.distance(a, b) - 1.0 / PHI) < 1e-9
                                           for ring in rings for a, b in zip(ring, ring[1:] + ring[:1])),
            "inscribed_24cells": len(cosets),
            "cosets_are_24cells": all(is_24cell([fourd.quaternion_to_point(e) for e in coset]) for coset in cosets)}


def controls():
    shape = polytope()
    moved = dict(shape, vertices=[fourd.add(shape["vertices"][0], (0.01, 0.0, 0.0, 0.0))] + shape["vertices"][1:])
    trimmed = clique_polytope(shape["vertices"], 1.0 / PHI)
    trimmed_edges = trimmed["edges"][1:]
    neighbours = {index: set() for index in range(120)}
    for a, b in trimmed_edges:
        neighbours[a].add(b)
        neighbours[b].add(a)
    cliques = sum(1 for a, b, c in (tuple(face) for face in trimmed["faces"])
                  if b in neighbours[a] and c in neighbours[a] and c in neighbours[b]
                  for d in neighbours[a] & neighbours[b] & neighbours[c] if d > c)
    ring = hopf_decagons()[0]
    broken = ring[:9] + [hopf_decagons()[1][0]]
    root2 = 2 ** -0.5

    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    return {"moved_vertex_not_regular": not fourd.regularity_report(moved)["regular"],
            "missing_edge_loses_five_cells": cliques == 595,
            "swapped_ring_member_not_decagon": not is_regular_decagon(broken),
            "extra_generator_refused": refused(lambda: closure((S, T, (root2, root2, 0.0, 0.0))))}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hexacosichoron_600cell.py",
                                     description="Write the 600-cell built from the binary icosahedral group.")
    parser.add_argument("--rotate", default="xw=0.35,yz=0.2", help="plane rotations applied in order")
    parser.add_argument("--project", choices=fourd.PROJECTIONS, default="perspective", help="4D to 3D projection")
    parser.add_argument("--eye", type=float, default=2.4, help="4D eye distance (circumradius is 1)")
    parser.add_argument("--radius", type=float, default=0.012, help="radius of the Hopf decagon tubes")
    parser.add_argument("--sides", type=int, default=6, help="sides of each tube (3 or more)")
    parser.add_argument("--out", required=True, help=".gltf model or .json polytope record")
    args = parser.parse_args(argv)
    if args.eye <= 0 or args.radius <= 0 or args.sides < 3:
        parser.error("eye and radius are positive; sides is 3 or more")
    try:
        summary = export(args.out, args.rotate, args.project, args.eye, args.radius, args.sides)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
