"""fourd: four-dimensional geometry with the Python standard library only.

Points are tuples (x, y, z, w). A projection to 3D keeps (x, y, z) as glTF and Godot coordinates, +Y up.
Quaternions are tuples (a, b, c, d) = a + bi + cj + dk; the point (x, y, z, w) is the quaternion
w + xi + yj + zk, so the hyperplane w = 0 holds the pure imaginary quaternions.

Sections: vectors and matrices; plane rotations and quaternion pairs; projections; Coxeter groups;
convex polytopes (facets, faces, edges, checks); hyperplane slices; 3D meshes; marching tetrahedra;
a text glTF 2.0 writer and a structural glTF checker; a small PNG writer; the polytope JSON record.
"""
from __future__ import annotations

import base64
import itertools
import json
import math
import struct
import zlib
from collections import defaultdict
from functools import lru_cache

VERSION = "1.0.0"
AXES = "xyzw"
PLANES = ("xy", "xz", "xw", "yz", "yw", "zw")
POLYTOPE_RECORD = "fourd_polytope/v1"
#: The largest glTF example a package ships (bytes).
MAXIMUM_EXAMPLE_BYTES = 200 * 1024


# ---------------------------------------------------------------------------------------------------------------
# Vectors and matrices
# ---------------------------------------------------------------------------------------------------------------

def add(a, b):
    """Componentwise sum."""
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    """Componentwise difference a - b."""
    return tuple(x - y for x, y in zip(a, b))


def scale(a, factor):
    """The vector a times a number."""
    return tuple(x * factor for x in a)


def dot(a, b):
    """Euclidean inner product."""
    return sum(x * y for x, y in zip(a, b))


def norm(a):
    """Euclidean length."""
    return math.sqrt(dot(a, a))


def normalize(a):
    """The unit vector along a; a zero vector is refused."""
    length = norm(a)
    if length <= 1e-15:
        raise ValueError("cannot normalize a zero vector")
    return tuple(x / length for x in a)


def distance(a, b):
    """Euclidean distance between two points."""
    return norm(sub(a, b))


def lerp(a, b, t):
    """The point a + t (b - a)."""
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def centroid(points):
    """Mean of a non-empty list of points."""
    points = list(points)
    if not points:
        raise ValueError("centroid of no points")
    count = len(points)
    return tuple(sum(point[index] for point in points) / count for index in range(len(points[0])))


def angle_between(a, b):
    """The angle in radians between two non-zero vectors."""
    value = dot(a, b) / (norm(a) * norm(b))
    return math.acos(max(-1.0, min(1.0, value)))


def cross3(a, b):
    """The 3D cross product."""
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def cross4(a, b, c):
    """The vector x orthogonal to a, b and c with x . d = det[a, b, c, d] for every d (generalized cross product)."""
    result = []
    for index in range(4):
        axis = [0.0] * 4
        axis[index] = 1.0
        result.append(determinant([a, b, c, axis]))
    return tuple(result)


def identity(size=4):
    """The identity matrix as a tuple of rows."""
    return tuple(tuple(1.0 if row == column else 0.0 for column in range(size)) for row in range(size))


def matmul(a, b):
    """Matrix product a b (rows of tuples)."""
    columns = list(zip(*b))
    return tuple(tuple(sum(x * y for x, y in zip(row, column)) for column in columns) for row in a)


def matvec(matrix, vector):
    """Matrix times column vector."""
    return tuple(sum(x * y for x, y in zip(row, vector)) for row in matrix)


def transpose(matrix):
    """The transposed matrix."""
    return tuple(tuple(column) for column in zip(*matrix))


def determinant(matrix):
    """Determinant by Gaussian elimination with partial pivoting."""
    rows = [list(map(float, row)) for row in matrix]
    size = len(rows)
    if any(len(row) != size for row in rows):
        raise ValueError("determinant of a non-square matrix")
    result = 1.0
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(rows[row][column]))
        if rows[pivot][column] == 0.0:
            return 0.0
        if pivot != column:
            rows[column], rows[pivot] = rows[pivot], rows[column]
            result = -result
        lead = rows[column][column]
        result *= lead
        for row in range(column + 1, size):
            factor = rows[row][column] / lead
            if factor:
                for index in range(column, size):
                    rows[row][index] -= factor * rows[column][index]
    return result


def solve(matrix, vector):
    """The x with matrix x = vector, by Gaussian elimination; a singular matrix is refused."""
    size = len(matrix)
    rows = [list(map(float, row)) + [float(value)] for row, value in zip(matrix, vector)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(rows[row][column]))
        if abs(rows[pivot][column]) < 1e-12:
            raise ValueError("singular matrix")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        lead = rows[column][column]
        rows[column] = [value / lead for value in rows[column]]
        for row in range(size):
            if row != column and rows[row][column]:
                factor = rows[row][column]
                rows[row] = [value - factor * other for value, other in zip(rows[row], rows[column])]
    return tuple(row[size] for row in rows)


def _row_reduce(matrix, tolerance):
    rows = [list(map(float, row)) for row in matrix]
    if not rows:
        return rows, []
    width = len(rows[0])
    largest = max((abs(value) for row in rows for value in row), default=0.0) or 1.0
    pivots, current = [], 0
    for column in range(width):
        if current >= len(rows):
            break
        pivot = max(range(current, len(rows)), key=lambda row: abs(rows[row][column]))
        if abs(rows[pivot][column]) <= tolerance * largest:
            continue
        rows[current], rows[pivot] = rows[pivot], rows[current]
        lead = rows[current][column]
        rows[current] = [value / lead for value in rows[current]]
        for row in range(len(rows)):
            if row != current and rows[row][column]:
                factor = rows[row][column]
                rows[row] = [value - factor * other for value, other in zip(rows[row], rows[current])]
        pivots.append(column)
        current += 1
    return rows, pivots


def rank(matrix, tolerance=1e-9):
    """Numerical rank of a list of rows."""
    return len(_row_reduce(matrix, tolerance)[1])


def null_space(matrix, tolerance=1e-9):
    """A basis of the vectors x with matrix x = 0 (from the reduced row echelon form)."""
    rows, pivots = _row_reduce(matrix, tolerance)
    width = len(matrix[0])
    basis = []
    for free in (column for column in range(width) if column not in pivots):
        vector = [0.0] * width
        vector[free] = 1.0
        for row, column in enumerate(pivots):
            vector[column] = -rows[row][free]
        basis.append(tuple(vector))
    return basis


def is_rotation(matrix, tolerance=1e-9):
    """True when the square matrix is orthogonal with determinant +1."""
    size = len(matrix)
    product = matmul(matrix, transpose(matrix))
    for row in range(size):
        for column in range(size):
            if abs(product[row][column] - (1.0 if row == column else 0.0)) > tolerance:
                return False
    return determinant(matrix) > 0.0


def orthonormalize(matrix):
    """Gram-Schmidt on the rows; the result is orthogonal with determinant +1 (drift repair for long animations)."""
    rows = []
    for row in matrix:
        vector = tuple(map(float, row))
        for previous in rows:
            vector = sub(vector, scale(previous, dot(vector, previous)))
        rows.append(normalize(vector))
    if determinant(rows) < 0.0:
        rows[-1] = scale(rows[-1], -1.0)
    return tuple(rows)


# ---------------------------------------------------------------------------------------------------------------
# Rotations: the six coordinate planes, and pairs of unit quaternions
# ---------------------------------------------------------------------------------------------------------------

def _plane_axes(plane):
    if not isinstance(plane, str) or len(plane) != 2 or plane[0] == plane[1] or any(axis not in AXES for axis in plane):
        raise ValueError(f"plane is two of x, y, z, w, such as xw: {plane!r}")
    return AXES.index(plane[0]), AXES.index(plane[1])


def plane_rotation(plane, angle):
    """Rotation by angle (radians) in a coordinate plane: the first axis turns toward the second ("xw": x toward w)."""
    first, second = _plane_axes(plane)
    cosine, sine = math.cos(angle), math.sin(angle)
    rows = [list(row) for row in identity(4)]
    rows[first][first] = cosine
    rows[second][second] = cosine
    rows[second][first] = sine
    rows[first][second] = -sine
    return tuple(tuple(row) for row in rows)


def parse_rotation(text):
    """Parse "xw=0.6,yz=0.3" (radians, or a value ending in deg) into [(plane, radians), ...]."""
    pairs = []
    if not isinstance(text, str):
        raise ValueError("rotation text is a string like xw=0.6,yz=0.3")
    for part in (piece.strip() for piece in text.split(",")):
        if not part:
            continue
        name, separator, value = part.partition("=")
        if not separator:
            raise ValueError(f"rotation term needs plane=angle: {part!r}")
        name = name.strip().lower()
        _plane_axes(name)
        value = value.strip().lower()
        factor = 1.0
        if value.endswith("deg"):
            value, factor = value[:-3], math.pi / 180.0
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"rotation angle is finite: {part!r}")
        pairs.append((name, number * factor))
    return pairs


def rotation_matrix(spec):
    """Compose plane rotations, applied in the order given; spec is text ("xw=0.6,yz=0.3") or (plane, angle) pairs."""
    pairs = parse_rotation(spec) if isinstance(spec, str) else list(spec)
    result = identity(4)
    for plane, angle in pairs:
        result = matmul(plane_rotation(plane, angle), result)
    return result


def rotate_points(matrix, points):
    """Apply a 4x4 matrix to every point."""
    return [matvec(matrix, point) for point in points]


