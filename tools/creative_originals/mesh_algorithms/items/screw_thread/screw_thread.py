"""Threaded rod: a helical trapezoidal thread on a cylinder, capped at both ends.

Command line: python3 screw_thread.py --output screw.gltf --major-radius 0.2 --minor-radius 0.16 --pitch 0.1 --length 0.8
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "major_radius", "type": "float", "default": 0.2, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius at the thread crest."},
    {"name": "minor_radius", "type": "float", "default": 0.16, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius at the thread root; below major_radius."},
    {"name": "pitch", "type": "float", "default": 0.1, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Axial distance between neighbouring crests (one turn for a single start)."},
    {"name": "length", "type": "float", "default": 0.8, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Length of the rod along Y."},
    {"name": "crest", "type": "float", "default": 0.15, "unit": "fraction", "minimum": 0.0, "maximum": 0.9,
     "meaning": "Fraction of the pitch that is flat at the crest."},
    {"name": "root", "type": "float", "default": 0.25, "unit": "fraction", "minimum": 0.0, "maximum": 0.9,
     "meaning": "Fraction of the pitch that is flat at the root; crest + root < 1."},
    {"name": "segments", "type": "int", "default": 32, "unit": "count", "minimum": 3, "maximum": 4096,
     "meaning": "Divisions around the rod."},
    {"name": "samples_per_pitch", "type": "int", "default": 8, "unit": "count", "minimum": 4, "maximum": 1000,
     "meaning": "Axial rows per pitch."},
]


def thread_profile(phase, crest=0.15, root=0.25):
    """Height of the thread in [0, 1] at ``phase`` (fraction of the pitch): root flat, rising flank, crest flat,
    falling flank, each flank (1 - crest - root) / 2 of the pitch."""
    phase -= math.floor(phase)
    flank = (1.0 - crest - root) / 2.0
    if phase < root:
        return 0.0
    if phase < root + flank:
        return (phase - root) / flank
    if phase < root + flank + crest:
        return 1.0
    return max(0.0, 1.0 - (phase - root - flank - crest) / flank)


def screw_thread(major_radius=0.2, minor_radius=0.16, pitch=0.1, length=0.8, crest=0.15, root=0.25, segments=32,
                 samples_per_pitch=8):
    """A closed threaded rod centred at the origin along Y: (rows + 1) * segments vertices, rows * segments
    quads and two polygon caps, where rows = ceil(length / pitch * samples_per_pitch). The radius at angle
    theta and height y is minor + (major - minor) * profile(y / pitch - theta / 2 pi): a right-hand thread."""
    if not 0 < minor_radius < major_radius or pitch <= 0 or length <= 0 or crest + root >= 1.0 or segments < 3:
        raise meshkit.MeshError("parameter_invalid", "0 < minor < major, pitch and length > 0, crest + root < 1")
    rows = int(math.ceil(length / pitch * samples_per_pitch))
    depth = major_radius - minor_radius
    vertices = []
    for j in range(rows + 1):
        y = -length / 2.0 + length * j / rows
        for i in range(segments):
            theta = 2.0 * math.pi * i / segments
            radius = minor_radius + depth * thread_profile((y + length / 2.0) / pitch - theta / (2.0 * math.pi), crest, root)
            vertices.append((radius * math.cos(theta), y, -radius * math.sin(theta)))
    faces = []
    for j in range(rows):
        for i in range(segments):
            ni = (i + 1) % segments
            faces.append((j * segments + i, j * segments + ni, (j + 1) * segments + ni, (j + 1) * segments + i))
    faces.append(tuple(reversed(range(segments))))
    faces.append(tuple(rows * segments + i for i in range(segments)))
    mesh = meshkit.Mesh(vertices, faces, name="screw_thread",
                        material=meshkit.material("screw", (0.74, 0.74, 0.76, 1.0), metallic=0.8, roughness=0.35))
    mesh.normals = meshkit.vertex_normals(mesh)
    return mesh


def main(argv=None):
    """Command line: write the threaded rod as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=screw_thread)


if __name__ == "__main__":
    raise SystemExit(main())
