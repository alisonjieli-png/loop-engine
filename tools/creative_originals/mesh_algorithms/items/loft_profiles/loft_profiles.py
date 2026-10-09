"""Loft: skin a solid through a stack of closed profiles, resampled to equal counts by arc length and aligned to
avoid twisting, with capped ends.

Command line: python3 loft_profiles.py --output loft.gltf --shape bottle --samples 48
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "shape", "type": "str", "default": "bottle", "unit": "name", "choices": ["bottle", "tower", "boat"],
     "meaning": "Demonstration stack of profiles."},
    {"name": "samples", "type": "int", "default": 48, "unit": "count", "minimum": 3, "maximum": 100000,
     "meaning": "Points per profile after resampling."},
]


def resample_closed(polygon, count):
    """``count`` points spaced evenly by arc length around a closed polygon, starting at its first vertex."""
    pts = [tuple(float(c) for c in p) for p in polygon]
    lengths = [meshkit.vdistance(pts[k], pts[(k + 1) % len(pts)]) for k in range(len(pts))]
    total = math.fsum(lengths)
    result, edge, walked = [], 0, 0.0
    for k in range(count):
        target = total * k / count
        while walked + lengths[edge] < target and edge < len(pts) - 1:
            walked += lengths[edge]
            edge += 1
        t = 0.0 if lengths[edge] == 0 else (target - walked) / lengths[edge]
        result.append(meshkit.vlerp(pts[edge], pts[(edge + 1) % len(pts)], t))
    return result


def align(reference, ring):
    """``ring`` cyclically shifted to minimize the summed squared distance to ``reference`` (same orientation
    assumed), which keeps the skin from twisting."""
    best, best_cost = ring, math.inf
    for shift in range(len(ring)):
        turned = ring[shift:] + ring[:shift]
        cost = math.fsum(meshkit.vdot(meshkit.vsub(a, b), meshkit.vsub(a, b)) for a, b in zip(reference, turned))
        if cost < best_cost - 1e-15:
            best, best_cost = turned, cost
    return best


def _centroid(ring):
    return tuple(math.fsum(p[k] for p in ring) / len(ring) for k in range(3))


def loft(profiles, samples=None, caps=True):
    """A closed skin through 3D profiles (each a closed planar polygon, listed from the first end to the other).

    With ``samples`` every profile is resampled to that count by arc length; without, all must have equal
    counts. Every ring is turned counter-clockwise about the loft direction (first centroid to last) and then
    cyclically aligned to the previous ring. Side quads join neighbouring rings; caps triangulate the end
    rings. Faces point outward. Vertices: profiles * count."""
    rings = [resample_closed(p, samples) if samples else [tuple(float(c) for c in q) for q in p] for p in profiles]
    count = len(rings[0])
    if len(rings) < 2 or count < 3 or any(len(r) != count for r in rings):
        raise meshkit.MeshError("profiles_invalid", "two or more profiles with equal point counts")
    direction = meshkit.vsub(_centroid(rings[-1]), _centroid(rings[0]))
    for k, ring in enumerate(rings):
        if meshkit.vdot(meshkit.face_normal(ring, tuple(range(count))), direction) < 0:
            rings[k] = [ring[0]] + ring[1:][::-1]
    for k in range(1, len(rings)):
        rings[k] = align(rings[k - 1], rings[k])
    vertices = [p for ring in rings for p in ring]
    faces = []
    for k in range(len(rings) - 1):
        for j in range(count):
            nj = (j + 1) % count
            faces.append((k * count + j, k * count + nj, (k + 1) * count + nj, (k + 1) * count + j))
    if caps:
        for ring_index, outward_is_forward in ((0, False), (len(rings) - 1, True)):
            ring = rings[ring_index]
            normal = meshkit.face_normal(ring, tuple(range(count)))
            axis = max(range(3), key=lambda a: abs(normal[a]))
            u, v = {0: (1, 2), 1: (2, 0), 2: (0, 1)}[axis]
            if normal[axis] < 0:
                u, v = v, u
            base = ring_index * count
            for a, b, c in meshkit.triangulate_polygon_2d([(p[u], p[v]) for p in ring]):
                faces.append((base + a, base + b, base + c) if outward_is_forward else (base + c, base + b, base + a))
    return meshkit.Mesh(vertices, faces, name="loft")


def demo_profiles(shape="bottle"):
    """Closed profiles (3D, horizontal) for a bottle (circles), a tower (square turning into an octagon) or a
    boat hull (U-shaped sections closed at the deck)."""
    if shape == "bottle":
        radii = [(0.0, 0.40), (0.1, 0.45), (0.8, 0.45), (1.0, 0.30), (1.25, 0.14), (1.6, 0.14), (1.65, 0.17)]
        return [[(r * math.cos(2 * math.pi * k / 32), y, -r * math.sin(2 * math.pi * k / 32)) for k in range(32)]
                for y, r in radii]
    if shape == "tower":
        result = []
        for level in range(5):
            y = 0.6 * level
            sides = 4 if level < 2 else 8
            radius = 0.7 - 0.08 * level
            result.append([(radius * math.cos(2 * math.pi * k / sides + math.pi / sides), y,
                            -radius * math.sin(2 * math.pi * k / sides + math.pi / sides)) for k in range(sides)])
        return result
    if shape == "boat":
        result = []
        for station in range(7):
            x = -1.5 + 0.5 * station
            beam = 0.5 * math.sqrt(max(0.05, 1.0 - (x / 1.6) ** 2))
            depth = 0.35 * math.sqrt(max(0.1, 1.0 - (x / 1.7) ** 2))
            section = [(x, 0.3 - depth * math.sin(math.pi * k / 12), -beam * math.cos(math.pi * k / 12)) for k in range(13)]
            result.append(section)
        return result
    raise meshkit.MeshError("shape_unknown", str(shape))


def build(shape="bottle", samples=48):
    """The lofted demonstration solid with smooth normals."""
    mesh = loft(demo_profiles(shape), samples)
    mesh.normals = meshkit.vertex_normals(mesh)
    mesh.material = meshkit.material("loft", (0.50, 0.72, 0.62, 1.0))
    return mesh


def main(argv=None):
    """Command line: write the lofted solid (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
