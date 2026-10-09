"""Mesh checks with the standard library only.

A mesh is a list of (x, y, z) vertices in metres and a list of faces. Each face lists vertex indices
counter-clockwise when seen from outside, so a closed mesh has outward normals and positive volume.
Every function is read-only and returns plain values, so a test can use them without Blender.
"""
from __future__ import annotations

import math


def face_normal(vertices, face):
    """Newell normal of a polygon; its length is twice the polygon area."""
    nx = ny = nz = 0.0
    count = len(face)
    for position in range(count):
        x1, y1, z1 = vertices[face[position]]
        x2, y2, z2 = vertices[face[(position + 1) % count]]
        nx += (y1 - y2) * (z1 + z2)
        ny += (z1 - z2) * (x1 + x2)
        nz += (x1 - x2) * (y1 + y2)
    return (nx, ny, nz)


def face_area(vertices, face):
    """Area of a planar or nearly planar polygon in square metres."""
    nx, ny, nz = face_normal(vertices, face)
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


def problems(vertices, faces, *, allow_degenerate=False, minimum_area=1e-12):
    """Every structural problem as (code, index) pairs; an empty list means the mesh is well formed.

    Codes: vertex_invalid, face_too_small, index_invalid, index_out_of_range, face_repeats_vertex,
    face_degenerate."""
    found = []
    count = len(vertices)
    for index, vertex in enumerate(vertices):
        if (not isinstance(vertex, (list, tuple)) or len(vertex) != 3
                or not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                           for value in vertex)):
            found.append(("vertex_invalid", index))
    if found:
        return found
    for index, face in enumerate(faces):
        if not isinstance(face, (list, tuple)) or len(face) < 3:
            found.append(("face_too_small", index))
            continue
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in face):
            found.append(("index_invalid", index))
            continue
        if any(value < 0 or value >= count for value in face):
            found.append(("index_out_of_range", index))
            continue
        if len(set(face)) != len(face):
            found.append(("face_repeats_vertex", index))
            continue
        if not allow_degenerate and face_area(vertices, face) <= minimum_area:
            found.append(("face_degenerate", index))
    return found


def edge_use(faces):
    """Map of each undirected edge (low, high) to the number of faces that use it."""
    use = {}
    for face in faces:
        for position in range(len(face)):
            a, b = face[position], face[(position + 1) % len(face)]
            key = (a, b) if a < b else (b, a)
            use[key] = use.get(key, 0) + 1
    return use


def boundary_edges(faces):
    """Edges used by exactly one face, sorted."""
    return sorted(edge for edge, count in edge_use(faces).items() if count == 1)


def closed_problems(faces):
    """Problems that keep a mesh from being a closed, consistently oriented 2-manifold.

    Codes: open_edge (used once), non_manifold_edge (used three or more times), orientation_flipped (a directed
    edge used twice in the same direction), duplicate_face."""
    found = []
    for edge, count in sorted(edge_use(faces).items()):
        if count == 1:
            found.append(("open_edge", edge))
        elif count > 2:
            found.append(("non_manifold_edge", edge))
    directed = {}
    for face in faces:
        for position in range(len(face)):
            key = (face[position], face[(position + 1) % len(face)])
            directed[key] = directed.get(key, 0) + 1
    for key, count in sorted(directed.items()):
        if count > 1:
            found.append(("orientation_flipped", key))
    seen = set()
    for face in faces:
        key = tuple(sorted(face))
        if key in seen:
            found.append(("duplicate_face", key))
        seen.add(key)
    return found


def is_closed_manifold(faces):
    return not closed_problems(faces)


def euler_characteristic(vertices, faces):
    """V - E + F over the vertices that faces use (2 for a closed mesh of genus 0)."""
    used = {index for face in faces for index in face}
    return len(used) - len(edge_use(faces)) + len(faces)


def bounds(vertices):
    """[[min x, min y, min z], [max x, max y, max z]] of the vertices."""
    if not vertices:
        raise ValueError("an empty vertex list has no bounds")
    return [[min(vertex[axis] for vertex in vertices) for axis in range(3)],
            [max(vertex[axis] for vertex in vertices) for axis in range(3)]]


def signed_volume(vertices, faces):
    """Volume enclosed by a closed mesh in cubic metres (positive when normals point outward)."""
    total = 0.0
    for face in faces:
        x0, y0, z0 = vertices[face[0]]
        for position in range(1, len(face) - 1):
            x1, y1, z1 = vertices[face[position]]
            x2, y2, z2 = vertices[face[position + 1]]
            total += (x0 * (y1 * z2 - z1 * y2) - y0 * (x1 * z2 - z1 * x2) + z0 * (x1 * y2 - y1 * x2))
    return total / 6.0


def surface_area(vertices, faces):
    return sum(face_area(vertices, face) for face in faces)


def triangle_count(faces):
    """Triangles after fan triangulation of every face."""
    return sum(len(face) - 2 for face in faces)


def unused_vertices(vertices, faces):
    used = {index for face in faces for index in face}
    return [index for index in range(len(vertices)) if index not in used]


def uv_problems(faces, uv):
    """Per-corner UV problems: a wrong corner count or a non-finite coordinate."""
    corners = sum(len(face) for face in faces)
    if len(uv) != corners:
        return [("uv_corner_count", (len(uv), corners))]
    return [("uv_invalid", index) for index, value in enumerate(uv)
            if len(value) != 2 or not all(isinstance(c, (int, float)) and math.isfinite(c) for c in value)]


__all__ = ["face_normal", "face_area", "problems", "edge_use", "boundary_edges", "closed_problems",
           "is_closed_manifold", "euler_characteristic", "bounds", "signed_volume", "surface_area",
           "triangle_count", "unused_vertices", "uv_problems"]
