"""Extrude a 2D polygon with holes into a closed solid, with optional taper of the top face.

Command line: python3 extrude_polygon_holes.py --output extrusion.gltf --height 0.4 --taper 1.0
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "height", "type": "float", "default": 0.4, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Extrusion distance along +Y (the solid spans y = 0 to height)."},
    {"name": "taper", "type": "float", "default": 1.0, "unit": "ratio", "minimum": 0.0, "maximum": 100.0,
     "meaning": "Scale of the top face about the origin (1 straight walls, below 1 inward slope)."},
]
DEMO_OUTER = [(-1.2, -0.8), (1.2, -0.8), (1.2, 0.3), (0.6, 0.8), (-0.6, 0.8), (-1.2, 0.3)]
DEMO_HOLES = [[(-0.8 + 0.25 * math.cos(-2 * math.pi * k / 20), -0.2 + 0.25 * math.sin(-2 * math.pi * k / 20)) for k in range(20)],
              [(0.3, -0.5), (0.3, 0.1), (0.9, 0.1), (0.9, -0.5)]]


def extrude(outer, holes=(), height=0.4, taper=1.0):
    """A closed solid: the polygon at y = 0 (facing -Y), the same polygon scaled by ``taper`` at y = height
    (facing +Y) and quad walls. 2D (x, y) maps to (x, *, -y). Each hole adds one tunnel (genus = holes).
    Volume = area * height * (1 + taper + taper^2) / 3, which is area * height when taper = 1."""
    rings = [list(outer)] + [list(h) for h in holes]
    if len(rings[0]) < 3 or height <= 0 or taper < 0:
        raise meshkit.MeshError("parameter_invalid", "an outer ring of three points, height > 0, taper >= 0")
    if meshkit.polygon_area_2d(rings[0]) < 0:
        rings[0].reverse()
    for k in range(1, len(rings)):
        if meshkit.polygon_area_2d(rings[k]) > 0:
            rings[k].reverse()
    flat = [p for ring in rings for p in ring]
    count = len(flat)
    vertices = [meshkit.plane_to_3d(p, 0.0) for p in flat]
    vertices += [meshkit.plane_to_3d((taper * p[0], taper * p[1]), height) for p in flat]
    faces = []
    for a, b, c in meshkit.triangulate_polygon_2d(rings[0], rings[1:]):
        faces.append((count + a, count + b, count + c))
        faces.append((c, b, a))
    start = 0
    for ring in rings:
        size = len(ring)
        for k in range(size):
            a, b = start + k, start + (k + 1) % size
            faces.append((a, b, count + b, count + a))
        start += size
    return meshkit.Mesh(vertices, faces, name="extrusion")


def polygon_area(outer, holes=()):
    """Area of the polygon minus its holes (shoelace)."""
    return abs(meshkit.polygon_area_2d(outer)) - math.fsum(abs(meshkit.polygon_area_2d(h)) for h in holes)


def build(height=0.4, taper=1.0):
    """The extruded demonstration plate (outline with a round and a square hole), flat shaded."""
    mesh = meshkit.flat_shaded(extrude(DEMO_OUTER, DEMO_HOLES, height, taper))
    mesh.material = meshkit.material("extrusion", (0.60, 0.66, 0.84, 1.0), roughness=0.5)
    return mesh


def main(argv=None):
    """Command line: write the extruded solid (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
