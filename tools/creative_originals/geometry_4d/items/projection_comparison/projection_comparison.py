"""Perspective, stereographic and orthographic projections of one 4D object, side by side, with their properties.

- Perspective (eye at (0, 0, 0, d), image on w = 0) maps straight lines to straight lines; parallels converge.
- Stereographic (from the pole of the circumscribed 3-sphere) is conformal and maps circles on the sphere to
  circles or lines. Edges are drawn as their great-circle arcs (the chord pushed out to the sphere), whose images
  are circular arcs. Tangent angles are compared exactly through the derivative of the map,
  dS(v) = R/(R - w) (v_xyz + v_w/(R - w) p_xyz).
- Orthographic (drop w) is linear: it keeps parallel edges parallel and changes lengths and angles.

The CLI writes all three wireframes in one glTF (left to right: perspective, stereographic, orthographic), from a
built-in polytope or a fourd_polytope/v1 JSON record.

    python projection_comparison.py --polytope tesseract --rotate xw=0.5,yz=0.35,zw=0.2 --out comparison.gltf
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys

import fourd

POLYTOPES = ("tesseract", "16cell", "24cell", "5cell")
ORDER = ("perspective", "stereographic", "orthographic")


def make_polytope(name):
    """One of POLYTOPES with circumradius-scaled coordinates (vertices and facet normals)."""
    signs = [tuple(point) for point in itertools.product((-1.0, 1.0), repeat=4)]
    axes = [tuple(sign if axis == index else 0.0 for axis in range(4)) for index in range(4) for sign in (-1.0, 1.0)]
    if name == "tesseract":
        return fourd.polytope_from_facets(signs, axes)
    if name == "16cell":
        return fourd.polytope_from_facets(axes, signs)
    if name == "24cell":
        points = []
        for first, second in itertools.combinations(range(4), 2):
            for a, b in itertools.product((-1.0, 1.0), repeat=2):
                vector = [0.0] * 4
                vector[first], vector[second] = a, b
                points.append(tuple(vector))
        return fourd.polytope_from_facets(points, axes + signs)
    if name == "5cell":
        root5 = math.sqrt(5.0)
        points = [(1.0, 1.0, 1.0, -1.0 / root5), (1.0, -1.0, -1.0, -1.0 / root5), (-1.0, 1.0, -1.0, -1.0 / root5),
                  (-1.0, -1.0, 1.0, -1.0 / root5), (0.0, 0.0, 0.0, 4.0 / root5)]
        return fourd.polytope_from_facets(points, [fourd.scale(point, -1.0) for point in points])
    raise ValueError(f"polytope is one of {POLYTOPES}")


def load_polytope(source):
    """A built-in name or the path of a fourd_polytope/v1 JSON record."""
    if source in POLYTOPES:
        return make_polytope(source)
    with open(source, "r", encoding="utf-8") as stream:
        return fourd.polytope_from_record(json.load(stream))


def arc(a, b, radius, segments):
    """Points along the great-circle arc from a to b on the sphere of the given radius (the radial image of the chord)."""
    return [fourd.scale(fourd.normalize(fourd.lerp(a, b, k / segments)), radius) for k in range(segments + 1)]


def stereographic_derivative(point, direction, radius):
    """The image of a tangent direction under stereographic projection from (0, 0, 0, R)."""
    depth = radius - point[3]
    factor = radius / depth
    return tuple(factor * (direction[axis] + direction[3] / depth * point[axis]) for axis in range(3))


def tangent_on_sphere(point, other):
    """Unit tangent at `point` of the great circle toward `other`."""
    unit = fourd.normalize(point)
    toward = fourd.sub(other, fourd.scale(unit, fourd.dot(other, unit)))
    return fourd.normalize(toward)


def angle_errors(vertices, edges, radius):
    """Largest |3D angle - 4D angle| between incident edge tangents, per projection (stereographic tangents are
    great-circle tangents mapped by the derivative; the others use the straight chords)."""
    neighbours = {index: [] for index in range(len(vertices))}
    for a, b in edges:
        neighbours[a].append(b)
        neighbours[b].append(a)
    worst = {name: 0.0 for name in ORDER}
    for vertex, around in neighbours.items():
        p = vertices[vertex]
        for a, b in itertools.combinations(around, 2):
            ta, tb = tangent_on_sphere(p, vertices[a]), tangent_on_sphere(p, vertices[b])
            true_sphere = fourd.angle_between(ta, tb)
            image = fourd.angle_between(stereographic_derivative(p, ta, radius), stereographic_derivative(p, tb, radius))
            worst["stereographic"] = max(worst["stereographic"], abs(image - true_sphere))
            chord = fourd.angle_between(fourd.sub(vertices[a], p), fourd.sub(vertices[b], p))
            for name in ("perspective", "orthographic"):
                images = fourd.project_points([p, vertices[a], vertices[b]], name, eye_distance=2.5 * radius)
                flat = fourd.angle_between(fourd.sub(images[1], images[0]), fourd.sub(images[2], images[0]))
                worst[name] = max(worst[name], abs(flat - chord))
    return worst


def is_concyclic(points, tolerance=1e-9):
    """True when 3D points lie on one circle (coplanar and equidistant from the circumcentre of the first three)."""
    a, b, c = points[:3]
    ab, ac = fourd.sub(b, a), fourd.sub(c, a)
    normal = fourd.cross3(ab, ac)
    if fourd.norm(normal) < 1e-12:
        return False
    centre = fourd.add(a, fourd.scale(fourd.add(fourd.scale(fourd.cross3(normal, ab), fourd.dot(ac, ac)),
                                                fourd.scale(fourd.cross3(ac, normal), fourd.dot(ab, ab))),
                                      1.0 / (2.0 * fourd.dot(normal, normal))))
    radius = fourd.distance(centre, a)
    unit = fourd.normalize(normal)
    return all(abs(fourd.dot(fourd.sub(point, a), unit)) <= tolerance * max(1.0, radius)
               and abs(fourd.distance(point, centre) - radius) <= tolerance * max(1.0, radius) for point in points)


def meshes(shape, rotation="xw=0.5,yz=0.35,zw=0.2", eye=2.5, gap=2.6, radius=0.035, sides=5, segments=6):
    """Three tube wireframes: perspective, stereographic (great-circle arcs), orthographic, placed along x. Each view
    is scaled so its farthest vertex sits at the circumradius, so the three shapes compare at one size."""
    rotated = fourd.rotate_points(fourd.rotation_matrix(rotation), shape["vertices"])
    reach = max(fourd.norm(point) for point in rotated)
    colours = fourd.depth_colors([point[3] for point in rotated])
    result = []
    for position, name in enumerate(ORDER):
        if name == "stereographic":
            images = [fourd.stereographic(point, reach) for point in rotated]
            factor = reach / max(fourd.norm(point) for point in images)
            points, edges, point_colours = [], [], []
            for a, b in shape["edges"]:
                start = len(points)
                for k, point in enumerate(arc(rotated[a], rotated[b], reach, segments)):
                    points.append(fourd.scale(fourd.stereographic(point, reach), factor))
                    point_colours.append(fourd.lerp(colours[a], colours[b], k / segments))
                edges += [(start + k, start + k + 1) for k in range(segments)]
            tubes = fourd.tube_mesh(points, edges, radius * reach, sides, point_colours)
            joints = [fourd.sphere_mesh(fourd.scale(image, factor), radius * reach * 1.8, colours[index])
                      for index, image in enumerate(images)]
            mesh = fourd.merge_meshes([tubes] + joints)
        else:
            projected = fourd.project_points(rotated, name, eye_distance=eye * reach)
            factor = reach / max(fourd.norm(point) for point in projected)
            projected = [fourd.scale(point, factor) for point in projected]
            mesh = fourd.wireframe_mesh(projected, shape["edges"], radius * reach, None, sides, colours)
        result.append(dict(mesh, name=name, translation=((position - 1) * gap * reach, 0.0, 0.0)))
    return result


def export(path, source="tesseract", rotation="xw=0.5,yz=0.35,zw=0.2", eye=2.5, gap=2.6, radius=0.035, sides=5,
           segments=6):
    shape = load_polytope(source)
    document = fourd.gltf_document(meshes(shape, rotation, eye, gap, radius, sides, segments),
                                   generator="projection_comparison.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    shape = make_polytope("tesseract")
    rotated = fourd.rotate_points(fourd.rotation_matrix("xw=0.5,yz=0.35,zw=0.2"), shape["vertices"])
    reach = max(fourd.norm(point) for point in rotated)
    errors = angle_errors(rotated, shape["edges"], reach)
    a, b = rotated[shape["edges"][0][0]], rotated[shape["edges"][0][1]]
    middle = fourd.lerp(a, b, 0.37)
    pa, pb, pm = fourd.project_points([a, b, middle], "perspective", eye_distance=2.5 * reach)
    collinear = fourd.norm(fourd.cross3(fourd.sub(pb, pa), fourd.sub(pm, pa))) < 1e-12
    circle = [fourd.stereographic(point, reach) for point in arc(a, b, reach, 5)]
    directions = {}
    for first, second in shape["edges"]:
        key = tuple(round(abs(v), 6) for v in fourd.sub(shape["vertices"][second], shape["vertices"][first]))
        directions.setdefault(key, []).append((first, second))

    def parallel(name):
        images = fourd.project_points(rotated, name, eye_distance=2.5 * reach)
        for group in directions.values():
            reference = fourd.sub(images[group[0][1]], images[group[0][0]])
            for first, second in group[1:]:
                if fourd.norm(fourd.cross3(reference, fourd.sub(images[second], images[first]))) > 1e-9:
                    return False
        return True

    plain = make_polytope("tesseract")
    flat = fourd.project_points(plain["vertices"], "orthographic")
    lengths = sorted({round(fourd.distance(flat[a], flat[b]), 12) for a, b in plain["edges"]})
    return {"stereographic_conformal": errors["stereographic"] < 1e-9,
            "perspective_conformal": errors["perspective"] < 1e-9,
            "orthographic_conformal": errors["orthographic"] < 1e-9,
            "perspective_keeps_lines": collinear, "stereographic_arcs_are_circles": is_concyclic(circle),
            "orthographic_keeps_parallels": parallel("orthographic"),
            "perspective_keeps_parallels": parallel("perspective"),
            "axis_tesseract_orthographic_edge_lengths": lengths}


def controls():
    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    shape = make_polytope("tesseract")
    straight = [fourd.stereographic(fourd.lerp((2.0, 0.0, 0.0, 0.0), (0.0, 2.0, 0.0, 0.0), k / 5.0), 2.0) for k in range(6)]
    return {"chord_points_not_concyclic_with_far_point": not is_concyclic(straight[:5] + [(9.0, 9.0, 9.0)]),
            "unknown_polytope_refused": refused(lambda: make_polytope("7cell")),
            "pole_point_refused": refused(lambda: fourd.stereographic((0.0, 0.0, 0.0, 2.0), 2.0)),
            "eye_inside_refused": refused(lambda: meshes(shape, eye=0.5)),
            "broken_record_refused": refused(lambda: fourd.polytope_from_record({"record_type": "x"}))}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="projection_comparison.py",
                                     description="Write one 4D object in perspective, stereographic and orthographic view.")
    parser.add_argument("--polytope", default="tesseract",
                        help="built-in name (tesseract, 16cell, 24cell, 5cell) or a fourd_polytope/v1 JSON path")
    parser.add_argument("--rotate", default="xw=0.5,yz=0.35,zw=0.2", help="plane rotations applied in order")
    parser.add_argument("--eye", type=float, default=2.5, help="perspective eye distance in circumradii")
    parser.add_argument("--gap", type=float, default=2.6, help="spacing of the three views in circumradii")
    parser.add_argument("--radius", type=float, default=0.035, help="tube radius in circumradii")
    parser.add_argument("--sides", type=int, default=5, help="sides of each tube")
    parser.add_argument("--segments", type=int, default=6, help="segments per stereographic arc")
    parser.add_argument("--out", required=True, help="output .gltf")
    args = parser.parse_args(argv)
    if args.eye <= 1.0 or args.gap <= 0 or args.radius <= 0 or args.sides < 3 or not 1 <= args.segments <= 64:
        parser.error("eye above 1, gap and radius positive, sides 3 or more, segments 1 to 64")
    try:
        summary = export(args.out, args.polytope, args.rotate, args.eye, args.gap, args.radius, args.sides, args.segments)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
