"""Package tests for one mesh_algorithms component (standard library only).

The tests read component.json, check every file against its digest, import the item module the contract
names and confirm the card declares exactly its public functions and parameters. They run every declared
case with its example arguments and compare the result with the declared known answers (exact counts,
closed-form volumes and areas, topology), then run known-wrong controls: each declared value, made wrong,
must be refused; a damaged result must be refused; meshkit must detect a flipped face, an out-of-range
index and a corrupted glTF. Finally they run the item's command line and verify the files it writes and
any example model the package ships.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import importlib
import inspect
import io
import json
import math
import struct
import tempfile
import unittest
from pathlib import Path

import meshkit

ROOT = Path(__file__).resolve().parent
CARD = json.loads((ROOT / "component.json").read_text(encoding="utf-8"))
CONTRACT = CARD["contract"]
MODULE = importlib.import_module(CONTRACT["module"])
CHECKS = {}


def _check(name, perturb=None):
    def register(function):
        CHECKS[name] = (function, perturb)
        return function
    return register


# ------------------------------------------------------------------------------------------- result adapters

def _select(value, path):
    if path is None:
        return value
    for step in (path if isinstance(path, list) else [path]):
        value = value[step] if isinstance(value, (dict, list, tuple)) else getattr(value, step)
    return value


def _as_mesh(result):
    if isinstance(result, meshkit.Mesh):
        return result
    if isinstance(result, dict) and result.get("meshes"):
        result = result["meshes"]
    if isinstance(result, (list, tuple)) and result and all(isinstance(m, meshkit.Mesh) for m in result):
        return meshkit.combine(result)
    raise AssertionError("the result is not a mesh")


def _as_points(result):
    if isinstance(result, dict) and "points" in result:
        result = result["points"]
    points = [tuple(float(c) for c in p) for p in result]
    if not points or any(len(p) not in (2, 3) for p in points):
        raise AssertionError("the result is not a list of 2D or 3D points")
    return points


def _as_triangulation(result):
    if isinstance(result, dict):
        return [tuple(map(float, p)) for p in result["points"]], [tuple(t) for t in result["triangles"]]
    points, triangles = result
    return [tuple(map(float, p)) for p in points], [tuple(t) for t in triangles]


def _as_polygons(result):
    if isinstance(result, dict) and "polygons" in result:
        result = result["polygons"]
    if result and isinstance(result[0], (list, tuple)) and result[0] and isinstance(result[0][0], (int, float)):
        result = [result]
    return [[tuple(float(c) for c in p) for p in polygon] for polygon in result]


def _scale(points):
    low, high = meshkit.bounding_box([p if len(p) == 3 else (p[0], p[1], 0.0) for p in points])
    return max(1e-12, math.sqrt(sum((high[k] - low[k]) ** 2 for k in range(3))))


def _differs(actual, expected):
    return None if actual == expected else f"got {actual}, expected {expected}"


def _near(actual, value, tolerance):
    return None if abs(actual - value) <= tolerance else f"got {actual!r}, expected {value} within {tolerance}"


def _shift_int(value):
    return value + 1


def _flip_bool(value):
    return not value


def _shift_value(expected):
    value, tolerance = expected
    return [value + 3 * tolerance + 0.01 * max(1.0, abs(value)), tolerance]


def _shift_first_vector(expected):
    shifted = [list(part) if isinstance(part, list) else part for part in expected]
    shifted[0][0] += 3 * expected[-1] + 0.01 * max(1.0, abs(shifted[0][0]))
    return shifted


# ------------------------------------------------------------------------------------------- mesh checks

@_check("vertex_count", _shift_int)
def _vertex_count(result, expected):
    return _differs(len(_as_mesh(result).vertices), expected)


@_check("face_count", _shift_int)
def _face_count(result, expected):
    return _differs(len(_as_mesh(result).faces), expected)


@_check("triangle_count", _shift_int)
def _triangle_count(result, expected):
    return _differs(_as_mesh(result).triangle_count(), expected)


@_check("line_count", _shift_int)
def _line_count(result, expected):
    return _differs(len(_as_mesh(result).lines), expected)


@_check("quad_count", _shift_int)
def _quad_count(result, expected):
    return _differs(sum(1 for face in _as_mesh(result).faces if len(face) == 4), expected)


@_check("closed", _flip_bool)
def _closed(result, expected):
    return _differs(meshkit.is_closed(_as_mesh(result)), expected)


@_check("oriented", _flip_bool)
def _oriented(result, expected):
    return _differs(meshkit.is_consistently_oriented(_as_mesh(result)), expected)


@_check("manifold", _flip_bool)
def _manifold(result, expected):
    return _differs(meshkit.is_manifold(_as_mesh(result)), expected)


@_check("watertight", _flip_bool)
def _watertight(result, expected):
    return _differs(meshkit.is_watertight(_as_mesh(result)), expected)


def _welded(result):
    mesh = _as_mesh(result)
    return meshkit.merge_by_distance(mesh, 1e-7 * _scale(mesh.vertices))


@_check("welded_watertight", _flip_bool)
def _welded_watertight(result, expected):
    return _differs(meshkit.is_watertight(_welded(result)), expected)


@_check("welded_closed", _flip_bool)
def _welded_closed(result, expected):
    return _differs(meshkit.is_closed(_welded(result)), expected)


@_check("euler_characteristic", _shift_int)
def _euler(result, expected):
    return _differs(meshkit.euler_characteristic(_as_mesh(result)), expected)


@_check("welded_euler_characteristic", _shift_int)
def _welded_euler(result, expected):
    return _differs(meshkit.euler_characteristic(_welded(result)), expected)


@_check("genus", _shift_int)
def _genus(result, expected):
    return _differs(meshkit.genus(_welded(result)), expected)


@_check("components", _shift_int)
def _components(result, expected):
    return _differs(len(meshkit.connected_components(_as_mesh(result))), expected)


@_check("welded_components", _shift_int)
def _welded_components(result, expected):
    return _differs(len(meshkit.connected_components(_welded(result))), expected)


@_check("boundary_loops", _shift_int)
def _boundary_loops(result, expected):
    return _differs(len(meshkit.boundary_loops(_as_mesh(result))), expected)


@_check("welded_boundary_loops", _shift_int)
def _welded_boundary_loops(result, expected):
    return _differs(len(meshkit.boundary_loops(_welded(result))), expected)


@_check("boundary_edges", _shift_int)
def _boundary_edges(result, expected):
    return _differs(len(meshkit.boundary_edges(_as_mesh(result))), expected)


@_check("volume", _shift_value)
def _volume(result, expected):
    return _near(meshkit.signed_volume(_as_mesh(result)), *expected)


@_check("area", _shift_value)
def _area(result, expected):
    return _near(meshkit.surface_area(_as_mesh(result)), *expected)


@_check("bounds", _shift_first_vector)
def _bounds(result, expected):
    low, high, tolerance = expected
    actual_low, actual_high = meshkit.bounding_box(_as_mesh(result).vertices)
    for k in range(3):
        if abs(actual_low[k] - low[k]) > tolerance or abs(actual_high[k] - high[k]) > tolerance:
            return f"got {actual_low} to {actual_high}, expected {low} to {high} within {tolerance}"
    return None


@_check("within", lambda e: [e[1], e[1], e[2]])
def _within(result, expected):
    low, high, tolerance = expected
    for vertex in _as_mesh(result).vertices:
        if any(vertex[k] < low[k] - tolerance or vertex[k] > high[k] + tolerance for k in range(3)):
            return f"vertex {vertex} outside {low} to {high}"
    return None


@_check("centroid", _shift_first_vector)
def _centroid(result, expected):
    point, tolerance = expected
    actual = meshkit.centroid(_as_mesh(result))
    return None if all(abs(actual[k] - point[k]) <= tolerance for k in range(3)) else f"got {actual}"


@_check("surface_centroid", _shift_first_vector)
def _surface_centroid(result, expected):
    point, tolerance = expected
    actual = meshkit.surface_centroid(_as_mesh(result))
    return None if all(abs(actual[k] - point[k]) <= tolerance for k in range(3)) else f"got {actual}"


@_check("convex", _flip_bool)
def _convex(result, expected):
    mesh = _as_mesh(result)
    tolerance = 1e-7 * _scale(mesh.vertices)
    convex = True
    for face in mesh.faces:
        normal = meshkit.face_normal(mesh.vertices, face)
        origin = mesh.vertices[face[0]]
        if any(meshkit.vdot(normal, meshkit.vsub(v, origin)) > tolerance for v in mesh.vertices):
            convex = False
            break
    return _differs(convex, expected)


@_check("contains_points", lambda e: [e[0], e[1], not (e[2] if len(e) == 3 else True)])
def _contains_points(result, expected):
    """Every listed point lies inside or on the closed convex mesh (all face planes), written independently."""
    points, tolerance, _expected_value = expected if len(expected) == 3 else (expected[0], expected[1], True)
    mesh = _as_mesh(result)
    inside = True
    for face in mesh.faces:
        normal = meshkit.face_normal(mesh.vertices, face)
        origin = mesh.vertices[face[0]]
        if any(meshkit.vdot(normal, meshkit.vsub(tuple(p), origin)) > tolerance for p in points):
            inside = False
            break
    return _differs(inside, _expected_value)


@_check("vertices_on_sphere", lambda e: [e[0], e[1] + 3 * e[2] + 0.01 * max(1.0, abs(e[1])), e[2]])
def _on_sphere(result, expected):
    center, radius, tolerance = expected
    for vertex in _as_mesh(result).vertices:
        distance = meshkit.vdistance(vertex, center)
        if abs(distance - radius) > tolerance:
            return f"vertex {vertex} at distance {distance}, expected {radius}"
    return None


@_check("vertices_on_plane", lambda e: [e[0], e[1] + 3 * e[2] + 0.01, e[2]])
def _on_plane(result, expected):
    normal, offset, tolerance = expected
    for vertex in _as_mesh(result).vertices:
        if abs(meshkit.vdot(normal, vertex) - offset) > tolerance:
            return f"vertex {vertex} is off the plane"
    return None


@_check("normals")
def _normals(result, expected):
    mesh = _as_mesh(result)
    if expected != "unit":
        return "the normals check expects 'unit'"
    if mesh.normals is None or len(mesh.normals) != len(mesh.vertices):
        return "per-vertex normals are missing"
    for normal in mesh.normals:
        if abs(meshkit.vlength(normal) - 1.0) > 1e-6:
            return f"normal {normal} is not unit length"
    return None


@_check("normals_agree", lambda e: min(1.0, e + 0.5) if e < 0.5 else e - 2.0)
def _normals_agree(result, expected):
    mesh = _as_mesh(result)
    if mesh.normals is None:
        return "per-vertex normals are missing"
    agree = total = 0
    for a, b, c in mesh.triangles():
        face = meshkit.vcross(meshkit.vsub(mesh.vertices[b], mesh.vertices[a]),
                              meshkit.vsub(mesh.vertices[c], mesh.vertices[a]))
        if meshkit.vlength(face) <= 1e-15:
            continue
        total += 1
        mean = meshkit.vadd(meshkit.vadd(mesh.normals[a], mesh.normals[b]), mesh.normals[c])
        agree += meshkit.vdot(face, mean) > 0
    fraction = agree / total if total else 0.0
    return None if expected >= 0 and fraction >= expected else f"{fraction:.4f} of triangles agree, expected {expected}"


@_check("uv_range", _shift_first_vector)
def _uv_range(result, expected):
    low, high, tolerance = expected
    mesh = _as_mesh(result)
    if mesh.uvs is None or len(mesh.uvs) != len(mesh.vertices):
        return "texture coordinates are missing"
    for uv in mesh.uvs:
        if any(uv[k] < low[k] - tolerance or uv[k] > high[k] + tolerance for k in range(2)):
            return f"uv {uv} outside {low} to {high}"
    for k in range(2):
        if abs(min(uv[k] for uv in mesh.uvs) - low[k]) > tolerance or abs(max(uv[k] for uv in mesh.uvs) - high[k]) > tolerance:
            return f"uv range on axis {k} does not reach {low[k]} to {high[k]}"
    return None


@_check("has_colors", _flip_bool)
def _has_colors(result, expected):
    mesh = _as_mesh(result)
    present = mesh.colors is not None and len(mesh.colors) == len(mesh.vertices) and all(
        0.0 <= c <= 1.0 for color in mesh.colors for c in color)
    return _differs(present, expected)


@_check("has_tangents", _flip_bool)
def _has_tangents(result, expected):
    mesh = _as_mesh(result)
    present = mesh.tangents is not None and len(mesh.tangents) == len(mesh.vertices)
    return _differs(present, expected)


@_check("min_triangle_area", lambda e: e * 1e9 + 1e9)
def _min_triangle_area(result, expected):
    mesh = _as_mesh(result)
    smallest = min(meshkit.triangle_area(mesh.vertices[a], mesh.vertices[b], mesh.vertices[c])
                   for a, b, c in mesh.triangles())
    return None if smallest >= expected else f"smallest triangle area {smallest}, expected at least {expected}"


@_check("edge_length_range", lambda e: [e[1] * 2.0 + 1.0, e[1] * 3.0 + 2.0])
def _edge_length_range(result, expected):
    low, high = expected
    mesh = _as_mesh(result)
    lengths = [meshkit.vdistance(mesh.vertices[a], mesh.vertices[b]) for a, b in meshkit.edges(mesh)]
    if min(lengths) < low or max(lengths) > high:
        return f"edge lengths {min(lengths)} to {max(lengths)}, expected {low} to {high}"
    return None


@_check("mesh_count", _shift_int)
def _mesh_count(result, expected):
    if isinstance(result, meshkit.Mesh):
        count = 1
    elif isinstance(result, dict):
        count = len(result["meshes"])
    else:
        count = len(result)
    return _differs(count, expected)


@_check("node_count", _shift_int)
def _node_count(result, expected):
    return _differs(len(result.get("nodes") or []), expected)


@_check("animation_count", _shift_int)
def _animation_count(result, expected):
    return _differs(len(result.get("animations") or []), expected)


@_check("channel_count", _shift_int)
def _channel_count(result, expected):
    return _differs(sum(len(a["channels"]) for a in result.get("animations") or []), expected)


# ------------------------------------------------------------------------------------------- point checks

@_check("point_count", _shift_int)
def _point_count(result, expected):
    return _differs(len(_as_points(result)), expected)


def _polyline_length(points, closed):
    pairs = list(zip(points, points[1:])) + ([(points[-1], points[0])] if closed else [])
    return math.fsum(math.sqrt(sum((a[k] - b[k]) ** 2 for k in range(len(a)))) for a, b in pairs)


@_check("polyline_length", _shift_value)
def _open_length(result, expected):
    return _near(_polyline_length(_as_points(result), False), *expected)


@_check("closed_polyline_length", _shift_value)
def _closed_length(result, expected):
    return _near(_polyline_length(_as_points(result), True), *expected)


def _point_near(actual, point, tolerance):
    return None if len(actual) == len(point) and all(abs(actual[k] - point[k]) <= tolerance for k in range(len(point))) \
        else f"got {actual}, expected {point} within {tolerance}"


@_check("first_point", _shift_first_vector)
def _first_point(result, expected):
    return _point_near(_as_points(result)[0], *expected)


@_check("last_point", _shift_first_vector)
def _last_point(result, expected):
    return _point_near(_as_points(result)[-1], *expected)


@_check("points_on_circle", lambda e: [e[0], e[1] + 3 * e[2] + 0.01 * max(1.0, abs(e[1])), e[2]])
def _points_on_circle(result, expected):
    center, radius, tolerance = expected
    for point in _as_points(result):
        distance = math.sqrt(sum((point[k] - center[k]) ** 2 for k in range(len(center))))
        if abs(distance - radius) > tolerance:
            return f"point {point} at distance {distance}, expected {radius}"
    return None


@_check("min_spacing", lambda e: e * 1e6 + 1e6)
def _min_spacing(result, expected):
    points = _as_points(result)
    smallest = math.inf
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            smallest = min(smallest, math.sqrt(sum((points[i][k] - points[j][k]) ** 2 for k in range(len(points[i])))))
    return None if smallest >= expected else f"closest pair {smallest}, expected at least {expected}"


@_check("points_within", lambda e: [e[1], e[1], e[2]])
def _points_within(result, expected):
    low, high, tolerance = expected
    for point in _as_points(result):
        if any(point[k] < low[k] - tolerance or point[k] > high[k] + tolerance for k in range(len(low))):
            return f"point {point} outside {low} to {high}"
    return None


@_check("points_close", lambda e: [[[c + 3 * e[1] + 0.01 for c in p] for p in e[0]], e[1]])
def _points_close(result, expected):
    targets, tolerance = expected
    points = _as_points(result)
    if len(points) != len(targets):
        return f"got {len(points)} points, expected {len(targets)}"
    for actual, target in zip(points, targets):
        problem = _point_near(actual, target, tolerance)
        if problem:
            return problem
    return None


# ------------------------------------------------------------------------------------------- value checks

def _plain(value):
    if isinstance(value, meshkit.Mesh):
        return {"vertices": _plain(value.vertices), "faces": _plain(value.faces), "normals": _plain(value.normals),
                "uvs": _plain(value.uvs), "colors": _plain(value.colors), "lines": _plain(value.lines),
                "tangents": _plain(value.tangents)}
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _path(value, dotted):
    for part in str(dotted).split("."):
        value = value[int(part)] if isinstance(value, (list, tuple)) else value[part]
    return value


@_check("equals", lambda e: {"wrong": e})
def _equals(result, expected):
    return _differs(_plain(result), expected)


@_check("close", _shift_value)
def _close(result, expected):
    return _near(float(result), *expected)


@_check("at_most", lambda e: -1e300)
def _at_most(result, expected):
    return None if float(result) <= expected else f"got {result}, expected at most {expected}"


@_check("at_least", lambda e: 1e300)
def _at_least(result, expected):
    return None if float(result) >= expected else f"got {result}, expected at least {expected}"


@_check("fields_equal", lambda e: {k: (v + 1 if isinstance(v, int) and not isinstance(v, bool) else
                                       (not v if isinstance(v, bool) else [v])) for k, v in e.items()})
def _fields_equal(result, expected):
    for dotted, value in expected.items():
        actual = _plain(_path(result, dotted))
        if actual != value:
            return f"{dotted}: got {actual}, expected {value}"
    return None


@_check("fields_close", lambda e: {k: _shift_value(v) for k, v in e.items()})
def _fields_close(result, expected):
    for dotted, (value, tolerance) in expected.items():
        problem = _near(float(_path(result, dotted)), value, tolerance)
        if problem:
            return f"{dotted}: {problem}"
    return None


@_check("length", _shift_int)
def _length(result, expected):
    return _differs(len(result), expected)


def _flatten(value):
    if isinstance(value, (list, tuple)):
        return [x for item in value for x in _flatten(item)]
    return [float(value)]


@_check("sequence_close", lambda e: [[x + 3 * e[1] + 0.01 for x in _flatten(e[0])], e[1]])
def _sequence_close(result, expected):
    values, tolerance = expected
    actual, target = _flatten(_plain(result)), _flatten(values)
    if len(actual) != len(target):
        return f"got {len(actual)} numbers, expected {len(target)}"
    for k, (a, b) in enumerate(zip(actual, target)):
        if abs(a - b) > tolerance:
            return f"value {k}: got {a}, expected {b} within {tolerance}"
    return None


# ------------------------------------------------------------------------------------------- 2D checks

@_check("triangulation_count", _shift_int)
def _triangulation_count(result, expected):
    return _differs(len(_as_triangulation(result)[1]), expected)


@_check("triangles_ccw", _flip_bool)
def _triangles_ccw(result, expected):
    points, triangles = _as_triangulation(result)
    return _differs(all(meshkit.cross2(points[a], points[b], points[c]) > 0 for a, b, c in triangles), expected)


@_check("triangulation_area", _shift_value)
def _triangulation_area(result, expected):
    points, triangles = _as_triangulation(result)
    area = math.fsum(meshkit.cross2(points[a], points[b], points[c]) for a, b, c in triangles) / 2.0
    return _near(area, *expected)


@_check("uses_all_points", _flip_bool)
def _uses_all_points(result, expected):
    points, triangles = _as_triangulation(result)
    return _differs({i for t in triangles for i in t} == set(range(len(points))), expected)


@_check("delaunay", _flip_bool)
def _delaunay(result, expected):
    """Empty circumcircle test, written here independently of any item."""
    points, triangles = _as_triangulation(result)
    scale = _scale(points)
    empty = True
    for a, b, c in triangles:
        ax, ay = points[a]
        bx, by = points[b]
        cx, cy = points[c]
        d = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) <= 1e-18:
            continue
        ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
        uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
        radius = math.sqrt((ax - ux) ** 2 + (ay - uy) ** 2)
        for index, (px, py) in enumerate(points):
            if index in (a, b, c):
                continue
            if math.sqrt((px - ux) ** 2 + (py - uy) ** 2) < radius - 1e-9 * scale:
                empty = False
                break
        if not empty:
            break
    return _differs(empty, expected)


@_check("polygon_count", _shift_int)
def _polygon_count(result, expected):
    return _differs(len(_as_polygons(result)), expected)


@_check("polygon_area", _shift_value)
def _polygon_area(result, expected):
    return _near(math.fsum(meshkit.polygon_area_2d(p) for p in _as_polygons(result)), *expected)


@_check("polygon_vertex_count", _shift_int)
def _polygon_vertex_count(result, expected):
    return _differs(sum(len(p) for p in _as_polygons(result)), expected)


@_check("polygons_convex", _flip_bool)
def _polygons_convex(result, expected):
    polygons = _as_polygons(result)
    tolerance = 1e-9 * _scale([p for polygon in polygons for p in polygon])
    convex = all(meshkit.cross2(poly[k - 1], poly[k], poly[(k + 1) % len(poly)]) >= -tolerance * tolerance
                 for poly in polygons for k in range(len(poly)))
    return _differs(convex, expected)


def _segments_cross(p1, p2, q1, q2):
    d1, d2 = meshkit.cross2(q1, q2, p1), meshkit.cross2(q1, q2, p2)
    d3, d4 = meshkit.cross2(p1, p2, q1), meshkit.cross2(p1, p2, q2)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)) and 0 not in (d1, d2, d3, d4)


@_check("polygons_simple", _flip_bool)
def _polygons_simple(result, expected):
    simple = True
    for polygon in _as_polygons(result):
        count = len(polygon)
        for i in range(count):
            for j in range(i + 2, count):
                if i == 0 and j == count - 1:
                    continue
                if _segments_cross(polygon[i], polygon[(i + 1) % count], polygon[j], polygon[(j + 1) % count]):
                    simple = False
    return _differs(simple, expected)


# ------------------------------------------------------------------------------------------- evaluation

def resolve(value):
    """Example arguments with {"$mesh": ...}, {"$meshkit": name} and {"$call": name} replaced by objects."""
    if isinstance(value, dict):
        if "$mesh" in value:
            return meshkit.Mesh(value["$mesh"]["vertices"], value["$mesh"]["faces"])
        if "$meshkit" in value:
            return getattr(meshkit, value["$meshkit"])(**resolve(value.get("arguments", {})))
        if "$call" in value:
            return _select(getattr(MODULE, value["$call"])(**resolve(value.get("arguments", {}))), value.get("select"))
        return {key: resolve(item) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item) for item in value]
    return value


def run_case(case):
    """Call the case's function with its resolved arguments and apply its selection."""
    return _select(getattr(MODULE, case["call"])(**resolve(case.get("arguments", {}))), case.get("select"))


