"""Klein bottle as the figure-eight immersion: a closed one-sided surface without boundary.

Command line: python3 klein_bottle.py --output klein.gltf --radius 2 --scale 0.5 --u-segments 80 --v-segments 24
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "radius", "type": "float", "default": 2.0, "unit": "m", "minimum": 1.0, "maximum": 1000000.0,
     "meaning": "Radius of the centre circle before scaling; above 1 keeps the figure eight off the axis."},
    {"name": "scale", "type": "float", "default": 0.5, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Uniform scale applied to the whole surface."},
    {"name": "u_segments", "type": "int", "default": 80, "unit": "count", "minimum": 3, "maximum": 100000,
     "meaning": "Divisions around the centre circle."},
    {"name": "v_segments", "type": "int", "default": 24, "unit": "count", "minimum": 4, "maximum": 100000,
     "meaning": "Divisions around the figure-eight cross-section."},
]


def figure_eight_point(u, v, radius=2.0):
    """Point of the figure-eight immersion at angles u (around the centre circle) and v (around the eight)."""
    half = 0.5 * u
    ring = radius + math.cos(half) * math.sin(v) - math.sin(half) * math.sin(2.0 * v)
    return (ring * math.cos(u), math.sin(half) * math.sin(v) + math.cos(half) * math.sin(2.0 * v), -ring * math.sin(u))


def klein_bottle(radius=2.0, scale=0.5, u_segments=80, v_segments=24):
    """A closed figure-eight Klein bottle: u_segments * v_segments vertices and as many quads.

    Going once around u maps v to -v, so the last column joins the first in reverse. Every edge has two
    faces, there is no boundary, the Euler characteristic is 0 and no consistent orientation exists. The
    immersion crosses itself along one circle. Normals are angle weighted from the faces."""
    if radius < 1.0 or not scale > 0 or u_segments < 3 or v_segments < 4:
        raise meshkit.MeshError("parameter_invalid", "radius >= 1, scale > 0, u_segments >= 3, v_segments >= 4")
    vertices = []
    for i in range(u_segments):
        u = 2.0 * math.pi * i / u_segments
        for j in range(v_segments):
            vertices.append(meshkit.vscale(figure_eight_point(u, 2.0 * math.pi * j / v_segments, radius), scale))
    faces = []
    for i in range(u_segments):
        for j in range(v_segments):
            jn = (j + 1) % v_segments
            if i + 1 < u_segments:
                c, d = (i + 1) * v_segments + jn, (i + 1) * v_segments + j
            else:
                c, d = (v_segments - jn) % v_segments, (v_segments - j) % v_segments
            faces.append((i * v_segments + j, i * v_segments + jn, c, d))
    mesh = meshkit.Mesh(vertices, faces, name="klein_bottle",
                        material=meshkit.material("klein", (0.56, 0.74, 0.88, 1.0), double_sided=True))
    mesh.normals = meshkit.vertex_normals(mesh)
    return mesh


def main(argv=None):
    """Command line: write the surface as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=klein_bottle)


if __name__ == "__main__":
    raise SystemExit(main())
