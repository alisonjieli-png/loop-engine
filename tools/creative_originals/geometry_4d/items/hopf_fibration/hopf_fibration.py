"""Fibres of the Hopf fibration S^3 -> S^2, drawn as linked circles after stereographic projection.

With quaternions q = a + bi + cj + dk (the point (b, c, d, a)), the Hopf map is h(q) = q i conj(q), the image of i
under the rotation q. Right multiplication by e^{it} does not change h (it fixes i under conjugation), so the
fibre over a base point p is the great circle q(p) e^{it}, with q(p) any lift of p. The first coordinate of
h(q) is |a + bi|^2 - |c + di|^2, so fibres over a circle of latitude around the x axis fill a torus, and over the
circle x = 0 they fill the Clifford torus. Any two fibres are Clifford parallel (every point of one is at the same
distance from the other) and link once. Base points sit on circles of latitude about the x axis, which keeps
every fibre away from the projection pole (0, 0, 0, 1), whose fibre lies over (1, 0, 0). The glTF holds the
fibres as tubes and, beside them, the base sphere with dots in the matching colours.

    python hopf_fibration.py --latitudes 100,130,155 --per-ring 8 --out hopf.gltf
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import fourd


def hopf_map(q):
    """h(q) = q i conj(q) for a unit quaternion q = (a, b, c, d); returns a point of S^2."""
    image = fourd.quat_mul(fourd.quat_mul(q, (0.0, 1.0, 0.0, 0.0)), fourd.quat_conjugate(q))
    return image[1:]


def lift(base):
    """A unit quaternion over the base point (the shortest rotation from i to it)."""
    x, y, z = fourd.normalize(base)
    if 1.0 + x < 1e-12:
        return (0.0, 0.0, 1.0, 0.0)
    return fourd.normalize((1.0 + x, 0.0, -z, y))


def fibre(base, samples=36):
    """Points of the fibre over a base point, as 4D points (x, y, z, w) = (b, c, d, a)."""
    start = lift(base)
    return [fourd.quaternion_to_point(fourd.quat_mul(start, (math.cos(t), math.sin(t), 0.0, 0.0)))
            for t in (2.0 * math.pi * k / samples for k in range(samples))]


def base_points(latitudes=(60.0, 90.0, 120.0), per_ring=6):
    """Base points on circles at the given angles (degrees) from the x axis, per_ring each, rings staggered."""
    points = []
    for ring, angle in enumerate(latitudes):
        if not 0.0 < angle < 180.0:
            raise ValueError("latitudes are angles strictly between 0 and 180 degrees from the x axis")
        polar = math.radians(angle)
        for step in range(per_ring):
            around = 2.0 * math.pi * (step + 0.5 * (ring % 2)) / per_ring
            points.append((math.cos(polar), math.sin(polar) * math.cos(around), math.sin(polar) * math.sin(around)))
    return points


def colour(base):
    """Hue from the angle around the x axis, brightness from the angle to it."""
    around = (math.atan2(base[2], base[1]) / (2.0 * math.pi)) % 1.0
    hue = fourd.depth_color(around)
    light = 0.55 + 0.45 * (1.0 - (base[0] + 1.0) / 2.0)
    return (hue[0] * light, hue[1] * light, hue[2] * light, 1.0)


def is_great_circle(points, tolerance=1e-9):
    """Unit points spanning a 2-plane through the origin."""
    return (all(abs(fourd.norm(point) - 1.0) <= tolerance for point in points)
            and fourd.rank(list(points), tolerance) == 2)


def is_circle_3d(points, tolerance=1e-7):
    """Coplanar 3D points at one distance from the circumcentre of the first three."""
    a, b, c = points[:3]
    ab, ac = fourd.sub(b, a), fourd.sub(c, a)
    normal = fourd.cross3(ab, ac)
    centre = fourd.add(a, fourd.scale(fourd.add(fourd.scale(fourd.cross3(normal, ab), fourd.dot(ac, ac)),
                                                fourd.scale(fourd.cross3(ac, normal), fourd.dot(ab, ab))),
                                      1.0 / (2.0 * fourd.dot(normal, normal))))
    radius = fourd.distance(centre, a)
    unit = fourd.normalize(normal)
    return all(abs(fourd.dot(fourd.sub(p, a), unit)) <= tolerance * max(1.0, radius)
               and abs(fourd.distance(p, centre) - radius) <= tolerance * max(1.0, radius) for p in points)


def linking_number(first, second):
    """Gauss linking integral of two closed 3D polygons."""
    total = 0.0
    for a0, a1 in zip(first, first[1:] + first[:1]):
        da, ma = fourd.sub(a1, a0), fourd.lerp(a0, a1, 0.5)
        for b0, b1 in zip(second, second[1:] + second[:1]):
            db = fourd.sub(b1, b0)
            r = fourd.sub(ma, fourd.lerp(b0, b1, 0.5))
            total += fourd.dot(r, fourd.cross3(da, db)) / fourd.norm(r) ** 3
    return total / (4.0 * math.pi)


def distance_spread(first, second):
    """Largest minus smallest angular distance from the points of one fibre to the great circle of another
    (0 for Clifford parallel circles)."""
    u = fourd.normalize(second[0])
    quarter = second[len(second) // 4]
    v = fourd.normalize(fourd.sub(quarter, fourd.scale(u, fourd.dot(quarter, u))))
    angles = [math.acos(max(-1.0, min(1.0, math.hypot(fourd.dot(point, u), fourd.dot(point, v))))) for point in first]
    return max(angles) - min(angles)


def meshes(latitudes=(100.0, 130.0, 155.0), per_ring=8, samples=30, radius=0.04, sides=4, inset=True):
    """Fibre tubes (stereographic images) and, optionally, the base sphere with matching dots placed to the side."""
    bases = base_points(latitudes, per_ring)
    tubes = []
    for base in bases:
        image = [fourd.stereographic(point, 1.0) for point in fibre(base, samples)]
        tubes.append(fourd.curve_tube(image, radius, sides, closed=True, colors=[colour(base)] * samples))
    result = [dict(fourd.merge_meshes(tubes), name="hopf_fibres")]
    if inset:
        reach = max(fourd.norm(p) for tube in tubes for p in tube["positions"])
        size = 0.4 * reach
        place = (1.5 * reach, 0.0, 0.0)
        sphere = dict(fourd.sphere_mesh((0.0, 0.0, 0.0), size, None, 2), name="base_sphere",
                      color=(0.7, 0.72, 0.78, 0.35), translation=place)
        dots = fourd.merge_meshes([fourd.sphere_mesh(fourd.scale(base, size * 1.04), size * 0.09, colour(base))
                                   for base in bases])
        result += [sphere, dict(dots, name="base_points", translation=place)]
    return result


def export(path, latitudes=(100.0, 130.0, 155.0), per_ring=8, samples=30, radius=0.04, sides=4, inset=True):
    document = fourd.gltf_document(meshes(latitudes, per_ring, samples, radius, sides, inset), generator="hopf_fibration.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    bases = base_points((60.0, 90.0, 120.0), 4)
    fibres = [fibre(base, 48) for base in bases]
    images = [[fourd.stereographic(point, 1.0) for point in points] for points in fibres]
    links = sorted({round(linking_number(images[i], images[j])) for i in range(0, len(images), 3)
                    for j in range(i + 1, len(images), 2)})
    equator = [point for base in base_points((90.0,), 6) for point in fibre(base, 24)]
    tilted = [point for base in base_points((60.0,), 6) for point in fibre(base, 24)]
    return {"fibres_map_to_base": all(fourd.distance(hopf_map(fourd.point_to_quaternion(point)), base) < 1e-12
                                      for base, points in zip(bases, fibres) for point in points),
            "fibres_are_great_circles": all(is_great_circle(points) for points in fibres),
            "images_are_circles": all(is_circle_3d(points) for points in images),
            "pairwise_linking_numbers": links,
            "clifford_parallel_spread": round(max(distance_spread(fibres[0], fibres[k]) for k in range(1, len(fibres))), 9),
            "equator_fibres_on_clifford_torus": all(abs(p[0] ** 2 + p[3] ** 2 - 0.5) < 1e-12 and abs(p[1] ** 2 + p[2] ** 2 - 0.5) < 1e-12
                                                    for p in equator),
            "latitude_60_torus_level": round(max(p[0] ** 2 + p[3] ** 2 - p[1] ** 2 - p[2] ** 2 for p in tilted), 12),
            "hopf_map_of_one": [round(v, 12) for v in hopf_map((1.0, 0.0, 0.0, 0.0))]}


def controls():
    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    points = fibre((0.0, 1.0, 0.0), 24)
    bent = points[:12] + [fourd.normalize(fourd.add(p, (0.0, 0.0, 0.2, 0.0))) for p in points[12:]]
    images = [fourd.stereographic(point, 1.0) for point in points]
    squeezed = [(x, 1.4 * y, z) for x, y, z in images]
    far = [fourd.add(p, (40.0, 0.0, 0.0)) for p in images]
    return {"bent_fibre_not_great_circle": not is_great_circle(bent),
            "squeezed_image_not_circle": not is_circle_3d(squeezed),
            "pole_latitude_refused": refused(lambda: base_points((0.0,), 3)),
            "separated_copy_does_not_link": round(linking_number(images, far)) == 0}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hopf_fibration.py", description="Write Hopf fibres as linked circles.")
    parser.add_argument("--latitudes", default="100,130,155",
                        help="comma-separated angles in degrees from the x axis of the base circles")
    parser.add_argument("--per-ring", type=int, default=8, help="fibres per base circle")
    parser.add_argument("--samples", type=int, default=30, help="points per fibre")
    parser.add_argument("--radius", type=float, default=0.04, help="tube radius")
    parser.add_argument("--sides", type=int, default=4, help="sides of each tube")
    parser.add_argument("--inset", choices=("on", "off"), default="on", help="draw the base sphere with coloured dots")
    parser.add_argument("--out", required=True, help="output .gltf")
    args = parser.parse_args(argv)
    try:
        latitudes = tuple(float(value) for value in args.latitudes.split(","))
    except ValueError:
        parser.error("latitudes are numbers separated by commas")
    if not 1 <= args.per_ring <= 64 or not 8 <= args.samples <= 720 or args.radius <= 0 or args.sides < 3:
        parser.error("per-ring 1 to 64, samples 8 to 720, radius positive, sides 3 or more")
    try:
        summary = export(args.out, latitudes, args.per_ring, args.samples, args.radius, args.sides, args.inset == "on")
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