def evaluate(result, expect):
    """Failure messages, one per declared expectation that the result does not meet."""
    failures = []
    for name, expected in expect.items():
        if name not in CHECKS:
            failures.append(f"{name}: no such check")
            continue
        try:
            problem = CHECKS[name][0](result, resolve(expected))
        except Exception as error:  # a checker that cannot read the result is a failure, not a pass
            problem = f"raised {type(error).__name__}: {error}"
        if problem:
            failures.append(f"{name}: {problem}")
    return failures


def damaged(result):
    """A copy of the result with one element removed, or None when the result has no such element."""
    if isinstance(result, meshkit.Mesh):
        if not result.faces:
            return None
        copy = result.copy()
        copy.faces = copy.faces[:-1]
        return copy
    if isinstance(result, (list, tuple)) and result and all(isinstance(m, meshkit.Mesh) for m in result):
        return list(result[:-1]) + [damaged(result[-1])] if damaged(result[-1]) is not None else list(result[:-1])
    if isinstance(result, dict) and result.get("meshes"):
        copy = dict(result)
        copy["meshes"] = damaged(list(result["meshes"]))
        return copy
    if isinstance(result, dict) and "triangles" in result and result["triangles"]:
        copy = dict(result)
        copy["triangles"] = list(result["triangles"])[:-1]
        return copy
    if isinstance(result, dict) and "points" in result and len(result["points"]) > 1:
        copy = dict(result)
        copy["points"] = list(result["points"])[:-1]
        return copy
    if isinstance(result, dict) and "polygons" in result and result["polygons"]:
        copy = dict(result)
        copy["polygons"] = [list(p) for p in result["polygons"]]
        copy["polygons"][0] = copy["polygons"][0][:-1]
        return copy
    if isinstance(result, (list, tuple)) and len(result) > 1 and all(isinstance(p, (list, tuple)) for p in result):
        return list(result[:-1])
    return None


