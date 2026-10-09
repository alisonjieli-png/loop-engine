"""Hyperplane slices of a convex 4-polytope as one glTF mesh whose morph targets play the exact slice sequence.

A hyperplane n . p = s sweeps through the polytope. Each cell is split into tetrahedra coned from one of its
vertices. Sort a tetrahedron's vertices by height h0 <= h1 <= h2 <= h3. Its slice is a triangle, then a
quadrilateral, then a triangle; written as one 4-gon (V1, V2, V3, V4) whose corners slide along tetrahedron edges:

    V1 = e02 until h2, then e23        V2 = e03
    V3 = e01 until h1, then e13        V4 = e01 until h1, then e12 until h2, then e23

Every corner is piecewise linear in s with breaks only at vertex heights, so keyframes at the distinct heights
and linear interpolation reproduce every slice exactly. Base mesh = first keyframe, morph target k = keyframe k
minus base, weights one-hot per keyframe. Where a corner jumps between two coincident positions (a tie of
heights) a second keyframe a moment later carries the jump. Slice faces of one cell share one normal (the cell
normal projected into the hyperplane), so normals need no morph targets.

    python slice_morph_animation.py --polytope tesseract --direction vertex --out tesseract_slices.gltf
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys

import fourd

POLYTOPES = ("5cell", "tesseract", "16cell", "24cell")
DIRECTIONS = ("cell", "face", "edge", "vertex")


def make_polytope(name):
    """One of POLYTOPES, centred at the origin, from its vertices and facet normals."""
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


def direction_vector(shape, direction):
    """A unit slicing normal: toward the first cell, face, edge or vertex centroid, or parsed from 'a,b,c,d'."""
    if direction in DIRECTIONS:
        vertices = shape["vertices"]
        if direction == "vertex":
            members = [0]
        elif direction == "edge":
            members = list(shape["edges"][0])
        elif direction == "face":
            members = shape["faces"][0]
        else:
            members = sorted(fourd.cell_vertex_sets(shape)[0])
        return fourd.normalize(fourd.centroid([vertices[index] for index in members]))
    try:
        values = tuple(float(part) for part in direction.split(","))
    except ValueError:
        raise ValueError("direction is cell, face, edge, vertex or four numbers a,b,c,d") from None
    if len(values) != 4 or not all(math.isfinite(value) for value in values):
        raise ValueError("direction is cell, face, edge, vertex or four numbers a,b,c,d")
    return fourd.normalize(values)


def _levels(values, tolerance=1e-9):
    ordered = sorted(values)
    levels = [ordered[0]]
    for value in ordered[1:]:
        if value - levels[-1] > tolerance:
            levels.append(value)
    return levels


def _snap(value, levels):
    return min(levels, key=lambda level: abs(level - value))


def tetrahedra(shape):
    """(cell index, four vertex indices) for every tetrahedron of every cell, coned from the cell's lowest index."""
    faces = shape["faces"]
    result = []
    for cell_index, cell in enumerate(shape["cells"]):
        apex = min(vertex for face_index in cell for vertex in faces[face_index])
        for face_index in cell:
            face = faces[face_index]
            if apex in face:
                continue
            for second, third in zip(face[1:-1], face[2:]):
                result.append((cell_index, (apex, face[0], second, third)))
    return result


def _edge_point(points, heights, first, second, level, side):
    low, high = heights[first], heights[second]
    if high - low <= 0.0:
        return points[first] if (level < low or (level == low and side < 0)) else points[second]
    t = (level - low) / (high - low)
    return fourd.lerp(points[first], points[second], 0.0 if t < 0.0 else (1.0 if t > 1.0 else t))


def _corners(points, heights, order, level, side):
    v0, v1, v2, v3 = order
    first = level < heights[v1] or (level == heights[v1] and side < 0)
    before_two = level < heights[v2] or (level == heights[v2] and side < 0)
    p1 = _edge_point(points, heights, v0, v2, level, side) if before_two else \
        _edge_point(points, heights, v2, v3, level, side)
    p2 = _edge_point(points, heights, v0, v3, level, side)
    p3 = _edge_point(points, heights, v0, v1, level, side) if first else \
        _edge_point(points, heights, v1, v3, level, side)
    if first:
        p4 = _edge_point(points, heights, v0, v1, level, side)
    elif before_two:
        p4 = _edge_point(points, heights, v1, v2, level, side)
    else:
        p4 = _edge_point(points, heights, v2, v3, level, side)
    return (p1, p2, p3, p4)


def _area(a, b, c):
    return 0.5 * fourd.norm(fourd.cross3(fourd.sub(b, a), fourd.sub(c, a)))


