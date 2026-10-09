"""Coil spring: a round wire swept along a helix with exact rotation-minimizing frames and flat end caps.

Command line: python3 coil_spring.py --output spring.gltf --coil-radius 0.5 --pitch 0.25 --turns 6 --wire-radius 0.05
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "coil_radius", "type": "float", "default": 0.5, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Distance from the Y axis to the wire centre."},
    {"name": "pitch", "type": "float", "default": 0.25, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Rise per turn; keep it above twice the wire radius so turns do not touch."},
    {"name": "turns", "type": "float", "default": 6.0, "unit": "turns", "minimum": 0.01, "maximum": 10000.0,
     "meaning": "Number of turns (fractions allowed)."},
    {"name": "wire_radius", "type": "float", "default": 0.05, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Radius of the wire cross-section."},
    {"name": "steps_per_turn", "type": "int", "default": 36, "unit": "count", "minimum": 3, "maximum": 100000,
     "meaning": "Samples along the helix per turn."},
    {"name": "sides", "type": "int", "default": 10, "unit": "count", "minimum": 3, "maximum": 1024,
     "meaning": "Divisions around the wire."},
]


def helix_frame(t, coil_radius=0.5, pitch=0.25):
    """(tangent, normal, binormal) at helix angle t; the normal is the Frenet normal turned back by the
    accumulated torsion, which makes the frame rotation-minimizing (no twist about the tangent)."""
    b = pitch / (2.0 * math.pi)
    speed = math.sqrt(coil_radius * coil_radius + b * b)
    tangent = (-coil_radius * math.sin(t) / speed, b / speed, -coil_radius * math.cos(t) / speed)
    frenet_n = (-math.cos(t), 0.0, math.sin(t))
    frenet_b = meshkit.vcross(tangent, frenet_n)
    turn = -b * t / speed
    normal = meshkit.vadd(meshkit.vscale(frenet_n, math.cos(turn)), meshkit.vscale(frenet_b, math.sin(turn)))
    return tangent, normal, meshkit.vcross(tangent, normal)


def coil_spring(coil_radius=0.5, pitch=0.25, turns=6.0, wire_radius=0.05, steps_per_turn=36, sides=10):
    """A closed spring mesh centred at the origin along Y.

    Wire rings: steps + 1 with steps = ceil(turns * steps_per_turn), each with ``sides`` vertices; each end has
    its own ring of cap vertices with a flat normal and one polygon face. Vertices (steps + 3) * sides,
    faces steps * sides + 2; closed after welding the cap rings to the wire ends."""
    if min(coil_radius, turns, wire_radius) <= 0 or pitch < 0 or steps_per_turn < 3 or sides < 3:
        raise meshkit.MeshError("parameter_invalid", "radii and turns > 0, pitch >= 0, steps >= 3, sides >= 3")
    steps = int(math.ceil(turns * steps_per_turn))
    total = 2.0 * math.pi * turns
    height = pitch * turns
    vertices, normals, faces, rings = [], [], [], []
    frames = []
    for k in range(steps + 1):
        t = total * k / steps
        center = (coil_radius * math.cos(t), pitch * t / (2.0 * math.pi) - height / 2.0, -coil_radius * math.sin(t))
        tangent, normal, binormal = helix_frame(t, coil_radius, pitch)
        frames.append((center, tangent))
        ring = []
        for j in range(sides):
            angle = 2.0 * math.pi * j / sides
            direction = meshkit.vadd(meshkit.vscale(normal, math.cos(angle)), meshkit.vscale(binormal, math.sin(angle)))
            ring.append(len(vertices))
            vertices.append(meshkit.vadd(center, meshkit.vscale(direction, wire_radius)))
            normals.append(direction)
        rings.append(ring)
    for k in range(steps):
        for j in range(sides):
            nj = (j + 1) % sides
            faces.append((rings[k][j], rings[k][nj], rings[k + 1][nj], rings[k + 1][j]))
    for end, sign in ((0, -1.0), (steps, 1.0)):
        center, tangent = frames[end]
        cap = []
        for index in rings[end]:
            cap.append(len(vertices))
            vertices.append(vertices[index])
            normals.append(meshkit.vscale(tangent, sign))
        faces.append(tuple(cap) if sign > 0 else tuple(reversed(cap)))
    return meshkit.Mesh(vertices, faces, normals=normals, name="coil_spring",
                        material=meshkit.material("spring", (0.72, 0.74, 0.78, 1.0), metallic=0.8, roughness=0.35))


def main(argv=None):
    """Command line: write the spring as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=coil_spring)


if __name__ == "__main__":
    raise SystemExit(main())
