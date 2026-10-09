"""Standard-library mesh toolkit shared by every mesh_algorithms package.

What it holds:

- an indexed polygon mesh type with optional normals, tangents, texture coordinates, colours and lines;
- vector, matrix and quaternion helpers;
- face and vertex normals (area or angle weighted), bounding box, surface area, signed volume, centroids;
- edge and adjacency maps, boundary loops, manifold, closed, orientation and watertight checks,
  Euler characteristic, genus and connected components;
- welding by distance, unused-vertex removal, flipping, transforms, combining and flat shading;
- polygon triangulation (ear clipping, holes joined by bridges) and a grid quad helper;
- an iso-surface polygonizer (marching tetrahedra on a Freudenthal grid) and seeded gradient noise;
- a text glTF 2.0 writer (one .gltf, buffer embedded as base64, optional node hierarchy and animations),
  a strict structural glTF reader, an OBJ writer and reader;
- the command line runner every item module uses.

Conventions: right-handed coordinates, +Y up, metres. Faces list vertex indices counter-clockwise seen
from outside, so face normals point outward. Two-dimensional points (x, y) map to (x, 0, -y) when a planar
result is exported, so the plane faces +Y. Everything is deterministic and runs on Python 3.10 or newer
with the standard library alone.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import struct
import sys

__version__ = "1.0.0"
GENERATOR = "Baltor mesh_algorithms meshkit " + __version__
EPSILON = 1e-12


class MeshError(ValueError):
    """A mesh, polygon or parameter that cannot be used. ``reason`` is a short closed code."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


class GltfError(ValueError):
    """A glTF document that does not verify. ``reason`` is a short closed code."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


# ----------------------------------------------------------------------------------------------- vectors

def vadd(a, b):
    """Component-wise sum of two 3-vectors."""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vsub(a, b):
    """Component-wise difference a - b of two 3-vectors."""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vscale(a, s):
    """A 3-vector multiplied by a scalar."""
    return (a[0] * s, a[1] * s, a[2] * s)


def vdot(a, b):
    """Dot product of two 3-vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vcross(a, b):
    """Cross product a x b of two 3-vectors."""
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def vlength(a):
    """Euclidean length of a 3-vector."""
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def vnormalize(a, fallback=(0.0, 0.0, 0.0)):
    """The unit vector along ``a``, or ``fallback`` when ``a`` has no length."""
    length = vlength(a)
    if length <= 1e-300:
        return tuple(fallback)
    return (a[0] / length, a[1] / length, a[2] / length)


def vlerp(a, b, t):
    """Linear interpolation from a (t = 0) to b (t = 1)."""
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def vdistance(a, b):
    """Euclidean distance between two 3-points."""
    return vlength(vsub(a, b))


def cross2(o, a, b):
    """Twice the signed area of triangle (o, a, b) in 2D: positive when counter-clockwise."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def polygon_area_2d(points):
    """Signed shoelace area of a 2D polygon: positive when its vertices run counter-clockwise."""
    count = len(points)
    return 0.5 * math.fsum(points[i][0] * points[(i + 1) % count][1] - points[(i + 1) % count][0] * points[i][1]
                           for i in range(count))


def point_in_triangle_2d(p, a, b, c, strict=False):
    """Whether 2D point p lies in triangle (a, b, c) of either orientation; ``strict`` excludes the boundary."""
    d1, d2, d3 = cross2(a, b, p), cross2(b, c, p), cross2(c, a, p)
    if strict:
        return (d1 > 0 and d2 > 0 and d3 > 0) or (d1 < 0 and d2 < 0 and d3 < 0)
    negative = d1 < 0 or d2 < 0 or d3 < 0
    positive = d1 > 0 or d2 > 0 or d3 > 0
    return not (negative and positive)


def plane_to_3d(point, height=0.0):
    """Map a 2D point (x, y) to the glTF ground plane: (x, height, -y), so counter-clockwise faces +Y."""
    return (float(point[0]), float(height), -float(point[1]))


# ----------------------------------------------------------------------------------------------- matrices

def identity_matrix():
    """The 4 x 4 identity matrix as a list of rows."""
    return [[1.0 if row == column else 0.0 for column in range(4)] for row in range(4)]


def matrix_multiply(a, b):
    """The product a * b of two 4 x 4 row-major matrices."""
    return [[math.fsum(a[row][k] * b[k][column] for k in range(4)) for column in range(4)] for row in range(4)]


def translation_matrix(offset):
    """A 4 x 4 matrix that translates by ``offset``."""
    matrix = identity_matrix()
    matrix[0][3], matrix[1][3], matrix[2][3] = float(offset[0]), float(offset[1]), float(offset[2])
    return matrix


def scale_matrix(factors):
    """A 4 x 4 matrix that scales by a number or by (sx, sy, sz)."""
    if isinstance(factors, (int, float)):
        factors = (factors, factors, factors)
    matrix = identity_matrix()
    matrix[0][0], matrix[1][1], matrix[2][2] = float(factors[0]), float(factors[1]), float(factors[2])
    return matrix


def rotation_matrix(axis, angle):
    """A 4 x 4 matrix rotating by ``angle`` radians counter-clockwise about ``axis`` (right-hand rule)."""
    x, y, z = vnormalize(axis, (0.0, 1.0, 0.0))
    c, s = math.cos(angle), math.sin(angle)
    t = 1.0 - c
    return [[t * x * x + c, t * x * y - s * z, t * x * z + s * y, 0.0],
            [t * x * y + s * z, t * y * y + c, t * y * z - s * x, 0.0],
            [t * x * z - s * y, t * y * z + s * x, t * z * z + c, 0.0],
            [0.0, 0.0, 0.0, 1.0]]


def transform_point(matrix, point):
    """A 3-point transformed by a 4 x 4 affine matrix."""
    x, y, z = point[0], point[1], point[2]
    return (matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3],
            matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3],
            matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3])


def transform_direction(matrix, direction):
    """A 3-vector transformed by the linear part of a 4 x 4 matrix (no translation)."""
    x, y, z = direction[0], direction[1], direction[2]
    return (matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z,
            matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z,
            matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z)


def _normal_matrix(matrix):
    """Inverse transpose of the 3 x 3 linear part, for transforming normals."""
    a = [[matrix[row][column] for column in range(3)] for row in range(3)]
    determinant = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
                   - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                   + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    if abs(determinant) < 1e-300:
        raise MeshError("matrix_singular", "the transform has no inverse")
    cofactor = [[(a[(r + 1) % 3][(c + 1) % 3] * a[(r + 2) % 3][(c + 2) % 3]
                  - a[(r + 1) % 3][(c + 2) % 3] * a[(r + 2) % 3][(c + 1) % 3]) / determinant
                 for c in range(3)] for r in range(3)]
    return cofactor, determinant


def quaternion_from_axis_angle(axis, angle):
    """Unit quaternion (x, y, z, w) for a rotation of ``angle`` radians about ``axis``."""
    x, y, z = vnormalize(axis, (0.0, 1.0, 0.0))
    s = math.sin(angle * 0.5)
    return (x * s, y * s, z * s, math.cos(angle * 0.5))


def quaternion_multiply(a, b):
    """Hamilton product a * b of quaternions given as (x, y, z, w): apply b first, then a."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def quaternion_matrix(quaternion):
    """The 4 x 4 rotation matrix of a unit quaternion (x, y, z, w)."""
    x, y, z, w = quaternion
    return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0.0],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0.0],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0.0],
            [0.0, 0.0, 0.0, 1.0]]


def trs_matrix(translation=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0, 1.0), scale=(1.0, 1.0, 1.0)):
    """The glTF node matrix T * R * S from translation, quaternion rotation and scale."""
    return matrix_multiply(matrix_multiply(translation_matrix(translation), quaternion_matrix(rotation)),
                           scale_matrix(scale))


# ----------------------------------------------------------------------------------------------- mesh type

def material(name="default", base_color=(0.8, 0.8, 0.8, 1.0), metallic=0.0, roughness=0.6, double_sided=None,
             emissive=None):
    """A glTF metallic-roughness material description. ``double_sided`` None lets the writer decide."""
    color = tuple(float(c) for c in base_color)
    if len(color) == 3:
        color = color + (1.0,)
    if len(color) != 4 or not all(0.0 <= c <= 1.0 for c in color):
        raise MeshError("material_invalid", "base_color has three or four components in [0, 1]")
    return {"name": str(name), "base_color": color, "metallic": float(metallic), "roughness": float(roughness),
            "double_sided": double_sided, "emissive": None if emissive is None else tuple(float(c) for c in emissive)}


class Mesh:
    """An indexed polygon mesh.

    ``vertices`` are (x, y, z) tuples; ``faces`` are tuples of three or more vertex indices, counter-clockwise
    seen from outside. ``normals`` (unit), ``tangents`` (x, y, z, w), ``uvs`` (u, v) and ``colors`` (r, g, b, a in
    [0, 1]) are optional per-vertex lists. ``lines`` is an optional list of (a, b) index pairs exported as a
    separate line primitive. ``material`` is a dict from :func:`material` or None.
    """

    def __init__(self, vertices=(), faces=(), normals=None, uvs=None, colors=None, lines=None, tangents=None,
                 name="mesh", material=None):
        self.vertices = [(float(v[0]), float(v[1]), float(v[2])) for v in vertices]
        self.faces = [tuple(int(i) for i in face) for face in faces]
        self.normals = None if normals is None else [(float(n[0]), float(n[1]), float(n[2])) for n in normals]
        self.uvs = None if uvs is None else [(float(t[0]), float(t[1])) for t in uvs]
        self.colors = None if colors is None else [_rgba(c) for c in colors]
        self.lines = [] if lines is None else [(int(a), int(b)) for a, b in lines]
        self.tangents = None if tangents is None else [tuple(float(c) for c in t) for t in tangents]
        self.name = str(name)
        self.material = material

    def copy(self):
        """An independent copy of the mesh."""
        return Mesh(self.vertices, self.faces, self.normals, self.uvs, self.colors, self.lines, self.tangents,
                    self.name, None if self.material is None else dict(self.material))

    def vertex_count(self):
        """Number of vertices."""
        return len(self.vertices)

    def face_count(self):
        """Number of faces as stored (polygons count once)."""
        return len(self.faces)

    def triangle_count(self):
        """Number of triangles after triangulating every face (a polygon of n corners gives n - 2)."""
        return sum(len(face) - 2 for face in self.faces)

    def triangles(self):
        """Every face split into counter-clockwise triangles (fans for convex faces, ear clipping otherwise)."""
        result = []
        for face in self.faces:
            result.extend(triangulate_face(self.vertices, face))
        return result

    def validate(self):
        """Raise MeshError on non-finite coordinates, bad indices or attribute lists of the wrong length."""
        count = len(self.vertices)
        for index, vertex in enumerate(self.vertices):
            if not all(math.isfinite(c) for c in vertex):
                raise MeshError("vertex_not_finite", f"vertex {index}")
        for index, face in enumerate(self.faces):
            if len(face) < 3:
                raise MeshError("face_too_small", f"face {index} has {len(face)} indices")
            for corner in face:
                if not 0 <= corner < count:
                    raise MeshError("index_out_of_range", f"face {index} uses vertex {corner} of {count}")
            if len(set(face)) != len(face):
                raise MeshError("face_repeats_vertex", f"face {index}")
        for index, (a, b) in enumerate(self.lines):
            if not (0 <= a < count and 0 <= b < count) or a == b:
                raise MeshError("line_invalid", f"line {index}")
        for label, values, widths in (("normals", self.normals, (3,)), ("uvs", self.uvs, (2,)),
                                      ("colors", self.colors, (3, 4)), ("tangents", self.tangents, (4,))):
            if values is None:
                continue
            if len(values) != count:
                raise MeshError("attribute_length", f"{label} has {len(values)} entries for {count} vertices")
            if any(len(value) not in widths or not all(math.isfinite(c) for c in value) for value in values):
                raise MeshError("attribute_invalid", label)
        return self


