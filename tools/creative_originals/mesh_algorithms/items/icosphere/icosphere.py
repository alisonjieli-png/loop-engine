"""Icosphere: a regular icosahedron subdivided into four triangles per face and projected onto a sphere.

Command line: python3 icosphere.py --output icosphere.gltf --radius 1 --subdivisions 3
"""
from __future__ import annotations

import itertools
import math

import meshkit

PARAMETERS = [
    {"name": "radius", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Distance from the centre to every vertex."},
    {"name": "subdivisions", "type": "int", "default": 3, "unit": "count", "minimum": 0, "maximum": 7,
     "meaning": "Times each triangle is split into four; 10 * 4^n + 2 vertices."},
]


def icosahedron(radius=1.0):
    """The regular icosahedron inscribed in a sphere of ``radius``: 12 vertices and 20 outward triangles.

    Vertices are the corners of three golden rectangles; faces are found as the triples of vertices that are
    pairwise one edge length apart, then wound outward."""
    golden = (1.0 + math.sqrt(5.0)) / 2.0
    raw = []
    for a in (-1.0, 1.0):
        for b in (-golden, golden):
            raw += [(0.0, a, b), (a, b, 0.0), (b, 0.0, a)]
    scale = radius / math.sqrt(1.0 + golden * golden)
    vertices = [meshkit.vscale(p, scale) for p in raw]
    edge = 2.0 * scale
    faces = []
    for a, b, c in itertools.combinations(range(12), 3):
        if all(abs(meshkit.vdistance(vertices[i], vertices[j]) - edge) < 1e-9 * edge for i, j in ((a, b), (b, c), (a, c))):
            normal = meshkit.vcross(meshkit.vsub(vertices[b], vertices[a]), meshkit.vsub(vertices[c], vertices[a]))
            faces.append((a, b, c) if meshkit.vdot(normal, vertices[a]) > 0 else (a, c, b))
    return meshkit.Mesh(vertices, faces, name="icosahedron")


def icosphere(radius=1.0, subdivisions=3):
    """An icosphere with 10 * 4^n + 2 vertices and 20 * 4^n triangles, every vertex on the sphere.

    Each step splits every triangle into four through its edge midpoints (shared between neighbours) and
    pushes the new vertices out to the sphere. Normals are the unit position vectors."""
    if not radius > 0 or subdivisions < 0:
        raise meshkit.MeshError("parameter_invalid", "radius > 0 and subdivisions >= 0")
    mesh = icosahedron(1.0)
    vertices, faces = list(mesh.vertices), list(mesh.faces)
    for _ in range(int(subdivisions)):
        middle = {}

        def midpoint(a, b):
            key = (a, b) if a < b else (b, a)
            if key not in middle:
                middle[key] = len(vertices)
                vertices.append(meshkit.vnormalize(meshkit.vlerp(vertices[a], vertices[b], 0.5)))
            return middle[key]

        split = []
        for a, b, c in faces:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            split += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = split
    normals = [meshkit.vnormalize(v) for v in vertices]
    return meshkit.Mesh([meshkit.vscale(n, radius) for n in normals], faces, normals=normals, name="icosphere",
                        material=meshkit.material("icosphere", (0.70, 0.80, 0.66, 1.0)))


def main(argv=None):
    """Command line: write the icosphere as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=icosphere)


if __name__ == "__main__":
    raise SystemExit(main())
