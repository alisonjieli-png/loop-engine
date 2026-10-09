"""Rounded box: a box with every edge and corner rounded to one radius, as one welded quad mesh.

Command line: python3 rounded_box.py --output rounded_box.gltf --size-x 2 --size-y 1 --size-z 1.4 --radius 0.25
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "size_x", "type": "float", "default": 2.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Overall size along X."},
    {"name": "size_y", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Overall size along Y."},
    {"name": "size_z", "type": "float", "default": 1.4, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Overall size along Z."},
    {"name": "radius", "type": "float", "default": 0.25, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Rounding radius; at most half the smallest size."},
    {"name": "bevel_segments", "type": "int", "default": 6, "unit": "count", "minimum": 1, "maximum": 256,
     "meaning": "Divisions across each rounded edge (a quarter circle)."},
    {"name": "flat_segments", "type": "int", "default": 2, "unit": "count", "minimum": 1, "maximum": 1024,
     "meaning": "Divisions across each flat face strip."},
]


def _axis(half, radius, bevel, flat):
    inner = half - radius
    values = [-inner - radius * math.cos(0.5 * math.pi * k / bevel) for k in range(bevel)]
    values += [-inner + 2.0 * inner * k / flat for k in range(flat + 1)] if inner > 0 else [0.0]
    values += [inner + radius * math.sin(0.5 * math.pi * k / bevel) for k in range(1, bevel + 1)]
    return values


def rounded_box_volume(size_x=2.0, size_y=1.0, size_z=1.4, radius=0.25):
    """Exact volume of the smooth rounded box: inner box, six slabs, twelve quarter cylinders, one sphere."""
    a, b, c = size_x - 2 * radius, size_y - 2 * radius, size_z - 2 * radius
    return (a * b * c + 2 * radius * (a * b + b * c + a * c) + math.pi * radius * radius * (a + b + c)
            + 4.0 / 3.0 * math.pi * radius ** 3)


def rounded_box(size_x=2.0, size_y=1.0, size_z=1.4, radius=0.25, bevel_segments=6, flat_segments=2):
    """A closed rounded box centred at the origin with unit normals.

    A lattice is laid on the box surface with extra lines across each rounded band; every lattice point is
    pulled onto the surface as nearest(inner box) + radius * direction, where the inner box is shrunk by the
    radius. Vertex count = nx ny nz - (nx - 2)(ny - 2)(nz - 2) for the per-axis line counts."""
    half = (size_x / 2.0, size_y / 2.0, size_z / 2.0)
    if radius < 0 or radius > min(half) or bevel_segments < 1 or flat_segments < 1:
        raise meshkit.MeshError("parameter_invalid", "0 <= radius <= half the smallest size")
    if radius == 0:
        axes = [[-h + 2.0 * h * k / flat_segments for k in range(flat_segments + 1)] for h in half]
    else:
        axes = [_axis(h, radius, bevel_segments, flat_segments) for h in half]
    counts = [len(values) for values in axes]
    index, vertices, normals = {}, [], []

    def vertex(key):
        if key not in index:
            point = tuple(axes[k][key[k]] for k in range(3))
            inner = tuple(max(-(half[k] - radius), min(half[k] - radius, point[k])) for k in range(3))
            outward = meshkit.vsub(point, inner)
            on_face = tuple(1.0 if key[k] == counts[k] - 1 else -1.0 if key[k] == 0 else 0.0 for k in range(3))
            direction = meshkit.vnormalize(outward, meshkit.vnormalize(on_face))
            index[key] = len(vertices)
            vertices.append(meshkit.vadd(inner, meshkit.vscale(direction, radius)) if radius > 0 else point)
            normals.append(direction if radius > 0 else meshkit.vnormalize(on_face))
        return index[key]

    faces = []
    for axis in range(3):
        u, v = (axis + 1) % 3, (axis + 2) % 3
        for side in (0, counts[axis] - 1):
            for a in range(counts[u] - 1):
                for b in range(counts[v] - 1):
                    corners = []
                    for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        key = [0, 0, 0]
                        key[axis], key[u], key[v] = side, a + du, b + dv
                        corners.append(vertex(tuple(key)))
                    faces.append(tuple(corners) if side else tuple(reversed(corners)))
    mesh = meshkit.Mesh(vertices, faces, normals=normals, name="rounded_box",
                        material=meshkit.material("rounded_box", (0.58, 0.68, 0.80, 1.0), roughness=0.5))
    if radius == 0:
        mesh.normals = meshkit.vertex_normals(mesh)
    return mesh


def main(argv=None):
    """Command line: write the rounded box as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=rounded_box)


if __name__ == "__main__":
    raise SystemExit(main())