def build(shape, normal, duration=4.0):
    """Keyframes, mesh topology, normals and colours of the slice animation."""
    unit = fourd.normalize(normal)
    basis = fourd.hyperplane_basis(unit)
    raw = [fourd.dot(vertex, unit) for vertex in shape["vertices"]]
    levels = _levels(raw)
    if len(levels) < 2:
        raise ValueError("the polytope is flat along this direction")
    heights = [_snap(value, levels) for value in raw]
    vertices = shape["vertices"]
    middle = fourd.centroid(vertices)
    cell_sets = fourd.cell_vertex_sets(shape)
    cell_normals = []
    for members in cell_sets:
        members = sorted(members)
        normal4 = fourd.null_space([fourd.sub(vertices[index], vertices[members[0]]) for index in members[1:]])[0]
        if fourd.dot(normal4, fourd.sub(fourd.centroid([vertices[index] for index in members]), middle)) < 0.0:
            normal4 = fourd.scale(normal4, -1.0)
        projected = tuple(fourd.dot(normal4, axis) for axis in basis)
        cell_normals.append(fourd.normalize(projected) if fourd.norm(projected) > 1e-9 else (0.0, 1.0, 0.0))
    pieces = []
    for cell_index, tetrahedron in tetrahedra(shape):
        order = tuple(sorted(tetrahedron, key=lambda index: (heights[index], index)))
        pieces.append((cell_index, order))

    def configuration(level, side):
        positions = []
        for _cell, order in pieces:
            for corner in _corners(vertices, heights, order, level, side):
                positions.append(tuple(fourd.dot(corner, axis) for axis in basis))
        return positions

    span = levels[-1] - levels[0]
    times = [duration * (level - levels[0]) / span for level in levels]
    frames = [(times[0], levels[0], configuration(levels[0], 1))]
    for index in range(1, len(levels) - 1):
        left, right = configuration(levels[index], -1), configuration(levels[index], 1)
        frames.append((times[index], levels[index], left))
        if max(fourd.distance(a, b) for a, b in zip(left, right)) > 1e-12:
            step = min(duration * 1e-3, (times[index + 1] - times[index]) / 4.0)
            level = levels[index] + step * span / duration
            frames.append((times[index] + step, level, configuration(level, 1)))
    frames.append((times[-1], levels[-1], configuration(levels[-1], -1)))
    indices, normals, colours = [], [], []
    palette = fourd.palette(len(shape["cells"]))
    for piece_index, (cell_index, order) in enumerate(pieces):
        lows = [heights[index] for index in order]
        spans = [(lows[1] - lows[0], lows[0], lows[1]), (lows[2] - lows[1], lows[1], lows[2]),
                 (lows[3] - lows[2], lows[2], lows[3])]
        length, start, end = max(spans)
        flip = False
        if length > 0.0:
            p1, p2, p3, p4 = (tuple(fourd.dot(corner, axis) for axis in basis)
                              for corner in _corners(vertices, heights, order, (start + end) / 2.0, 1))
            a, b, c = (p1, p2, p3) if _area(p1, p2, p3) >= _area(p1, p3, p4) else (p1, p3, p4)
            flip = fourd.dot(fourd.cross3(fourd.sub(b, a), fourd.sub(c, a)), cell_normals[cell_index]) < 0.0
        base = 4 * piece_index
        if flip:
            indices += [base, base + 2, base + 1, base, base + 3, base + 2]
        else:
            indices += [base, base + 1, base + 2, base, base + 2, base + 3]
        normals += [cell_normals[cell_index]] * 4
        colours += [palette[cell_index]] * 4
    return {"frames": frames, "indices": indices, "normals": normals, "colors": colours, "levels": levels,
            "basis": basis, "normal": unit, "duration": duration}


def positions_at(animation, time):
    """Vertex positions at a time, by the same linear interpolation a glTF viewer applies to the weights."""
    frames = animation["frames"]
    if time <= frames[0][0]:
        return frames[0][2]
    for (t0, _l0, p0), (t1, _l1, p1) in zip(frames, frames[1:]):
        if t0 <= time <= t1:
            fraction = (time - t0) / (t1 - t0)
            return [fourd.lerp(a, b, fraction) for a, b in zip(p0, p1)]
    return frames[-1][2]


def mesh_measures(positions, indices):
    """Total triangle area and enclosed signed volume of the morph mesh at one pose."""
    area = volume = 0.0
    for start in range(0, len(indices), 3):
        a, b, c = (positions[index] for index in indices[start:start + 3])
        area += _area(a, b, c)
        volume += fourd.dot(a, fourd.cross3(b, c)) / 6.0
    return area, volume


def exact_measures(shape, normal, level):
    """Surface area and volume of the exact cross-section (fourd.slice_polytope)."""
    section = fourd.slice_polytope(shape, normal, level)
    area = 0.0
    for face in section["faces"]:
        corners = [section["points3"][index] for index in face]
        area += 0.5 * fourd.norm(fourd.polygon_normal(corners))
    return area, section["volume"]


def morph_error(shape, normal, animation, samples=(0.3, 0.5, 0.7)):
    """Largest relative difference of area and volume between the morph mesh and exact slices inside each interval."""
    levels, duration = animation["levels"], animation["duration"]
    span = levels[-1] - levels[0]
    worst = 0.0
    for low, high in zip(levels, levels[1:]):
        for fraction in samples:
            level = low + (high - low) * fraction
            time = duration * (level - levels[0]) / span
            area, volume = mesh_measures(positions_at(animation, time), animation["indices"])
            exact_area, exact_volume = exact_measures(shape, normal, level)
            worst = max(worst, abs(area - exact_area) / max(1e-12, exact_area),
                        abs(volume - exact_volume) / max(1e-12, exact_volume))
    return worst


