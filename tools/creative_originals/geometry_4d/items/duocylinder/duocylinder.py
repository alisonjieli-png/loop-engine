"""The duocylinder {x^2 + y^2 <= r1^2, z^2 + w^2 <= r2^2}: measures, slices and an exact diagonal slice sweep.

Hypervolume pi^2 r1^2 r2^2 (a product of two disks). Its boundary is two solid tori, a circle of length 2 pi r1
times a disk of area pi r2^2 and the reverse, so its 3-volume is 2 pi^2 r1 r2 (r1 + r2); they meet on the flat ridge
torus of area 4 pi^2 r1 r2. A slice w = c is a solid cylinder (disk r1, height 2 sqrt(r2^2 - c^2)); integrating those
volumes over c gives the hypervolume again (Cavalieri). The diagonal slice x + z = k of the unit duocylinder is
{x^2 + y^2 <= 1, (k - x)^2 + w^2 <= 1}: two unit cylinders with perpendicular axes k apart, so at k = 0 it is a
Steinmetz bicylinder, stretched by sqrt(2) along the slice's first axis (volume 16 sqrt(2)/3). Each cylinder face is
ruled (straight along w or y), so four strips over a Chebyshev grid in x give an exact-edged mesh whose topology
stays fixed for every k; the CLI writes the sweep as glTF morph targets.

    python duocylinder.py --frames 12 --out duocylinder_sweep.gltf
"""
from __future__ import annotations

import argparse
import json
import math
import sys

import fourd

ROOT2 = math.sqrt(2.0)


def contains(p, r1=1.0, r2=1.0):
    """True when the point lies in the duocylinder."""
    return p[0] ** 2 + p[1] ** 2 <= r1 * r1 and p[2] ** 2 + p[3] ** 2 <= r2 * r2


def hypervolume(r1=1.0, r2=1.0):
    """pi^2 r1^2 r2^2."""
    return math.pi ** 2 * r1 * r1 * r2 * r2


def boundary_volume(r1=1.0, r2=1.0):
    """3-volume of the boundary: 2 pi^2 r1 r2 (r1 + r2)."""
    return 2.0 * math.pi ** 2 * r1 * r2 * (r1 + r2)


def ridge_area(r1=1.0, r2=1.0):
    """Area of the flat ridge torus where the two solid tori meet: (2 pi r1)(2 pi r2)."""
    return 4.0 * math.pi ** 2 * r1 * r2


def _simpson(function, low, high, steps=400):
    width = (high - low) / steps
    total = function(low) + function(high)
    for index in range(1, steps):
        total += (4 if index % 2 else 2) * function(low + index * width)
    return total * width / 3.0


def axis_slice_volume(c, r1=1.0, r2=1.0):
    """Volume of the slice w = c: pi r1^2 times 2 sqrt(r2^2 - c^2)."""
    if abs(c) > r2:
        return 0.0
    return math.pi * r1 * r1 * 2.0 * math.sqrt(r2 * r2 - c * c)


def cavalieri_axis(r1=1.0, r2=1.0):
    """Integral of the axis slice volumes over c = r2 sin(t) (smooth integrand, Simpson's rule)."""
    return _simpson(lambda t: axis_slice_volume(r2 * math.sin(t), r1, r2) * r2 * math.cos(t), -math.pi / 2.0, math.pi / 2.0)


def _overlap(k):
    low, high = max(-1.0, k - 1.0), min(1.0, k + 1.0)
    if high <= low:
        raise ValueError("the diagonal offset k lies in (-2, 2)")
    return low, high


def diagonal_slice_volume(k, steps=800):
    """Exact-to-quadrature volume of the slice x + z = k of the unit duocylinder:
    sqrt(2) times the integral over x of 4 sqrt(1 - x^2) sqrt(1 - (k - x)^2)."""
    low, high = _overlap(k)
    middle, half = (low + high) / 2.0, (high - low) / 2.0

    def integrand(t):
        x = middle - half * math.cos(t)
        return 4.0 * math.sqrt(max(0.0, 1.0 - x * x)) * math.sqrt(max(0.0, 1.0 - (k - x) ** 2)) * half * math.sin(t)

    return ROOT2 * _simpson(integrand, 0.0, math.pi, steps)


def cavalieri_diagonal(steps=800):
    """Integral of the diagonal slice volumes over the offset c = k/sqrt(2), with k = 2 sin(t) (should equal pi^2)."""
    def integrand(t):
        k = 2.0 * math.sin(t)
        return diagonal_slice_volume(k, 400) * 2.0 * math.cos(t) / ROOT2 if abs(k) < 2.0 - 1e-12 else 0.0
    return _simpson(integrand, -math.pi / 2.0, math.pi / 2.0, steps)


def diagonal_slice(k, segments=24):
    """(positions, indices) of the slice x + z = k: four ruled strips in slice coordinates ((2x - k)/sqrt 2, y, w)."""
    low, high = _overlap(k)
    middle, half = (low + high) / 2.0, (high - low) / 2.0
    positions, indices = [], []
    for patch in range(4):
        base = len(positions)
        for j in range(segments + 1):
            t = middle - half * math.cos(math.pi * j / segments)
            for s in (-1.0, 1.0):
                if patch < 2:
                    x = t
                    y = (1.0 if patch == 0 else -1.0) * math.sqrt(max(0.0, 1.0 - x * x))
                    w = s * math.sqrt(max(0.0, 1.0 - (k - x) ** 2))
                else:
                    z = t
                    x = k - z
                    w = (1.0 if patch == 2 else -1.0) * math.sqrt(max(0.0, 1.0 - z * z))
                    y = s * math.sqrt(max(0.0, 1.0 - x * x))
                positions.append(((2.0 * x - k) / ROOT2, y, w))
        for j in range(segments):
            a, b, c, d = base + 2 * j, base + 2 * j + 1, base + 2 * j + 3, base + 2 * j + 2
            if patch in (0, 2):
                indices += [a, b, c, a, c, d]
            else:
                indices += [a, c, b, a, d, c]
    return positions, indices