def quat_mul(p, q):
    """Hamilton product p q of quaternions (a, b, c, d)."""
    a1, b1, c1, d1 = p
    a2, b2, c2, d2 = q
    return (a1 * a2 - b1 * b2 - c1 * c2 - d1 * d2,
            a1 * b2 + b1 * a2 + c1 * d2 - d1 * c2,
            a1 * c2 - b1 * d2 + c1 * a2 + d1 * b2,
            a1 * d2 + b1 * c2 - c1 * b2 + d1 * a2)


def quat_conjugate(q):
    """The conjugate a - bi - cj - dk."""
    return (q[0], -q[1], -q[2], -q[3])


def quat_normalize(q):
    """The unit quaternion along q."""
    return normalize(q)


def quat_from_axis_angle(axis, angle):
    """Unit quaternion cos(angle/2) + sin(angle/2) (axis), the 3D rotation by angle about axis under conjugation."""
    unit = normalize(axis)
    half = angle / 2.0
    return (math.cos(half),) + scale(unit, math.sin(half))


def point_to_quaternion(point):
    """(x, y, z, w) -> w + xi + yj + zk."""
    return (point[3], point[0], point[1], point[2])


def quaternion_to_point(q):
    """w + xi + yj + zk -> (x, y, z, w)."""
    return (q[1], q[2], q[3], q[0])


def quaternion_pair_matrix(left, right):
    """The 4x4 matrix of p -> left * p * right; unit quaternions give a rotation of 4-space (every rotation is one)."""
    columns = []
    for index in range(4):
        axis = [0.0] * 4
        axis[index] = 1.0
        columns.append(quaternion_to_point(quat_mul(quat_mul(left, point_to_quaternion(axis)), right)))
    return transpose(columns)


# ---------------------------------------------------------------------------------------------------------------
# Projections from 4-space to 3-space
# ---------------------------------------------------------------------------------------------------------------

def perspective(point, eye_distance=3.0):
    """Central projection from the eye (0, 0, 0, d) onto w = 0: (x, y, z) * d / (d - w); points at or past the eye are refused."""
    depth = eye_distance - point[3]
    if depth <= 1e-9:
        raise ValueError("point at or behind the 4D eye")
    factor = eye_distance / depth
    return (point[0] * factor, point[1] * factor, point[2] * factor)


def stereographic(point, radius=None):
    """Stereographic projection of the 3-sphere of the given radius (default |point|) from its pole (0, 0, 0, r)."""
    radius = norm(point) if radius is None else radius
    depth = radius - point[3]
    if radius <= 0.0 or depth <= 1e-12 * radius:
        raise ValueError("point at the projection pole")
    factor = radius / depth
    return (point[0] * factor, point[1] * factor, point[2] * factor)


def orthographic(point):
    """Parallel projection along w: drop the fourth coordinate."""
    return (point[0], point[1], point[2])


PROJECTIONS = (PERSPECTIVE, STEREOGRAPHIC, ORTHOGRAPHIC) = ("perspective", "stereographic", "orthographic")


def project_points(points, mode="perspective", eye_distance=3.0, radius=None):
    """Project every point with one of PROJECTIONS."""
    if mode == PERSPECTIVE:
        return [perspective(point, eye_distance) for point in points]
    if mode == STEREOGRAPHIC:
        if radius is None:
            radius = max(norm(point) for point in points)
        return [stereographic(point, radius) for point in points]
    if mode == ORTHOGRAPHIC:
        return [orthographic(point) for point in points]
    raise ValueError(f"projection is one of {PROJECTIONS}")


# ---------------------------------------------------------------------------------------------------------------
# Finite Coxeter groups of rank 4
# ---------------------------------------------------------------------------------------------------------------

#: Branches of each rank 4 Coxeter diagram: (node, node) -> m, the order of the product of the two reflections.
#: Node 0 is the first mirror of the Schlafli symbol {p,q,r}: m01 = p, m12 = q, m23 = r (D4 branches at node 1).
COXETER_DIAGRAMS = {
    "A4": {(0, 1): 3, (1, 2): 3, (2, 3): 3},
    "B4": {(0, 1): 4, (1, 2): 3, (2, 3): 3},
    "D4": {(0, 1): 3, (1, 2): 3, (1, 3): 3},
    "F4": {(0, 1): 3, (1, 2): 4, (2, 3): 3},
    "H4": {(0, 1): 5, (1, 2): 3, (2, 3): 3},
}
GROUP_ORDERS = {"A4": 120, "B4": 384, "D4": 192, "F4": 1152, "H4": 14400}
COXETER_NUMBERS = {"A4": 5, "B4": 8, "D4": 6, "F4": 12, "H4": 30}


def coxeter_gram(group):
    """The Gram matrix of unit simple roots: 1 on the diagonal, -cos(pi/m) on a branch, 0 elsewhere."""
    if group not in COXETER_DIAGRAMS:
        raise ValueError(f"group is one of {sorted(COXETER_DIAGRAMS)}")
    gram = [[1.0 if row == column else 0.0 for column in range(4)] for row in range(4)]
    for (first, second), order in COXETER_DIAGRAMS[group].items():
        gram[first][second] = gram[second][first] = -math.cos(math.pi / order)
    return gram


def simple_roots(group):
    """Unit simple roots: axis-aligned coordinates for B4 and F4, a Cholesky factor of the Gram matrix otherwise."""
    half = math.sqrt(0.5)
    if group == "B4":
        return [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, half, -half), (0.0, half, -half, 0.0), (half, -half, 0.0, 0.0)]
    if group == "F4":
        return [(0.0, half, -half, 0.0), (0.0, 0.0, half, -half), (0.0, 0.0, 0.0, 1.0), (0.5, -0.5, -0.5, -0.5)]
    gram = coxeter_gram(group)
    lower = [[0.0] * 4 for _ in range(4)]
    for row in range(4):
        for column in range(row + 1):
            value = gram[row][column] - sum(lower[row][k] * lower[column][k] for k in range(column))
            if row == column:
                if value <= 1e-12:
                    raise ValueError("Gram matrix is not positive definite")
                lower[row][column] = math.sqrt(value)
            else:
                lower[row][column] = value / lower[column][column]
    return [tuple(row) for row in lower]


def reflect(vector, root):
    """Reflection of a vector in the hyperplane orthogonal to root."""
    return sub(vector, scale(root, 2.0 * dot(vector, root) / dot(root, root)))


def point_key(point, digits=8):
    """A hashable key of a point rounded to `digits` decimals (minus zero folded to zero), for merging duplicates."""
    return tuple(round(value, digits) + 0.0 for value in point)


def orbit(point, roots, limit=20000):
    """Every image of a point under the group generated by reflections in the roots (sorted, duplicates merged)."""
    start = tuple(float(value) for value in point)
    seen = {point_key(start): start}
    frontier = [start]
    while frontier:
        found = []
        for current in frontier:
            for root in roots:
                image = reflect(current, root)
                key = point_key(image)
                if key not in seen:
                    seen[key] = image
                    found.append(image)
                    if len(seen) > limit:
                        raise ValueError(f"orbit larger than {limit} points")
        frontier = found
    return [seen[key] for key in sorted(seen)]


def wythoff_point(roots, ringed, edge=1.0):
    """The point at distance edge/2 from each ringed mirror and on every other mirror (the Wythoff construction)."""
    units = [normalize(root) for root in roots]
    ringed = set(ringed)
    if not ringed or not ringed <= set(range(len(units))):
        raise ValueError("ringed is a non-empty set of node indices")
    return solve(units, [edge / 2.0 if index in ringed else 0.0 for index in range(len(units))])


def fundamental_weights(roots):
    """The vectors w_i with unit(root_j) . w_i = 1 when i = j and 0 otherwise."""
    units = [normalize(root) for root in roots]
    weights = []
    for index in range(len(units)):
        target = [0.0] * len(units)
        target[index] = 1.0
        weights.append(solve(units, target))
    return weights


# ---------------------------------------------------------------------------------------------------------------
# Convex polytopes: {"vertices": [...], "edges": [(i, j)], "faces": [[cycle]], "cells": [[face index]]}
# ---------------------------------------------------------------------------------------------------------------

def affine_dimension(points, tolerance=1e-7):
    """Dimension of the affine hull of the points (-1 for none)."""
    points = list(points)
    if not points:
        return -1
    base = points[0]
    differences = [sub(point, base) for point in points[1:]]
    size = max((norm(difference) for difference in differences), default=0.0)
    if size <= tolerance:
        return 0
    return rank([scale(difference, 1.0 / size) for difference in differences], tolerance)


def order_cycle(points, indices):
    """The indices of coplanar points (any dimension) sorted by angle about their centroid."""
    indices = list(indices)
    if len(indices) < 3:
        return indices
    selected = [points[index] for index in indices]
    middle = centroid(selected)
    offsets = [sub(point, middle) for point in selected]
    first = max(offsets, key=norm)
    axis_u = normalize(first)
    best, axis_v = 0.0, None
    for offset in offsets:
        rest = sub(offset, scale(axis_u, dot(offset, axis_u)))
        if norm(rest) > best:
            best, axis_v = norm(rest), rest
    if axis_v is None or best <= 1e-12:
        raise ValueError("points are collinear")
    axis_v = normalize(axis_v)
    angles = [math.atan2(dot(offset, axis_v), dot(offset, axis_u)) for offset in offsets]
    return [index for _angle, index in sorted(zip(angles, indices))]