def _rgba(color):
    values = tuple(float(c) for c in color)
    if len(values) == 3:
        values = values + (1.0,)
    if len(values) != 4:
        raise MeshError("color_invalid", "colors have three or four components")
    return values


def box(size=(1.0, 1.0, 1.0), center=(0.0, 0.0, 0.0)):
    """An axis-aligned box: 8 vertices and 6 outward quads. A fixture for tests and examples."""
    hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    cx, cy, cz = center
    vertices = [(cx + sx * hx, cy + sy * hy, cz + sz * hz)
                for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    # index = 4 * (sx > 0) + 2 * (sy > 0) + (sz > 0)
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return Mesh(vertices, faces, name="box")


def tetrahedron(size=1.0):
    """A regular tetrahedron inscribed in a cube of side ``size``: 4 vertices, 4 outward triangles."""
    h = size * 0.5
    vertices = [(h, h, h), (h, -h, -h), (-h, h, -h), (-h, -h, h)]
    faces = [(0, 2, 3), (0, 3, 1), (0, 1, 2), (1, 3, 2)]
    return Mesh(vertices, faces, name="tetrahedron")


def grid_faces(columns, rows, wrap_columns=False, wrap_rows=False):
    """Quads over a row-major vertex grid (index = row * columns + column).

    Each quad is (r, c), (r + 1, c), (r + 1, c + 1), (r, c + 1); a wrapped direction joins its last
    vertex back to its first. Reverse each quad when the parameterization faces the other way."""
    if columns < 2 or rows < 2:
        raise MeshError("grid_too_small", f"{columns} x {rows}")
    faces = []
    column_steps = columns if wrap_columns else columns - 1
    row_steps = rows if wrap_rows else rows - 1
    for row in range(row_steps):
        next_row = (row + 1) % rows
        for column in range(column_steps):
            next_column = (column + 1) % columns
            faces.append((row * columns + column, next_row * columns + column,
                          next_row * columns + next_column, row * columns + next_column))
    return faces


# ----------------------------------------------------------------------------------------------- triangulation

def _ring_area(points, ring):
    count = len(ring)
    return 0.5 * math.fsum(points[ring[i]][0] * points[ring[(i + 1) % count]][1]
                           - points[ring[(i + 1) % count]][0] * points[ring[i]][1] for i in range(count))


def _in_cone(points, before, apex, after, target):
    """Whether direction apex->target lies inside the counter-clockwise interior angle at apex."""
    a, b, c, p = points[before], points[apex], points[after], points[target]
    if cross2(a, b, c) >= 0:  # convex corner
        return cross2(b, c, p) >= 0 and cross2(a, b, p) >= 0
    return not (cross2(b, c, p) < 0 and cross2(a, b, p) < 0)


def _bridge(points, polygon, hole):
    hole_start = max(range(len(hole)), key=lambda k: (points[hole[k]][0], -points[hole[k]][1], -hole[k]))
    mx, my = points[hole[hole_start]]
    best_x, best_edge, vertex_hit = math.inf, None, None
    count = len(polygon)
    for position in range(count):
        a, b = points[polygon[position]], points[polygon[(position + 1) % count]]
        if not (a[1] <= my <= b[1] and a[1] < b[1]):
            continue
        x = a[0] + (my - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
        if x < mx or x >= best_x:
            continue
        best_x, best_edge = x, position
        vertex_hit = None
        if x == a[0] and my == a[1]:
            vertex_hit = position
        elif x == b[0] and my == b[1]:
            vertex_hit = (position + 1) % count
    if best_edge is None:
        raise MeshError("hole_outside_polygon", "a hole is not inside the outer boundary")
    if vertex_hit is not None:
        candidate = polygon[vertex_hit]
    else:
        a_index, b_index = polygon[best_edge], polygon[(best_edge + 1) % count]
        candidate = a_index if points[a_index][0] > points[b_index][0] else b_index
        hit = (best_x, my)
        cp = points[candidate]
        best_key = None
        for position in range(count):
            index = polygon[position]
            if index == candidate:
                continue
            p = points[index]
            if p == (mx, my) or p == cp:
                continue
            previous, following = polygon[position - 1], polygon[(position + 1) % count]
            if cross2(points[previous], p, points[following]) >= 0:
                continue  # only reflex vertices can hide the candidate
            if point_in_triangle_2d(p, (mx, my), hit, cp) and p[0] >= mx:
                dx = p[0] - mx
                key = (abs(p[1] - my) / dx if dx > 0 else math.inf, dx * dx + (p[1] - my) ** 2)
                if best_key is None or key < best_key:
                    best_key, candidate = key, index
    positions = [k for k in range(count) if polygon[k] == candidate]
    chosen = positions[0]
    for k in positions:
        if _in_cone(points, polygon[k - 1], polygon[k], polygon[(k + 1) % count], hole[hole_start]):
            chosen = k
            break
    loop = hole[hole_start:] + hole[:hole_start + 1]
    return polygon[:chosen + 1] + loop + [polygon[chosen]] + polygon[chosen + 1:]


def _ear_clip(points, polygon):
    indices = list(polygon)
    triangles = []
    while len(indices) > 3:
        count = len(indices)
        clipped = False
        for strict in (False, True):
            for k in range(count):
                i0, i1, i2 = indices[k - 1], indices[k], indices[(k + 1) % count]
                a, b, c = points[i0], points[i1], points[i2]
                if cross2(a, b, c) <= 0:
                    continue
                blocked = False
                for other in indices:
                    if other in (i0, i1, i2):
                        continue
                    p = points[other]
                    if p == a or p == b or p == c:
                        continue
                    if point_in_triangle_2d(p, a, b, c, strict=strict):
                        blocked = True
                        break
                if not blocked:
                    triangles.append((i0, i1, i2))
                    del indices[k]
                    clipped = True
                    break
            if clipped:
                break
        if clipped:
            continue
        # Degenerate input: drop a collinear corner, otherwise force the most convex corner.
        flat = [k for k in range(count)
                if cross2(points[indices[k - 1]], points[indices[k]], points[indices[(k + 1) % count]]) == 0]
        if flat:
            del indices[flat[0]]
            continue
        best = max(range(count), key=lambda k: cross2(points[indices[k - 1]], points[indices[k]],
                                                       points[indices[(k + 1) % count]]))
        if cross2(points[indices[best - 1]], points[indices[best]], points[indices[(best + 1) % count]]) <= 0:
            break
        triangles.append((indices[best - 1], indices[best], indices[(best + 1) % count]))
        del indices[best]
    if len(indices) == 3 and cross2(points[indices[0]], points[indices[1]], points[indices[2]]) > 0:
        triangles.append(tuple(indices))
    return triangles


def triangulate_polygon_2d(outer, holes=()):
    """Triangulate a simple 2D polygon with optional holes by ear clipping; holes join through bridges.

    Returns counter-clockwise index triples into the points of ``outer`` followed by each hole in order.
    Either orientation is accepted for any ring. For a polygon of n vertices in total and h holes in general
    position the result has n + 2h - 2 triangles. O(n^2) typical, O(n^3) worst case."""
    points = [(float(p[0]), float(p[1])) for p in outer]
    if len(points) < 3:
        raise MeshError("polygon_too_small", "the outer boundary needs three points")
    outer_ring = list(range(len(points)))
    if _ring_area(points, outer_ring) < 0:
        outer_ring.reverse()
    hole_rings = []
    for hole in holes:
        start = len(points)
        points.extend((float(p[0]), float(p[1])) for p in hole)
        ring = list(range(start, len(points)))
        if len(ring) < 3:
            raise MeshError("polygon_too_small", "a hole needs three points")
        if _ring_area(points, ring) > 0:
            ring.reverse()
        hole_rings.append(ring)
    polygon = outer_ring
    for ring in sorted(hole_rings, key=lambda r: (-max(points[i][0] for i in r), r[0])):
        polygon = _bridge(points, polygon, ring)
    return _ear_clip(points, polygon)


def face_normal(vertices, face):
    """Unit normal of a polygon by Newell's method (zero vector for a degenerate face)."""
    nx = ny = nz = 0.0
    count = len(face)
    for k in range(count):
        cx, cy, cz = vertices[face[k]]
        x2, y2, z2 = vertices[face[(k + 1) % count]]
        nx += (cy - y2) * (cz + z2)
        ny += (cz - z2) * (cx + x2)
        nz += (cx - x2) * (cy + y2)
    return vnormalize((nx, ny, nz))


def triangulate_face(vertices, face):
    """Counter-clockwise triangles of one face: itself, the shorter diagonal of a quad, a fan of a convex
    polygon, or ear clipping in the face plane for a concave polygon."""
    count = len(face)
    if count == 3:
        return [tuple(face)]
    if count == 4:
        a, b, c, d = (vertices[i] for i in face)
        normal = face_normal(vertices, face)
        first_ok = (vdot(vcross(vsub(b, a), vsub(c, a)), normal) > 0
                    and vdot(vcross(vsub(c, a), vsub(d, a)), normal) > 0)
        second_ok = (vdot(vcross(vsub(b, a), vsub(d, a)), normal) > 0
                     and vdot(vcross(vsub(c, b), vsub(d, b)), normal) > 0)
        if first_ok and (not second_ok or vdistance(a, c) <= vdistance(b, d) * (1.0 + 1e-12)):
            return [(face[0], face[1], face[2]), (face[0], face[2], face[3])]
        if second_ok:
            return [(face[0], face[1], face[3]), (face[1], face[2], face[3])]
        return [(face[0], face[1], face[2]), (face[0], face[2], face[3])]
    normal = face_normal(vertices, face)
    axis = max(range(3), key=lambda k: abs(normal[k]))
    u, v = {0: (1, 2), 1: (2, 0), 2: (0, 1)}[axis]
    if normal[axis] < 0:
        u, v = v, u
    flat = [(vertices[i][u], vertices[i][v]) for i in face]
    if all(cross2(flat[k - 1], flat[k], flat[(k + 1) % count]) > 0 for k in range(count)):
        return [(face[0], face[k], face[k + 1]) for k in range(1, count - 1)]
    return [(face[a], face[b], face[c]) for a, b, c in _ear_clip(flat, list(range(count)))]


def triangulated(mesh):
    """A copy whose faces are all triangles (attributes unchanged)."""
    result = mesh.copy()
    result.faces = mesh.triangles()
    return result


# ----------------------------------------------------------------------------------------------- normals, measures

def face_normals(mesh):
    """Unit Newell normal of every face."""
    return [face_normal(mesh.vertices, face) for face in mesh.faces]


def vertex_normals(mesh, weighting="angle"):
    """Unit vertex normals from the faces around each vertex, weighted by corner ``angle`` or face ``area``.

    A vertex used by no face, or whose weighted sum vanishes, gets (0, 1, 0)."""
    if weighting not in ("angle", "area"):
        raise MeshError("weighting_invalid", "weighting is 'angle' or 'area'")
    sums = [[0.0, 0.0, 0.0] for _ in mesh.vertices]
    vertices = mesh.vertices
    for face in mesh.faces:
        count = len(face)
        if weighting == "area":
            for a, b, c in triangulate_face(vertices, face):
                n = vcross(vsub(vertices[b], vertices[a]), vsub(vertices[c], vertices[a]))
                for index in (a, b, c):
                    total = sums[index]
                    total[0] += n[0]
                    total[1] += n[1]
                    total[2] += n[2]
            continue
        normal = face_normal(vertices, face)
        for k in range(count):
            p = vertices[face[k]]
            e1 = vnormalize(vsub(vertices[face[(k + 1) % count]], p))
            e2 = vnormalize(vsub(vertices[face[k - 1]], p))
            angle = math.acos(max(-1.0, min(1.0, vdot(e1, e2))))
            total = sums[face[k]]
            total[0] += normal[0] * angle
            total[1] += normal[1] * angle
            total[2] += normal[2] * angle
    return [vnormalize(tuple(total), (0.0, 1.0, 0.0)) for total in sums]


def with_normals(mesh, weighting="angle"):
    """A copy carrying smooth vertex normals."""
    result = mesh.copy()
    result.normals = vertex_normals(mesh, weighting)
    return result


def bounding_box(points):
    """(minimum, maximum) corners of the axis-aligned box around 3D points or a mesh's vertices."""
    if isinstance(points, Mesh):
        points = points.vertices
    points = list(points)
    if not points:
        raise MeshError("no_points", "a bounding box needs at least one point")
    return (tuple(min(p[k] for p in points) for k in range(3)), tuple(max(p[k] for p in points) for k in range(3)))


def triangle_area(a, b, c):
    """Area of the 3D triangle (a, b, c)."""
    return 0.5 * vlength(vcross(vsub(b, a), vsub(c, a)))


def surface_area(mesh):
    """Total area of every face."""
    v = mesh.vertices
    return math.fsum(triangle_area(v[a], v[b], v[c]) for a, b, c in mesh.triangles())


def signed_volume(mesh):
    """Enclosed volume by the divergence theorem; positive for a closed mesh with outward faces."""
    v = mesh.vertices
    return math.fsum(vdot(v[a], vcross(v[b], v[c])) for a, b, c in mesh.triangles()) / 6.0


def centroid(mesh):
    """Centre of mass of the solid a closed mesh encloses (uniform density)."""
    v = mesh.vertices
    weights, xs, ys, zs = [], [], [], []
    for a, b, c in mesh.triangles():
        w = vdot(v[a], vcross(v[b], v[c]))
        weights.append(w)
        xs.append(w * (v[a][0] + v[b][0] + v[c][0]))
        ys.append(w * (v[a][1] + v[b][1] + v[c][1]))
        zs.append(w * (v[a][2] + v[b][2] + v[c][2]))
    total = math.fsum(weights)
    if abs(total) <= EPSILON:
        raise MeshError("no_volume", "the centroid of a solid needs a closed mesh with volume")
    return (math.fsum(xs) / (4.0 * total), math.fsum(ys) / (4.0 * total), math.fsum(zs) / (4.0 * total))


def surface_centroid(mesh):
    """Area-weighted centre of the surface (works for open meshes)."""
    v = mesh.vertices
    weights, xs, ys, zs = [], [], [], []
    for a, b, c in mesh.triangles():
        w = triangle_area(v[a], v[b], v[c])
        weights.append(w)
        xs.append(w * (v[a][0] + v[b][0] + v[c][0]) / 3.0)
        ys.append(w * (v[a][1] + v[b][1] + v[c][1]) / 3.0)
        zs.append(w * (v[a][2] + v[b][2] + v[c][2]) / 3.0)
    total = math.fsum(weights)
    if total <= EPSILON:
        raise MeshError("no_area", "the surface centroid needs a mesh with area")
    return (math.fsum(xs) / total, math.fsum(ys) / total, math.fsum(zs) / total)


# ----------------------------------------------------------------------------------------------- topology

def edge_faces(mesh):
    """Map from each undirected edge (low, high) to the faces that use it, in face order."""
    result = {}
    for index, face in enumerate(mesh.faces):
        count = len(face)
        for k in range(count):
            a, b = face[k], face[(k + 1) % count]
            result.setdefault((a, b) if a < b else (b, a), []).append(index)
    return result


def edges(mesh):
    """Sorted list of the undirected edges (low, high) of the faces."""
    return sorted(edge_faces(mesh))


def vertex_neighbors(mesh):
    """For each vertex, the sorted indices of the vertices it shares a face edge with."""
    neighbors = [set() for _ in mesh.vertices]
    for a, b in edge_faces(mesh):
        neighbors[a].add(b)
        neighbors[b].add(a)
    return [sorted(group) for group in neighbors]


def vertex_faces(mesh):
    """For each vertex, the indices of the faces that use it."""
    result = [[] for _ in mesh.vertices]
    for index, face in enumerate(mesh.faces):
        for corner in face:
            result[corner].append(index)
    return result


def boundary_edges(mesh):
    """Directed edges (a, b), in face order, whose undirected edge belongs to exactly one face."""
    counts = edge_faces(mesh)
    result = []
    for face in mesh.faces:
        count = len(face)
        for k in range(count):
            a, b = face[k], face[(k + 1) % count]
            if len(counts[(a, b) if a < b else (b, a)]) == 1:
                result.append((a, b))
    return result


def boundary_loops(mesh):
    """Boundary edges chained into closed vertex loops.

    Loops follow face orientation where the faces agree; on a one-sided or inconsistently wound surface the
    chain continues through the undirected boundary edge, so a Moebius strip has one loop."""
    directed = boundary_edges(mesh)
    around = {}
    for a, b in directed:
        around.setdefault(a, []).append(b)
        around.setdefault(b, []).append(a)
    forward = {}
    for a, b in directed:
        forward.setdefault(a, []).append(b)
    used = set()
    loops = []
    for a, b in directed:
        if (min(a, b), max(a, b)) in used:
            continue
        loop = [a]
        used.add((min(a, b), max(a, b)))
        current = b
        while current != a:
            loop.append(current)
            options = [n for n in forward.get(current, []) if (min(current, n), max(current, n)) not in used]
            options += [n for n in around.get(current, []) if (min(current, n), max(current, n)) not in used
                        and n not in options]
            if not options:
                break
            following = a if a in options and len(loop) > 2 else options[0]
            used.add((min(current, following), max(current, following)))
            current = following
        loops.append(loop)
    return loops


def is_edge_manifold(mesh):
    """Whether every edge belongs to one or two faces."""
    return all(len(faces) <= 2 for faces in edge_faces(mesh).values())


def is_vertex_manifold(mesh):
    """Whether the faces around every vertex form a single fan (no bow-tie vertices)."""
    around = {}
    for index, face in enumerate(mesh.faces):
        count = len(face)
        for k in range(count):
            around.setdefault(face[k], []).append((index, face[k - 1], face[(k + 1) % count]))
    for vertex, rows in around.items():
        parent = list(range(len(rows)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        by_neighbor = {}
        for position, (_face, before, after) in enumerate(rows):
            for neighbor in (before, after):
                by_neighbor.setdefault(neighbor, []).append(position)
        for positions in by_neighbor.values():
            for other in positions[1:]:
                parent[find(other)] = find(positions[0])
        if len({find(position) for position in range(len(rows))}) > 1:
            return False
    return True


def is_manifold(mesh):
    """Edge-manifold and vertex-manifold."""
    return is_edge_manifold(mesh) and is_vertex_manifold(mesh)


def is_closed(mesh):
    """Whether every edge belongs to exactly two faces (no boundary, no fins)."""
    counts = edge_faces(mesh)
    return bool(counts) and all(len(faces) == 2 for faces in counts.values())


def is_consistently_oriented(mesh):
    """Whether no directed edge is used twice, so neighbouring faces agree on winding."""
    seen = set()
    for face in mesh.faces:
        count = len(face)
        for k in range(count):
            edge = (face[k], face[(k + 1) % count])
            if edge in seen:
                return False
            seen.add(edge)
    return True


def is_watertight(mesh):
    """Closed, manifold and consistently oriented."""
    return is_closed(mesh) and is_manifold(mesh) and is_consistently_oriented(mesh)


def euler_characteristic(mesh):
    """V - E + F, counting only vertices that some face uses."""
    used = {corner for face in mesh.faces for corner in face}
    return len(used) - len(edge_faces(mesh)) + len(mesh.faces)


def connected_components(mesh):
    """Lists of face indices, one per group of faces connected through shared vertices, in face order."""
    parent = list(range(len(mesh.vertices)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for face in mesh.faces:
        root = find(face[0])
        for corner in face[1:]:
            other = find(corner)
            if other != root:
                parent[other] = root
    groups = {}
    for index, face in enumerate(mesh.faces):
        groups.setdefault(find(face[0]), []).append(index)
    return list(groups.values())


def genus(mesh):
    """Total genus of a closed orientable mesh: (2 * components - V + E - F) / 2."""
    if not is_closed(mesh):
        raise MeshError("not_closed", "genus is defined here for closed meshes")
    value = 2 * len(connected_components(mesh)) - euler_characteristic(mesh)
    if value % 2:
        raise MeshError("not_orientable", "the Euler characteristic is odd")
    return value // 2


# ----------------------------------------------------------------------------------------------- editing

def merge_by_distance(mesh, tolerance=1e-6):
    """Weld vertices closer than ``tolerance`` (the first vertex of a group keeps its attributes).

    Faces that collapse below three distinct corners and lines that collapse to a point are dropped.
    Uses a spatial hash, about O(n) for well spread points."""
    if tolerance < 0:
        raise MeshError("tolerance_invalid", "tolerance is not negative")
    kept, remap = [], []
    if tolerance == 0:
        exact = {}
        for index, vertex in enumerate(mesh.vertices):
            if vertex not in exact:
                exact[vertex] = len(kept)
                kept.append(index)
            remap.append(exact[vertex])
    else:
        cells = {}
        for index, vertex in enumerate(mesh.vertices):
            key = (math.floor(vertex[0] / tolerance), math.floor(vertex[1] / tolerance),
                   math.floor(vertex[2] / tolerance))
            found = -1
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for candidate in cells.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                            if vdistance(mesh.vertices[kept[candidate]], vertex) <= tolerance:
                                found = candidate
                                break
                        if found >= 0:
                            break
                    if found >= 0:
                        break
                if found >= 0:
                    break
            if found < 0:
                found = len(kept)
                kept.append(index)
                cells.setdefault(key, []).append(found)
            remap.append(found)
    faces = []
    for face in mesh.faces:
        mapped = [remap[i] for i in face]
        cleaned = [corner for k, corner in enumerate(mapped) if corner != mapped[k - 1]]
        if len(cleaned) >= 3 and len(set(cleaned)) == len(cleaned):
            faces.append(tuple(cleaned))
    lines = [(remap[a], remap[b]) for a, b in mesh.lines if remap[a] != remap[b]]

    def pick(values):
        return None if values is None else [values[i] for i in kept]

    return Mesh([mesh.vertices[i] for i in kept], faces, pick(mesh.normals), pick(mesh.uvs), pick(mesh.colors),
                lines, pick(mesh.tangents), mesh.name, mesh.material)


def remove_unused_vertices(mesh):
    """A copy without vertices that no face or line uses (indices renumbered in order)."""
    used = sorted({corner for face in mesh.faces for corner in face} | {i for line in mesh.lines for i in line})
    remap = {old: new for new, old in enumerate(used)}

    def pick(values):
        return None if values is None else [values[i] for i in used]

    return Mesh([mesh.vertices[i] for i in used], [tuple(remap[i] for i in face) for face in mesh.faces],
                pick(mesh.normals), pick(mesh.uvs), pick(mesh.colors),
                [(remap[a], remap[b]) for a, b in mesh.lines], pick(mesh.tangents), mesh.name, mesh.material)


def flipped(mesh):
    """A copy with every face wound the other way and normals negated."""
    result = mesh.copy()
    result.faces = [tuple(reversed(face)) for face in mesh.faces]
    if result.normals is not None:
        result.normals = [vscale(n, -1.0) for n in result.normals]
    if result.tangents is not None:
        result.tangents = [(t[0], t[1], t[2], -t[3]) for t in result.tangents]
    return result


def transformed(mesh, matrix):
    """A copy with vertices moved by a 4 x 4 affine matrix; normals use the inverse transpose and a
    mirroring matrix reverses the winding so faces keep pointing outward."""
    normal_matrix, determinant = _normal_matrix(matrix)
    result = mesh.copy()
    result.vertices = [transform_point(matrix, v) for v in mesh.vertices]
    if mesh.normals is not None:
        result.normals = [vnormalize(tuple(math.fsum(normal_matrix[r][c] * n[c] for c in range(3))
                                           for r in range(3)), (0.0, 1.0, 0.0)) for n in mesh.normals]
    if mesh.tangents is not None:
        result.tangents = [vnormalize(transform_direction(matrix, t[:3]), (1.0, 0.0, 0.0)) + (t[3],)
                           for t in mesh.tangents]
    if determinant < 0:
        result.faces = [tuple(reversed(face)) for face in mesh.faces]
    return result


def translated(mesh, offset):
    """A copy moved by ``offset``."""
    return transformed(mesh, translation_matrix(offset))


def scaled(mesh, factors):
    """A copy scaled by a number or (sx, sy, sz) about the origin."""
    return transformed(mesh, scale_matrix(factors))


def rotated(mesh, axis, angle):
    """A copy rotated ``angle`` radians about ``axis`` through the origin."""
    return transformed(mesh, rotation_matrix(axis, angle))


def combine(meshes, name="combined"):
    """One mesh holding every face and line of ``meshes``; an attribute survives when every part has it."""
    meshes = list(meshes)
    vertices, faces, lines = [], [], []
    keep = {key: all(getattr(m, key) is not None for m in meshes) and bool(meshes)
            for key in ("normals", "uvs", "colors", "tangents")}
    attributes = {key: [] for key in keep}
    for part in meshes:
        offset = len(vertices)
        vertices.extend(part.vertices)
        faces.extend(tuple(i + offset for i in face) for face in part.faces)
        lines.extend((a + offset, b + offset) for a, b in part.lines)
        for key in keep:
            if keep[key]:
                attributes[key].extend(getattr(part, key))
    return Mesh(vertices, faces, attributes["normals"] if keep["normals"] else None,
                attributes["uvs"] if keep["uvs"] else None, attributes["colors"] if keep["colors"] else None,
                lines, attributes["tangents"] if keep["tangents"] else None, name,
                meshes[0].material if meshes else None)


def flat_shaded(mesh):
    """A copy where every face owns its corners and carries its face normal (faceted shading)."""
    vertices, faces, normals = [], [], []
    uvs = [] if mesh.uvs is not None else None
    colors = [] if mesh.colors is not None else None
    for face in mesh.faces:
        normal = face_normal(mesh.vertices, face)
        start = len(vertices)
        for corner in face:
            vertices.append(mesh.vertices[corner])
            normals.append(normal if vlength(normal) > 0 else (0.0, 1.0, 0.0))
            if uvs is not None:
                uvs.append(mesh.uvs[corner])
            if colors is not None:
                colors.append(mesh.colors[corner])
        faces.append(tuple(range(start, start + len(face))))
    return Mesh(vertices, faces, normals, uvs, colors, None, None, mesh.name, mesh.material)


def _rodrigues(vector, axis, angle):
    c, s = math.cos(angle), math.sin(angle)
    return vadd(vadd(vscale(vector, c), vscale(vcross(axis, vector), s)), vscale(axis, vdot(axis, vector) * (1.0 - c)))


def polyline_tube(points, radius=0.02, sides=8, closed=False, name="tube", material=None):
    """A tube of ``sides`` around a 3D polyline, for showing a curve in a viewer.

    Each ring is perpendicular to the averaged direction at its point; the ring frame is carried along by
    rotating it with the turn between neighbouring directions (parallel transport), and a closed polyline
    spreads the leftover angle evenly. An open tube gets one polygon cap at each end, so it is closed.
    Consecutive duplicate points are skipped. Vertices: n * sides for n distinct points."""
    pts = []
    for p in points:
        p = (float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0)
        if not pts or vdistance(p, pts[-1]) > 1e-12:
            pts.append(p)
    if closed and len(pts) > 2 and vdistance(pts[0], pts[-1]) <= 1e-12:
        pts.pop()
    count = len(pts)
    if count < 2 or sides < 3 or radius <= 0:
        raise MeshError("tube_invalid", "two distinct points, three sides and a positive radius")
    segments = [vnormalize(vsub(pts[(k + 1) % count], pts[k])) for k in range(count if closed else count - 1)]
    tangents = []
    for k in range(count):
        if closed:
            tangents.append(vnormalize(vadd(segments[k - 1], segments[k]), segments[k]))
        elif k == 0:
            tangents.append(segments[0])
        elif k == count - 1:
            tangents.append(segments[-1])
        else:
            tangents.append(vnormalize(vadd(segments[k - 1], segments[k]), segments[k]))
    first = tangents[0]
    helper = (0.0, 1.0, 0.0) if abs(first[1]) < 0.9 else (1.0, 0.0, 0.0)
    normals = [vnormalize(vcross(vcross(first, helper), first))]
    for k in range(1, count + (1 if closed else 0)):
        a, b = tangents[k - 1], tangents[k % count]
        axis = vcross(a, b)
        size = vlength(axis)
        normal = normals[-1]
        if size > 1e-15:
            normal = _rodrigues(normal, vscale(axis, 1.0 / size), math.atan2(size, vdot(a, b)))
        normals.append(vnormalize(vsub(normal, vscale(b, vdot(normal, b))), normals[-1]))
    if closed:
        closing = normals.pop()
        gap = math.atan2(vdot(closing, vcross(first, normals[0])), vdot(closing, normals[0]))
        normals = [_rodrigues(normals[k], tangents[k], -gap * k / count) for k in range(count)]
    vertices, vertex_normals, faces = [], [], []
    for point, tangent, normal in zip(pts, tangents, normals):
        binormal = vcross(tangent, normal)
        for j in range(sides):
            angle = 2.0 * math.pi * j / sides
            direction = vadd(vscale(normal, math.cos(angle)), vscale(binormal, math.sin(angle)))
            vertices.append(vadd(point, vscale(direction, radius)))
            vertex_normals.append(direction)
    for k in range(count if closed else count - 1):
        nk = (k + 1) % count
        for j in range(sides):
            nj = (j + 1) % sides
            faces.append((k * sides + j, k * sides + nj, nk * sides + nj, nk * sides + j))
    if not closed:
        faces.append(tuple(range(sides - 1, -1, -1)))
        faces.append(tuple((count - 1) * sides + j for j in range(sides)))
    return Mesh(vertices, faces, normals=vertex_normals, name=name, material=material)


# ----------------------------------------------------------------------------------------------- iso-surfaces

_FREUDENTHAL = ((0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0))


def isosurface(field, minimum, maximum, resolution, iso=0.0, normals="gradient"):
    """Polygonize the set field(x, y, z) = iso inside a box by marching tetrahedra.

    The box is sampled on a regular grid of ``resolution`` cells per axis (a number or (nx, ny, nz)); each cell
    splits into the six tetrahedra of the Freudenthal subdivision, which match across cells, so the result is
    watertight when the field is at least ``iso`` on the box boundary. Inside is field < iso; faces point
    toward increasing field. Vertices are shared through grid edges. ``normals`` is "gradient" (central
    differences of the field) or "mesh" (angle weighted). O(nx * ny * nz) field samples."""
    if isinstance(resolution, int):
        resolution = (resolution, resolution, resolution)
    nx, ny, nz = (int(r) for r in resolution)
    if min(nx, ny, nz) < 1:
        raise MeshError("resolution_invalid", "at least one cell per axis")
    lo = tuple(float(c) for c in minimum)
    hi = tuple(float(c) for c in maximum)
    step = ((hi[0] - lo[0]) / nx, (hi[1] - lo[1]) / ny, (hi[2] - lo[2]) / nz)
    if min(step) <= 0:
        raise MeshError("bounds_invalid", "maximum must exceed minimum on every axis")
    sx, sy = nx + 1, ny + 1

    def point(i, j, k):
        return (lo[0] + i * step[0], lo[1] + j * step[1], lo[2] + k * step[2])

    values = [float(field(*point(i, j, k))) for k in range(nz + 1) for j in range(ny + 1) for i in range(nx + 1)]
    vertices, faces, cache = [], [], {}

    def grid_index(i, j, k):
        return (k * sy + j) * sx + i

    def edge_vertex(a, b, pa, pb):
        key = (a, b) if a < b else (b, a)
        found = cache.get(key)
        if found is None:
            fa, fb = values[a], values[b]
            t = (iso - fa) / (fb - fa)
            found = len(vertices)
            vertices.append(vlerp(pa, pb, t))
            cache[key] = found
        return found

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                signs = {values[grid_index(i + di, j + dj, k + dk)] < iso
                         for di in (0, 1) for dj in (0, 1) for dk in (0, 1)}
                if len(signs) == 1:
                    continue
                corners = []
                for order in _FREUDENTHAL:
                    corners.clear()
                    offset = [0, 0, 0]
                    corners.append(tuple(offset))
                    for axis in order:
                        offset[axis] = 1
                        corners.append(tuple(offset))
                    ids = [grid_index(i + c[0], j + c[1], k + c[2]) for c in corners]
                    inside = [values[g] < iso for g in ids]
                    count = sum(inside)
                    if count == 0 or count == 4:
                        continue
                    points = [point(i + c[0], j + c[1], k + c[2]) for c in corners]
                    ins = [q for q in range(4) if inside[q]]
                    outs = [q for q in range(4) if not inside[q]]
                    if count == 1 or count == 3:
                        lone = ins[0] if count == 1 else outs[0]
                        others = outs if count == 1 else ins
                        tri = [edge_vertex(ids[lone], ids[o], points[lone], points[o]) for o in others]
                        polygons = [tri]
                    else:
                        a, b = ins
                        c, d = outs
                        polygons = [[edge_vertex(ids[a], ids[c], points[a], points[c]),
                                     edge_vertex(ids[a], ids[d], points[a], points[d]),
                                     edge_vertex(ids[b], ids[d], points[b], points[d]),
                                     edge_vertex(ids[b], ids[c], points[b], points[c])]]
                    inner = [points[q] for q in ins]
                    outer = [points[q] for q in outs]
                    direction = vsub(vscale(_sum3(outer), 1.0 / len(outer)), vscale(_sum3(inner), 1.0 / len(inner)))
                    for polygon in polygons:
                        if len(polygon) == 4:
                            tris = [(polygon[0], polygon[1], polygon[2]), (polygon[0], polygon[2], polygon[3])]
                        else:
                            tris = [tuple(polygon)]
                        for tri in tris:
                            if len(set(tri)) < 3:
                                continue
                            pa, pb, pc = (vertices[q] for q in tri)
                            n = vcross(vsub(pb, pa), vsub(pc, pa))
                            faces.append(tri if vdot(n, direction) >= 0 else (tri[0], tri[2], tri[1]))
    mesh = Mesh(vertices, faces, name="isosurface")
    if normals == "gradient":
        h = 0.25 * min(step)
        result = []
        for p in vertices:
            g = ((float(field(p[0] + h, p[1], p[2])) - float(field(p[0] - h, p[1], p[2]))),
                 (float(field(p[0], p[1] + h, p[2])) - float(field(p[0], p[1] - h, p[2]))),
                 (float(field(p[0], p[1], p[2] + h)) - float(field(p[0], p[1], p[2] - h))))
            result.append(vnormalize(g, (0.0, 1.0, 0.0)))
        mesh.normals = result
    elif normals == "mesh":
        mesh.normals = vertex_normals(mesh)
    elif normals is not None:
        raise MeshError("normals_invalid", "normals is 'gradient', 'mesh' or None")
    return mesh


def _sum3(points):
    return (math.fsum(p[0] for p in points), math.fsum(p[1] for p in points), math.fsum(p[2] for p in points))


# ----------------------------------------------------------------------------------------------- noise

_MASK = 0xFFFFFFFF


def hash_integers(*values, seed=0):
    """A well mixed 32-bit hash of integers and a seed (integer avalanche mixing, deterministic everywhere)."""
    h = (int(seed) * 0x9E3779B1 + 0x7F4A7C15) & _MASK
    for value in values:
        h ^= (int(value) * 0x85EBCA77) & _MASK
        h = ((h << 13) | (h >> 19)) & _MASK
        h = (h * 0xC2B2AE3D + 0x27D4EB2F) & _MASK
    h ^= h >> 16
    h = (h * 0x7FEB352D) & _MASK
    h ^= h >> 15
    h = (h * 0x846CA68B) & _MASK
    h ^= h >> 16
    return h


def _fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


_GRADIENTS_2D = ((1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
                 (0.7071067811865476, 0.7071067811865476), (-0.7071067811865476, 0.7071067811865476),
                 (0.7071067811865476, -0.7071067811865476), (-0.7071067811865476, -0.7071067811865476))
_GRADIENTS_3D = ((1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0), (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1),
                 (0, 1, 1), (0, -1, 1), (0, 1, -1), (0, -1, -1))


def gradient_noise_2d(x, y, seed=0):
    """Seeded 2D gradient noise in about [-1, 1], zero at integer lattice points, quintic interpolation."""
    x0, y0 = math.floor(x), math.floor(y)
    fx, fy = x - x0, y - y0
    total = []
    for dx in (0, 1):
        for dy in (0, 1):
            gx, gy = _GRADIENTS_2D[hash_integers(x0 + dx, y0 + dy, seed=seed) & 7]
            total.append(gx * (fx - dx) + gy * (fy - dy))
    u, v = _fade(fx), _fade(fy)
    bottom = total[0] + (total[2] - total[0]) * u
    top = total[1] + (total[3] - total[1]) * u
    return 1.4142135623730951 * (bottom + (top - bottom) * v)


def gradient_noise_3d(x, y, z, seed=0):
    """Seeded 3D gradient noise in about [-1, 1], zero at integer lattice points, quintic interpolation."""
    x0, y0, z0 = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = x - x0, y - y0, z - z0
    corner = {}
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                g = _GRADIENTS_3D[hash_integers(x0 + dx, y0 + dy, z0 + dz, seed=seed) % 12]
                corner[(dx, dy, dz)] = g[0] * (fx - dx) + g[1] * (fy - dy) + g[2] * (fz - dz)
    u, v, w = _fade(fx), _fade(fy), _fade(fz)

    def mix(a, b, t):
        return a + (b - a) * t

    x00 = mix(corner[(0, 0, 0)], corner[(1, 0, 0)], u)
    x10 = mix(corner[(0, 1, 0)], corner[(1, 1, 0)], u)
    x01 = mix(corner[(0, 0, 1)], corner[(1, 0, 1)], u)
    x11 = mix(corner[(0, 1, 1)], corner[(1, 1, 1)], u)
    return mix(mix(x00, x10, v), mix(x01, x11, v), w)


def fbm_2d(x, y, octaves=5, lacunarity=2.0, gain=0.5, seed=0):
    """Fractal sum of 2D gradient noise octaves, normalized by the total amplitude (about [-1, 1])."""
    total, amplitude, frequency, norm = 0.0, 1.0, 1.0, 0.0
    for octave in range(int(octaves)):
        total += amplitude * gradient_noise_2d(x * frequency, y * frequency, seed + 1013 * octave)
        norm += amplitude
        amplitude *= gain
        frequency *= lacunarity
    return total / norm if norm else 0.0


def fbm_3d(x, y, z, octaves=5, lacunarity=2.0, gain=0.5, seed=0):
    """Fractal sum of 3D gradient noise octaves, normalized by the total amplitude (about [-1, 1])."""
    total, amplitude, frequency, norm = 0.0, 1.0, 1.0, 0.0
    for octave in range(int(octaves)):
        total += amplitude * gradient_noise_3d(x * frequency, y * frequency, z * frequency, seed + 1013 * octave)
        norm += amplitude
        amplitude *= gain
        frequency *= lacunarity
    return total / norm if norm else 0.0


# ----------------------------------------------------------------------------------------------- glTF writer

_FLOAT, _UBYTE, _USHORT, _UINT = 5126, 5121, 5123, 5125
_COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
_ARRAY_BUFFER, _ELEMENT_ARRAY_BUFFER = 34962, 34963
#: The node properties a transform or an animation channel sets; a rotation is a unit quaternion (VEC4), the others
#: are VEC3.
_NODE_PATHS = (_TRANSLATION, _ROTATION, _SCALE) = ("translation", "rotation", "scale")


def _sanitize(name, fallback):
    cleaned = "".join(ch if ch.isascii() and (ch.isalnum() or ch == "_") else "_" for ch in str(name)).strip("_")
    return cleaned or fallback


def _f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


class _Buffer:
    def __init__(self):
        self.data = bytearray()
        self.views = []
        self.accessors = []

    def add(self, payload, target=None):
        while len(self.data) % 4:
            self.data.append(0)
        view = {"buffer": 0, "byteOffset": len(self.data), "byteLength": len(payload)}
        if target is not None:
            view["target"] = target
        self.data += payload
        self.views.append(view)
        return len(self.views) - 1

    def accessor(self, rows, kind, component=_FLOAT, target=_ARRAY_BUFFER, normalized=False, bounds=False):
        width = _WIDTH[kind]
        code = _COMPONENT[component][0]
        flat = []
        for row in rows:
            if width == 1:
                flat.append(row)
            else:
                flat.extend(row)
        if component == _FLOAT:
            flat = [float(v) for v in flat]
        else:
            flat = [int(v) for v in flat]
        payload = struct.pack("<" + code * len(flat), *flat)
        view = self.add(payload, target)
        record = {"bufferView": view, "componentType": component, "count": len(flat) // width, "type": kind}
        if normalized:
            record["normalized"] = True
        if bounds:
            rounded = [_f32(v) for v in flat] if component == _FLOAT else flat
            record["min"] = [min(rounded[k::width]) for k in range(width)]
            record["max"] = [max(rounded[k::width]) for k in range(width)]
        self.accessors.append(record)
        return len(self.accessors) - 1


def gltf_document(meshes, nodes=None, animations=None, generator=GENERATOR):
    """A glTF 2.0 document (a JSON-ready dict) with one embedded base64 buffer.

    ``meshes`` is a list of :class:`Mesh`. Each becomes one glTF mesh with a triangle primitive (faces
    triangulated) and, when it has lines, a line primitive. ``nodes`` is an optional list of dicts with
    ``name``, ``mesh`` (index or None), ``children``, ``translation``, ``rotation`` (x, y, z, w) and ``scale``;
    without it every mesh gets one node. ``animations`` is an optional list of dicts with ``name`` and
    ``channels`` (dicts with ``node``, ``path`` of translation, rotation or scale, ``times``, ``values`` and an
    optional ``interpolation`` of LINEAR or STEP)."""
    meshes = list(meshes)
    if not meshes:
        raise MeshError("no_meshes", "a document needs at least one mesh")
    buffer = _Buffer()
    gltf_meshes, materials, material_index = [], [], {}
    used_names = set()

    def unique(name, fallback):
        base = _sanitize(name, fallback)
        candidate, counter = base, 1
        while candidate in used_names:
            counter += 1
            candidate = f"{base}_{counter}"
        used_names.add(candidate)
        return candidate

    for mesh_number, mesh in enumerate(meshes):
        mesh.validate()
        triangles = mesh.triangles()
        if not triangles and not mesh.lines:
            raise MeshError("mesh_empty", f"mesh {mesh_number} has no faces and no lines")
        if not mesh.vertices:
            raise MeshError("mesh_empty", f"mesh {mesh_number} has no vertices")
        attribute_cache = {}

        def attribute_set(used, with_surface):
            """Accessors for the vertices ``used`` (all when None); each primitive carries only what it indexes."""
            key = (tuple(used) if used is not None else None, with_surface)
            if key in attribute_cache:
                return attribute_cache[key]
            pick = (lambda values: values) if used is None else (lambda values: [values[i] for i in used])
            accessors = {"POSITION": buffer.accessor(pick(mesh.vertices), "VEC3", bounds=True)}
            if with_surface and mesh.normals is not None:
                accessors["NORMAL"] = buffer.accessor([vnormalize(n, (0.0, 1.0, 0.0)) for n in pick(mesh.normals)], "VEC3")
            if with_surface and mesh.tangents is not None:
                accessors["TANGENT"] = buffer.accessor(
                    [vnormalize(t[:3], (1.0, 0.0, 0.0)) + (1.0 if t[3] >= 0 else -1.0,) for t in pick(mesh.tangents)], "VEC4")
            if with_surface and mesh.uvs is not None:
                accessors["TEXCOORD_0"] = buffer.accessor(pick(mesh.uvs), "VEC2")
            if mesh.colors is not None:
                accessors["COLOR_0"] = buffer.accessor(
                    [tuple(max(0, min(255, int(round(c * 255.0)))) for c in _rgba(color)) for color in pick(mesh.colors)],
                    "VEC4", component=_UBYTE, normalized=True)
            attribute_cache[key] = accessors
            return accessors

        def compact(indices):
            used = sorted(set(indices))
            if len(used) == len(mesh.vertices):
                return None, list(indices), len(mesh.vertices)
            remap = {old: new for new, old in enumerate(used)}
            return used, [remap[i] for i in indices], len(used)

        primitives = []
        if triangles:
            spec = dict(mesh.material) if mesh.material else material("default", (0.78, 0.8, 0.84, 1.0))
            if spec.get("double_sided") is None:
                spec["double_sided"] = not is_closed(mesh)
            key = json.dumps(spec, sort_keys=True)
            if key not in material_index:
                record = {"name": _sanitize(spec["name"], "material"),
                          "pbrMetallicRoughness": {"baseColorFactor": list(spec["base_color"]),
                                                   "metallicFactor": spec["metallic"],
                                                   "roughnessFactor": spec["roughness"]}}
                if spec["double_sided"]:
                    record["doubleSided"] = True
                if spec.get("emissive"):
                    record["emissiveFactor"] = list(spec["emissive"])
                material_index[key] = len(materials)
                materials.append(record)
            used, indices, count = compact([i for tri in triangles for i in tri])
            primitives.append({"attributes": attribute_set(used, True),
                               "indices": buffer.accessor(indices, "SCALAR", _USHORT if count <= 65535 else _UINT,
                                                          _ELEMENT_ARRAY_BUFFER),
                               "material": material_index[key], "mode": 4})
        if mesh.lines:
            used, indices, count = compact([i for line in mesh.lines for i in line])
            primitives.append({"attributes": attribute_set(used, False),
                               "indices": buffer.accessor(indices, "SCALAR", _USHORT if count <= 65535 else _UINT,
                                                          _ELEMENT_ARRAY_BUFFER), "mode": 1})
        gltf_meshes.append({"name": unique(mesh.name, f"mesh_{mesh_number}"), "primitives": primitives})
    if nodes is None:
        nodes = [{"name": gltf_meshes[k]["name"], "mesh": k} for k in range(len(meshes))]
    gltf_nodes, children_of = [], set()
    node_names = set()
    for number, node in enumerate(nodes):
        name = _sanitize(node.get("name", f"node_{number}"), f"node_{number}")
        candidate, counter = name, 1
        while candidate in node_names:
            counter += 1
            candidate = f"{name}_{counter}"
        node_names.add(candidate)
        record = {"name": candidate}
        if node.get("mesh") is not None:
            if not 0 <= int(node["mesh"]) < len(gltf_meshes):
                raise MeshError("node_invalid", f"node {number} names mesh {node['mesh']}")
            record["mesh"] = int(node["mesh"])
        if node.get("children"):
            record["children"] = [int(c) for c in node["children"]]
            children_of.update(record["children"])
        for key, size in ((_TRANSLATION, 3), (_ROTATION, 4), (_SCALE, 3)):
            if node.get(key) is not None:
                value = [float(c) for c in node[key]]
                if len(value) != size:
                    raise MeshError("node_invalid", f"node {number} {key} has {size} values")
                if key == _ROTATION:
                    norm = math.sqrt(sum(c * c for c in value))
                    value = [c / norm for c in value]
                record[key] = value
        gltf_nodes.append(record)
    roots = [k for k in range(len(gltf_nodes)) if k not in children_of]
    document = {"asset": {"version": "2.0", "generator": generator}, "scene": 0,
                "scenes": [{"name": "scene", "nodes": roots}], "nodes": gltf_nodes, "meshes": gltf_meshes}
    if materials:
        document["materials"] = materials
    if animations:
        gltf_animations = []
        for number, animation in enumerate(animations):
            channels, samplers = [], []
            for channel in animation["channels"]:
                path = channel["path"]
                if path not in _NODE_PATHS:
                    raise MeshError("animation_invalid", f"path {path}")
                times = [float(t) for t in channel["times"]]
                values = [tuple(float(c) for c in v) for v in channel["values"]]
                if len(times) != len(values) or not times:
                    raise MeshError("animation_invalid", "times and values differ in length")
                if any(b <= a for a, b in zip(times, times[1:])):
                    raise MeshError("animation_invalid", "times must increase")
                if path == _ROTATION:
                    values = [tuple(c / math.sqrt(sum(q * q for q in v)) for c in v) for v in values]
                kind = "VEC4" if path == _ROTATION else "VEC3"
                inputs = buffer.accessor(times, "SCALAR", target=None, bounds=True)
                outputs = buffer.accessor(values, kind, target=None)
                samplers.append({"input": inputs, "output": outputs,
                                 "interpolation": channel.get("interpolation", "LINEAR")})
                channels.append({"sampler": len(samplers) - 1, "target": {"node": int(channel["node"]), "path": path}})
            gltf_animations.append({"name": _sanitize(animation.get("name", f"animation_{number}"),
                                                      f"animation_{number}"), "channels": channels,
                                    "samplers": samplers})
        document["animations"] = gltf_animations
    while len(buffer.data) % 4:
        buffer.data.append(0)
    document["buffers"] = [{"byteLength": len(buffer.data),
                            "uri": "data:application/octet-stream;base64," + base64.b64encode(bytes(buffer.data)).decode()}]
    document["bufferViews"] = buffer.views
    document["accessors"] = buffer.accessors
    return document


def gltf_text(meshes, nodes=None, animations=None, generator=GENERATOR):
    """The glTF document as compact UTF-8 JSON text (deterministic for the same input)."""
    return json.dumps(gltf_document(meshes, nodes, animations, generator), separators=(",", ":")) + "\n"


def write_gltf(path, meshes, nodes=None, animations=None):
    """Write a .gltf file and return :func:`read_gltf`'s summary of what was written."""
    text = gltf_text(meshes, nodes, animations)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    return read_gltf(text)


# ----------------------------------------------------------------------------------------------- glTF reader

def _decode_buffer(document, number):
    buffers = document.get("buffers")
    if not isinstance(buffers, list) or not 0 <= number < len(buffers):
        raise GltfError("buffer_missing", f"buffer {number}")
    record = buffers[number]
    uri = record.get("uri") if isinstance(record, dict) else None
    prefix = "data:application/octet-stream;base64,"
    if not isinstance(uri, str) or not (uri.startswith(prefix) or uri.startswith("data:application/gltf-buffer;base64,")):
        raise GltfError("buffer_not_embedded", f"buffer {number} is not an embedded base64 data URI")
    try:
        data = base64.b64decode(uri.split(",", 1)[1], validate=True)
    except (ValueError, TypeError):
        raise GltfError("buffer_base64_invalid", f"buffer {number}") from None
    if record.get("byteLength") != len(data):
        raise GltfError("buffer_length_mismatch", f"buffer {number} declares {record.get('byteLength')} bytes, holds {len(data)}")
    return data


def _accessor_rows(document, buffers, number):
    accessors = document.get("accessors", [])
    if not isinstance(number, int) or not 0 <= number < len(accessors):
        raise GltfError("accessor_missing", f"accessor {number}")
    accessor = accessors[number]
    kind, component, count = accessor.get("type"), accessor.get("componentType"), accessor.get("count")
    if kind not in _WIDTH or component not in _COMPONENT or not isinstance(count, int) or count < 1:
        raise GltfError("accessor_invalid", f"accessor {number}")
    views = document.get("bufferViews", [])
    view_number = accessor.get("bufferView")
    if not isinstance(view_number, int) or not 0 <= view_number < len(views):
        raise GltfError("buffer_view_missing", f"accessor {number}")
    view = views[view_number]
    data = buffers[view.get("buffer", -1)] if view.get("buffer") in buffers else None
    if data is None:
        raise GltfError("buffer_missing", f"buffer view {view_number}")
    view_offset, view_length = view.get("byteOffset", 0), view.get("byteLength")
    if not isinstance(view_length, int) or view_offset < 0 or view_offset + view_length > len(data):
        raise GltfError("buffer_view_out_of_range", f"buffer view {view_number}")
    code, size = _COMPONENT[component]
    width = _WIDTH[kind]
    element = size * width
    stride = view.get("byteStride", element)
    offset = accessor.get("byteOffset", 0)
    if offset % size or (view_offset + offset) % size or stride < element:
        raise GltfError("accessor_misaligned", f"accessor {number}")
    if offset + stride * (count - 1) + element > view_length:
        raise GltfError("accessor_out_of_range", f"accessor {number} reads past its buffer view")
    rows = []
    base = view_offset + offset
    unpack = struct.Struct("<" + code * width).unpack_from
    for row in range(count):
        values = unpack(data, base + row * stride)
        if accessor.get("normalized"):
            scale = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}.get(component)
            if scale is None:
                raise GltfError("accessor_invalid", f"accessor {number} normalizes a type that cannot be")
            values = tuple(max(v / scale, -1.0) for v in values)
        if component == _FLOAT and not all(math.isfinite(v) for v in values):
            raise GltfError("accessor_not_finite", f"accessor {number}")
        rows.append(values[0] if width == 1 else values)
    for key in ("min", "max"):
        if key in accessor and (not isinstance(accessor[key], list) or len(accessor[key]) != width):
            raise GltfError("accessor_bounds_invalid", f"accessor {number} {key}")
    return accessor, rows


def _check_bounds(accessor, rows, number, width):
    columns = [[row[k] if width > 1 else row for row in rows] for k in range(width)]
    for k in range(width):
        low, high = min(columns[k]), max(columns[k])
        scale = max(1.0, abs(low), abs(high))
        if abs(accessor["min"][k] - low) > 1e-6 * scale or abs(accessor["max"][k] - high) > 1e-6 * scale:
            raise GltfError("accessor_bounds_wrong", f"accessor {number} axis {k}: declared "
                                                     f"[{accessor['min'][k]}, {accessor['max'][k]}], data [{low}, {high}]")


def read_gltf(source):
    """Strictly verify a .gltf (path, JSON text or parsed dict) whose buffers are embedded, and summarize it.

    Checks the asset version, buffer lengths, buffer view and accessor ranges and alignment, POSITION
    bounds against the data, attribute counts, unit normals, tangent signs, index range and multiplicity,
    materials, the node tree (no cycles, one parent), scenes and animation samplers. Raises GltfError with a
    reason code on the first problem. Returns {"meshes": [{"name", "primitives": [{"mode", "vertex_count",
    "index_count", "attributes", "positions", "indices"}]}], "nodes", "scene_nodes", "animations",
    "materials", "vertex_count", "triangle_count", "line_count"}."""
    if isinstance(source, dict):
        document = source
    else:
        text = source
        if not (isinstance(source, str) and source.lstrip().startswith("{")):
            with open(source, "r", encoding="utf-8") as stream:
                text = stream.read()
        try:
            document = json.loads(text)
        except json.JSONDecodeError as error:
            raise GltfError("json_invalid", str(error)) from None
    if not isinstance(document, dict) or document.get("asset", {}).get("version") != "2.0":
        raise GltfError("asset_version_invalid", "asset.version must be 2.0")
    buffers = {number: _decode_buffer(document, number) for number in range(len(document.get("buffers", [])))}
    for number, view in enumerate(document.get("bufferViews", [])):
        if view.get("buffer") not in buffers:
            raise GltfError("buffer_missing", f"buffer view {number}")
        if view.get("byteOffset", 0) + view.get("byteLength", 0) > len(buffers[view["buffer"]]):
            raise GltfError("buffer_view_out_of_range", f"buffer view {number}")
        stride = view.get("byteStride")
        if stride is not None and (stride < 4 or stride > 252 or stride % 4):
            raise GltfError("buffer_view_stride_invalid", f"buffer view {number}")
    material_count = len(document.get("materials", []))
    summary_meshes = []
    totals = {"vertex_count": 0, "triangle_count": 0, "line_count": 0}
    for mesh_number, mesh in enumerate(document.get("meshes", [])):
        primitives = mesh.get("primitives")
        if not isinstance(primitives, list) or not primitives:
            raise GltfError("mesh_invalid", f"mesh {mesh_number} has no primitives")
        rows = []
        for primitive_number, primitive in enumerate(primitives):
            where = f"mesh {mesh_number} primitive {primitive_number}"
            attributes = primitive.get("attributes", {})
            if "POSITION" not in attributes:
                raise GltfError("position_missing", where)
            mode = primitive.get("mode", 4)
            if mode not in (0, 1, 2, 3, 4, 5, 6):
                raise GltfError("mode_invalid", where)
            data = {}
            for name, accessor_number in attributes.items():
                accessor, values = _accessor_rows(document, buffers, accessor_number)
                data[name] = (accessor, values)
            vertex_count = len(data["POSITION"][1])
            for name, (accessor, values) in data.items():
                if len(values) != vertex_count:
                    raise GltfError("attribute_count_mismatch", f"{where} {name}")
            position_accessor, positions = data["POSITION"]
            if position_accessor["type"] != "VEC3" or position_accessor["componentType"] != _FLOAT:
                raise GltfError("position_invalid", where)
            if "min" not in position_accessor or "max" not in position_accessor:
                raise GltfError("position_bounds_missing", where)
            _check_bounds(position_accessor, positions, attributes["POSITION"], 3)
            if "NORMAL" in data:
                accessor, normals = data["NORMAL"]
                if accessor["type"] != "VEC3" or accessor["componentType"] != _FLOAT:
                    raise GltfError("normal_invalid", where)
                for k, n in enumerate(normals):
                    if abs(math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) - 1.0) > 5e-4:
                        raise GltfError("normal_not_unit", f"{where} vertex {k}")
            if "TANGENT" in data:
                accessor, tangents = data["TANGENT"]
                if accessor["type"] != "VEC4" or accessor["componentType"] != _FLOAT:
                    raise GltfError("tangent_invalid", where)
                for k, t in enumerate(tangents):
                    if abs(math.sqrt(t[0] * t[0] + t[1] * t[1] + t[2] * t[2]) - 1.0) > 5e-4 or t[3] not in (1.0, -1.0):
                        raise GltfError("tangent_invalid", f"{where} vertex {k}")
            if "TEXCOORD_0" in data and data["TEXCOORD_0"][0]["type"] != "VEC2":
                raise GltfError("texcoord_invalid", where)
            if "COLOR_0" in data:
                accessor = data["COLOR_0"][0]
                if accessor["type"] not in ("VEC3", "VEC4") or (accessor["componentType"] != _FLOAT
                                                                 and not accessor.get("normalized")):
                    raise GltfError("color_invalid", where)
            indices = None
            if "indices" in primitive:
                accessor, indices = _accessor_rows(document, buffers, primitive["indices"])
                if accessor["type"] != "SCALAR" or accessor["componentType"] not in (_UBYTE, _USHORT, _UINT):
                    raise GltfError("indices_invalid", where)
                restart = {_UBYTE: 255, _USHORT: 65535, _UINT: 4294967295}[accessor["componentType"]]
                for value in indices:
                    if value >= vertex_count or value == restart:
                        raise GltfError("index_out_of_range", f"{where}: index {value} for {vertex_count} vertices")
            count = len(indices) if indices is not None else vertex_count
            if mode == 4 and count % 3:
                raise GltfError("index_count_invalid", f"{where}: {count} is not a multiple of 3")
            if mode == 1 and count % 2:
                raise GltfError("index_count_invalid", f"{where}: {count} is not a multiple of 2")
            if "material" in primitive and not 0 <= primitive["material"] < material_count:
                raise GltfError("material_missing", where)
            totals["vertex_count"] += vertex_count
            if mode == 4:
                totals["triangle_count"] += count // 3
            elif mode == 1:
                totals["line_count"] += count // 2
            rows.append({"mode": mode, "vertex_count": vertex_count, "index_count": None if indices is None else count,
                         "attributes": sorted(attributes), "positions": positions,
                         "indices": indices if indices is not None else list(range(vertex_count))})
        summary_meshes.append({"name": mesh.get("name", f"mesh_{mesh_number}"), "primitives": rows})
    nodes = document.get("nodes", [])
    parents = {}
    for number, node in enumerate(nodes):
        if "mesh" in node and not 0 <= node["mesh"] < len(summary_meshes):
            raise GltfError("node_mesh_missing", f"node {number}")
        for child in node.get("children", []):
            if not 0 <= child < len(nodes) or child == number or child in parents:
                raise GltfError("node_tree_invalid", f"node {number} child {child}")
            parents[child] = number
        if "rotation" in node:
            q = node["rotation"]
            if len(q) != 4 or abs(math.sqrt(sum(c * c for c in q)) - 1.0) > 1e-5:
                raise GltfError("node_rotation_invalid", f"node {number}")
    for start in range(len(nodes)):
        seen, current = set(), start
        while current in parents:
            if current in seen:
                raise GltfError("node_cycle", f"node {start}")
            seen.add(current)
            current = parents[current]
    scenes = document.get("scenes", [])
    if not scenes or not 0 <= document.get("scene", 0) < len(scenes):
        raise GltfError("scene_missing", "the document needs a scene")
    scene_nodes = scenes[document.get("scene", 0)].get("nodes", [])
    for number in scene_nodes:
        if not 0 <= number < len(nodes) or number in parents:
            raise GltfError("scene_node_invalid", f"node {number}")
    animation_count = 0
    for number, animation in enumerate(document.get("animations", [])):
        samplers = animation.get("samplers", [])
        for sampler in samplers:
            accessor, times = _accessor_rows(document, buffers, sampler.get("input"))
            if accessor["type"] != "SCALAR" or "min" not in accessor or "max" not in accessor:
                raise GltfError("animation_input_invalid", f"animation {number}")
            _check_bounds(accessor, times, sampler.get("input"), 1)
            if any(b <= a for a, b in zip(times, times[1:])):
                raise GltfError("animation_times_invalid", f"animation {number}")
            _out, values = _accessor_rows(document, buffers, sampler.get("output"))
            factor = 3 if sampler.get("interpolation") == "CUBICSPLINE" else 1
            if len(values) != factor * len(times):
                raise GltfError("animation_output_count", f"animation {number}")
        for channel in animation.get("channels", []):
            if not 0 <= channel.get("sampler", -1) < len(samplers):
                raise GltfError("animation_channel_invalid", f"animation {number}")
            target = channel.get("target", {})
            if not 0 <= target.get("node", -1) < len(nodes) or target.get("path") not in (
                    "translation", "rotation", "scale", "weights"):
                raise GltfError("animation_channel_invalid", f"animation {number}")
        animation_count += 1
    return {"meshes": summary_meshes, "nodes": len(nodes), "scene_nodes": list(scene_nodes),
            "animations": animation_count, "materials": material_count, **totals}


def node_world_matrices(document):
    """World matrix of every node of a parsed glTF document (TRS composed down the hierarchy)."""
    nodes = document.get("nodes", [])
    parents = {child: number for number, node in enumerate(nodes) for child in node.get("children", [])}
    cache = {}

    def world(number):
        if number not in cache:
            node = nodes[number]
            local = trs_matrix(node.get("translation", (0.0, 0.0, 0.0)), node.get("rotation", (0.0, 0.0, 0.0, 1.0)),
                               node.get("scale", (1.0, 1.0, 1.0)))
            cache[number] = matrix_multiply(world(parents[number]), local) if number in parents else local
        return cache[number]

    return [world(number) for number in range(len(nodes))]


def mesh_from_gltf(source, mesh_index=0):
    """The triangles of one glTF mesh as a :class:`Mesh` (positions and triangle faces only)."""
    summary = read_gltf(source)
    if not 0 <= mesh_index < len(summary["meshes"]):
        raise GltfError("mesh_missing", f"mesh {mesh_index}")
    vertices, faces = [], []
    for primitive in summary["meshes"][mesh_index]["primitives"]:
        if primitive["mode"] != 4:
            continue
        offset = len(vertices)
        vertices.extend(primitive["positions"])
        indices = primitive["indices"]
        faces.extend((offset + indices[k], offset + indices[k + 1], offset + indices[k + 2])
                     for k in range(0, len(indices), 3))
    return Mesh(vertices, faces, name=summary["meshes"][mesh_index]["name"])


# ----------------------------------------------------------------------------------------------- OBJ

def _number(value):
    return repr(float(value))


def obj_text(meshes):
    """Wavefront OBJ text for ``meshes`` (one object each; positions, texture coordinates, normals, polygon
    faces and lines; indices are 1-based)."""
    lines = [f"# {GENERATOR}"]
    v_offset = vt_offset = vn_offset = 0
    for number, mesh in enumerate(meshes):
        mesh.validate()
        lines.append("o " + _sanitize(mesh.name, f"mesh_{number}"))
        lines.extend("v " + " ".join(_number(c) for c in v) for v in mesh.vertices)
        if mesh.uvs is not None:
            lines.extend("vt " + " ".join(_number(c) for c in t) for t in mesh.uvs)
        if mesh.normals is not None:
            lines.extend("vn " + " ".join(_number(c) for c in vnormalize(n, (0.0, 1.0, 0.0))) for n in mesh.normals)
        for face in mesh.faces:
            corners = []
            for i in face:
                token = str(v_offset + i + 1)
                if mesh.uvs is not None and mesh.normals is not None:
                    token += f"/{vt_offset + i + 1}/{vn_offset + i + 1}"
                elif mesh.uvs is not None:
                    token += f"/{vt_offset + i + 1}"
                elif mesh.normals is not None:
                    token += f"//{vn_offset + i + 1}"
                corners.append(token)
            lines.append("f " + " ".join(corners))
        lines.extend(f"l {v_offset + a + 1} {v_offset + b + 1}" for a, b in mesh.lines)
        v_offset += len(mesh.vertices)
        vt_offset += len(mesh.uvs) if mesh.uvs is not None else 0
        vn_offset += len(mesh.normals) if mesh.normals is not None else 0
    return "\n".join(lines) + "\n"


def write_obj(path, meshes):
    """Write an OBJ file and return the mesh it reads back as (see :func:`read_obj`)."""
    text = obj_text(meshes)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    return read_obj(text)


def read_obj(source):
    """Parse OBJ text (or a path) into one :class:`Mesh` of positions, polygon faces and lines.

    Accepts v, v/vt, v//vn and v/vt/vn corners and negative (relative) indices; raises MeshError on an index
    out of range or a malformed line."""
    text = source
    if not isinstance(source, str) or ("\n" not in source and not source.lstrip().startswith(("v ", "#", "o "))):
        with open(source, "r", encoding="utf-8") as stream:
            text = stream.read()
    vertices, faces, lines = [], [], []

    def resolve(token, number):
        raw = token.split("/")[0]
        try:
            value = int(raw)
        except ValueError:
            raise MeshError("obj_invalid", f"line {number}: {token}") from None
        index = value - 1 if value > 0 else len(vertices) + value
        if not 0 <= index < len(vertices):
            raise MeshError("index_out_of_range", f"line {number}: {token}")
        return index

    for number, line in enumerate(text.splitlines(), 1):
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        if parts[0] == "v":
            try:
                vertices.append(tuple(float(c) for c in parts[1:4]))
            except ValueError:
                raise MeshError("obj_invalid", f"line {number}") from None
            if len(vertices[-1]) != 3:
                raise MeshError("obj_invalid", f"line {number}")
        elif parts[0] == "f":
            if len(parts) < 4:
                raise MeshError("face_too_small", f"line {number}")
            faces.append(tuple(resolve(token, number) for token in parts[1:]))
        elif parts[0] == "l":
            indices = [resolve(token, number) for token in parts[1:]]
            lines.extend(zip(indices, indices[1:]))
    return Mesh(vertices, faces, lines=lines, name="obj")


# ----------------------------------------------------------------------------------------------- command line

def _boolean(text):
    lowered = str(text).strip().lower()
    if lowered in ("1", "true", "yes", "on"):
        return True
    if lowered in ("0", "false", "no", "off"):
        return False
    raise argparse.ArgumentTypeError(f"{text!r} is not true or false")


def parameter_parser(parameters, description=""):
    """An argparse parser with ``--output`` and one option per parameter description.

    A parameter is a dict with ``name``, ``type`` (float, int, str or bool), ``default`` and optionally
    ``minimum``, ``maximum``, ``choices``, ``unit`` and ``meaning``."""
    parser = argparse.ArgumentParser(description=(description or "").strip().splitlines()[0] if description else None)
    parser.add_argument("--output", required=True, help="where to write: a .gltf or .obj path")
    parser.add_argument("--report", help="optional .json path for the item's report, when it makes one")
    kinds = {"float": float, "int": int, "str": str, "bool": _boolean}
    for spec in parameters:
        flag = "--" + spec["name"].replace("_", "-")
        options = {"dest": spec["name"], "type": kinds[spec["type"]], "default": spec["default"],
                   "help": f"{spec.get('meaning', '')} ({spec.get('unit', '')}, default {spec['default']})"}
        if spec.get("choices"):
            options["choices"] = spec["choices"]
        parser.add_argument(flag, **options)
    return parser


def _scene_parts(result):
    if isinstance(result, Mesh):
        return {"meshes": [result]}
    if isinstance(result, (list, tuple)) and result and all(isinstance(m, Mesh) for m in result):
        return {"meshes": list(result)}
    if isinstance(result, dict) and result.get("meshes"):
        return result
    raise MeshError("build_result_invalid", "build returns a Mesh, a list of Mesh or a dict with meshes")


def run_cli(argv, *, description, parameters, build):
    """Parse the options, call ``build(**values)`` and write its result as .gltf or .obj.

    ``build`` returns a Mesh, a list of Mesh, or a dict with ``meshes`` and optionally ``nodes``,
    ``animations`` and ``report``. Prints a one-line JSON summary and returns 0. A value outside its declared
    range, an unknown option or an output that is neither .gltf nor .obj exits with status 2 (argparse)."""
    parser = parameter_parser(parameters, description)
    arguments = parser.parse_args(argv)
    values = {}
    for spec in parameters:
        value = getattr(arguments, spec["name"])
        if spec.get("minimum") is not None and value < spec["minimum"]:
            parser.error(f"--{spec['name'].replace('_', '-')} must be at least {spec['minimum']}")
        if spec.get("maximum") is not None and value > spec["maximum"]:
            parser.error(f"--{spec['name'].replace('_', '-')} must be at most {spec['maximum']}")
        values[spec["name"]] = value
    output = arguments.output
    suffix = output.lower().rsplit(".", 1)[-1] if "." in output else ""
    if suffix not in ("gltf", "obj"):
        parser.error("--output ends with .gltf or .obj")
    parts = _scene_parts(build(**values))
    meshes = parts["meshes"]
    if suffix == "gltf":
        summary = write_gltf(output, meshes, parts.get("nodes"), parts.get("animations"))
        line = {"format": "gltf", "meshes": len(summary["meshes"]), "nodes": summary["nodes"],
                "animations": summary["animations"], "vertices": summary["vertex_count"],
                "triangles": summary["triangle_count"], "lines": summary["line_count"]}
    else:
        if parts.get("nodes"):
            meshes = _baked(meshes, parts["nodes"])
        mesh = write_obj(output, meshes)
        line = {"format": "obj", "meshes": len(meshes), "vertices": len(mesh.vertices),
                "faces": len(mesh.faces), "lines": len(mesh.lines)}
    if parts.get("report") is not None:
        line["report"] = parts["report"]
        if arguments.report:
            with open(arguments.report, "w", encoding="utf-8") as stream:
                json.dump(parts["report"], stream, indent=1, sort_keys=True)
                stream.write("\n")
    print(json.dumps(line, sort_keys=True))
    return 0


def _baked(meshes, nodes):
    """Meshes placed by their nodes' world transforms (for formats without a node hierarchy)."""
    document = {"nodes": [{key: node[key] for key in ("translation", "rotation", "scale", "children")
                           if node.get(key) is not None} for node in nodes]}
    worlds = node_world_matrices(document)
    placed = []
    for number, node in enumerate(nodes):
        if node.get("mesh") is not None:
            part = transformed(meshes[node["mesh"]], worlds[number])
            part.name = node.get("name", part.name)
            placed.append(part)
    return placed


__all__ = [name for name in dir() if not name.startswith("_") and name not in (
    "annotations", "argparse", "base64", "json", "math", "struct", "sys")]