def section_types(shape, normal):
    """(V, E, F) of the exact slice in the middle of every interval between distinct vertex heights."""
    unit = fourd.normalize(normal)
    levels = _levels([fourd.dot(vertex, unit) for vertex in shape["vertices"]])
    result = []
    for low, high in zip(levels, levels[1:]):
        section = fourd.slice_polytope(shape, unit, (low + high) / 2.0)
        result.append([len(section["points3"]), len(section["edges"]), len(section["faces"])])
    return result


def document(animation, name="slice"):
    """The glTF document: one mesh, its morph targets and one weights animation."""
    frames = animation["frames"]
    base = frames[0][2]
    targets = [{"positions": [fourd.sub(p, q) for p, q in zip(frame[2], base)]} for frame in frames[1:]]
    weights = []
    for index in range(len(frames)):
        row = [0.0] * len(targets)
        if index:
            row[index - 1] = 1.0
        weights.append(row)
    mesh = {"name": name, "positions": base, "normals": animation["normals"], "colors": animation["colors"],
            "indices": animation["indices"], "mode": 4, "targets": targets, "color": (1.0, 1.0, 1.0, 1.0)}
    return fourd.gltf_document([mesh], animations=[{"name": "slice_sweep", "channels": [
        {"node": 0, "path": "weights", "times": [frame[0] for frame in frames], "values": weights}]}],
        generator="slice_morph_animation.py")


def export(path, polytope="tesseract", direction="vertex", duration=4.0):
    """Write the slice animation glTF; returns a summary."""
    shape = make_polytope(polytope)
    normal = direction_vector(shape, direction)
    animation = build(shape, normal, duration)
    gltf = document(animation, f"{polytope}_slice")
    return {"path": str(path), "bytes": fourd.write_gltf(path, gltf), "keyframes": len(animation["frames"]),
            "levels": len(animation["levels"]), **fourd.gltf_summary(gltf)}


def invariants():
    tesseract = make_polytope("tesseract")
    exact = []
    for name in POLYTOPES:
        shape = make_polytope(name)
        for direction in DIRECTIONS:
            normal = direction_vector(shape, direction)
            exact.append(morph_error(shape, normal, build(shape, normal)))
    centre = fourd.slice_polytope(tesseract, (1, 1, 1, 1), 0.0)
    cuboctahedron = fourd.slice_polytope(make_polytope("16cell"), (1, 1, 1, 1), 0.0)
    return {"tesseract_vertex_first": section_types(tesseract, (1, 1, 1, 1)),
            "tesseract_vertex_first_center": [len(centre["points3"]), len(centre["edges"]), len(centre["faces"])],
            "tesseract_vertex_first_center_volume": centre["volume"],
            "tesseract_edge_first": section_types(tesseract, (1, 1, 1, 0)),
            "tesseract_face_first": section_types(tesseract, (1, 1, 0, 0)),
            "tesseract_cell_first": section_types(tesseract, (0, 0, 0, 1)),
            "cell16_cell_first_center": [len(cuboctahedron["points3"]), len(cuboctahedron["edges"]),
                                         len(cuboctahedron["faces"])],
            "cell5_vertex_first": section_types(make_polytope("5cell"), direction_vector(make_polytope("5cell"), "vertex")),
            "cell5_edge_first": section_types(make_polytope("5cell"), direction_vector(make_polytope("5cell"), "edge")),
            "morph_matches_exact_slices": max(exact) < 1e-9,
            "example_keyframes": len(build(tesseract, direction_vector(tesseract, "vertex"))["frames"])}


def controls():
    shape = make_polytope("tesseract")
    normal = direction_vector(shape, "vertex")
    animation = build(shape, normal)
    shifted = dict(animation, frames=[(t, level, [fourd.add(p, (0.05, 0.0, 0.0)) if index % 7 == 0 else p
                                                  for index, p in enumerate(positions)])
                                      for t, level, positions in animation["frames"]])

    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    return {"zero_direction_refused": refused(lambda: direction_vector(shape, "0,0,0,0")),
            "unknown_polytope_refused": refused(lambda: make_polytope("7cell")),
            "malformed_direction_refused": refused(lambda: direction_vector(shape, "1,2,x,4")),
            "displaced_keyframes_detected": morph_error(shape, normal, shifted) > 1e-3}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="slice_morph_animation.py",
                                     description="Write the exact slice sweep of a 4-polytope as glTF morph targets.")
    parser.add_argument("--polytope", choices=POLYTOPES, default="tesseract", help="polytope to slice")
    parser.add_argument("--direction", default="vertex",
                        help="slicing normal: cell, face, edge, vertex (first) or four numbers a,b,c,d")
    parser.add_argument("--duration", type=float, default=4.0, help="seconds for the full sweep")
    parser.add_argument("--out", required=True, help="output .gltf path")
    args = parser.parse_args(argv)
    if args.duration <= 0:
        parser.error("duration is positive")
    try:
        summary = export(args.out, args.polytope, args.direction, args.duration)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
