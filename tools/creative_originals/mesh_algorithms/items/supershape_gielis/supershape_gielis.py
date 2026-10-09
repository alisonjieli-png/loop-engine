"""3D supershape: the spherical product of two Gielis superformula curves (flowers, stars, shells, crystals).

Command line: python3 supershape_gielis.py --output supershape.gltf --m1 7 --n1 0.2 --n2 1.7 --n3 1.7
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "m1", "type": "float", "default": 7.0, "unit": "symmetry", "minimum": 0.0, "maximum": 100.0,
     "meaning": "Rotational symmetry of the horizontal curve (lobes around Y)."},
    {"name": "n1", "type": "float", "default": 0.2, "unit": "exponent", "minimum": 0.01, "maximum": 100.0,
     "meaning": "Overall exponent of the horizontal curve."},
    {"name": "n2", "type": "float", "default": 1.7, "unit": "exponent", "minimum": 0.0, "maximum": 100.0,
     "meaning": "Cosine term exponent of the horizontal curve."},
    {"name": "n3", "type": "float", "default": 1.7, "unit": "exponent", "minimum": 0.0, "maximum": 100.0,
     "meaning": "Sine term exponent of the horizontal curve."},
    {"name": "m2", "type": "float", "default": 7.0, "unit": "symmetry", "minimum": 0.0, "maximum": 100.0,
     "meaning": "Symmetry of the vertical (latitude) curve."},
    {"name": "p1", "type": "float", "default": 0.2, "unit": "exponent", "minimum": 0.01, "maximum": 100.0,
     "meaning": "Overall exponent of the vertical curve."},
    {"name": "p2", "type": "float", "default": 1.7, "unit": "exponent", "minimum": 0.0, "maximum": 100.0,
     "meaning": "Cosine term exponent of the vertical curve."},
    {"name": "p3", "type": "float", "default": 1.7, "unit": "exponent", "minimum": 0.0, "maximum": 100.0,
     "meaning": "Sine term exponent of the vertical curve."},
    {"name": "size", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Uniform scale of the result."},
    {"name": "segments", "type": "int", "default": 64, "unit": "count", "minimum": 3, "maximum": 4096,
     "meaning": "Divisions around the Y axis."},
    {"name": "rings", "type": "int", "default": 32, "unit": "count", "minimum": 2, "maximum": 4096,
     "meaning": "Divisions from pole to pole."},
]


def superformula(angle, m=7.0, n1=0.2, n2=1.7, n3=1.7, a=1.0, b=1.0):
    """Gielis superformula radius r(angle) = (|cos(m angle / 4) / a|^n2 + |sin(m angle / 4) / b|^n3)^(-1 / n1)."""
    total = abs(math.cos(m * angle / 4.0) / a) ** n2 + abs(math.sin(m * angle / 4.0) / b) ** n3
    if total <= 0.0:
        raise meshkit.MeshError("superformula_undefined", "the radius is unbounded at this angle")
    return total ** (-1.0 / n1)


def supershape(m1=7.0, n1=0.2, n2=1.7, n3=1.7, m2=7.0, p1=0.2, p2=1.7, p3=1.7, size=1.0, segments=64, rings=32):
    """A welded 3D supershape: 2 + (rings - 1) * segments vertices and segments * rings outward faces.

    Point = size * (r1(t) cos t * r2(p) cos p, r2(p) sin p, -r1(t) sin t * r2(p) cos p) for longitude t and
    latitude p sampled evenly; the poles are single vertices with triangle fans. With m1 = m2 = 0 (and n2 = p2)
    the shape is a sphere of radius size. Normals are angle weighted."""
    if not size > 0 or segments < 3 or rings < 2:
        raise meshkit.MeshError("parameter_invalid", "size > 0, segments >= 3, rings >= 2")

    def point(latitude, longitude):
        r2 = superformula(latitude, m2, p1, p2, p3)
        r1 = superformula(longitude, m1, n1, n2, n3)
        return (size * r1 * math.cos(longitude) * r2 * math.cos(latitude), size * r2 * math.sin(latitude),
                -size * r1 * math.sin(longitude) * r2 * math.cos(latitude))

    top = point(0.5 * math.pi, 0.0)
    vertices = [(0.0, top[1], 0.0)]
    for r in range(1, rings):
        latitude = 0.5 * math.pi - math.pi * r / rings
        for s in range(segments):
            vertices.append(point(latitude, -math.pi + 2.0 * math.pi * s / segments))
    bottom = point(-0.5 * math.pi, 0.0)
    vertices.append((0.0, bottom[1], 0.0))
    south = len(vertices) - 1

    def ring(r, s):
        return 1 + (r - 1) * segments + s % segments

    faces = [(0, ring(1, s), ring(1, s + 1)) for s in range(segments)]
    for r in range(1, rings - 1):
        faces += [(ring(r, s), ring(r + 1, s), ring(r + 1, s + 1), ring(r, s + 1)) for s in range(segments)]
    faces += [(ring(rings - 1, s), south, ring(rings - 1, s + 1)) for s in range(segments)]
    mesh = meshkit.Mesh(vertices, faces, name="supershape",
                        material=meshkit.material("supershape", (0.90, 0.58, 0.66, 1.0)))
    mesh.normals = meshkit.vertex_normals(mesh)
    return mesh


def main(argv=None):
    """Command line: write the supershape as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=supershape)


if __name__ == "__main__":
    raise SystemExit(main())
