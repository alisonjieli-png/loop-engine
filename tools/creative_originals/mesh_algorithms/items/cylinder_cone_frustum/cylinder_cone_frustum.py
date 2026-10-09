"""Cylinder, cone, frustum and pipe: one generator for straight solids of revolution with caps and an optional bore.

Command line: python3 cylinder_cone_frustum.py --output frustum.gltf --bottom-radius 0.6 --top-radius 0.3 --height 1.2
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "bottom_radius", "type": "float", "default": 0.6, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Outer radius at the bottom (y = -height / 2); 0 makes a cone pointing down."},
    {"name": "top_radius", "type": "float", "default": 0.3, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Outer radius at the top (y = +height / 2); 0 makes a cone; equal radii make a cylinder."},
    {"name": "height", "type": "float", "default": 1.2, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Distance between the bottom and top planes."},
    {"name": "segments", "type": "int", "default": 32, "unit": "count", "minimum": 3, "maximum": 4096,
     "meaning": "Divisions around the Y axis."},
    {"name": "inner_radius", "type": "float", "default": 0.12, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Radius of a straight bore along Y; 0 for a solid. Must be below both outer radii."},
    {"name": "caps", "type": "bool", "default": True, "unit": "flag",
     "meaning": "Close the ends; without caps the result is an open tube (or two tubes with a bore)."},
]


def _ring(radius, y, segments, normal_radial, normal_y, seam, uv_v):
    rows = []
    for s in range(segments + (1 if seam else 0)):
        phi = 2.0 * math.pi * (s % segments) / segments
        c, d = math.cos(phi), math.sin(phi)
        rows.append(((radius * c, y, -radius * d), (normal_radial * c, normal_y, -normal_radial * d), (s / segments, uv_v)))
    return rows


def frustum(bottom_radius=0.6, top_radius=0.3, height=1.2, segments=32, inner_radius=0.12, caps=True):
    """A straight solid of revolution around Y, centred at the origin, with outward faces.

    Side vertices repeat the seam column for texture coordinates and caps own their vertices (flat normals),
    so the solid is closed after welding. A zero top or bottom radius gives a cone with one apex vertex per
    segment; ``inner_radius`` > 0 adds a bore (annular caps and an inward-facing inner wall)."""
    if height <= 0 or segments < 3 or min(bottom_radius, top_radius, inner_radius) < 0:
        raise meshkit.MeshError("parameter_invalid", "height > 0, segments >= 3, radii >= 0")
    if bottom_radius == 0 and top_radius == 0:
        raise meshkit.MeshError("parameter_invalid", "at least one outer radius must be positive")
    if inner_radius > 0 and inner_radius >= min(bottom_radius, top_radius):
        raise meshkit.MeshError("parameter_invalid", "the bore must be narrower than both outer radii")
    vertices, normals, uvs, faces = [], [], [], []

    def add(rows):
        start = len(vertices)
        for position, normal, uv in rows:
            vertices.append(position)
            normals.append(meshkit.vnormalize(normal, (0.0, 1.0, 0.0)))
            uvs.append(uv)
        return list(range(start, len(vertices)))

    half = height / 2.0
    slope = meshkit.vnormalize((height, bottom_radius - top_radius, 0.0))
    if bottom_radius > 0 and top_radius > 0:
        low = add(_ring(bottom_radius, -half, segments, slope[0], slope[1], True, 1.0))
        high = add(_ring(top_radius, half, segments, slope[0], slope[1], True, 0.0))
        faces += [(low[s], low[s + 1], high[s + 1], high[s]) for s in range(segments)]
    else:
        apex_y = half if top_radius == 0 else -half
        base = add(_ring(max(bottom_radius, top_radius), -apex_y, segments, slope[0], slope[1], True,
                         1.0 if top_radius == 0 else 0.0))
        apex = []
        for s in range(segments):
            phi = 2.0 * math.pi * (s + 0.5) / segments
            apex += add([((0.0, apex_y, 0.0), (slope[0] * math.cos(phi), slope[1], -slope[0] * math.sin(phi)),
                          ((s + 0.5) / segments, 0.0 if top_radius == 0 else 1.0))])
        if top_radius == 0:
            faces += [(base[s], base[s + 1], apex[s]) for s in range(segments)]
        else:
            faces += [(base[s + 1], base[s], apex[s]) for s in range(segments)]
    if inner_radius > 0:
        low_in = add(_ring(inner_radius, -half, segments, -1.0, 0.0, True, 1.0))
        high_in = add(_ring(inner_radius, half, segments, -1.0, 0.0, True, 0.0))
        faces += [(low_in[s + 1], low_in[s], high_in[s], high_in[s + 1]) for s in range(segments)]
    if caps:
        for y, sign, radius in ((-half, -1.0, bottom_radius), (half, 1.0, top_radius)):
            if radius == 0:
                continue
            outer = add([((radius * math.cos(2 * math.pi * s / segments), y, -radius * math.sin(2 * math.pi * s / segments)),
                          (0.0, sign, 0.0), (0.5 + 0.5 * math.cos(2 * math.pi * s / segments),
                                             0.5 + 0.5 * sign * math.sin(2 * math.pi * s / segments)))
                         for s in range(segments)])
            if inner_radius > 0:
                ratio = inner_radius / radius
                inner = add([((inner_radius * math.cos(2 * math.pi * s / segments), y,
                               -inner_radius * math.sin(2 * math.pi * s / segments)), (0.0, sign, 0.0),
                              (0.5 + 0.5 * ratio * math.cos(2 * math.pi * s / segments),
                               0.5 + 0.5 * ratio * sign * math.sin(2 * math.pi * s / segments))) for s in range(segments)])
                for s in range(segments):
                    t = (s + 1) % segments
                    quad = (outer[s], outer[t], inner[t], inner[s])
                    faces.append(quad if sign > 0 else tuple(reversed(quad)))
            else:
                faces.append(tuple(outer) if sign > 0 else tuple(reversed(outer)))
    return meshkit.Mesh(vertices, faces, normals=normals, uvs=uvs, name="frustum",
                        material=meshkit.material("frustum", (0.80, 0.80, 0.70, 1.0)))


def main(argv=None):
    """Command line: write the solid as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=frustum)


if __name__ == "__main__":
    raise SystemExit(main())
