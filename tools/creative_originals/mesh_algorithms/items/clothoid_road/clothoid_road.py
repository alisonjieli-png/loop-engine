"""Clothoid (Euler spiral) road: a straight, a clothoid easing into a circular arc, the arc, and a clothoid back,
as a flat ribbon with lane markings.

Command line: python3 clothoid_road.py --output road.gltf --radius 8 --transition 6 --arc-angle 60 --width 3
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "radius", "type": "float", "default": 8.0, "unit": "m", "minimum": 0.1, "maximum": 1000000.0,
     "meaning": "Radius of the circular arc in the middle of the bend."},
    {"name": "transition", "type": "float", "default": 6.0, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Length of each clothoid, over which curvature grows linearly from 0 to 1 / radius."},
    {"name": "arc_angle", "type": "float", "default": 60.0, "unit": "degrees", "minimum": 0.0, "maximum": 300.0,
     "meaning": "Turn of the circular arc between the two clothoids."},
    {"name": "width", "type": "float", "default": 3.0, "unit": "m", "minimum": 0.01, "maximum": 1000.0,
     "meaning": "Road width."},
    {"name": "step", "type": "float", "default": 0.5, "unit": "m", "minimum": 0.01, "maximum": 100.0,
     "meaning": "Arc-length spacing of the road cross-sections."},
]


def clothoid_point(s, scale):
    """(x, y, heading) on the unit-direction clothoid at arc length s: x = integral cos(u^2 / (2 A^2)) du,
    y = integral sin(u^2 / (2 A^2)) du from 0 to s with A = ``scale``, heading s^2 / (2 A^2). Integrated by the
    power series of the Fresnel integrals (converges for every s)."""
    if s == 0:
        return 0.0, 0.0, 0.0
    a2 = 2.0 * scale * scale
    x_terms, y_terms = [], []
    k = 0
    while True:
        # cos(t) = sum (-1)^k t^(2k) / (2k)!, t = u^2 / a2: integrate u^(4k) / a2^(2k) and u^(4k+2) / a2^(2k+1)
        term_x = (-1) ** k * s ** (4 * k + 1) / (math.factorial(2 * k) * a2 ** (2 * k) * (4 * k + 1))
        term_y = (-1) ** k * s ** (4 * k + 3) / (math.factorial(2 * k + 1) * a2 ** (2 * k + 1) * (4 * k + 3))
        x_terms.append(term_x)
        y_terms.append(term_y)
        if abs(term_x) + abs(term_y) < 1e-17 * max(1.0, abs(s)) or k > 200:
            break
        k += 1
    return math.fsum(x_terms), math.fsum(y_terms), s * s / a2


def curvature_at(s, transition=6.0, radius=8.0, arc_length=0.0):
    """Curvature of the road centre line at distance s along the bend: rising linearly over the first
    clothoid, 1 / radius along the arc, falling over the second clothoid, 0 elsewhere."""
    if s <= 0:
        return 0.0
    if s < transition:
        return s / (transition * radius)
    if s <= transition + arc_length:
        return 1.0 / radius
    if s < 2 * transition + arc_length:
        return (2 * transition + arc_length - s) / (transition * radius)
    return 0.0


def centre_line(radius=8.0, transition=6.0, arc_angle=60.0, step=0.5, lead=6.0):
    """Points (x, y) and headings of the road centre line, starting with a straight of length ``lead`` along +x,
    integrating the piecewise-linear curvature exactly segment by segment (clothoid series inside the
    transitions, circles on the arc)."""
    arc_length = math.radians(arc_angle) * radius
    total = lead + 2 * transition + arc_length + lead
    count = max(2, int(math.ceil(total / step)))
    samples = []
    for k in range(count + 1):
        samples.append(total * k / count)
    points = []
    x, y, heading = -lead, 0.0, 0.0
    last = 0.0
    scale = math.sqrt(radius * transition) if transition > 0 else 0.0
    for s in samples:
        x, y, heading = _advance(x, y, heading, last - lead, s - lead, transition, radius, arc_length, scale)
        last = s
        points.append((x, y, heading))
    return points


def _advance(x, y, heading, s0, s1, transition, radius, arc_length, scale):
    """Move from s0 to s1 along the centre line, splitting at the curvature breakpoints."""
    breaks = [0.0, transition, transition + arc_length, 2 * transition + arc_length]
    cuts = sorted({s0, s1} | {b for b in breaks if s0 < b < s1})
    for a, b in zip(cuts, cuts[1:]):
        middle = 0.5 * (a + b)
        if middle <= 0 or middle >= 2 * transition + arc_length:
            x, y = x + (b - a) * math.cos(heading), y + (b - a) * math.sin(heading)
        elif middle <= transition or middle >= transition + arc_length:
            if middle <= transition:
                # rising curvature: heading(s) = base + theta(s) with base = heading(a) - theta(a)
                p0, p1 = clothoid_point(a, scale), clothoid_point(b, scale)
                base = heading - p0[2]
                dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                x += dx * math.cos(base) - dy * math.sin(base)
                y += dx * math.sin(base) + dy * math.cos(base)
                heading = base + p1[2]
            else:
                # falling curvature: with u = end - s, heading(s) = c - theta(u) where c = heading(a) + theta(u(a))
                end = 2 * transition + arc_length
                p0, p1 = clothoid_point(end - a, scale), clothoid_point(end - b, scale)
                c = heading + p0[2]
                dx, dy = p0[0] - p1[0], p0[1] - p1[1]
                x += math.cos(c) * dx + math.sin(c) * dy
                y += math.sin(c) * dx - math.cos(c) * dy
                heading = c - p1[2]
        else:
            turn = (b - a) / radius
            x += radius * (math.sin(heading + turn) - math.sin(heading))
            y += radius * (math.cos(heading) - math.cos(heading + turn))
            heading += turn
    return x, y, heading


def road(radius=8.0, transition=6.0, arc_angle=60.0, width=3.0, step=0.5):
    """A flat road ribbon in the XZ plane (2D y maps to -z) with asphalt colour and white edge lines."""
    points = centre_line(radius, transition, arc_angle, step)
    offsets = (-0.5, -0.45, 0.45, 0.5)
    colors = ((0.95, 0.95, 0.92, 1.0), (0.22, 0.22, 0.24, 1.0), (0.22, 0.22, 0.24, 1.0), (0.95, 0.95, 0.92, 1.0))
    vertices, vertex_colors, faces = [], [], []
    for x, y, heading in points:
        nx, ny = -math.sin(heading), math.cos(heading)
        for offset, color in zip(offsets, colors):
            vertices.append(meshkit.plane_to_3d((x + offset * width * nx, y + offset * width * ny)))
            vertex_colors.append(color)
    lanes = len(offsets)
    for k in range(len(points) - 1):
        for j in range(lanes - 1):
            a, b = k * lanes + j, k * lanes + j + 1
            faces.append((a + lanes, b + lanes, b, a))
    mesh = meshkit.Mesh(vertices, faces, normals=[(0.0, 1.0, 0.0)] * len(vertices), colors=vertex_colors, name="road",
                        material=meshkit.material("road", (1.0, 1.0, 1.0, 1.0), roughness=0.9))
    if meshkit.face_normal(mesh.vertices, mesh.faces[0])[1] < 0:
        mesh.faces = [tuple(reversed(f)) for f in mesh.faces]
    return mesh


def main(argv=None):
    """Command line: write the road ribbon (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=road)


if __name__ == "__main__":
    raise SystemExit(main())
