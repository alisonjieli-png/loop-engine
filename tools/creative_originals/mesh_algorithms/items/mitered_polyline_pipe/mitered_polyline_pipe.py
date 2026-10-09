"""Mitered pipe: a constant polygon cross-section along a polyline, joined at corners by miter planes so every
wall stays flat and no wedge is lost or doubled.

Command line: python3 mitered_polyline_pipe.py --output pipe.gltf --radius 0.12 --sides 12 --route plumbing
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "radius", "type": "float", "default": 0.12, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Circumradius of the regular polygon cross-section."},
    {"name": "sides", "type": "int", "default": 12, "unit": "count", "minimum": 3, "maximum": 1024,
     "meaning": "Sides of the cross-section polygon."},
    {"name": "route", "type": "str", "default": "plumbing", "unit": "name", "choices": ["plumbing", "zigzag", "frame"],
     "meaning": "Demonstration polyline (frame is closed)."},
]


def _rotate(vector, axis, angle):
    c, s = math.cos(angle), math.sin(angle)
    return meshkit.vadd(meshkit.vadd(meshkit.vscale(vector, c), meshkit.vscale(meshkit.vcross(axis, vector), s)),
                        meshkit.vscale(axis, meshkit.vdot(axis, vector) * (1.0 - c)))


def mitered_pipe(points, radius=0.12, sides=12, closed=False):
    """A pipe with one ring per polyline point: end rings are perpendicular to their segment; every inner ring
    lies in the bisecting (miter) plane of its two segments, found by projecting the cross-section along the
    segment direction. The volume equals cross-section area times centre-line length for corners that do not
    fold back. Open pipes get flat caps; faces point outward."""
    pts = [tuple(float(c) for c in p) for p in points]
    count = len(pts)
    if count < 2 or sides < 3 or radius <= 0:
        raise meshkit.MeshError("parameter_invalid", "two points, three sides, radius > 0")
    segment_count = count if closed else count - 1
    directions = [meshkit.vnormalize(meshkit.vsub(pts[(k + 1) % count], pts[k])) for k in range(segment_count)]
    first = directions[0]
    helper = (0.0, 1.0, 0.0) if abs(first[1]) < 0.9 else (1.0, 0.0, 0.0)
    normals = [meshkit.vnormalize(meshkit.vcross(meshkit.vcross(first, helper), first))]
    for k in range(1, segment_count):
        axis = meshkit.vcross(directions[k - 1], directions[k])
        size = meshkit.vlength(axis)
        normal = normals[-1]
        if size > 1e-15:
            normal = _rotate(normal, meshkit.vscale(axis, 1.0 / size), math.atan2(size, meshkit.vdot(directions[k - 1], directions[k])))
        normals.append(meshkit.vnormalize(meshkit.vsub(normal, meshkit.vscale(directions[k], meshkit.vdot(normal, directions[k])))))
    vertices = []
    for k in range(count):
        if closed:
            before, after = (k - 1) % segment_count, k % segment_count
        else:
            before, after = max(k - 1, 0), min(k, segment_count - 1)
        travel, frame_normal = directions[after], normals[after]
        binormal = meshkit.vcross(travel, frame_normal)
        plane = meshkit.vnormalize(meshkit.vadd(directions[before], directions[after]), travel)
        for j in range(sides):
            angle = 2.0 * math.pi * j / sides
            offset = meshkit.vadd(meshkit.vscale(frame_normal, radius * math.cos(angle)),
                                  meshkit.vscale(binormal, radius * math.sin(angle)))
            shift = -meshkit.vdot(offset, plane) / meshkit.vdot(travel, plane)
            vertices.append(meshkit.vadd(pts[k], meshkit.vadd(offset, meshkit.vscale(travel, shift))))
    faces = []
    for k in range(segment_count):
        nk = (k + 1) % count
        for j in range(sides):
            nj = (j + 1) % sides
            faces.append((k * sides + j, k * sides + nj, nk * sides + nj, nk * sides + j))
    if not closed:
        faces.append(tuple(range(sides - 1, -1, -1)))
        faces.append(tuple((count - 1) * sides + j for j in range(sides)))
    return meshkit.Mesh(vertices, faces, name="mitered_pipe")


def demo_route(name="plumbing"):
    """Demonstration polylines: a plumbing run with right angles, a zigzag, or a closed rectangular frame."""
    if name == "plumbing":
        return [(-1.5, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 1.0, -1.0), (1.2, 1.0, -1.0), (1.2, 0.2, -1.0)]
    if name == "zigzag":
        return [(-2.0 + 0.5 * k, 0.4 * (k % 2), 0.0) for k in range(9)]
    if name == "frame":
        return [(-1.0, 0.0, -0.6), (1.0, 0.0, -0.6), (1.0, 0.0, 0.6), (-1.0, 0.0, 0.6)]
    raise meshkit.MeshError("route_unknown", str(name))


def build(radius=0.12, sides=12, route="plumbing"):
    """The flat-shaded demonstration pipe."""
    mesh = meshkit.flat_shaded(mitered_pipe(demo_route(route), radius, sides, closed=(route == "frame")))
    mesh.material = meshkit.material("pipe", (0.80, 0.52, 0.32, 1.0), metallic=0.6, roughness=0.35)
    return mesh


def main(argv=None):
    """Command line: write the pipe (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