def mesh_volume(positions, indices):
    """Signed volume enclosed by a triangle mesh (positive when normals point outward)."""
    return sum(fourd.dot(positions[indices[i]], fourd.cross3(positions[indices[i + 1]], positions[indices[i + 2]]))
               for i in range(0, len(indices), 3)) / 6.0


def _normals(positions, indices):
    accumulated = [[0.0, 0.0, 0.0] for _ in positions]
    for start in range(0, len(indices), 3):
        a, b, c = indices[start:start + 3]
        normal = fourd.cross3(fourd.sub(positions[b], positions[a]), fourd.sub(positions[c], positions[a]))
        for vertex in (a, b, c):
            for axis in range(3):
                accumulated[vertex][axis] += normal[axis]
    return [fourd.normalize(v) if fourd.norm(v) > 1e-15 else (0.0, 1.0, 0.0) for v in accumulated]


def export(path, frames=12, segments=24, reach=1.85, duration=6.0):
    """The diagonal slice sweep k from -reach to +reach as glTF morph targets (positions and normals)."""
    offsets = [-reach + 2.0 * reach * index / (frames - 1) for index in range(frames)]
    poses, normals = [], []
    for k in offsets:
        positions, indices = diagonal_slice(k, segments)
        poses.append(positions)
        normals.append(_normals(positions, indices))
    patch_colours = [(0.98, 0.62, 0.25, 1.0), (0.93, 0.42, 0.3, 1.0), (0.3, 0.6, 0.98, 1.0), (0.36, 0.86, 0.8, 1.0)]
    colours = [patch_colours[index // (2 * (segments + 1))] for index in range(len(poses[0]))]
    mesh = {"positions": poses[0], "normals": normals[0], "indices": indices, "colors": colours, "mode": 4,
            "name": "duocylinder_diagonal_slice"}
    times = [duration * index / (frames - 1) for index in range(frames)]
    animated, animation = fourd.morph_animation(mesh, poses, times, "diagonal_sweep", 0, normals)
    document = fourd.gltf_document([animated], animations=[animation], generator="duocylinder.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def invariants():
    exact = 16.0 * ROOT2 / 3.0
    positions, indices = diagonal_slice(0.0, 64)
    near, near_indices = diagonal_slice(1.0, 64)
    return {"hypervolume": hypervolume(), "hypervolume_cavalieri_axis": cavalieri_axis(),
            "hypervolume_cavalieri_diagonal": cavalieri_diagonal(),
            "boundary_volume": boundary_volume(), "ridge_area": ridge_area(),
            "axis_slice_volume_at_0": axis_slice_volume(0.0),
            "diagonal_slice_volume_at_0": diagonal_slice_volume(0.0), "steinmetz_volume_times_root2": exact,
            "diagonal_mesh_matches_at_0": abs(mesh_volume(positions, indices) - exact) / exact < 0.01,
            "diagonal_mesh_matches_at_1": abs(mesh_volume(near, near_indices) - diagonal_slice_volume(1.0))
            / diagonal_slice_volume(1.0) < 0.01,
            "slice_points_inside": all(contains(((p[0] * ROOT2 + 0.6) / 2.0, p[1], 0.6 - (p[0] * ROOT2 + 0.6) / 2.0, p[2]))
                                       or _on_boundary(((p[0] * ROOT2 + 0.6) / 2.0, p[1], 0.6 - (p[0] * ROOT2 + 0.6) / 2.0, p[2]))
                                       for p in diagonal_slice(0.6, 16)[0]),
            "centre_inside": contains((0.0, 0.0, 0.0, 0.0))}


def _on_boundary(p, tolerance=1e-9):
    return p[0] ** 2 + p[1] ** 2 <= 1.0 + tolerance and p[2] ** 2 + p[3] ** 2 <= 1.0 + tolerance


def controls():
    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    positions, indices = diagonal_slice(0.0, 32)
    flipped = indices[:]
    for start in range(0, len(flipped) // 4, 3):
        flipped[start + 1], flipped[start + 2] = flipped[start + 2], flipped[start + 1]
    exact = 16.0 * ROOT2 / 3.0
    return {"outside_point_not_contained": not contains((0.9, 0.9, 0.0, 0.0)),
            "offset_beyond_range_refused": refused(lambda: diagonal_slice(2.5)),
            "flipped_strip_breaks_volume": abs(mesh_volume(positions, flipped) - exact) / exact > 0.05,
            "wrong_radius_breaks_hypervolume": abs(hypervolume(1.0, 1.1) - math.pi ** 2) > 0.1}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="duocylinder.py",
                                     description="Write the diagonal slice sweep of the unit duocylinder.")
    parser.add_argument("--frames", type=int, default=12, help="keyframes from -reach to +reach")
    parser.add_argument("--segments", type=int, default=24, help="grid steps along x on each strip")
    parser.add_argument("--reach", type=float, default=1.85, help="largest |k| of the slice x + z = k (below 2)")
    parser.add_argument("--duration", type=float, default=6.0, help="seconds for the sweep")
    parser.add_argument("--out", required=True, help="output .gltf")
    args = parser.parse_args(argv)
    if not 2 <= args.frames <= 240 or args.segments < 2 or not 0 < args.reach < 2 or args.duration <= 0:
        parser.error("frames 2 to 240, segments 2 or more, reach in (0, 2), duration positive")
    summary = export(args.out, args.frames, args.segments, args.reach, args.duration)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
