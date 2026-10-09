"""Twisted band: a Moebius strip (one half twist) or any number of half twists, as an open quad surface.

Command line: python3 mobius_strip.py --output mobius.gltf --radius 1 --width 0.5 --half-twists 1
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "radius", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius of the centre circle around the Y axis."},
    {"name": "width", "type": "float", "default": 0.5, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Width of the band; keep it below twice the radius."},
    {"name": "half_twists", "type": "int", "default": 1, "unit": "count", "minimum": 0, "maximum": 64,
     "meaning": "Half turns of the band along the loop; odd values give a one-sided band."},
    {"name": "segments", "type": "int", "default": 120, "unit": "count", "minimum": 3, "maximum": 100000,
     "meaning": "Divisions along the loop."},
    {"name": "strips", "type": "int", "default": 6, "unit": "count", "minimum": 1, "maximum": 1000,
     "meaning": "Divisions across the width."},
]


def band_point(angle, offset, radius=1.0, half_twists=1):
    """Point at loop angle ``angle`` (radians, from +X toward -Z) and signed offset across the band."""
    turn = 0.5 * half_twists * angle
    ring = radius + offset * math.cos(turn)
    return (ring * math.cos(angle), offset * math.sin(turn), -ring * math.sin(angle))


def mobius_strip(radius=1.0, width=0.5, half_twists=1, segments=120, strips=6):
    """A twisted band of segments * (strips + 1) vertices and segments * strips quads, with no seam.

    The last column joins the first; with an odd number of half twists it joins upside down, so the surface
    is one-sided (no consistent orientation), has one boundary loop and Euler characteristic 0. With an
    even number it is two-sided with two boundary loops. Normals come from the parameterization."""
    if not (radius > 0 and width > 0) or half_twists < 0 or segments < 3 or strips < 1:
        raise meshkit.MeshError("parameter_invalid", "radius, width > 0; half_twists >= 0; segments >= 3; strips >= 1")
    columns = strips + 1
    vertices, normals = [], []
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        for j in range(columns):
            offset = width * (j / strips - 0.5)
            vertices.append(band_point(angle, offset, radius, half_twists))
            h = 1e-6
            du = meshkit.vsub(band_point(angle + h, offset, radius, half_twists), band_point(angle - h, offset, radius, half_twists))
            dv = meshkit.vsub(band_point(angle, offset + h, radius, half_twists), band_point(angle, offset - h, radius, half_twists))
            normals.append(meshkit.vnormalize(meshkit.vcross(dv, du), (0.0, 1.0, 0.0)))
    flipped = half_twists % 2 == 1
    faces = []
    for i in range(segments):
        nxt = (i + 1) % segments
        for j in range(strips):
            a, b = i * columns + j, i * columns + j + 1
            if nxt == 0 and flipped:
                c, d = nxt * columns + (strips - j - 1), nxt * columns + (strips - j)
            else:
                c, d = nxt * columns + j + 1, nxt * columns + j
            faces.append((a, b, c, d))
    return meshkit.Mesh(vertices, faces, normals=normals, name="mobius_strip",
                        material=meshkit.material("mobius", (0.93, 0.70, 0.36, 1.0), double_sided=True))


def main(argv=None):
    """Command line: write the band as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=mobius_strip)


if __name__ == "__main__":
    raise SystemExit(main())