def edges_by_length(vertices, length=None, tolerance=1e-6):
    """Vertex pairs at the given distance (default: the smallest distance), sorted."""
    count = len(vertices)
    squared = []
    smallest = math.inf
    for first in range(count):
        a = vertices[first]
        for second in range(first + 1, count):
            b = vertices[second]
            value = sum((x - y) * (x - y) for x, y in zip(a, b))
            squared.append((value, first, second))
            if value < smallest:
                smallest = value
    target = smallest if length is None else length * length
    if target <= 0.0 or not math.isfinite(target):
        raise ValueError("coincident or missing vertices")
    limit = tolerance * max(1.0, target)
    return sorted((first, second) for value, first, second in squared if abs(value - target) <= limit)


def polytope_from_facets(vertices, normals, tolerance=1e-7):
    """Faces, edges and cells of a convex 4-polytope from its vertices and outward facet normal directions.

    A cell is the vertex set maximizing n . v whose affine hull is 3-dimensional; a 2-face is a 2-dimensional
    intersection of two cells, ordered as a cycle; the edges are the sides of the 2-faces."""
    vertices = [tuple(float(value) for value in vertex) for vertex in vertices]
    reach = max(norm(vertex) for vertex in vertices) or 1.0
    cells, seen = [], set()
    for normal in normals:
        unit = normalize(normal)
        heights = [dot(vertex, unit) for vertex in vertices]
        top = max(heights)
        members = tuple(index for index, height in enumerate(heights) if height >= top - tolerance * reach)
        if len(members) < 4 or members in seen:
            continue
        if affine_dimension([vertices[index] for index in members], tolerance) != 3:
            continue
        seen.add(members)
        cells.append(members)
    containing = defaultdict(list)
    for cell_index, members in enumerate(cells):
        for vertex in members:
            containing[vertex].append(cell_index)
    face_keys, face_cells = {}, defaultdict(list)
    for cell_index, members in enumerate(cells):
        shared = defaultdict(int)
        for vertex in members:
            for other in containing[vertex]:
                if other > cell_index:
                    shared[other] += 1
        for other, count in sorted(shared.items()):
            if count < 3:
                continue
            common = tuple(sorted(set(members) & set(cells[other])))
            if affine_dimension([vertices[index] for index in common], tolerance) != 2:
                continue
            if common not in face_keys:
                face_keys[common] = len(face_keys)
            face_cells[common] += [cell_index, other]
    faces = [order_cycle(vertices, common) for common in face_keys]
    cell_faces = [[] for _ in cells]
    for common, index in face_keys.items():
        for cell_index in set(face_cells[common]):
            cell_faces[cell_index].append(index)
    edges = sorted({tuple(sorted(pair)) for face in faces for pair in zip(face, face[1:] + face[:1])})
    return {"vertices": vertices, "edges": edges, "faces": faces, "cells": [sorted(row) for row in cell_faces]}


def f_vector(polytope):
    """(vertices, edges, faces, cells) counts."""
    return (len(polytope["vertices"]), len(polytope["edges"]), len(polytope.get("faces", [])),
            len(polytope.get("cells", [])))


def euler_characteristic(polytope):
    """V - E + F - C; zero for the boundary of every convex 4-polytope."""
    vertices, edges, faces, cells = f_vector(polytope)
    return vertices - edges + faces - cells


def cell_vertex_sets(polytope):
    """The vertex index set of every cell."""
    faces = polytope["faces"]
    return [frozenset(vertex for face in cell for vertex in faces[face]) for cell in polytope["cells"]]


def regularity_report(polytope, tolerance=1e-6):
    """Checks a regular polytope passes: one circumradius about the centroid, one edge length, one vertex degree,
    one face size and one face count per cell. Moving a single vertex fails it."""
    vertices = polytope["vertices"]
    middle = centroid(vertices)
    radii = [distance(vertex, middle) for vertex in vertices]
    lengths = [distance(vertices[a], vertices[b]) for a, b in polytope["edges"]]
    degree = defaultdict(int)
    for a, b in polytope["edges"]:
        degree[a] += 1
        degree[b] += 1
    face_sizes = {len(face) for face in polytope.get("faces", [])}
    cell_sizes = {len(cell) for cell in polytope.get("cells", [])}
    radius_spread = max(radii) - min(radii)
    edge_spread = max(lengths) - min(lengths) if lengths else 0.0
    degrees = {degree[index] for index in range(len(vertices))}
    regular = (radius_spread <= tolerance * max(radii) and edge_spread <= tolerance * max(lengths)
               and len(degrees) == 1 and len(face_sizes) <= 1 and len(cell_sizes) <= 1)
    return {"circumradius": sum(radii) / len(radii), "edge_length": sum(lengths) / max(1, len(lengths)),
            "radius_spread": radius_spread, "edge_spread": edge_spread, "degrees": sorted(degrees),
            "face_sizes": sorted(face_sizes), "cell_face_counts": sorted(cell_sizes), "regular": regular}


def schlafli_symbol(polytope):
    """(p, q, r) when every face has p sides, every cell has q faces at each of its vertices and every edge lies
    in r cells; None when any of these varies (the polytope is then not regular)."""
    faces, cells = polytope["faces"], polytope["cells"]
    sides = {len(face) for face in faces}
    at_vertex, at_edge = set(), defaultdict(set)
    for cell_index, cell in enumerate(cells):
        count = defaultdict(int)
        for face_index in cell:
            face = faces[face_index]
            for vertex in face:
                count[vertex] += 1
            for a, b in zip(face, face[1:] + face[:1]):
                at_edge[(min(a, b), max(a, b))].add(cell_index)
        at_vertex.update(count.values())
    around = {len(members) for members in at_edge.values()}
    if len(sides) != 1 or len(at_vertex) != 1 or len(around) != 1:
        return None
    return (sides.pop(), at_vertex.pop(), around.pop())


def cell_volume(polytope, cell_index):
    """The 3-volume of one cell, from tetrahedra coned at one of its vertices (Gram determinants)."""
    faces, vertices = polytope["faces"], polytope["vertices"]
    cell = polytope["cells"][cell_index]
    apex = faces[cell[0]][0]
    total = 0.0
    for face_index in cell:
        face = faces[face_index]
        if apex in face:
            continue
        for second, third in zip(face[1:-1], face[2:]):
            spans = [sub(vertices[corner], vertices[apex]) for corner in (face[0], second, third)]
            gram = [[dot(a, b) for b in spans] for a in spans]
            total += math.sqrt(max(0.0, determinant(gram))) / 6.0
    return total


def hypervolume(polytope):
    """The 4-volume: pyramids from the vertex centroid over every cell, height times cell volume over 4."""
    vertices = polytope["vertices"]
    middle = centroid(vertices)
    total = 0.0
    for cell_index, members in enumerate(cell_vertex_sets(polytope)):
        members = sorted(members)
        base = vertices[members[0]]
        normal = null_space([sub(vertices[index], base) for index in members[1:]], 1e-9)
        if len(normal) != 1:
            raise ValueError(f"cell {cell_index} does not span a hyperplane")
        height = abs(dot(normalize(normal[0]), sub(base, middle)))
        total += height * cell_volume(polytope, cell_index) / 4.0
    return total


def polytope_problems(polytope, tolerance=1e-7):
    """Structural problems of a 4-polytope record (an empty list when it is a closed polytope boundary)."""
    problems = []
    vertices = polytope.get("vertices", [])
    count = len(vertices)
    edges = [tuple(edge) for edge in polytope.get("edges", [])]
    edge_set = set()
    for edge in edges:
        if len(edge) != 2 or not all(isinstance(index, int) and 0 <= index < count for index in edge) or edge[0] >= edge[1]:
            problems.append(f"edge {edge} is not an ordered pair of vertex indices")
        elif edge in edge_set:
            problems.append(f"edge {edge} repeated")
        edge_set.add(edge)
    faces = polytope.get("faces", [])
    valid = set()
    for index, face in enumerate(faces):
        if len(face) < 3 or len(set(face)) != len(face) or not all(isinstance(v, int) and 0 <= v < count for v in face):
            problems.append(f"face {index} is not a cycle of distinct vertex indices")
            continue
        valid.add(index)
        for a, b in zip(face, face[1:] + face[:1]):
            if (min(a, b), max(a, b)) not in edge_set:
                problems.append(f"face {index} side {a}-{b} is not an edge")
        if affine_dimension([vertices[v] for v in face], tolerance) != 2:
            problems.append(f"face {index} is not planar")
    used = defaultdict(int)
    for index, cell in enumerate(polytope.get("cells", [])):
        sides = defaultdict(int)
        for face_index in cell:
            if not isinstance(face_index, int) or not 0 <= face_index < len(faces):
                problems.append(f"cell {index} names face {face_index}")
                continue
            used[face_index] += 1
            face = faces[face_index]
            for a, b in zip(face, face[1:] + face[:1]):
                sides[(min(a, b), max(a, b))] += 1
        if any(value != 2 for value in sides.values()):
            problems.append(f"cell {index} is not a closed surface")
        members = {v for face_index in cell if face_index in valid for v in faces[face_index]}
        if members and affine_dimension([vertices[v] for v in members], tolerance) != 3:
            problems.append(f"cell {index} is not 3-dimensional")
    if polytope.get("cells"):
        for face_index in range(len(faces)):
            if used[face_index] != 2:
                problems.append(f"face {face_index} lies in {used[face_index]} cells, not 2")
    in_faces = {(min(a, b), max(a, b)) for index, face in enumerate(faces) if index in valid
                for a, b in zip(face, face[1:] + face[:1])}
    if faces and in_faces != edge_set:
        problems.append("the edges are not exactly the sides of the faces")
    return problems