def fingerprint(value):
    """A deterministic text form of a result for determinism checks."""
    return json.dumps(_plain(value), sort_keys=True, default=repr)


# ------------------------------------------------------------------------------------------- tests

class CardTests(unittest.TestCase):
    def test_files_match_card(self):
        for row in CARD["files"]:
            with self.subTest(path=row["path"]):
                self.assertEqual(hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest(), row["sha256"])

    def test_contract_shape(self):
        for key in ("module", "entry_points", "parameters", "invariants", "complexity", "outputs", "axes"):
            self.assertIn(key, CONTRACT)
        self.assertEqual(CONTRACT["module"], CARD["job"]["identity"])
        self.assertTrue((ROOT / (CONTRACT["module"] + ".py")).is_file())
        self.assertTrue(CONTRACT["invariants"], "at least one known-answer case")
        self.assertIn("+Y up", CONTRACT["axes"])

    def test_entry_points_are_the_public_api(self):
        declared = {row["name"] for row in CONTRACT["entry_points"]}
        public = {name for name, value in vars(MODULE).items()
                  if not name.startswith("_") and (inspect.isfunction(value) or inspect.isclass(value))
                  and getattr(value, "__module__", None) == MODULE.__name__}
        self.assertEqual(public, declared)
        self.assertIn("main", declared)

    def test_parameters_match_module(self):
        self.assertEqual(json.loads(json.dumps(MODULE.PARAMETERS)), CONTRACT["parameters"])

    def test_known_wrong_card_is_refused(self):
        broken = dict(CARD["files"][0])
        broken["sha256"] = "0" * 64
        self.assertNotEqual(hashlib.sha256((ROOT / broken["path"]).read_bytes()).hexdigest(), broken["sha256"])


