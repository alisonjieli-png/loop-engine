"""UV sphere: rings of latitude and segments of longitude, with a texture seam and one pole vertex per segment.

Command line: python3 uv_sphere.py --output sphere.gltf --radius 1 --segments 32 --rings 16
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "radius", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Distance from the centre to every vertex."},
    {"name": "segments", "type": "int", "default": 32, "unit": "count", "minimum": 3, "maximum": 2048,
     "meaning": "Divisions around the Y axis (longitude)."},
    {"name": "rings", "type": "int", "default": 16, "unit": "count", "minimum": 2, "maximum": 2048,
     "meaning": "Divisions from the north pole to the south pole (latitude)."},
]


def uv_sphere(radius=1.0, segments=32, rings=16):
    """A UV sphere centred at the origin with unit normals, texture coordinates and outward faces.

    Row r of the grid sits at polar angle pi * r / rings from +Y; column s at longitude 2 pi s / segments,
    measured from +X toward -Z so u grows to the right seen from outside. The seam column repeats column 0
    with u = 1 and each pole keeps one vertex per segment (u at the segment centre), so the texture has no
    stretched pole fan. Vertices: 2 * segments + (rings - 1) * (segments + 1). Triangles: 2 * segments * (rings - 1).
    """
    if not radius > 0 or segments < 3 or rings < 2:
        raise meshkit.MeshError("parameter_invalid", "radius > 0, segments >= 3 and rings >= 2")
    vertices, normals, uvs, faces = [], [], [], []
    for s in range(segments):
        vertices.append((0.0, radius, 0.0))
        normals.append((0.0, 1.0, 0.0))
        uvs.append(((s + 0.5) / segments, 0.0))
    first = len(vertices)
    for r in range(1, rings):
        theta = math.pi * r / rings
        sin_theta, cos_theta = math.sin(theta), math.cos(theta)
        for s in range(segments + 1):
            phi = 2.0 * math.pi * (s % segments) / segments
            normal = (sin_theta * math.cos(phi), cos_theta, -sin_theta * math.sin(phi))
            vertices.append((radius * normal[0], radius * normal[1], radius * normal[2]))
            normals.append(normal)
            uvs.append((s / segments, r / rings))
    south = len(vertices)
    for s in range(segments):
        vertices.append((0.0, -radius, 0.0))
        normals.append((0.0, -1.0, 0.0))
        uvs.append(((s + 0.5) / segments, 1.0))
    columns = segments + 1

    def ring(r, s):
        return first + (r - 1) * columns + s

    for s in range(segments):
        faces.append((s, ring(1, s), ring(1, s + 1)))
    for r in range(1, rings - 1):
        for s in range(segments):
            faces.append((ring(r, s), ring(r + 1, s), ring(r + 1, s + 1), ring(r, s + 1)))
    for s in range(segments):
        faces.append((ring(rings - 1, s), south + s, ring(rings - 1, s + 1)))
    return meshkit.Mesh(vertices, faces, normals=normals, uvs=uvs, name="uv_sphere",
                        material=meshkit.material("uv_sphere", (0.62, 0.72, 0.86, 1.0)))


def main(argv=None):
    """Command line: write the sphere as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=uv_sphere)


if __name__ == "__main__":
    raise SystemExit(main())