def polytope_record(polytope, name="polytope"):
    """The polytope as a JSON-ready fourd_polytope/v1 record."""
    return {"record_type": POLYTOPE_RECORD, "name": name,
            "vertices": [[round(value, 12) + 0.0 for value in vertex] for vertex in polytope["vertices"]],
            "edges": [list(edge) for edge in polytope["edges"]], "faces": [list(face) for face in polytope.get("faces", [])],
            "cells": [list(cell) for cell in polytope.get("cells", [])]}


def polytope_from_record(record):
    """Read a fourd_polytope/v1 record back; a record with structural problems is refused."""
    if not isinstance(record, dict) or record.get("record_type") != POLYTOPE_RECORD:
        raise ValueError(f"record_type is {POLYTOPE_RECORD}")
    vertices = [tuple(float(value) for value in vertex) for vertex in record["vertices"]]
    if any(len(vertex) != 4 or not all(math.isfinite(value) for value in vertex) for vertex in vertices):
        raise ValueError("vertices are finite 4-vectors")
    polytope = {"vertices": vertices, "edges": [tuple(edge) for edge in record["edges"]],
                "faces": [list(face) for face in record.get("faces", [])],
                "cells": [list(cell) for cell in record.get("cells", [])]}
    problems = polytope_problems(polytope)
    if problems:
        raise ValueError("polytope record refused: " + "; ".join(problems[:3]))
    return polytope


# ---------------------------------------------------------------------------------------------------------------
# Hyperplane slices of convex polytopes
# ---------------------------------------------------------------------------------------------------------------

def hyperplane_basis(normal):
    """Three orthonormal vectors spanning the hyperplane orthogonal to normal, right-handed with it.

    For normal = (0, 0, 0, 1) the basis is the x, y and z axes."""
    unit = normalize(normal)
    basis = []
    for axis in identity(4):
        vector = sub(axis, scale(unit, dot(axis, unit)))
        for previous in basis:
            vector = sub(vector, scale(previous, dot(vector, previous)))
        if norm(vector) > 1e-6:
            basis.append(normalize(vector))
        if len(basis) == 3:
            break
    if determinant([basis[0], basis[1], basis[2], unit]) < 0.0:
        basis[2] = scale(basis[2], -1.0)
    return basis


def polygon_normal(points):
    """Newell's normal of a 3D polygon; it follows the right-hand rule of the vertex order."""
    nx = ny = nz = 0.0
    for (x1, y1, z1), (x2, y2, z2) in zip(points, points[1:] + points[:1]):
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return (nx, ny, nz)


def polyhedron_volume(points, faces):
    """Volume of a closed 3D polyhedron with outward-ordered faces (divergence theorem)."""
    total = 0.0
    for face in faces:
        origin = points[face[0]]
        for second, third in zip(face[1:-1], face[2:]):
            total += dot(origin, cross3(points[second], points[third]))
    return total / 6.0


def slice_polytope(polytope, normal, offset=0.0, tolerance=1e-9):
    """The exact cross-section {p : n . p = offset} of a convex 4-polytope.

    Slice vertices are the polytope vertices on the hyperplane and the crossings of edges; each cell meeting the
    hyperplane in a polygon gives one face. Points are returned in 4D and in the hyperplane's own 3D coordinates
    (hyperplane_basis), faces ordered counter-clockwise seen from outside, with the edge list and the volume."""
    unit = normalize(normal)
    basis = hyperplane_basis(unit)
    vertices = polytope["vertices"]
    heights = [dot(vertex, unit) - offset for vertex in vertices]
    limit = tolerance * max(1.0, max(abs(height) for height in heights))
    points = {}
    for index, height in enumerate(heights):
        if abs(height) <= limit:
            points[("v", index)] = vertices[index]
    for first, second in polytope["edges"]:
        h1, h2 = heights[first], heights[second]
        if (h1 < -limit and h2 > limit) or (h1 > limit and h2 < -limit):
            points[("e", min(first, second), max(first, second))] = lerp(vertices[first], vertices[second],
                                                                         h1 / (h1 - h2))
    faces = polytope["faces"]
    polygons, seen = [], set()
    for cell in polytope["cells"]:
        keys = set()
        for face_index in cell:
            face = faces[face_index]
            for vertex in face:
                if ("v", vertex) in points:
                    keys.add(("v", vertex))
            for a, b in zip(face, face[1:] + face[:1]):
                key = ("e", min(a, b), max(a, b))
                if key in points:
                    keys.add(key)
        if len(keys) < 3:
            continue
        frozen = frozenset(keys)
        if frozen in seen or affine_dimension([points[key] for key in keys]) != 2:
            continue
        seen.add(frozen)
        polygons.append(sorted(keys))
    keys = sorted(points)
    index = {key: position for position, key in enumerate(keys)}
    points4 = [points[key] for key in keys]
    points3 = [tuple(dot(point, axis) for axis in basis) for point in points4]
    result_faces = []
    if points3:
        middle = centroid(points3)
        for polygon in polygons:
            ordered = order_cycle(points3, [index[key] for key in polygon])
            outward = sub(centroid([points3[i] for i in ordered]), middle)
            if dot(polygon_normal([points3[i] for i in ordered]), outward) < 0.0:
                ordered.reverse()
            result_faces.append(ordered)
    edges = sorted({tuple(sorted(pair)) for face in result_faces for pair in zip(face, face[1:] + face[:1])})
    return {"normal": unit, "offset": offset, "basis": basis, "keys": keys, "points4": points4, "points3": points3,
            "faces": result_faces, "edges": edges,
            "volume": polyhedron_volume(points3, result_faces) if result_faces else 0.0}


# ---------------------------------------------------------------------------------------------------------------
# 3D meshes: {"positions", "normals", "indices", "colors", "mode"}; mode 4 triangles, 1 lines, 0 points
# ---------------------------------------------------------------------------------------------------------------

def depth_color(t):
    """A colour for a depth value t in [0, 1]: blue, through magenta, to amber (RGBA, linear 0..1)."""
    t = max(0.0, min(1.0, float(t)))
    stops = ((0.12, 0.42, 0.95), (0.80, 0.25, 0.72), (1.0, 0.68, 0.18))
    if t <= 0.5:
        colour = lerp(stops[0], stops[1], t * 2.0)
    else:
        colour = lerp(stops[1], stops[2], (t - 0.5) * 2.0)
    return colour + (1.0,)


def depth_colors(values):
    """depth_color for every value, scaled to the values' own range."""
    values = list(values)
    low, high = min(values), max(values)
    span = high - low
    return [depth_color(0.5 if span <= 1e-12 else (value - low) / span) for value in values]


def palette(count, saturation=0.62, value=0.95):
    """`count` distinct RGBA colours, hues stepped by the golden angle."""
    colours = []
    for index in range(count):
        hue = (0.07 + index * 0.6180339887498949) % 1.0
        sector = hue * 6.0
        chroma = value * saturation
        middle = chroma * (1.0 - abs(sector % 2.0 - 1.0))
        rgb = [(chroma, middle, 0.0), (middle, chroma, 0.0), (0.0, chroma, middle), (0.0, middle, chroma),
               (middle, 0.0, chroma), (chroma, 0.0, middle)][int(sector) % 6]
        floor = value - chroma
        colours.append((rgb[0] + floor, rgb[1] + floor, rgb[2] + floor, 1.0))
    return colours


def tube_mesh(points, edges, radius, sides=8, colors=None):
    """A cylinder of the given radius around every edge between 3D points (no caps), outward normals."""
    positions, normals, indices, result_colors = [], [], [], []
    for first, second in edges:
        a, b = points[first], points[second]
        direction = sub(b, a)
        length = norm(direction)
        if length <= 1e-12:
            continue
        direction = scale(direction, 1.0 / length)
        helper = (1.0, 0.0, 0.0) if abs(direction[0]) < 0.9 else (0.0, 1.0, 0.0)
        axis_u = normalize(cross3(direction, helper))
        axis_v = cross3(direction, axis_u)
        base = len(positions)
        for step in range(sides):
            angle = 2.0 * math.pi * step / sides
            radial = add(scale(axis_u, math.cos(angle)), scale(axis_v, math.sin(angle)))
            positions += [add(a, scale(radial, radius)), add(b, scale(radial, radius))]
            normals += [radial, radial]
            if colors is not None:
                result_colors += [colors[first], colors[second]]
        for step in range(sides):
            following = (step + 1) % sides
            a0, b0 = base + 2 * step, base + 2 * step + 1
            a1, b1 = base + 2 * following, base + 2 * following + 1
            indices += [a0, a1, b0, b0, a1, b1]
    return {"positions": positions, "normals": normals, "indices": indices,
            "colors": result_colors if colors is not None else None, "mode": 4}