class MeshkitTests(unittest.TestCase):
    def test_box_known_answers(self):
        box = meshkit.box((2.0, 3.0, 4.0), (1.0, 0.0, 0.0))
        self.assertAlmostEqual(meshkit.signed_volume(box), 24.0, places=12)
        self.assertAlmostEqual(meshkit.surface_area(box), 52.0, places=12)
        self.assertEqual(meshkit.euler_characteristic(box), 2)
        self.assertTrue(meshkit.is_watertight(box))
        self.assertEqual(meshkit.genus(box), 0)
        self.assertEqual(meshkit.bounding_box(box), ((0.0, -1.5, -2.0), (2.0, 1.5, 2.0)))
        for actual, expected in zip(meshkit.centroid(box), (1.0, 0.0, 0.0)):
            self.assertAlmostEqual(actual, expected, places=12)
        self.assertEqual(len(meshkit.edges(box)), 12)
        self.assertEqual(box.triangle_count(), 12)

    def test_tetrahedron_known_answers(self):
        tetrahedron = meshkit.tetrahedron(2.0)
        self.assertAlmostEqual(meshkit.signed_volume(tetrahedron), 8.0 / 3.0, places=12)
        self.assertAlmostEqual(meshkit.surface_area(tetrahedron), 4 * math.sqrt(3) / 4 * 8.0, places=12)
        self.assertTrue(meshkit.is_watertight(tetrahedron))

    def test_flipped_face_is_detected(self):
        tetrahedron = meshkit.tetrahedron()
        tetrahedron.faces[1] = tuple(reversed(tetrahedron.faces[1]))
        self.assertFalse(meshkit.is_consistently_oriented(tetrahedron))
        self.assertFalse(meshkit.is_watertight(tetrahedron))
        self.assertTrue(meshkit.is_closed(tetrahedron))

    def test_out_of_range_index_is_detected(self):
        mesh = meshkit.Mesh([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [(0, 1, 99)])
        with self.assertRaises(meshkit.MeshError) as caught:
            mesh.validate()
        self.assertEqual(caught.exception.reason, "index_out_of_range")
        with self.assertRaises(meshkit.MeshError):
            meshkit.gltf_document([mesh])

    def test_open_and_bow_tie_meshes(self):
        quad = meshkit.Mesh([(0, 0, 0), (1, 0, 0), (1, 0, -1), (0, 0, -1)], [(0, 1, 2, 3)])
        self.assertFalse(meshkit.is_closed(quad))
        self.assertEqual(len(meshkit.boundary_loops(quad)), 1)
        self.assertEqual(len(meshkit.boundary_edges(quad)), 4)
        a, b = meshkit.tetrahedron(), meshkit.translated(meshkit.tetrahedron(), (1.0, 1.0, 0.0))
        joined = meshkit.merge_by_distance(meshkit.combine([a, b]), 1e-9)
        self.assertEqual(len(joined.vertices), 7)
        self.assertFalse(meshkit.is_vertex_manifold(joined))
        self.assertEqual(len(meshkit.connected_components(meshkit.combine([a, b]))), 2)

    def test_triangulation_with_holes(self):
        outer = [(0, 0), (10, 0), (10, 10), (0, 10)]
        holes = [[(2, 2), (4, 2), (4, 4), (2, 4)], [(6, 6), (8, 6), (8, 8), (6, 8)], [(6, 2), (8, 2), (7, 4)]]
        triangles = meshkit.triangulate_polygon_2d(outer, holes)
        points = outer + [p for hole in holes for p in hole]
        self.assertEqual(len(triangles), len(points) + 2 * len(holes) - 2)
        area = math.fsum(meshkit.cross2(points[a], points[b], points[c]) for a, b, c in triangles) / 2
        self.assertAlmostEqual(area, 90.0, places=9)
        self.assertTrue(all(meshkit.cross2(points[a], points[b], points[c]) > 0 for a, b, c in triangles))
        star = [(math.cos(k * math.pi / 5) * (1 if k % 2 == 0 else 0.4), math.sin(k * math.pi / 5) * (1 if k % 2 == 0 else 0.4))
                for k in range(10)]
        triangles = meshkit.triangulate_polygon_2d(list(reversed(star)))
        self.assertEqual(len(triangles), 8)
        self.assertAlmostEqual(abs(meshkit.polygon_area_2d(star)),
                               math.fsum(meshkit.cross2(*(star[9 - i] for i in t)) for t in triangles) / 2, places=12)

    def test_concave_face_triangulation(self):
        vertices = [(0, 0, 0), (2, 0, 0), (1, 0, -0.4), (2, 0, -2), (0, 0, -2)]
        face = (0, 1, 2, 3, 4)
        self.assertGreater(meshkit.face_normal(vertices, face)[1], 0.99)
        triangles = meshkit.triangulate_face(vertices, face)
        self.assertEqual(len(triangles), 3)
        for a, b, c in triangles:
            self.assertGreater(meshkit.vcross(meshkit.vsub(vertices[b], vertices[a]), meshkit.vsub(vertices[c], vertices[a]))[1], 0)

    def test_weld_normals_and_flat_shading(self):
        flat = meshkit.flat_shaded(meshkit.box())
        self.assertEqual(len(flat.vertices), 24)
        self.assertFalse(meshkit.is_closed(flat))
        welded = meshkit.merge_by_distance(flat, 1e-9)
        self.assertEqual(len(welded.vertices), 8)
        self.assertTrue(meshkit.is_watertight(welded))
        self.assertEqual(len(meshkit.remove_unused_vertices(meshkit.Mesh(flat.vertices, flat.faces[:1])).vertices), 4)
        for weighting in ("angle", "area"):
            normals = meshkit.vertex_normals(meshkit.box(), weighting)
            for vertex, normal in zip(meshkit.box().vertices, normals):
                self.assertAlmostEqual(meshkit.vlength(normal), 1.0, places=12)
                self.assertGreater(meshkit.vdot(vertex, normal), 0.0)
        self.assertEqual(meshkit.face_normals(meshkit.box())[3], (0.0, 1.0, 0.0))
        self.assertEqual(len(meshkit.triangulated(meshkit.box()).faces), 12)
        self.assertEqual(meshkit.vertex_neighbors(meshkit.tetrahedron())[0], [1, 2, 3])
        self.assertEqual(len(meshkit.vertex_faces(meshkit.box())[0]), 3)

    def test_transforms(self):
        box = meshkit.box((1.0, 2.0, 3.0))
        turned = meshkit.rotated(box, (1.0, 1.0, 0.0), 0.7)
        self.assertAlmostEqual(meshkit.signed_volume(turned), 6.0, places=9)
        mirrored = meshkit.scaled(box, (-1.0, 1.0, 1.0))
        self.assertAlmostEqual(meshkit.signed_volume(mirrored), 6.0, places=9)
        self.assertAlmostEqual(meshkit.signed_volume(meshkit.flipped(box)), -6.0, places=9)
        moved = meshkit.translated(box, (5.0, 0.0, 0.0))
        self.assertAlmostEqual(meshkit.centroid(moved)[0], 5.0, places=9)
        q = meshkit.quaternion_from_axis_angle((0.0, 0.0, 1.0), math.pi / 2)
        point = meshkit.transform_point(meshkit.quaternion_matrix(q), (1.0, 0.0, 0.0))
        self.assertAlmostEqual(point[1], 1.0, places=12)
        twice = meshkit.quaternion_multiply(q, q)
        self.assertAlmostEqual(meshkit.transform_point(meshkit.quaternion_matrix(twice), (1.0, 0.0, 0.0))[0], -1.0, places=12)
        matrix = meshkit.trs_matrix((1.0, 2.0, 3.0), q, (2.0, 2.0, 2.0))
        self.assertEqual(tuple(round(c, 9) for c in meshkit.transform_point(matrix, (1.0, 0.0, 0.0))), (1.0, 4.0, 3.0))
        direction = meshkit.transform_direction(meshkit.rotation_matrix((0.0, 1.0, 0.0), math.pi), (1.0, 0.0, 0.0))
        self.assertAlmostEqual(direction[0], -1.0, places=12)
        product = meshkit.matrix_multiply(meshkit.identity_matrix(), meshkit.scale_matrix(3.0))
        self.assertEqual(product[1][1], 3.0)
        self.assertEqual(meshkit.plane_to_3d((1.0, 2.0)), (1.0, 0.0, -2.0))

    def test_vector_and_polygon_helpers(self):
        self.assertEqual(meshkit.vadd((1, 2, 3), (1, 1, 1)), (2, 3, 4))
        self.assertEqual(meshkit.vscale((1, 2, 3), 2), (2, 4, 6))
        self.assertEqual(meshkit.vcross((1, 0, 0), (0, 1, 0)), (0, 0, 1))
        self.assertEqual(meshkit.vnormalize((0, 0, 0), (1.0, 0.0, 0.0)), (1.0, 0.0, 0.0))
        self.assertEqual(meshkit.vlerp((0, 0, 0), (2, 4, 6), 0.5), (1.0, 2.0, 3.0))
        self.assertAlmostEqual(meshkit.vdistance((0, 0, 0), (3, 4, 0)), 5.0)
        self.assertAlmostEqual(meshkit.polygon_area_2d([(0, 0), (2, 0), (2, 1), (0, 1)]), 2.0)
        self.assertTrue(meshkit.point_in_triangle_2d((0.2, 0.2), (0, 0), (1, 0), (0, 1)))
        self.assertFalse(meshkit.point_in_triangle_2d((1.0, 0.0), (0, 0), (1, 0), (0, 1), strict=True))
        self.assertAlmostEqual(meshkit.triangle_area((0, 0, 0), (1, 0, 0), (0, 1, 0)), 0.5)
        self.assertEqual(len(meshkit.grid_faces(4, 3)), 6)
        self.assertEqual(len(meshkit.grid_faces(4, 3, wrap_columns=True)), 8)
        grid = meshkit.Mesh([(c, 0, r) for r in range(3) for c in range(4)], meshkit.grid_faces(4, 3))
        self.assertGreater(meshkit.face_normals(grid)[0][1], 0.99)
        self.assertAlmostEqual(meshkit.surface_centroid(grid)[0], 1.5)
        self.assertEqual(meshkit.material("m", (1, 0, 0))["base_color"], (1.0, 0.0, 0.0, 1.0))

    def test_polyline_tube(self):
        line = meshkit.polyline_tube([(0, 0, 0), (1, 0, 0), (2, 0, 0)], radius=0.5, sides=4)
        self.assertEqual((len(line.vertices), len(line.faces)), (12, 10))
        self.assertTrue(meshkit.is_watertight(line))
        self.assertAlmostEqual(meshkit.signed_volume(line), 2.0 * 0.5, places=12)
        ring = meshkit.polyline_tube([(math.cos(a), 0.0, math.sin(a)) for a in [k * math.pi / 8 for k in range(16)]],
                                     radius=0.1, sides=6, closed=True)
        self.assertTrue(meshkit.is_watertight(ring))
        self.assertEqual(meshkit.euler_characteristic(ring), 0)
        self.assertGreater(meshkit.signed_volume(ring), 0.0)
        with self.assertRaises(meshkit.MeshError):
            meshkit.polyline_tube([(0, 0, 0), (0, 0, 0)])

    def test_isosurface_sphere(self):
        sphere = meshkit.isosurface(lambda x, y, z: math.sqrt(x * x + y * y + z * z) - 1.0,
                                    (-1.25, -1.25, -1.25), (1.25, 1.25, 1.25), 12)
        self.assertTrue(meshkit.is_watertight(sphere))
        self.assertEqual(meshkit.euler_characteristic(sphere), 2)
        self.assertAlmostEqual(meshkit.signed_volume(sphere), 4.0 / 3.0 * math.pi, delta=0.06 * 4.0 / 3.0 * math.pi)
        self.assertTrue(all(abs(meshkit.vlength(n) - 1.0) < 1e-9 for n in sphere.normals))

    def test_noise_is_deterministic_and_bounded(self):
        values = [meshkit.gradient_noise_2d(x * 0.37, y * 0.23, seed=4) for x in range(20) for y in range(20)]
        self.assertEqual(values, [meshkit.gradient_noise_2d(x * 0.37, y * 0.23, seed=4) for x in range(20) for y in range(20)])
        self.assertTrue(all(-1.5 <= v <= 1.5 for v in values))
        self.assertGreater(max(values) - min(values), 0.5)
        self.assertEqual(meshkit.gradient_noise_2d(3.0, -2.0), 0.0)
        self.assertEqual(meshkit.gradient_noise_3d(1.0, 2.0, 3.0), 0.0)
        self.assertNotEqual(meshkit.fbm_2d(0.3, 0.7, seed=1), meshkit.fbm_2d(0.3, 0.7, seed=2))
        self.assertTrue(-1.5 <= meshkit.fbm_3d(0.3, 0.7, 0.1) <= 1.5)
        self.assertNotEqual(meshkit.hash_integers(1, 2, seed=3), meshkit.hash_integers(2, 1, seed=3))

    def test_gltf_round_trip(self):
        box = meshkit.with_normals(meshkit.box())
        box.uvs = [(v[0] + 0.5, v[2] + 0.5) for v in box.vertices]
        box.colors = [(1.0, 0.5, 0.0, 1.0)] * 8
        box.lines = [(0, 7)]
        nodes = [{"name": "root", "children": [1]}, {"name": "child", "mesh": 0, "translation": (1.0, 0.0, 0.0)}]
        animations = [{"name": "spin", "channels": [{"node": 1, "path": "rotation", "times": [0.0, 1.0],
                                                      "values": [(0, 0, 0, 1), (0, 1, 0, 0)]}]}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "box.gltf"
            summary = meshkit.write_gltf(path, [box], nodes, animations)
            self.assertEqual((summary["vertex_count"], summary["triangle_count"], summary["line_count"]), (10, 12, 1))
            self.assertEqual([p["vertex_count"] for p in summary["meshes"][0]["primitives"]], [8, 2])
            self.assertEqual((summary["nodes"], summary["animations"], summary["scene_nodes"]), (2, 1, [0]))
            back = meshkit.mesh_from_gltf(path)
            self.assertAlmostEqual(meshkit.signed_volume(back), 1.0, places=6)
            worlds = meshkit.node_world_matrices(json.loads(path.read_text()))
            self.assertEqual(worlds[1][0][3], 1.0)
            self.assertEqual(meshkit.gltf_text([box]), meshkit.gltf_text([box]))

    def test_gltf_validator_refuses_corruption(self):
        document = meshkit.gltf_document([meshkit.with_normals(meshkit.box())])
        self.assertEqual(meshkit.read_gltf(document)["triangle_count"], 12)
        data = bytearray(base64.b64decode(document["buffers"][0]["uri"].split(",", 1)[1]))
        index_view = document["bufferViews"][document["accessors"][document["meshes"][0]["primitives"][0]["indices"]]["bufferView"]]

        def rebuilt(payload):
            copy = json.loads(json.dumps(document))
            copy["buffers"][0]["uri"] = "data:application/octet-stream;base64," + base64.b64encode(bytes(payload)).decode()
            return copy

        bad_index = bytearray(data)
        bad_index[index_view["byteOffset"]:index_view["byteOffset"] + 2] = (99).to_bytes(2, "little")
        short = rebuilt(data[:-4])
        wrong_bounds = json.loads(json.dumps(document))
        wrong_bounds["accessors"][0]["max"] = [9.0, 9.0, 9.0]
        bad_normal = bytearray(data)
        normal_view = document["bufferViews"][document["accessors"][1]["bufferView"]]
        bad_normal[normal_view["byteOffset"]:normal_view["byteOffset"] + 4] = struct.pack("<f", 3.0)
        cases = {"index_out_of_range": rebuilt(bad_index), "buffer_length_mismatch": short,
                 "accessor_bounds_wrong": wrong_bounds, "normal_not_unit": rebuilt(bad_normal),
                 "asset_version_invalid": {**document, "asset": {"version": "1.0"}}}
        for reason, broken in cases.items():
            with self.subTest(reason=reason), self.assertRaises(meshkit.GltfError) as caught:
                meshkit.read_gltf(broken)
            self.assertEqual(caught.exception.reason, reason)

    def test_obj_round_trip_and_refusal(self):
        box = meshkit.with_normals(meshkit.box())
        with tempfile.TemporaryDirectory() as folder:
            back = meshkit.write_obj(Path(folder) / "box.obj", [box])
        self.assertEqual((len(back.vertices), len(back.faces)), (8, 6))
        self.assertAlmostEqual(meshkit.signed_volume(back), 1.0, places=12)
        self.assertIn("f 1//1", meshkit.obj_text([box]))
        with self.assertRaises(meshkit.MeshError) as caught:
            meshkit.read_obj("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 9\n")
        self.assertEqual(caught.exception.reason, "index_out_of_range")

    def test_command_line_parser(self):
        parameters = [{"name": "size", "type": "float", "default": 1.0, "minimum": 0.0}]
        parser = meshkit.parameter_parser(parameters, "demo")
        self.assertEqual(parser.parse_args(["--output", "x.gltf", "--size", "2"]).size, 2.0)
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()) as out:
            status = meshkit.run_cli(["--output", str(Path(folder) / "b.gltf"), "--size", "2"], description="demo",
                                     parameters=parameters, build=lambda size: meshkit.box((size, size, size)))
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(out.getvalue())["triangles"], 12)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            meshkit.run_cli(["--output", "b.gltf", "--size", "-1"], description="demo", parameters=parameters,
                            build=lambda size: meshkit.box())


