"""Point sets on the 3-sphere S^3 (unit quaternions): three samplers and the measures that compare them.

- gaussian: four independent normal numbers, normalized (uniform by rotational symmetry of the normal law).
- hopf_grid: a Fibonacci spiral on the base sphere S^2 times evenly spaced points on each Hopf fibre. The fibre
  over a base point p is q(p) e^{it}, with q(p) the shortest rotation taking i to p, because conj by e^{it} fixes i;
  the Hopf map q -> q i conj(q) is a Riemannian submersion with fibres of equal length, so the grid is uniform.
- super_fibonacci: q_k = (r sin a, r cos a, R sin b, R cos b) with s = k + 1/2, r = sqrt(s/n), R = sqrt(1 - s/n),
  a = 2 pi s/sqrt(2), b = 2 pi s/psi and psi^4 = psi + 4 (a super-Fibonacci spiral): r^2 is uniform on [0, 1] as for
  uniform points, and two irrational turn rates spread the angles.

Measures: smallest pairwise distance, covering radius over probe points, and cap discrepancy against the exact
cap volume fraction (theta - sin(theta) cos(theta))/pi of S^3. The CLI writes the stereographic image of a set as
a glTF POINTS cloud (points beyond a radius are clipped) coloured by w.

    python three_sphere_sampling.py --method super_fibonacci --count 2000 --out s3_points.gltf
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys

import fourd

METHODS = ("gaussian", "hopf_grid", "super_fibonacci")
PSI = 1.533751168755204288118041


def gaussian(count, seed=1):
    """Uniform random unit quaternions (normalized normal vectors)."""
    generator = random.Random(seed)
    points = []
    while len(points) < count:
        vector = tuple(generator.gauss(0.0, 1.0) for _ in range(4))
        if fourd.norm(vector) > 1e-9:
            points.append(fourd.normalize(vector))
    return points


def fibonacci_sphere(count):
    """count points on S^2 by the golden-angle spiral (equal-area latitude steps)."""
    golden = math.pi * (3.0 - math.sqrt(5.0))
    points = []
    for index in range(count):
        z = 1.0 - (2.0 * index + 1.0) / count
        radius = math.sqrt(max(0.0, 1.0 - z * z))
        points.append((radius * math.cos(golden * index), radius * math.sin(golden * index), z))
    return points


def lift(base):
    """A unit quaternion q with q i conj(q) = base (the shortest rotation from i to the unit vector base)."""
    x, y, z = base
    if 1.0 + x < 1e-12:
        return (0.0, 0.0, 1.0, 0.0)
    return fourd.normalize((1.0 + x, 0.0, -z, y))


def hopf_map(quaternion):
    """q -> q i conj(q), a point of S^2."""
    image = fourd.quat_mul(fourd.quat_mul(quaternion, (0.0, 1.0, 0.0, 0.0)), fourd.quat_conjugate(quaternion))
    return image[1:]


def hopf_grid(bases, fibre):
    """bases Fibonacci points on S^2 times fibre points on each Hopf fibre q(p) e^{it} (alternate fibres shifted by
    half a step): bases * fibre unit quaternions."""
    if bases < 1 or fibre < 1:
        raise ValueError("bases and fibre are positive")
    points = []
    for base in fibonacci_sphere(bases):
        start = lift(base)
        offset = 0.5 * (len(points) // fibre % 2)
        for step in range(fibre):
            angle = 2.0 * math.pi * (step + offset) / fibre
            points.append(fourd.quat_mul(start, (math.cos(angle), math.sin(angle), 0.0, 0.0)))
    return points


def super_fibonacci(count):
    """The super-Fibonacci spiral of count unit quaternions."""
    if count < 1:
        raise ValueError("count is positive")
    root2 = math.sqrt(2.0)
    points = []
    for index in range(count):
        s = index + 0.5
        r = math.sqrt(s / count)
        big = math.sqrt(1.0 - s / count)
        alpha = 2.0 * math.pi * s / root2
        beta = 2.0 * math.pi * s / PSI
        points.append((r * math.sin(alpha), r * math.cos(alpha), big * math.sin(beta), big * math.cos(beta)))
    return points


def sample(method, count, seed=1):
    """count points from one of METHODS (hopf_grid uses the nearest fibre count to the cube root shape)."""
    if method == "gaussian":
        return gaussian(count, seed)
    if method == "super_fibonacci":
        return super_fibonacci(count)
    if method == "hopf_grid":
        fibre = max(3, int(round((count * math.pi) ** (1.0 / 3.0))))
        return hopf_grid(max(1, count // fibre), fibre)
    raise ValueError(f"method is one of {METHODS}")


def cap_fraction(theta):
    """Fraction of the volume of S^3 within angle theta of a point: (theta - sin(theta) cos(theta))/pi."""
    return (theta - math.sin(theta) * math.cos(theta)) / math.pi


def separation(points):
    """Smallest Euclidean distance between two points of the set."""
    best = math.inf
    for i in range(len(points)):
        a = points[i]
        for j in range(i + 1, len(points)):
            b = points[j]
            value = (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2 + (a[3] - b[3]) ** 2
            if value < best:
                best = value
    return math.sqrt(best)


def covering_radius(points, probes=400, seed=7):
    """Largest distance from a random probe point to its nearest sample (an estimate of the covering radius)."""
    worst = 0.0
    for probe in gaussian(probes, seed):
        nearest = min(fourd.distance(probe, point) for point in points)
        worst = max(worst, nearest)
    return worst


def cap_discrepancy(points, caps=60, seed=3):
    """Largest |empirical cap fraction - exact cap fraction| over random caps of random angular radius."""
    generator = random.Random(seed)
    worst = 0.0
    for centre in gaussian(caps, seed):
        theta = generator.uniform(0.2, 2.9)
        limit = math.cos(theta)
        inside = sum(1 for point in points if fourd.dot(point, centre) >= limit)
        worst = max(worst, abs(inside / len(points) - cap_fraction(theta)))
    return worst


def export(path, method="super_fibonacci", count=2000, clip=3.0, seed=1):
    """Write the stereographic image of a point set as a glTF POINTS cloud coloured by w."""
    points = [point for point in sample(method, count, seed)]
    kept = [point for point in points if point[3] < 0.999 and fourd.norm(fourd.stereographic(point, 1.0)) <= clip]
    images = [fourd.stereographic(point, 1.0) for point in kept]
    colours = fourd.depth_colors([point[3] for point in kept])
    document = fourd.gltf_document([dict(fourd.point_mesh(images, colours), name=f"s3_{method}", unlit=True)],
                                   generator="three_sphere_sampling.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), "clipped": len(points) - len(kept),
            **fourd.gltf_summary(document)}


def invariants():
    grid = hopf_grid(40, 12)
    bases = fibonacci_sphere(40)
    fibre_ok = all(fourd.distance(hopf_map(point), bases[index // 12]) < 1e-12 for index, point in enumerate(grid))
    chord = fourd.distance(grid[0], grid[1])
    spiral = super_fibonacci(600)
    random_set = gaussian(600)
    hemisphere = sum(1 for point in super_fibonacci(1000) if point[3] > 0.0)
    return {"unit_norms": all(abs(fourd.norm(point) - 1.0) < 1e-12 for method in METHODS
                              for point in sample(method, 300)),
            "hopf_fibres_map_to_base": fibre_ok,
            "fibre_chord_12": round(chord, 12),
            "cap_fraction_hemisphere": cap_fraction(math.pi / 2.0),
            "cap_fraction_whole": cap_fraction(math.pi),
            "super_fibonacci_hemisphere_count_1000": hemisphere,
            "super_fibonacci_better_separated": separation(spiral) > 3.0 * separation(random_set),
            "super_fibonacci_low_discrepancy": cap_discrepancy(spiral) < 0.02,
            "hopf_grid_low_discrepancy": cap_discrepancy(hopf_grid(50, 12)) < 0.03}


def controls():
    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    clustered = [fourd.normalize((1.0, 0.01 * k, 0.0, 0.0)) for k in range(300)]
    shifted = [fourd.normalize(fourd.add(point, (0.6, 0.0, 0.0, 0.0))) for point in super_fibonacci(600)]
    return {"clustered_set_fails_discrepancy": cap_discrepancy(clustered) > 0.2,
            "shifted_set_fails_discrepancy": cap_discrepancy(shifted) > 0.05,
            "unknown_method_refused": refused(lambda: sample("halton", 10)),
            "zero_count_refused": refused(lambda: super_fibonacci(0))}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="three_sphere_sampling.py",
                                     description="Write a point set on the 3-sphere, stereographically projected.")
    parser.add_argument("--method", choices=METHODS, default="super_fibonacci", help="sampler")
    parser.add_argument("--count", type=int, default=2000, help="number of points")
    parser.add_argument("--clip", type=float, default=3.0, help="drop points whose image lies beyond this radius")
    parser.add_argument("--seed", type=int, default=1, help="seed of the gaussian sampler")
    parser.add_argument("--out", required=True, help="output .gltf")
    args = parser.parse_args(argv)
    if not 1 <= args.count <= 200000 or args.clip <= 0:
        parser.error("count is 1 to 200000 and clip is positive")
    summary = export(args.out, args.method, args.count, args.clip, args.seed)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
