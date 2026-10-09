"""Capsule: a cylinder with hemispherical ends, UVs following the profile length.

Command line: python3 capsule.py --output capsule.gltf --radius 0.5 --length 1 --segments 32 --cap-rings 8
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "radius", "type": "float", "default": 0.5, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius of the cylinder and of both hemispheres."},
    {"name": "length", "type": "float", "default": 1.0, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Length of the straight part; the total height is length + 2 * radius."},
    {"name": "segments", "type": "int", "default": 32, "unit": "count", "minimum": 3, "maximum": 4096,
     "meaning": "Divisions around the Y axis."},
    {"name": "cap_rings", "type": "int", "default": 8, "unit": "count", "minimum": 1, "maximum": 2048,
     "meaning": "Rings in each hemisphere from the pole to the equator."},
]


def capsule_profile(radius=0.5, length=1.0, cap_rings=8):
    """The (r, y) profile from the north pole to the south pole: quarter arcs joined by the straight part."""
    top = [(radius * math.sin(0.5 * math.pi * r / cap_rings), 0.5 * length + radius * math.cos(0.5 * math.pi * r / cap_rings))
           for r in range(cap_rings + 1)]
    bottom = [(radius * math.sin(0.5 * math.pi + 0.5 * math.pi * r / cap_rings),
               -0.5 * length + radius * math.cos(0.5 * math.pi + 0.5 * math.pi * r / cap_rings)) for r in range(cap_rings + 1)]
    top[0], bottom[-1] = (0.0, 0.5 * length + radius), (0.0, -0.5 * length - radius)
    return top + bottom


def capsule(radius=0.5, length=1.0, segments=32, cap_rings=8):
    """A capsule along Y centred at the origin: 2 segments + 2 cap_rings (segments + 1) vertices and
    4 cap_rings segments triangles, with unit normals and UVs (v from the north pole by profile length)."""
    if not radius > 0 or length < 0 or segments < 3 or cap_rings < 1:
        raise meshkit.MeshError("parameter_invalid", "radius > 0, length >= 0, segments >= 3, cap_rings >= 1")
    profile = capsule_profile(radius, length, cap_rings)
    count = len(profile)
    run = [0.0]
    for (r0, y0), (r1, y1) in zip(profile, profile[1:]):
        run.append(run[-1] + math.sqrt((r1 - r0) ** 2 + (y1 - y0) ** 2))
    total = run[-1]
    normals_2d = []
    for k, (r, y) in enumerate(profile):
        center = 0.5 * length if k <= cap_rings else -0.5 * length
        normals_2d.append(meshkit.vnormalize((r, y - center, 0.0), (0.0, 1.0 if k == 0 else -1.0, 0.0)))
    vertices, normals, uvs, faces = [], [], [], []
    rows = []
    for k in range(count):
        r, y = profile[k]
        nr, ny = normals_2d[k][0], normals_2d[k][1]
        row = []
        if k in (0, count - 1):
            for s in range(segments):
                row.append(len(vertices))
                vertices.append((0.0, y, 0.0))
                normals.append((0.0, ny, 0.0))
                uvs.append(((s + 0.5) / segments, run[k] / total))
        else:
            for s in range(segments + 1):
                phi = 2.0 * math.pi * (s % segments) / segments
                c, d = math.cos(phi), math.sin(phi)
                row.append(len(vertices))
                vertices.append((r * c, y, -r * d))
                normals.append((nr * c, ny, -nr * d))
                uvs.append((s / segments, run[k] / total))
        rows.append(row)
    for s in range(segments):
        faces.append((rows[0][s], rows[1][s], rows[1][s + 1]))
    for k in range(1, count - 2):
        for s in range(segments):
            faces.append((rows[k][s], rows[k + 1][s], rows[k + 1][s + 1], rows[k][s + 1]))
    for s in range(segments):
        faces.append((rows[count - 2][s], rows[count - 1][s], rows[count - 2][s + 1]))
    return meshkit.Mesh(vertices, faces, normals=normals, uvs=uvs, name="capsule",
                        material=meshkit.material("capsule", (0.66, 0.74, 0.90, 1.0)))


def main(argv=None):
    """Command line: write the capsule as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=capsule)


if __name__ == "__main__":
    raise SystemExit(main())