class KnownAnswerTests(unittest.TestCase):
    def cases(self, refusals=False):
        return sorted((name, case) for name, case in CONTRACT["invariants"].items() if ("raises" in case) == refusals)

    def test_declared_cases_hold(self):
        for name, case in self.cases():
            with self.subTest(case=name):
                failures = evaluate(run_case(case), case["expect"])
                self.assertEqual(failures, [], f"{name}: {failures}")

    def test_declared_refusals_hold(self):
        for name, case in self.cases(refusals=True):
            with self.subTest(case=name):
                with self.assertRaises(meshkit.MeshError) as caught:
                    run_case(case)
                self.assertEqual(caught.exception.reason, case["raises"])

    def test_results_are_deterministic(self):
        for name, case in self.cases():
            with self.subTest(case=name):
                self.assertEqual(fingerprint(run_case(case)), fingerprint(run_case(case)))

    def test_wrong_expectations_are_refused(self):
        refused = 0
        for name, case in self.cases():
            result = run_case(case)
            for check, expected in case["expect"].items():
                perturb = CHECKS[check][1] if check in CHECKS else None
                if perturb is None:
                    continue
                with self.subTest(case=name, check=check):
                    self.assertNotEqual(evaluate(result, {check: perturb(resolve(expected))}), [],
                                        f"{name}: a wrong {check} was accepted")
                    refused += 1
        self.assertGreater(refused, 0, "at least one declared value can be made wrong")

    def test_damaged_results_are_refused(self):
        tried = 0
        for name, case in self.cases():
            broken = damaged(run_case(case))
            if broken is None:
                continue
            with self.subTest(case=name):
                self.assertNotEqual(evaluate(broken, case["expect"]), [], f"{name}: a damaged result was accepted")
                tried += 1
        mesh_cases = [name for name, case in self.cases() if any(key in case["expect"] for key in (
            "vertex_count", "face_count", "triangle_count"))]
        if mesh_cases:
            self.assertGreater(tried, 0)


