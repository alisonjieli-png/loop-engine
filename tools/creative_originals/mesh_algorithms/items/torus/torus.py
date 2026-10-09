"""Torus: a ring tube around the Y axis with normals and a texture grid that wraps in both directions.

Command line: python3 torus.py --output torus.gltf --major-radius 1 --minor-radius 0.35 --segments 48 --sides 24
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "major_radius", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Distance from the Y axis to the centre of the tube."},
    {"name": "minor_radius", "type": "float", "default": 0.35, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius of the tube; below major_radius for a ring torus."},
    {"name": "segments", "type": "int", "default": 48, "unit": "count", "minimum": 3, "maximum": 4096,
     "meaning": "Divisions around the Y axis."},
    {"name": "sides", "type": "int", "default": 24, "unit": "count", "minimum": 3, "maximum": 4096,
     "meaning": "Divisions around the tube."},
]


def torus(major_radius=1.0, minor_radius=0.35, segments=48, sides=24):
    """A torus centred at the origin around +Y with unit normals, UVs and outward quads.

    The grid has (segments + 1) x (sides + 1) vertices: the last column and row repeat the first so u and v
    each run from 0 to 1, which makes the mesh closed only after welding. u follows the ring from +X toward
    -Z, v goes around the tube starting at the outer equator and rising first."""
    if not (major_radius > 0 and minor_radius > 0) or segments < 3 or sides < 3:
        raise meshkit.MeshError("parameter_invalid", "radii > 0, segments >= 3, sides >= 3")
    vertices, normals, uvs = [], [], []
    for j in range(sides + 1):
        theta = 2.0 * math.pi * (j % sides) / sides
        for i in range(segments + 1):
            phi = 2.0 * math.pi * (i % segments) / segments
            ring = major_radius + minor_radius * math.cos(theta)
            vertices.append((ring * math.cos(phi), minor_radius * math.sin(theta), -ring * math.sin(phi)))
            normals.append((math.cos(theta) * math.cos(phi), math.sin(theta), -math.cos(theta) * math.sin(phi)))
            uvs.append((i / segments, j / sides))
    columns = segments + 1
    faces = []
    for j in range(sides):
        for i in range(segments):
            a, b = j * columns + i, j * columns + i + 1
            faces.append((a, b, b + columns, a + columns))
    return meshkit.Mesh(vertices, faces, normals=normals, uvs=uvs, name="torus",
                        material=meshkit.material("torus", (0.84, 0.56, 0.48, 1.0)))


def main(argv=None):
    """Command line: write the torus as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=torus)


if __name__ == "__main__":
    raise SystemExit(main())
