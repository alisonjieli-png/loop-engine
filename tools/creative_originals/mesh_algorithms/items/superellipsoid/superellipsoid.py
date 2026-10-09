"""Superellipsoid (Barr superquadric): boxes, cylinders, ellipsoids and pinched stars from two exponents.

Command line: python3 superellipsoid.py --output superellipsoid.gltf --east-west 0.3 --north-south 0.6
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "size_x", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Semi-axis along X."},
    {"name": "size_y", "type": "float", "default": 0.8, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Semi-axis along Y (up)."},
    {"name": "size_z", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Semi-axis along Z."},
    {"name": "north_south", "type": "float", "default": 0.6, "unit": "exponent", "minimum": 0.01, "maximum": 4.0,
     "meaning": "Exponent e1 of the latitude profile: below 1 squarer, 1 round, above 1 pinched."},
    {"name": "east_west", "type": "float", "default": 0.3, "unit": "exponent", "minimum": 0.01, "maximum": 4.0,
     "meaning": "Exponent e2 of the horizontal cross-section: below 1 squarer, 1 round, 2 diamond."},
    {"name": "segments", "type": "int", "default": 48, "unit": "count", "minimum": 3, "maximum": 4096,
     "meaning": "Divisions around the Y axis."},
    {"name": "rings", "type": "int", "default": 24, "unit": "count", "minimum": 2, "maximum": 4096,
     "meaning": "Divisions from pole to pole."},
]


def _power(value, exponent):
    return math.copysign(abs(value) ** exponent, value) if value != 0.0 else 0.0


def superellipsoid_point(polar, azimuth, size_x=1.0, size_y=0.8, size_z=1.0, north_south=0.6, east_west=0.3):
    """Surface point at polar angle ``polar`` from +Y and azimuth from +X toward -Z (signed powers of cos, sin)."""
    across = _power(math.sin(polar), north_south)
    return (size_x * across * _power(math.cos(azimuth), east_west), size_y * _power(math.cos(polar), north_south),
            -size_z * across * _power(math.sin(azimuth), east_west))


def superellipsoid(size_x=1.0, size_y=0.8, size_z=1.0, north_south=0.6, east_west=0.3, segments=48, rings=24):
    """A welded superellipsoid: 2 + (rings - 1) * segments vertices, segments * rings faces, outward winding.

    Polar and azimuth angles are sampled evenly; poles are single vertices with triangle fans. With both
    exponents 1 it is an ellipsoid with the same vertices as a UV sphere scaled per axis. Normals are angle
    weighted from the faces."""
    if min(size_x, size_y, size_z, north_south, east_west) <= 0 or segments < 3 or rings < 2:
        raise meshkit.MeshError("parameter_invalid", "sizes and exponents > 0, segments >= 3, rings >= 2")
    vertices = [(0.0, size_y, 0.0)]
    for r in range(1, rings):
        polar = math.pi * r / rings
        for s in range(segments):
            vertices.append(superellipsoid_point(polar, 2.0 * math.pi * s / segments, size_x, size_y, size_z,
                                                 north_south, east_west))
    vertices.append((0.0, -size_y, 0.0))
    south = len(vertices) - 1

    def ring(r, s):
        return 1 + (r - 1) * segments + s % segments

    faces = [(0, ring(1, s), ring(1, s + 1)) for s in range(segments)]
    for r in range(1, rings - 1):
        faces += [(ring(r, s), ring(r + 1, s), ring(r + 1, s + 1), ring(r, s + 1)) for s in range(segments)]
    faces += [(ring(rings - 1, s), south, ring(rings - 1, s + 1)) for s in range(segments)]
    mesh = meshkit.Mesh(vertices, faces, name="superellipsoid",
                        material=meshkit.material("superellipsoid", (0.74, 0.62, 0.86, 1.0)))
    mesh.normals = meshkit.vertex_normals(mesh)
    return mesh


def superellipsoid_volume(size_x=1.0, size_y=0.8, size_z=1.0, north_south=0.6, east_west=0.3):
    """Exact volume of the smooth surface: 2 a b c e1 e2 B(e1 / 2 + 1, e1) B(e2 / 2, e2 / 2), B the beta function."""
    def beta(x, y):
        return math.exp(math.lgamma(x) + math.lgamma(y) - math.lgamma(x + y))

    e1, e2 = north_south, east_west
    return 2.0 * size_x * size_y * size_z * e1 * e2 * beta(e1 / 2.0 + 1.0, e1) * beta(e2 / 2.0, e2 / 2.0)


def main(argv=None):
    """Command line: write the superellipsoid as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=superellipsoid)


if __name__ == "__main__":
    raise SystemExit(main())
