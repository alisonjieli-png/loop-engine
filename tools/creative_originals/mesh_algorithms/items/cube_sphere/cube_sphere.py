"""Cube sphere: the six faces of a subdivided cube mapped onto a sphere, welded into one quad mesh.

Command line: python3 cube_sphere.py --output cube_sphere.gltf --radius 1 --divisions 12 --mapping equal_area
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "radius", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Distance from the centre to every vertex."},
    {"name": "divisions", "type": "int", "default": 12, "unit": "count", "minimum": 1, "maximum": 512,
     "meaning": "Quads along each cube edge; 6 * divisions^2 quads in total."},
    {"name": "mapping", "type": "str", "default": "equal_area", "unit": "name", "choices": ["equal_area", "normalized"],
     "meaning": "Cube to sphere mapping: the polynomial mapping with more even cells, or plain normalization."},
]


def cube_to_sphere(point, mapping="equal_area"):
    """Map a point on the surface of the cube [-1, 1]^3 to the unit sphere.

    'normalized' divides by the length. 'equal_area' uses x * sqrt(1 - y^2/2 - z^2/2 + y^2 z^2 / 3) and its
    cyclic versions, which lands exactly on the sphere and keeps cell areas closer together."""
    x, y, z = point
    if mapping == "normalized":
        return meshkit.vnormalize((x, y, z))
    if mapping != "equal_area":
        raise meshkit.MeshError("mapping_unknown", str(mapping))
    xx, yy, zz = x * x, y * y, z * z
    return (x * math.sqrt(max(0.0, 1.0 - yy / 2.0 - zz / 2.0 + yy * zz / 3.0)),
            y * math.sqrt(max(0.0, 1.0 - zz / 2.0 - xx / 2.0 + zz * xx / 3.0)),
            z * math.sqrt(max(0.0, 1.0 - xx / 2.0 - yy / 2.0 + xx * yy / 3.0)))


def cube_sphere(radius=1.0, divisions=12, mapping="equal_area"):
    """A welded cube sphere: 6 n^2 + 2 vertices and 6 n^2 outward quads (n = divisions), unit normals.

    Vertices are the integer lattice points on the surface of an n x n x n cube, shared along cube edges and
    corners, then mapped to the sphere."""
    n = int(divisions)
    if not radius > 0 or n < 1:
        raise meshkit.MeshError("parameter_invalid", "radius > 0 and divisions >= 1")
    index, vertices = {}, []

    def vertex(i, j, k):
        key = (i, j, k)
        if key not in index:
            index[key] = len(vertices)
            vertices.append(cube_to_sphere((2.0 * i / n - 1.0, 2.0 * j / n - 1.0, 2.0 * k / n - 1.0), mapping))
        return index[key]

    faces = []
    for axis in range(3):
        u_axis, v_axis = (axis + 1) % 3, (axis + 2) % 3
        for side in (0, n):
            for a in range(n):
                for b in range(n):
                    corners = []
                    for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        key = [0, 0, 0]
                        key[axis], key[u_axis], key[v_axis] = side, a + du, b + dv
                        corners.append(vertex(*key))
                    faces.append(tuple(corners) if side == n else tuple(reversed(corners)))
    normals = [meshkit.vnormalize(v) for v in vertices]
    return meshkit.Mesh([meshkit.vscale(p, radius) for p in normals], faces, normals=normals, name="cube_sphere",
                        material=meshkit.material("cube_sphere", (0.86, 0.78, 0.55, 1.0)))


def face_area_ratio(mesh):
    """Largest face area divided by the smallest: 1 for perfectly even cells."""
    areas = [meshkit.surface_area(meshkit.Mesh(mesh.vertices, [face])) for face in mesh.faces]
    return max(areas) / min(areas)


def main(argv=None):
    """Command line: write the cube sphere as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=cube_sphere)


if __name__ == "__main__":
    raise SystemExit(main())
