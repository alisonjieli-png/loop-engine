"""The Clifford torus: the flat torus (cos u, sin u, cos v, sin v)/sqrt(2) inside the unit 3-sphere.

Its tangent vectors are orthogonal with squared length 1/2, so the induced metric is (u, v) -> (du^2 + dv^2)/2: flat,
with area (2 pi)^2/2 = 2 pi^2. It splits S^3 into two congruent solid tori; in Hopf coordinates
(cos eta e^{i a}, sin eta e^{i b}) the volume element is sin(eta) cos(eta) da db deta, so each side
(eta < pi/4 and eta > pi/4) has volume pi^2, half of 2 pi^2. Its two core circles (z = w = 0 and x = y = 0) link once.
Stereographic projection from (0, 0, 0, 1) maps it to a torus of revolution with major radius sqrt(2) and minor
radius 1. A rotation in a plane without w (xy, xz, yz) keeps every point away from the pole; in the xz plane the
image moves through a loop of Dupin cyclides and returns after 2 pi. The CLI writes that loop as glTF morph targets
(positions and normals).

    python clifford_torus.py --plane xz --frames 16 --out clifford_loop.gltf
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import fourd

ROOT_HALF = math.sqrt(0.5)


def point(u, v):
    """(cos u, sin u, cos v, sin v)/sqrt(2)."""
    return (ROOT_HALF * math.cos(u), ROOT_HALF * math.sin(u), ROOT_HALF * math.cos(v), ROOT_HALF * math.sin(v))


def metric(u, v):
    """(E, F, G) of the induced metric, from the exact partial derivatives."""
    du = (-ROOT_HALF * math.sin(u), ROOT_HALF * math.cos(u), 0.0, 0.0)
    dv = (0.0, 0.0, -ROOT_HALF * math.sin(v), ROOT_HALF * math.cos(v))
    return fourd.dot(du, du), fourd.dot(du, dv), fourd.dot(dv, dv)


def area():
    """Integral of sqrt(EG - F^2) over the parameter square (the integrand is constant)."""
    e, f, g = metric(0.3, 1.1)
    return (2.0 * math.pi) ** 2 * math.sqrt(e * g - f * f)


def solid_torus_volumes(steps=200):
    """Volumes of the two sides, integrating sin(eta) cos(eta) (2 pi)^2 by Simpson's rule over [0, pi/4] and [pi/4, pi/2]."""
    def simpson(low, high):
        width = (high - low) / steps
        total = 0.0
        for index in range(steps + 1):
            eta = low + index * width
            weight = 1 if index in (0, steps) else (4 if index % 2 else 2)
            total += weight * math.sin(eta) * math.cos(eta)
        return total * width / 3.0 * (2.0 * math.pi) ** 2
    return simpson(0.0, math.pi / 4.0), simpson(math.pi / 4.0, math.pi / 2.0)


def is_clifford(p, tolerance=1e-12):
    """On the unit 3-sphere with |(x, y)| = |(z, w)| = 1/sqrt(2)."""
    return (abs(math.hypot(p[0], p[1]) - ROOT_HALF) <= tolerance and abs(math.hypot(p[2], p[3]) - ROOT_HALF) <= tolerance)


def stereographic_from(p, pole):
    """Stereographic projection of a unit vector from a unit pole, in the pole's hyperplane basis."""
    unit = fourd.normalize(pole)
    depth = 1.0 - fourd.dot(p, unit)
    if depth <= 1e-12:
        raise ValueError("point at the projection pole")
    return tuple(fourd.dot(p, axis) / depth for axis in fourd.hyperplane_basis(unit))


def core_linking(samples=160):
    """Gauss linking number of the two core circles after projection from a pole on neither circle."""
    pole = (0.5, 0.5, 0.5, 0.5)
    first = [stereographic_from((math.cos(t), math.sin(t), 0.0, 0.0), pole)
             for t in (2.0 * math.pi * k / samples for k in range(samples))]
    second = [stereographic_from((0.0, 0.0, math.cos(t), math.sin(t)), pole)
              for t in (2.0 * math.pi * k / samples for k in range(samples))]
    total = 0.0
    for a0, a1 in zip(first, first[1:] + first[:1]):
        da, ma = fourd.sub(a1, a0), fourd.lerp(a0, a1, 0.5)
        for b0, b1 in zip(second, second[1:] + second[:1]):
            db = fourd.sub(b1, b0)
            r = fourd.sub(ma, fourd.lerp(b0, b1, 0.5))
            total += fourd.dot(r, fourd.cross3(da, db)) / fourd.norm(r) ** 3
    return total / (4.0 * math.pi)


def image_radii(samples=720):
    """(major, minor) radii of the stereographic image torus, from its widest and narrowest circles."""
    distances = [math.hypot(*fourd.stereographic(point(0.0, 2.0 * math.pi * k / samples), 1.0)[:2])
                 for k in range(samples)]
    return (max(distances) + min(distances)) / 2.0, (max(distances) - min(distances)) / 2.0


def grid(columns=24, rows=10):
    """(parameter pairs, triangle indices) of a periodic grid on the torus."""
    pairs = [(2.0 * math.pi * j / columns, 2.0 * math.pi * i / rows) for i in range(rows) for j in range(columns)]
    indices = []
    for i in range(rows):
        for j in range(columns):
            a, b = i * columns + j, i * columns + (j + 1) % columns
            c, d = ((i + 1) % rows) * columns + (j + 1) % columns, ((i + 1) % rows) * columns + j
            indices += [a, b, c, a, c, d]
    return pairs, indices