def _formats():
    return {row["format"] for row in CONTRACT["outputs"]}


class CommandLineTests(unittest.TestCase):
    def run_main(self, arguments):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            status = MODULE.main(arguments)
        lines = [line for line in out.getvalue().splitlines() if line.strip()]
        return status, json.loads(lines[-1])

    def test_writes_a_valid_gltf(self):
        self.assertIn("gltf", _formats())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "out.gltf"
            status, summary = self.run_main(["--output", str(path)])
            self.assertEqual(status, 0)
            read = meshkit.read_gltf(path)
        self.assertEqual(summary["triangles"], read["triangle_count"])
        self.assertEqual(summary["vertices"], read["vertex_count"])
        self.assertGreater(read["triangle_count"] + read["line_count"], 0)

    def test_writes_a_valid_obj(self):
        if "obj" not in _formats():
            self.skipTest("the item declares no OBJ output")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "out.obj"
            status, summary = self.run_main(["--output", str(path)])
            mesh = meshkit.read_obj(path)
        self.assertEqual(status, 0)
        self.assertEqual(summary["vertices"], len(mesh.vertices))
        self.assertGreater(len(mesh.faces) + len(mesh.lines), 0)

    def test_out_of_range_parameter_is_refused(self):
        bounded = [row for row in CONTRACT["parameters"] if row.get("minimum") is not None and row["type"] in ("int", "float")]
        if not bounded:
            self.skipTest("no bounded parameter")
        row = bounded[0]
        value = row["minimum"] - 1 if row["type"] == "int" else row["minimum"] - abs(row["minimum"]) - 1.0
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stderr(io.StringIO()), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                MODULE.main(["--output", str(Path(folder) / "x.gltf"), "--" + row["name"].replace("_", "-"), str(value)])
        self.assertEqual(caught.exception.code, 2)

    def test_example_models_match_the_generator(self):
        examples = [row["path"] for row in CARD["files"] if row["path"].endswith(".gltf")]
        if not examples:
            self.skipTest("the package ships no example model")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fresh.gltf"
            self.run_main(["--output", str(path)])
            fresh = meshkit.read_gltf(path)
        for example in examples:
            with self.subTest(example=example):
                shipped = meshkit.read_gltf(ROOT / example)
                self.assertEqual([[(p["mode"], p["vertex_count"], p["index_count"]) for p in m["primitives"]]
                                  for m in shipped["meshes"]],
                                 [[(p["mode"], p["vertex_count"], p["index_count"]) for p in m["primitives"]]
                                  for m in fresh["meshes"]])
                for mesh_a, mesh_b in zip(shipped["meshes"], fresh["meshes"]):
                    for prim_a, prim_b in zip(mesh_a["primitives"], mesh_b["primitives"]):
                        self.assertEqual(prim_a["indices"], prim_b["indices"])
                        scale = max(1.0, max(abs(c) for p in prim_a["positions"] for c in p))
                        worst = max(abs(a - b) for p, q in zip(prim_a["positions"], prim_b["positions"]) for a, b in zip(p, q))
                        self.assertLessEqual(worst, 1e-5 * scale)
                corrupted = json.loads((ROOT / example).read_text(encoding="utf-8"))
                corrupted["buffers"][0]["byteLength"] += 4
                with self.assertRaises(meshkit.GltfError):
                    meshkit.read_gltf(corrupted)


if __name__ == "__main__":
    unittest.main()