def curve_tube(points, radius, sides=6, closed=False, colors=None):
    """A smooth tube swept along a 3D polyline: one ring of `sides` vertices per point, frames carried by parallel
    transport. On a closed curve the leftover twist at the seam is spread evenly along the curve."""
    count = len(points)
    if count < 2 or sides < 3:
        raise ValueError("a tube needs two points and three sides")
    tangents = []
    for index in range(count):
        if closed:
            before, after = points[index - 1], points[(index + 1) % count]
        else:
            before, after = points[max(0, index - 1)], points[min(count - 1, index + 1)]
        tangents.append(normalize(sub(after, before)))
    helper = (1.0, 0.0, 0.0) if abs(tangents[0][0]) < 0.9 else (0.0, 1.0, 0.0)
    normals = [normalize(cross3(cross3(tangents[0], helper), tangents[0]))]
    for tangent in tangents[1:]:
        previous = normals[-1]
        candidate = sub(previous, scale(tangent, dot(previous, tangent)))
        normals.append(normalize(candidate) if norm(candidate) > 1e-9 else previous)
    if closed:
        last = sub(normals[-1], scale(tangents[0], dot(normals[-1], tangents[0])))
        twist = math.atan2(dot(cross3(normals[0], last), tangents[0]), dot(normals[0], last)) if norm(last) > 1e-9 else 0.0
        adjusted = []
        for index, (normal, tangent) in enumerate(zip(normals, tangents)):
            angle = -twist * index / count
            binormal = cross3(tangent, normal)
            adjusted.append(add(scale(normal, math.cos(angle)), scale(binormal, math.sin(angle))))
        normals = adjusted
    positions, vertex_normals, indices, vertex_colors = [], [], [], []
    for index, (point, tangent, normal) in enumerate(zip(points, tangents, normals)):
        binormal = cross3(tangent, normal)
        for step in range(sides):
            angle = 2.0 * math.pi * step / sides
            radial = add(scale(normal, math.cos(angle)), scale(binormal, math.sin(angle)))
            positions.append(add(point, scale(radial, radius)))
            vertex_normals.append(radial)
            if colors is not None:
                vertex_colors.append(colors[index])
    rings = count if closed else count - 1
    for ring in range(rings):
        following = (ring + 1) % count
        for step in range(sides):
            nxt = (step + 1) % sides
            a, b = ring * sides + step, ring * sides + nxt
            c, d = following * sides + nxt, following * sides + step
            indices += [a, b, c, a, c, d]
    return {"positions": positions, "normals": vertex_normals, "indices": indices,
            "colors": vertex_colors if colors is not None else None, "mode": 4}


@lru_cache(maxsize=4)
def _icosphere(subdivisions):
    golden = (1.0 + math.sqrt(5.0)) / 2.0
    corners = []
    for a in (-1.0, 1.0):
        for b in (-golden, golden):
            corners += [(0.0, a, b), (a, b, 0.0), (b, 0.0, a)]
    corners = [normalize(corner) for corner in corners]
    edge = min(distance(p, q) for p, q in itertools.combinations(corners, 2))
    faces = []
    for triple in itertools.combinations(range(12), 3):
        if all(abs(distance(corners[i], corners[j]) - edge) < 1e-9 for i, j in itertools.combinations(triple, 2)):
            a, b, c = triple
            if dot(cross3(sub(corners[b], corners[a]), sub(corners[c], corners[a])), corners[a]) < 0.0:
                b, c = c, b
            faces.append((a, b, c))
    points = list(corners)
    for _ in range(subdivisions):
        middle, refined = {}, []

        def midpoint(i, j):
            key = (min(i, j), max(i, j))
            if key not in middle:
                middle[key] = len(points)
                points.append(normalize(lerp(points[i], points[j], 0.5)))
            return middle[key]

        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            refined += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = refined
    return tuple(points), tuple(faces)


def sphere_mesh(center, radius, color=None, subdivisions=0):
    """An icosphere (12 vertices, 20 faces, times 4 per subdivision) with smooth outward normals."""
    points, faces = _icosphere(subdivisions)
    return {"positions": [add(center, scale(point, radius)) for point in points], "normals": list(points),
            "indices": [index for face in faces for index in face],
            "colors": [color] * len(points) if color is not None else None, "mode": 4}


def merge_meshes(meshes):
    """One mesh holding every input mesh (all of one mode); missing colours become white."""
    meshes = [mesh for mesh in meshes if mesh["positions"]]
    if not meshes:
        raise ValueError("no geometry to merge")
    modes = {mesh["mode"] for mesh in meshes}
    if len(modes) != 1:
        raise ValueError("meshes of different primitive modes")
    coloured = any(mesh.get("colors") for mesh in meshes)
    shaded = all(mesh.get("normals") for mesh in meshes)
    positions, normals, indices, colors = [], [], [], []
    for mesh in meshes:
        base = len(positions)
        positions += mesh["positions"]
        if shaded:
            normals += mesh["normals"]
        if coloured:
            colors += mesh.get("colors") or [(1.0, 1.0, 1.0, 1.0)] * len(mesh["positions"])
        if mesh.get("indices") is not None:
            indices += [base + index for index in mesh["indices"]]
    return {"positions": positions, "normals": normals if shaded else None,
            "indices": indices if any(mesh.get("indices") is not None for mesh in meshes) else None,
            "colors": colors if coloured else None, "mode": modes.pop()}


def wireframe_mesh(points, edges, radius, joint_radius=None, sides=8, colors=None):
    """Tubes along the edges and an icosphere at every point: a solid wireframe of a projected 4D object."""
    joint_radius = radius * 1.9 if joint_radius is None else joint_radius
    parts = [tube_mesh(points, edges, radius, sides, colors)]
    used = sorted({index for edge in edges for index in edge})
    for index in used:
        parts.append(sphere_mesh(points[index], joint_radius, colors[index] if colors is not None else None))
    return merge_meshes(parts)


def projected_wireframe(points, edges, matrix=None, mode="perspective", eye_distance=3.0, radius=0.04, sides=8,
                        style="tubes", joint_radius=None):
    """Rotate 4D points, project them to 3D and build tubes (or LINES) coloured by their rotated w depth."""
    rotated = rotate_points(matrix, points) if matrix is not None else [tuple(point) for point in points]
    projected = project_points(rotated, mode, eye_distance=eye_distance)
    colours = depth_colors([point[3] for point in rotated])
    if style == "lines":
        return line_mesh(projected, edges, colours)
    if style != "tubes":
        raise ValueError("style is tubes or lines")
    return wireframe_mesh(projected, edges, radius, joint_radius, sides, colours)


def polygon_mesh(points, faces, color=None, colors=None):
    """Flat-shaded convex polygons (fan triangulation), one normal per face."""
    positions, normals, indices, result_colors = [], [], [], []
    for face_index, face in enumerate(faces):
        corners = [points[index] for index in face]
        normal = polygon_normal(corners)
        if norm(normal) <= 1e-14:
            continue
        normal = normalize(normal)
        base = len(positions)
        positions += corners
        normals += [normal] * len(corners)
        if colors is not None:
            result_colors += [colors[face_index]] * len(corners)
        elif color is not None:
            result_colors += [color] * len(corners)
        for step in range(1, len(corners) - 1):
            indices += [base, base + step, base + step + 1]
    return {"positions": positions, "normals": normals, "indices": indices,
            "colors": result_colors if (colors is not None or color is not None) else None, "mode": 4}


def cell_normals(polytope, points=None):
    """Outward unit normal of every cell (pointing away from the vertex centroid); points default to the vertices."""
    points = polytope["vertices"] if points is None else points
    middle = centroid(points)
    normals = []
    for members in cell_vertex_sets(polytope):
        members = sorted(members)
        base = points[members[0]]
        normal = normalize(null_space([sub(points[index], base) for index in members[1:]], 1e-9)[0])
        if dot(normal, sub(centroid([points[index] for index in members]), middle)) < 0.0:
            normal = scale(normal, -1.0)
        normals.append(normal)
    return normals


def facing_cells(polytope, points, mode="perspective", eye_distance=3.0):
    """Indices of the cells a 4D eye sees (4D back-face culling): the eye lies on the outer side of the cell's
    hyperplane. The eye is (0, 0, 0, d) for perspective, the pole (0, 0, 0, R) for stereographic, and the +w
    direction for orthographic. The projections of these cells tile the projected hull without overlapping."""
    normals = cell_normals(polytope, points)
    if mode == STEREOGRAPHIC:
        eye = (0.0, 0.0, 0.0, max(norm(point) for point in points))
    elif mode == PERSPECTIVE:
        eye = (0.0, 0.0, 0.0, eye_distance)
    elif mode == ORTHOGRAPHIC:
        return [index for index, normal in enumerate(normals) if normal[3] > 1e-12]
    else:
        raise ValueError(f"projection is one of {PROJECTIONS}")
    result = []
    for index, (normal, members) in enumerate(zip(normals, cell_vertex_sets(polytope))):
        anchor = points[min(members)]
        if dot(normal, sub(eye, anchor)) > 1e-12:
            result.append(index)
    return result


def cell_mesh(points, polytope, shrink=0.8, colors=None, cells=None):
    """Flat-shaded faces of the chosen cells from projected 3D points, each cell shrunk toward its own centroid
    (an exploded view in which every cell stays visible); colors holds one RGBA per chosen cell."""
    faces = polytope["faces"]
    chosen = list(range(len(polytope["cells"]))) if cells is None else list(cells)
    parts = []
    for position, cell_index in enumerate(chosen):
        cell = polytope["cells"][cell_index]
        members = sorted({vertex for face_index in cell for vertex in faces[face_index]})
        middle = centroid([points[vertex] for vertex in members])
        local = [lerp(middle, points[vertex], shrink) for vertex in members]
        index_of = {vertex: index for index, vertex in enumerate(members)}
        oriented = []
        for face_index in cell:
            face = [index_of[vertex] for vertex in faces[face_index]]
            corners = [local[index] for index in face]
            if dot(polygon_normal(corners), sub(centroid(corners), middle)) < 0.0:
                face.reverse()
            oriented.append(face)
        parts.append(polygon_mesh(local, oriented, color=colors[position] if colors is not None else None))
    return merge_meshes(parts)


