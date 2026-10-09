"""Torus knot tube: the (p, q) torus knot swept by a circle with parallel-transport frames closed by an even twist.

Command line: python3 torus_knot.py --output knot.gltf --p 2 --q 3 --tube-radius 0.1 --segments 180 --sides 12
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "p", "type": "int", "default": 2, "unit": "count", "minimum": 1, "maximum": 64,
     "meaning": "Turns around the Y axis (the torus' axis of symmetry)."},
    {"name": "q", "type": "int", "default": 3, "unit": "count", "minimum": 1, "maximum": 64,
     "meaning": "Turns around the torus tube; p and q without a common factor give a knot."},
    {"name": "major_radius", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius of the torus the curve winds on."},
    {"name": "minor_radius", "type": "float", "default": 0.4, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Tube radius of that torus (how far the curve swings)."},
    {"name": "tube_radius", "type": "float", "default": 0.1, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius of the swept circle; keep it below half the closest approach of the strands."},
    {"name": "segments", "type": "int", "default": 180, "unit": "count", "minimum": 8, "maximum": 100000,
     "meaning": "Samples along the curve."},
    {"name": "sides", "type": "int", "default": 12, "unit": "count", "minimum": 3, "maximum": 1024,
     "meaning": "Divisions around the tube."},
]


def knot_point(t, p=2, q=3, major_radius=1.0, minor_radius=0.4):
    """Curve point at parameter t in [0, 2 pi): ((R + r cos qt) cos pt, r sin qt, -(R + r cos qt) sin pt)."""
    ring = major_radius + minor_radius * math.cos(q * t)
    return (ring * math.cos(p * t), minor_radius * math.sin(q * t), -ring * math.sin(p * t))


def knot_tangent(t, p=2, q=3, major_radius=1.0, minor_radius=0.4):
    """Unit tangent of the curve from its analytic derivative."""
    ring = major_radius + minor_radius * math.cos(q * t)
    dring = -minor_radius * q * math.sin(q * t)
    return meshkit.vnormalize((dring * math.cos(p * t) - ring * p * math.sin(p * t), minor_radius * q * math.cos(q * t),
                               -dring * math.sin(p * t) - ring * p * math.cos(p * t)))


def _rotate(vector, axis, angle):
    c, s = math.cos(angle), math.sin(angle)
    return meshkit.vadd(meshkit.vadd(meshkit.vscale(vector, c), meshkit.vscale(meshkit.vcross(axis, vector), s)),
                        meshkit.vscale(axis, meshkit.vdot(axis, vector) * (1.0 - c)))


def transport_frames(tangents):
    """Normals carried around a closed curve by rotating each one with the turn between consecutive tangents,
    then corrected by an even twist so the last normal meets the first."""
    count = len(tangents)
    first = tangents[0]
    helper = (0.0, 1.0, 0.0) if abs(first[1]) < 0.9 else (1.0, 0.0, 0.0)
    normals = [meshkit.vnormalize(meshkit.vcross(meshkit.vcross(first, helper), first))]
    for k in range(1, count + 1):
        a, b = tangents[k - 1], tangents[k % count]
        axis = meshkit.vcross(a, b)
        size = meshkit.vlength(axis)
        normal = normals[-1]
        if size > 1e-15:
            normal = _rotate(normal, meshkit.vscale(axis, 1.0 / size), math.atan2(size, meshkit.vdot(a, b)))
        normal = meshkit.vnormalize(meshkit.vsub(normal, meshkit.vscale(b, meshkit.vdot(normal, b))))
        normals.append(normal)
    closing = normals.pop()
    binormal = meshkit.vcross(first, normals[0])
    gap = math.atan2(meshkit.vdot(closing, binormal), meshkit.vdot(closing, normals[0]))
    return [_rotate(normals[k], tangents[k], -gap * k / count) for k in range(count)]


def torus_knot(p=2, q=3, major_radius=1.0, minor_radius=0.4, tube_radius=0.1, segments=180, sides=12):
    """A closed tube along the (p, q) torus knot: segments * sides vertices and quads, torus topology.

    The frame is carried along the curve by parallel transport and the leftover angle at the end is spread
    evenly, so the tube closes without a twist seam. Normals point from the curve to each vertex."""
    if min(p, q) < 1 or segments < 8 or sides < 3 or min(major_radius, minor_radius, tube_radius) <= 0:
        raise meshkit.MeshError("parameter_invalid", "p, q >= 1; segments >= 8; sides >= 3; radii > 0")
    params = [2.0 * math.pi * k / segments for k in range(segments)]
    centers = [knot_point(t, p, q, major_radius, minor_radius) for t in params]
    tangents = [knot_tangent(t, p, q, major_radius, minor_radius) for t in params]
    normals_along = transport_frames(tangents)
    vertices, normals = [], []
    for center, tangent, normal in zip(centers, tangents, normals_along):
        binormal = meshkit.vcross(tangent, normal)
        for j in range(sides):
            angle = 2.0 * math.pi * j / sides
            direction = meshkit.vadd(meshkit.vscale(normal, math.cos(angle)), meshkit.vscale(binormal, math.sin(angle)))
            vertices.append(meshkit.vadd(center, meshkit.vscale(direction, tube_radius)))
            normals.append(direction)
    faces = []
    for i in range(segments):
        ni = (i + 1) % segments
        for j in range(sides):
            nj = (j + 1) % sides
            faces.append((i * sides + j, i * sides + nj, ni * sides + nj, ni * sides + j))
    return meshkit.Mesh(vertices, faces, normals=normals, name="torus_knot",
                        material=meshkit.material("torus_knot", (0.88, 0.66, 0.30, 1.0), metallic=0.3, roughness=0.4))


def main(argv=None):
    """Command line: write the knot tube as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=torus_knot)


if __name__ == "__main__":
    raise SystemExit(main())
