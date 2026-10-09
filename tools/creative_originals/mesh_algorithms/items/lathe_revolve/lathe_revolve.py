"""Lathe: revolve an (r, y) profile polyline around the Y axis, fully or through a partial angle with flat side
caps, with the exact volume of the resulting polygonal solid.

Command line: python3 lathe_revolve.py --output vase.gltf --profile vase --segments 48 --angle 360
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "profile", "type": "str", "default": "vase", "unit": "name", "choices": ["vase", "bowl", "pawn", "spindle"],
     "meaning": "Demonstration (r, y) profile."},
    {"name": "segments", "type": "int", "default": 48, "unit": "count", "minimum": 3, "maximum": 4096,
     "meaning": "Divisions of the swept angle."},
    {"name": "angle", "type": "float", "default": 360.0, "unit": "degrees", "minimum": 1.0, "maximum": 360.0,
     "meaning": "Swept angle; below 360 the cut sides are closed with the profile polygon."},
]


def demo_profile(name="vase"):
    """An (r, y) polyline from bottom to top; r = 0 at an end closes the solid on the axis there."""
    if name == "vase":
        points = [(0.0, 0.0)]
        for k in range(25):
            y = 1.6 * k / 24
            points.append((0.35 + 0.18 * math.sin(2.6 * y + 0.4) + 0.05 * math.cos(9.0 * y), y))
        return points
    if name == "bowl":
        outer = [(0.9 * math.sin(0.5 * math.pi * k / 10), 0.6 - 0.6 * math.cos(0.5 * math.pi * k / 10)) for k in range(11)]
        inner = [(0.82 * math.sin(0.5 * math.pi * k / 10), 0.64 - 0.52 * math.cos(0.5 * math.pi * k / 10)) for k in range(10, -1, -1)]
        return outer + [(0.9, 0.62)] + inner
    if name == "pawn":
        return [(0.0, 0.0), (0.45, 0.0), (0.45, 0.08), (0.36, 0.14), (0.28, 0.2), (0.16, 0.55), (0.24, 0.6),
                (0.24, 0.64), (0.13, 0.68)] + [(0.2 * math.sin(math.pi * k / 10), 0.86 - 0.2 * math.cos(math.pi * k / 10))
                                                for k in range(10, -1, -1) if k <= 8]
    if name == "spindle":
        return [(0.0, -1.0)] + [(0.5 * math.sin(math.pi * k / 12), -math.cos(math.pi * k / 12)) for k in range(1, 12)] + [(0.0, 1.0)]
    raise meshkit.MeshError("profile_unknown", str(name))


def lathe(profile, segments=48, angle=360.0):
    """Revolve ``profile`` about Y; points with r = 0 become single vertices. A full turn welds the seam; a
    partial turn adds both cut faces (the profile closed along the axis) and is closed when both profile ends
    lie on the axis. Faces point outward for a profile listed from bottom to top with r >= 0."""
    pts = [(float(r), float(y)) for r, y in profile]
    if len(pts) < 2 or any(r < 0 for r, _ in pts) or segments < 3 or not 0 < angle <= 360:
        raise meshkit.MeshError("parameter_invalid", "two profile points with r >= 0, segments >= 3, 0 < angle <= 360")
    full = angle >= 360.0
    columns = segments if full else segments + 1
    sweep = math.radians(angle)
    vertices, rows = [], []
    for r, y in pts:
        if r == 0.0:
            rows.append([len(vertices)] * columns)
            vertices.append((0.0, y, 0.0))
            continue
        row = []
        for s in range(columns):
            phi = sweep * s / segments
            row.append(len(vertices))
            vertices.append((r * math.cos(phi), y, -r * math.sin(phi)))
        rows.append(row)
    faces = []
    for k in range(len(pts) - 1):
        for s in range(segments):
            ns = (s + 1) % columns if full else s + 1
            corners = [rows[k][s], rows[k][ns], rows[k + 1][ns], rows[k + 1][s]]
            unique = []
            for corner in corners:
                if corner not in unique:
                    unique.append(corner)
            if len(unique) >= 3:
                faces.append(tuple(reversed(unique)))
    if not full:
        flat = pts if pts[0][0] == 0.0 and pts[-1][0] == 0.0 else [(0.0, pts[0][1])] + pts + [(0.0, pts[-1][1])]
        for column, flip in ((0, True), (segments, False)):
            ring, seen = [], set()
            for r, y in flat:
                match = next((rows[i][column] for i, (pr, py) in enumerate(pts) if pr == r and py == y), None)
                if match is None:
                    match = len(vertices)
                    vertices.append((0.0, y, 0.0))
                if match not in seen:
                    seen.add(match)
                    ring.append(match)
            if len(ring) >= 3:
                order = list(reversed(ring)) if flip else ring
                faces.append(tuple(order))
    mesh = meshkit.Mesh(vertices, faces, name="lathe")
    if mesh.faces and meshkit.signed_volume(mesh) < 0:
        mesh.faces = [tuple(reversed(f)) for f in mesh.faces]
    return mesh


def revolved_volume(profile, segments=48, angle=360.0):
    """Exact volume of the lathe solid: segments * sin(angle / segments) * |first moment of the profile polygon
    closed along the axis| (each profile point sweeps straight chords, not circular arcs)."""
    pts = [(float(r), float(y)) for r, y in profile]
    closed = [(0.0, pts[0][1])] + pts + [(0.0, pts[-1][1])]
    moment = math.fsum((y1 - y0) * (r0 * r0 + r0 * r1 + r1 * r1) / 6.0
                       for (r0, y0), (r1, y1) in zip(closed, closed[1:] + closed[:1]))
    return segments * math.sin(math.radians(angle) / segments) * abs(moment)


def build(profile="vase", segments=48, angle=360.0):
    """The smooth-shaded lathe solid of a demonstration profile."""
    mesh = lathe(demo_profile(profile), segments, angle)
    mesh.normals = meshkit.vertex_normals(mesh)
    mesh.material = meshkit.material("lathe", (0.86, 0.70, 0.52, 1.0), double_sided=True)
    return mesh


def main(argv=None):
    """Command line: write the revolved solid (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