def line_mesh(points, edges, colors=None):
    """A LINES primitive: one segment per edge."""
    return {"positions": [tuple(point) for point in points], "normals": None,
            "indices": [index for edge in edges for index in edge],
            "colors": list(colors) if colors is not None else None, "mode": 1}


def point_mesh(points, colors=None):
    """A POINTS primitive."""
    return {"positions": [tuple(point) for point in points], "normals": None, "indices": None,
            "colors": list(colors) if colors is not None else None, "mode": 0}


def mesh_bounds(mesh):
    """(minimum corner, maximum corner) of a mesh's positions."""
    positions = mesh["positions"]
    return (tuple(min(point[axis] for point in positions) for axis in range(3)),
            tuple(max(point[axis] for point in positions) for axis in range(3)))


def mesh_euler_characteristic(mesh):
    """V - E + F of a triangle mesh after merging coincident positions (2 for a closed sphere-like surface)."""
    keys, remap = {}, []
    for position in mesh["positions"]:
        key = point_key(position, 7)
        remap.append(keys.setdefault(key, len(keys)))
    triangles = set()
    edges = set()
    indices = mesh["indices"]
    for start in range(0, len(indices), 3):
        a, b, c = (remap[indices[start + offset]] for offset in range(3))
        if len({a, b, c}) < 3:
            continue
        triangles.add(tuple(sorted((a, b, c))))
        edges.update({(min(a, b), max(a, b)), (min(b, c), max(b, c)), (min(a, c), max(a, c))})
    used = {vertex for triangle in triangles for vertex in triangle}
    return len(used) - len(edges) + len(triangles)


# ---------------------------------------------------------------------------------------------------------------
# Marching tetrahedra: isosurfaces of a scalar field on a 3D grid (used for slices of implicit 4D shapes)
# ---------------------------------------------------------------------------------------------------------------

#: The six tetrahedra of a cube around its main diagonal (corner index = x + 2y + 4z); neighbours share faces.
_CUBE_TETRAHEDRA = tuple((0, 1 << a, (1 << a) | (1 << b), 7) for a, b, _c in itertools.permutations((0, 1, 2)))


def marching_tetrahedra(field, lower, upper, divisions, level=0.0):
    """Triangle mesh of {field(p) = level} in the box [lower, upper] split into divisions (nx, ny, nz) cubes.

    Inside is field < level. Vertices on grid edges are shared, normals point toward larger field values."""
    nx, ny, nz = divisions
    steps = [(upper[axis] - lower[axis]) / divisions[axis] for axis in range(3)]

    def grid_point(i, j, k):
        return (lower[0] + i * steps[0], lower[1] + j * steps[1], lower[2] + k * steps[2])

    values = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            for k in range(nz + 1):
                values[(i, j, k)] = field(grid_point(i, j, k)) - level
    positions, indices, vertex_of = [], [], {}

    def edge_vertex(a, b):
        key = (a, b) if a < b else (b, a)
        if key not in vertex_of:
            va, vb = values[a], values[b]
            t = va / (va - vb)
            vertex_of[key] = len(positions)
            positions.append(lerp(grid_point(*a), grid_point(*b), t))
        return vertex_of[key]

    def emit(corner_points, triangle, inside, outside):
        a, b, c = (positions[index] for index in triangle)
        normal = cross3(sub(b, a), sub(c, a))
        if norm(normal) <= 1e-14:
            return
        direction = sub(centroid([grid_point(*corner_points[i]) for i in outside]),
                        centroid([grid_point(*corner_points[i]) for i in inside]))
        indices.extend(triangle if dot(normal, direction) > 0.0 else (triangle[0], triangle[2], triangle[1]))

    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                cube = [(i + (corner & 1), j + ((corner >> 1) & 1), k + ((corner >> 2) & 1)) for corner in range(8)]
                for tetrahedron in _CUBE_TETRAHEDRA:
                    corners = [cube[index] for index in tetrahedron]
                    inside = [index for index in range(4) if values[corners[index]] < 0.0]
                    outside = [index for index in range(4) if values[corners[index]] >= 0.0]
                    if len(inside) in (0, 4):
                        continue
                    if len(inside) in (1, 3):
                        lone = inside[0] if len(inside) == 1 else outside[0]
                        others = [index for index in range(4) if index != lone]
                        triangle = tuple(edge_vertex(corners[lone], corners[other]) for other in others)
                        emit(corners, triangle, inside, outside)
                    else:
                        a, b = inside
                        c, d = outside
                        quad = (edge_vertex(corners[a], corners[c]), edge_vertex(corners[a], corners[d]),
                                edge_vertex(corners[b], corners[d]), edge_vertex(corners[b], corners[c]))
                        emit(corners, (quad[0], quad[1], quad[2]), inside, outside)
                        emit(corners, (quad[0], quad[2], quad[3]), inside, outside)
    accumulated = [[0.0, 0.0, 0.0] for _ in positions]
    for start in range(0, len(indices), 3):
        a, b, c = indices[start:start + 3]
        normal = cross3(sub(positions[b], positions[a]), sub(positions[c], positions[a]))
        for vertex in (a, b, c):
            for axis in range(3):
                accumulated[vertex][axis] += normal[axis]
    normals = [normalize(vector) if norm(vector) > 1e-20 else (0.0, 1.0, 0.0) for vector in accumulated]
    return {"positions": positions, "normals": normals, "indices": indices, "colors": None, "mode": 4}


# ---------------------------------------------------------------------------------------------------------------
# glTF 2.0: a text writer with an embedded base64 buffer, and a structural checker
# ---------------------------------------------------------------------------------------------------------------

COMPONENT_TYPES = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
TYPE_SIZES = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
PRIMITIVE_MODES = {0: "points", 1: "lines", 2: "line_loop", 3: "line_strip", 4: "triangles", 5: "triangle_strip",
                   6: "triangle_fan"}
DATA_PREFIX = "data:application/octet-stream;base64,"
#: The animation channel paths whose output is not a VEC3: morph target weights (SCALAR) and rotations (VEC4).
WEIGHTS_PATH, ROTATION_PATH = "weights", "rotation"


def _f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


class _Buffer:
    def __init__(self):
        self.data = bytearray()
        self.views = []
        self.accessors = []

    def view(self, payload, target=None):
        while len(self.data) % 4:
            self.data.append(0)
        record = {"buffer": 0, "byteOffset": len(self.data), "byteLength": len(payload)}
        if target is not None:
            record["target"] = target
        self.data.extend(payload)
        self.views.append(record)
        return len(self.views) - 1

    def floats(self, rows, kind, target=None, bounds=False):
        width = TYPE_SIZES[kind]
        flat = [float(value) for row in rows for value in (row if width > 1 else (row,))]
        if not all(math.isfinite(value) for value in flat):
            raise ValueError("glTF data must be finite")
        payload = struct.pack(f"<{len(flat)}f", *flat)
        record = {"bufferView": self.view(payload, target), "componentType": 5126, "count": len(rows), "type": kind}
        if bounds:
            rounded = [_f32(value) for value in flat]
            record["min"] = [min(rounded[axis::width]) for axis in range(width)]
            record["max"] = [max(rounded[axis::width]) for axis in range(width)]
        self.accessors.append(record)
        return len(self.accessors) - 1

    def colors(self, rows):
        flat = [max(0, min(255, int(round(float(value) * 255.0)))) for row in rows for value in tuple(row)[:4]]
        payload = bytes(flat)
        self.accessors.append({"bufferView": self.view(payload, 34962), "componentType": 5121, "normalized": True,
                               "count": len(rows), "type": "VEC4"})
        return len(self.accessors) - 1

    def indices(self, values):
        largest = max(values) if values else 0
        component, code = (5123, "H") if largest < 65535 else (5125, "I")
        payload = struct.pack(f"<{len(values)}{code}", *values)
        self.accessors.append({"bufferView": self.view(payload, 34963), "componentType": component,
                               "count": len(values), "type": "SCALAR"})
        return len(self.accessors) - 1