def _normals(positions, indices):
    accumulated = [[0.0, 0.0, 0.0] for _ in positions]
    for start in range(0, len(indices), 3):
        a, b, c = indices[start:start + 3]
        normal = fourd.cross3(fourd.sub(positions[b], positions[a]), fourd.sub(positions[c], positions[a]))
        for vertex in (a, b, c):
            for axis in range(3):
                accumulated[vertex][axis] += normal[axis]
    return [fourd.normalize(vector) for vector in accumulated]


def frames(plane="xz", count=16, columns=24, rows=10):
    """Stereographic images of the rotated torus for angles 2 pi k/count, k = 0..count (the last equals the first)."""
    if "w" in plane:
        raise ValueError("rotation planes containing w move points onto the projection pole; use xy, xz or yz")
    pairs, indices = grid(columns, rows)
    poses, normals = [], []
    for k in range(count + 1):
        rotation = fourd.plane_rotation(plane, 2.0 * math.pi * k / count)
        positions = [fourd.stereographic(fourd.matvec(rotation, point(u, v)), 1.0) for u, v in pairs]
        poses.append(positions)
        normals.append(_normals(positions, indices))
    return pairs, indices, poses, normals


def export(path, plane="xz", count=16, columns=24, rows=10, duration=8.0):
    """Write the looping rotation as glTF morph targets (positions and normals), coloured by u and banded by v."""
    pairs, indices, poses, normals = frames(plane, count, columns, rows)
    colours = []
    for u, v in pairs:
        base = fourd.depth_color(u / (2.0 * math.pi))
        shade = 0.72 + 0.28 * math.cos(3.0 * v)
        colours.append((base[0] * shade, base[1] * shade, base[2] * shade, 1.0))
    mesh = {"positions": poses[0], "normals": normals[0], "indices": indices, "colors": colours, "mode": 4,
            "name": "clifford_torus"}
    times = [duration * k / count for k in range(count + 1)]
    animated, animation = fourd.morph_animation(mesh, poses, times, f"rotate_{plane}", 0, normals)
    document = fourd.gltf_document([animated], animations=[animation], generator="clifford_torus.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    pairs, _indices = grid(16, 8)
    first, second = solid_torus_volumes()
    major, minor = image_radii()
    rotated = {fourd.point_key(fourd.matvec(fourd.plane_rotation("xy", 2.0 * math.pi / 16), point(u, v)), 9)
               for u, v in pairs}
    original = {fourd.point_key(point(u, v), 9) for u, v in pairs}
    _p, _i, poses, _n = frames("xz", 8, 12, 6)
    loop = max(fourd.distance(a, b) for a, b in zip(poses[0], poses[-1]))
    return {"on_clifford_torus": all(is_clifford(point(u, v)) for u, v in pairs),
            "induced_metric": [round(value, 15) for value in metric(0.7, 2.1)],
            "area": area(), "solid_torus_volumes": [first, second],
            "image_radii": [round(major, 9), round(minor, 9)],
            "core_linking_number": round(core_linking()),
            "xy_rotation_maps_grid_to_itself": rotated == original,
            "xz_loop_closes": loop < 1e-12}


def controls():
    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    skewed = (0.6 * math.cos(0.4), 0.6 * math.sin(0.4), 0.8 * math.cos(1.0), 0.8 * math.sin(1.0))
    return {"pole_plane_refused": refused(lambda: frames("xw", 4, 8, 4)),
            "unequal_radii_not_clifford": abs(fourd.norm(skewed) - 1.0) < 1e-12 and not is_clifford(skewed),
            "pole_point_refused": refused(lambda: stereographic_from((0.5, 0.5, 0.5, 0.5), (0.5, 0.5, 0.5, 0.5))),
            "separate_circles_do_not_link": round(_unlinked()) == 0}


def _unlinked(samples=120):
    pole = (0.5, 0.5, 0.5, 0.5)
    first = [stereographic_from(fourd.normalize((math.cos(t), math.sin(t), 0.0, 3.0)), pole)
             for t in (2.0 * math.pi * k / samples for k in range(samples))]
    second = [stereographic_from(fourd.normalize((math.cos(t), math.sin(t), 0.0, -3.0)), pole)
              for t in (2.0 * math.pi * k / samples for k in range(samples))]
    total = 0.0
    for a0, a1 in zip(first, first[1:] + first[:1]):
        da, ma = fourd.sub(a1, a0), fourd.lerp(a0, a1, 0.5)
        for b0, b1 in zip(second, second[1:] + second[:1]):
            db = fourd.sub(b1, b0)
            r = fourd.sub(ma, fourd.lerp(b0, b1, 0.5))
            total += fourd.dot(r, fourd.cross3(da, db)) / fourd.norm(r) ** 3
    return total / (4.0 * math.pi)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="clifford_torus.py", description="Write the Clifford torus turning in 4D.")
    parser.add_argument("--plane", choices=("xy", "xz", "yz"), default="xz", help="rotation plane (planes with w would hit the pole)")
    parser.add_argument("--frames", type=int, default=16, help="keyframes per loop")
    parser.add_argument("--columns", type=int, default=24, help="grid steps along u")
    parser.add_argument("--rows", type=int, default=10, help="grid steps along v")
    parser.add_argument("--duration", type=float, default=8.0, help="seconds per loop")
    parser.add_argument("--out", required=True, help="output .gltf")
    args = parser.parse_args(argv)
    if not 2 <= args.frames <= 240 or args.columns < 3 or args.rows < 3 or args.duration <= 0:
        parser.error("frames 2 to 240, columns and rows 3 or more, duration positive")
    summary = export(args.out, args.plane, args.frames, args.columns, args.rows, args.duration)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