def gltf_document(meshes, animations=None, generator="fourd.py"):
    """A glTF 2.0 document: one node and one material per mesh.

    A mesh dict holds positions, optional normals, colors (RGBA 0..1), indices, mode, and may add name, color
    (material RGBA), translation, double_sided, unlit, targets ([{"positions": deltas, "normals": deltas}]) and
    weights. An animation is {"name", "channels": [{"node", "path", "times", "values", "interpolation"}]}; for the
    weights path values holds one list of target weights per time."""
    buffer = _Buffer()
    document = {"asset": {"version": "2.0", "generator": generator}, "scene": 0, "scenes": [{"nodes": []}],
                "nodes": [], "meshes": [], "materials": []}
    uses_unlit = False
    for index, mesh in enumerate(meshes):
        count = len(mesh["positions"])
        if count == 0:
            raise ValueError("a glTF mesh needs positions")
        attributes = {"POSITION": buffer.floats(mesh["positions"], "VEC3", 34962, bounds=True)}
        if mesh.get("normals"):
            attributes["NORMAL"] = buffer.floats(mesh["normals"], "VEC3", 34962)
        if mesh.get("colors"):
            attributes["COLOR_0"] = buffer.colors(mesh["colors"])
        material = {"name": f"{mesh.get('name', 'mesh')}_material",
                    "pbrMetallicRoughness": {"baseColorFactor": [float(value) for value in
                                                                 mesh.get("color", (0.82, 0.84, 0.9, 1.0))],
                                             "metallicFactor": 0.0, "roughnessFactor": 0.55},
                    "doubleSided": bool(mesh.get("double_sided", True))}
        if material["pbrMetallicRoughness"]["baseColorFactor"][3] < 1.0:
            material["alphaMode"] = "BLEND"
        if mesh.get("unlit"):
            material["extensions"] = {"KHR_materials_unlit": {}}
            uses_unlit = True
        document["materials"].append(material)
        primitive = {"attributes": attributes, "mode": int(mesh.get("mode", 4)), "material": index}
        if mesh.get("indices") is not None:
            primitive["indices"] = buffer.indices(list(mesh["indices"]))
        record = {"name": mesh.get("name", f"mesh_{index}"), "primitives": [primitive]}
        if mesh.get("targets"):
            targets = []
            for target in mesh["targets"]:
                if len(target["positions"]) != count:
                    raise ValueError("a morph target has one delta per vertex")
                entry = {"POSITION": buffer.floats(target["positions"], "VEC3", 34962, bounds=True)}
                if target.get("normals"):
                    entry["NORMAL"] = buffer.floats(target["normals"], "VEC3", 34962)
                targets.append(entry)
            primitive["targets"] = targets
            record["weights"] = [float(value) for value in mesh.get("weights", [0.0] * len(targets))]
        document["meshes"].append(record)
        node = {"name": mesh.get("name", f"mesh_{index}"), "mesh": index}
        if mesh.get("translation"):
            node["translation"] = [float(value) for value in mesh["translation"]]
        document["nodes"].append(node)
        document["scenes"][0]["nodes"].append(index)
    if animations:
        document["animations"] = []
        for animation in animations:
            samplers, channels = [], []
            for channel in animation["channels"]:
                times = [float(value) for value in channel["times"]]
                if channel["path"] == WEIGHTS_PATH:
                    output = buffer.floats([value for row in channel["values"] for value in row], "SCALAR")
                else:
                    kind = "VEC4" if channel["path"] == ROTATION_PATH else "VEC3"
                    output = buffer.floats(channel["values"], kind)
                samplers.append({"input": buffer.floats(times, "SCALAR", bounds=True), "output": output,
                                 "interpolation": channel.get("interpolation", "LINEAR")})
                channels.append({"sampler": len(samplers) - 1,
                                 "target": {"node": int(channel["node"]), "path": channel["path"]}})
            document["animations"].append({"name": animation.get("name", "animation"), "samplers": samplers,
                                           "channels": channels})
    if uses_unlit:
        document["extensionsUsed"] = ["KHR_materials_unlit"]
    document["accessors"] = buffer.accessors
    document["bufferViews"] = buffer.views
    document["buffers"] = [{"byteLength": len(buffer.data),
                            "uri": DATA_PREFIX + base64.b64encode(bytes(buffer.data)).decode("ascii")}]
    return document


def morph_animation(mesh, frames, times, name="animation", node=0, normals=None):
    """A mesh whose morph targets reproduce `frames` (lists of positions with one topology) at `times`, and the
    matching weights animation. Frame 0 is the base mesh; target k is frame k minus frame 0; the weights are
    one-hot per frame, so a viewer's linear interpolation moves every vertex along the chord between frames."""
    if len(frames) != len(times) or len(frames) < 2:
        raise ValueError("one time per frame, two frames or more")
    if any(later <= earlier for earlier, later in zip(times, times[1:])):
        raise ValueError("frame times increase")
    base = frames[0]
    targets = []
    for index, frame in enumerate(frames[1:], 1):
        if len(frame) != len(base):
            raise ValueError("every frame has one position per vertex")
        target = {"positions": [sub(point, origin) for point, origin in zip(frame, base)]}
        if normals is not None:
            target["normals"] = [sub(normal, first) for normal, first in zip(normals[index], normals[0])]
        targets.append(target)
    weights = [[0.0] * len(targets)]
    for index in range(len(targets)):
        weights.append([1.0 if column == index else 0.0 for column in range(len(targets))])
    animated = dict(mesh, positions=list(base), targets=targets)
    if normals is not None:
        animated["normals"] = list(normals[0])
    return animated, {"name": name, "channels": [{"node": node, "path": "weights", "times": list(times),
                                                  "values": weights}]}


def gltf_text(document):
    """The document as deterministic JSON text."""
    return json.dumps(document, indent=1, ensure_ascii=True, allow_nan=False) + "\n"


def write_gltf(path, document):
    """Write a .gltf file after checking it; returns the byte count."""
    problems = validate_gltf(document)
    if problems:
        raise ValueError("glTF refused: " + "; ".join(problems[:4]))
    text = gltf_text(document)
    with open(path, "w", encoding="ascii", newline="\n") as stream:
        stream.write(text)
    return len(text.encode("ascii"))


def read_gltf(path):
    """Read a .gltf JSON file (non-finite numbers refused)."""
    def refuse(name):
        raise ValueError(f"non-finite number {name}")

    with open(path, "r", encoding="utf-8") as stream:
        return json.loads(stream.read(), parse_constant=refuse)


def buffer_bytes(document):
    """Decoded bytes of every buffer (only embedded base64 data URIs are accepted)."""
    result = []
    for index, buffer in enumerate(document.get("buffers", [])):
        uri = buffer.get("uri", "")
        if not isinstance(uri, str) or not uri.startswith(DATA_PREFIX):
            raise ValueError(f"buffer {index} is not an embedded base64 data URI")
        result.append(base64.b64decode(uri[len(DATA_PREFIX):], validate=True))
    return result


def accessor_values(document, index, buffers=None):
    """The values of one accessor: numbers for SCALAR, tuples otherwise (normalized integers become 0..1)."""
    buffers = buffer_bytes(document) if buffers is None else buffers
    accessor = document["accessors"][index]
    view = document["bufferViews"][accessor["bufferView"]]
    code, size = COMPONENT_TYPES[accessor["componentType"]]
    width = TYPE_SIZES[accessor["type"]]
    stride = view.get("byteStride", size * width)
    data = buffers[view["buffer"]]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    values = []
    divisor = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}.get(accessor["componentType"])
    for element in range(accessor["count"]):
        row = struct.unpack_from(f"<{width}{code}", data, start + element * stride)
        if accessor.get("normalized") and divisor:
            row = tuple(max(-1.0, value / divisor) for value in row)
        values.append(row[0] if width == 1 else row)
    return values


def validate_gltf(document):
    """Structural problems of a glTF 2.0 document; an empty list when it passes.

    Checked: asset version, buffer lengths, buffer view and accessor bounds and alignment, component types,
    finite floats and declared position bounds, attribute counts, index range, primitive index counts, morph
    target counts, node and scene references, and animation samplers (increasing times, output counts)."""
    problems = []
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        return ["asset.version is not 2.0"]
    if document.get("extensionsRequired"):
        problems.append("extensionsRequired is not supported")
    try:
        buffers = buffer_bytes(document)
    except (ValueError, TypeError) as error:
        return [f"buffer unreadable: {error}"]
    for index, (buffer, data) in enumerate(zip(document.get("buffers", []), buffers)):
        if buffer.get("byteLength") != len(data):
            problems.append(f"buffer {index} byteLength {buffer.get('byteLength')} but {len(data)} bytes decoded")
    views = document.get("bufferViews", [])
    for index, view in enumerate(views):
        buffer = view.get("buffer")
        if not isinstance(buffer, int) or not 0 <= buffer < len(buffers):
            problems.append(f"bufferView {index} names buffer {buffer}")
            continue
        end = view.get("byteOffset", 0) + view.get("byteLength", 0)
        if view.get("byteLength", 0) <= 0 or end > len(buffers[buffer]):
            problems.append(f"bufferView {index} exceeds buffer {buffer}")
        stride = view.get("byteStride")
        if stride is not None and (stride < 4 or stride > 252 or stride % 4):
            problems.append(f"bufferView {index} byteStride {stride} invalid")
    accessors = document.get("accessors", [])
    readable = set()
    for index, accessor in enumerate(accessors):
        view_index = accessor.get("bufferView")
        kind, component = accessor.get("type"), accessor.get("componentType")
        if kind not in TYPE_SIZES or component not in COMPONENT_TYPES:
            problems.append(f"accessor {index} type or componentType invalid")
            continue
        if not isinstance(view_index, int) or not 0 <= view_index < len(views):
            problems.append(f"accessor {index} names bufferView {view_index}")
            continue
        count = accessor.get("count", 0)
        if not isinstance(count, int) or count < 1:
            problems.append(f"accessor {index} count {count} invalid")
            continue
        view = views[view_index]
        size = COMPONENT_TYPES[component][1]
        element = size * TYPE_SIZES[kind]
        stride = view.get("byteStride", element)
        offset = accessor.get("byteOffset", 0)
        if offset + stride * (count - 1) + element > view.get("byteLength", 0):
            problems.append(f"accessor {index} exceeds bufferView {view_index}")
            continue
        if (offset + view.get("byteOffset", 0)) % size:
            problems.append(f"accessor {index} is misaligned")
            continue
        if view.get("buffer") is None or view["buffer"] >= len(buffers) or \
                view.get("byteOffset", 0) + view.get("byteLength", 0) > len(buffers[view["buffer"]]):
            continue
        readable.add(index)
        if component == 5126:
            values = accessor_values(document, index, buffers)
            flat = [value for row in values for value in (row if isinstance(row, tuple) else (row,))]
            if not all(math.isfinite(value) for value in flat):
                problems.append(f"accessor {index} holds a non-finite float")
            width = TYPE_SIZES[kind]
            for name, pick in (("min", min), ("max", max)):
                if name in accessor:
                    actual = [pick(flat[axis::width]) for axis in range(width)]
                    if len(accessor[name]) != width or any(abs(a - b) > 1e-6 * max(1.0, abs(a))
                                                           for a, b in zip(actual, accessor[name])):
                        problems.append(f"accessor {index} declared {name} does not match its data")
    meshes = document.get("meshes", [])
    materials = document.get("materials", [])
    for mesh_index, mesh in enumerate(meshes):
        primitives = mesh.get("primitives", [])
        if not primitives:
            problems.append(f"mesh {mesh_index} has no primitives")
        target_counts = set()
        for primitive_index, primitive in enumerate(primitives):
            label = f"mesh {mesh_index} primitive {primitive_index}"
            attributes = primitive.get("attributes", {})
            position = attributes.get("POSITION")
            if not isinstance(position, int) or position not in readable:
                problems.append(f"{label} has no readable POSITION")
                continue
            if accessors[position]["type"] != "VEC3" or accessors[position]["componentType"] != 5126 \
                    or "min" not in accessors[position] or "max" not in accessors[position]:
                problems.append(f"{label} POSITION is not a float VEC3 with min and max")
            vertex_count = accessors[position]["count"]
            for name, accessor_index in attributes.items():
                if not isinstance(accessor_index, int) or accessor_index not in readable:
                    problems.append(f"{label} attribute {name} unreadable")
                elif accessors[accessor_index]["count"] != vertex_count:
                    problems.append(f"{label} attribute {name} count differs from POSITION")
            if "NORMAL" in attributes and attributes["NORMAL"] in readable:
                for normal in accessor_values(document, attributes["NORMAL"], buffers):
                    if abs(norm(normal) - 1.0) > 1e-3:
                        problems.append(f"{label} NORMAL is not unit length")
                        break
            mode = primitive.get("mode", 4)
            if mode not in PRIMITIVE_MODES:
                problems.append(f"{label} mode {mode} invalid")
            material = primitive.get("material")
            if material is not None and (not isinstance(material, int) or not 0 <= material < len(materials)):
                problems.append(f"{label} names material {material}")
            if "indices" in primitive:
                index_accessor = primitive["indices"]
                if not isinstance(index_accessor, int) or index_accessor not in readable:
                    problems.append(f"{label} indices unreadable")
                else:
                    record = accessors[index_accessor]
                    if record["type"] != "SCALAR" or record["componentType"] not in (5121, 5123, 5125):
                        problems.append(f"{label} indices are not unsigned scalars")
                    values = accessor_values(document, index_accessor, buffers)
                    if values and max(values) >= vertex_count:
                        problems.append(f"{label} index {max(values)} out of range for {vertex_count} vertices")
                    if mode == 4 and len(values) % 3:
                        problems.append(f"{label} triangle index count is not a multiple of 3")
                    if mode == 1 and len(values) % 2:
                        problems.append(f"{label} line index count is not a multiple of 2")
            targets = primitive.get("targets", [])
            target_counts.add(len(targets))
            for target_index, target in enumerate(targets):
                for name, accessor_index in target.items():
                    if not isinstance(accessor_index, int) or accessor_index not in readable:
                        problems.append(f"{label} target {target_index} {name} unreadable")
                    elif accessors[accessor_index]["count"] != vertex_count:
                        problems.append(f"{label} target {target_index} {name} count differs from POSITION")
                    elif name == "POSITION" and ("min" not in accessors[accessor_index]
                                                 or "max" not in accessors[accessor_index]):
                        problems.append(f"{label} target {target_index} POSITION lacks min and max")
        if len(target_counts) > 1:
            problems.append(f"mesh {mesh_index} primitives differ in morph target count")
        if "weights" in mesh and target_counts and len(mesh["weights"]) != max(target_counts):
            problems.append(f"mesh {mesh_index} weights length differs from its target count")
    nodes = document.get("nodes", [])
    parents = defaultdict(int)
    for node_index, node in enumerate(nodes):
        if "mesh" in node and (not isinstance(node["mesh"], int) or not 0 <= node["mesh"] < len(meshes)):
            problems.append(f"node {node_index} names mesh {node['mesh']}")
        for child in node.get("children", []):
            if not isinstance(child, int) or not 0 <= child < len(nodes) or child == node_index:
                problems.append(f"node {node_index} names child {child}")
            else:
                parents[child] += 1
    if any(count > 1 for count in parents.values()):
        problems.append("a node has more than one parent")
    scenes = document.get("scenes", [])
    for scene_index, scene in enumerate(scenes):
        for node_index in scene.get("nodes", []):
            if not isinstance(node_index, int) or not 0 <= node_index < len(nodes) or parents[node_index]:
                problems.append(f"scene {scene_index} names node {node_index} that is not a root node")
    if "scene" in document and (not isinstance(document["scene"], int) or not 0 <= document["scene"] < len(scenes)):
        problems.append("scene index invalid")
    for animation_index, animation in enumerate(document.get("animations", [])):
        samplers = animation.get("samplers", [])
        for channel_index, channel in enumerate(animation.get("channels", [])):
            label = f"animation {animation_index} channel {channel_index}"
            sampler_index = channel.get("sampler")
            target = channel.get("target", {})
            node_index = target.get("node")
            if not isinstance(sampler_index, int) or not 0 <= sampler_index < len(samplers):
                problems.append(f"{label} names sampler {sampler_index}")
                continue
            if not isinstance(node_index, int) or not 0 <= node_index < len(nodes):
                problems.append(f"{label} names node {node_index}")
                continue
            path = target.get("path")
            sampler = samplers[sampler_index]
            interpolation = sampler.get("interpolation", "LINEAR")
            if path not in ("translation", "rotation", "scale", "weights") or \
                    interpolation not in ("LINEAR", "STEP", "CUBICSPLINE"):
                problems.append(f"{label} path or interpolation invalid")
                continue
            source, output = sampler.get("input"), sampler.get("output")
            if source not in readable or output not in readable:
                problems.append(f"{label} sampler accessors unreadable")
                continue
            if "min" not in accessors[source] or "max" not in accessors[source]:
                problems.append(f"{label} input lacks min and max")
            times = accessor_values(document, source, buffers)
            if any(later <= earlier for earlier, later in zip(times, times[1:])) or (times and times[0] < 0.0):
                problems.append(f"{label} input times are not increasing from zero or later")
            factor = 3 if interpolation == "CUBICSPLINE" else 1
            if path == "weights":
                mesh_index = nodes[node_index].get("mesh")
                count = len(meshes[mesh_index]["primitives"][0].get("targets", [])) if isinstance(mesh_index, int) \
                    and 0 <= mesh_index < len(meshes) else 0
                if count == 0:
                    problems.append(f"{label} animates weights of a node without morph targets")
                elif accessors[output]["count"] != len(times) * count * factor:
                    problems.append(f"{label} weights output count differs from times x targets")
            elif accessors[output]["count"] != len(times) * factor:
                problems.append(f"{label} output count differs from input count")
    return problems


def gltf_summary(document):
    """Counts a viewer should see: meshes, primitives, vertices, triangles, lines, points, targets, animations."""
    summary = {"meshes": len(document.get("meshes", [])), "primitives": 0, "vertices": 0, "triangles": 0,
               "lines": 0, "points": 0, "morph_targets": 0, "animations": len(document.get("animations", [])),
               "vertices_per_mesh": []}
    accessors = document.get("accessors", [])
    for mesh in document.get("meshes", []):
        mesh_vertices = 0
        for primitive in mesh.get("primitives", []):
            summary["primitives"] += 1
            count = accessors[primitive["attributes"]["POSITION"]]["count"]
            mesh_vertices += count
            elements = accessors[primitive["indices"]]["count"] if "indices" in primitive else count
            mode = primitive.get("mode", 4)
            if mode == 4:
                summary["triangles"] += elements // 3
            elif mode == 1:
                summary["lines"] += elements // 2
            elif mode == 0:
                summary["points"] += elements
            summary["morph_targets"] = max(summary["morph_targets"], len(primitive.get("targets", [])))
        summary["vertices"] += mesh_vertices
        summary["vertices_per_mesh"].append(mesh_vertices)
    return summary


# ---------------------------------------------------------------------------------------------------------------
# A small PNG writer (8-bit RGB or gray), for textures and slice images
# ---------------------------------------------------------------------------------------------------------------

def png_bytes(width, height, pixels, channels=3):
    """PNG bytes of width x height pixels, rows from the top, `channels` samples of 0..255 each (1, 3 or 4)."""
    colour = {1: 0, 3: 2, 4: 6}.get(channels)
    if colour is None or len(pixels) != width * height * channels or width < 1 or height < 1:
        raise ValueError("pixels hold width * height * channels samples; channels is 1, 3 or 4")

    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

    row = width * channels
    raw = b"".join(b"\x00" + bytes(pixels[y * row:(y + 1) * row]) for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, colour, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))
