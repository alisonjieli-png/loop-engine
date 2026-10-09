"""Rotations of 4-space as pairs of unit quaternions: p -> l p conj(r), with p = w + xi + yj + zk.

Every rotation of R^4 has exactly two such pairs, (l, r) and (-l, -r) (the double cover S^3 x S^3 -> SO(4)).
Decomposition: R(1) = l conj(r) and, for x in {i, j, k}, R(x) conj(R(1)) = l x conj(l), a 3D rotation of the
imaginary quaternions from which l is read (Shepperd's method); then r = conj(R(1)) l. With l = cos(phi_l) + ...
and r = cos(phi_r) + ..., the plane angles are phi_l + phi_r and |phi_l - phi_r|: r = 1 gives a left-isoclinic
rotation (every vector turns by phi_l), l = r gives a 3D rotation fixing the w axis. Geodesic interpolation is
slerp on both quaternions after choosing the shorter of the two lifts. The CLI writes two 24-cells side by side,
one under a left-isoclinic and one under a right-isoclinic loop, as a glTF morph animation.

    python quaternion_pair_rotations.py --angle-rate 1 --out isoclinic_pair.gltf
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import sys

import fourd


def compose(left, right):
    """The 4x4 matrix of p -> left p conj(right) for unit quaternions (refused when not unit)."""
    for quaternion in (left, right):
        if abs(fourd.norm(quaternion) - 1.0) > 1e-9:
            raise ValueError("left and right are unit quaternions")
    return fourd.quaternion_pair_matrix(left, fourd.quat_conjugate(right))


def quaternion_from_rotation3(matrix):
    """The unit quaternion q (scalar first, non-negative where possible) with v -> q v conj(q) equal to the 3x3 matrix."""
    m = matrix
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        q = (s / 4.0, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2.0
        q = ((m[2][1] - m[1][2]) / s, s / 4.0, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2.0
        q = ((m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, s / 4.0, (m[1][2] + m[2][1]) / s)
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2.0
        q = ((m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, s / 4.0)
    return fourd.normalize(q)


def decompose(rotation):
    """(l, r) with rotation p = l p conj(r); l is chosen with a non-negative scalar part (the other pair is (-l, -r))."""
    if not fourd.is_rotation(rotation, 1e-8):
        raise ValueError("not a rotation: orthogonal with determinant +1 is required")
    image_one = fourd.point_to_quaternion(fourd.matvec(rotation, (0.0, 0.0, 0.0, 1.0)))
    columns = []
    for axis in range(3):
        point = [0.0] * 4
        point[axis] = 1.0
        turned = fourd.quat_mul(fourd.point_to_quaternion(fourd.matvec(rotation, point)),
                                fourd.quat_conjugate(image_one))
        columns.append(turned[1:])
    left = quaternion_from_rotation3(fourd.transpose(columns))
    right = fourd.quat_mul(fourd.quat_conjugate(image_one), left)
    if left[0] < 0.0:
        left, right = fourd.scale(left, -1.0), fourd.scale(right, -1.0)
    return left, fourd.normalize(right)


def half_angle(quaternion):
    """phi in [0, pi] with quaternion = cos(phi) + sin(phi) u."""
    return math.atan2(fourd.norm(quaternion[1:]), quaternion[0])


def pair_angles(left, right):
    """The two plane angles (alpha >= beta) in [0, pi] of p -> l p conj(r)."""
    a, b = half_angle(left), half_angle(right)
    first, second = a + b, abs(a - b)
    if first > math.pi:
        first = 2.0 * math.pi - first
    return tuple(sorted((first, second), reverse=True))


def classify(left, right, tolerance=1e-9):
    """identity, left_isoclinic (r = +-1), right_isoclinic (l = +-1), simple (equal half angles) or double."""
    a, b = half_angle(left), half_angle(right)
    a, b = min(a, math.pi - a), min(b, math.pi - b)
    if a <= tolerance and b <= tolerance:
        return "identity"
    if b <= tolerance:
        return "left_isoclinic"
    if a <= tolerance:
        return "right_isoclinic"
    if abs(a - b) <= tolerance:
        return "simple"
    return "double"


def slerp(q0, q1, t):
    """Spherical linear interpolation of unit quaternions along the arc from q0 to q1 (no sign flipping)."""
    cosine = max(-1.0, min(1.0, fourd.dot(q0, q1)))
    angle = math.acos(cosine)
    if angle < 1e-12:
        return tuple(q0)
    s0 = math.sin((1.0 - t) * angle) / math.sin(angle)
    s1 = math.sin(t * angle) / math.sin(angle)
    return fourd.normalize(fourd.add(fourd.scale(q0, s0), fourd.scale(q1, s1)))


def interpolate(start, end, t):
    """Geodesic in SO(4): slerp both quaternions, using the lift of `end` closer to the lift of `start`."""
    l0, r0 = decompose(start)
    l1, r1 = decompose(end)
    direct = math.acos(max(-1.0, min(1.0, fourd.dot(l0, l1)))) ** 2 + math.acos(max(-1.0, min(1.0, fourd.dot(r0, r1)))) ** 2
    flipped = math.acos(max(-1.0, min(1.0, -fourd.dot(l0, l1)))) ** 2 + math.acos(max(-1.0, min(1.0, -fourd.dot(r0, r1)))) ** 2
    if flipped < direct:
        l1, r1 = fourd.scale(l1, -1.0), fourd.scale(r1, -1.0)
    return compose(slerp(l0, l1, t), slerp(r0, r1, t))


def isoclinic(angle, axis=(1.0, 0.0, 0.0), side="left"):
    """The isoclinic rotation turning every vector by `angle`: multiplication by cos(angle) + sin(angle) axis."""
    unit = fourd.normalize(axis)
    quaternion = (math.cos(angle),) + fourd.scale(unit, math.sin(angle))
    one = (1.0, 0.0, 0.0, 0.0)
    return compose(quaternion, one) if side == "left" else compose(one, fourd.quat_conjugate(quaternion))


def _cell16():
    points = []
    for axis in range(4):
        for sign in (1.0, -1.0):
            points.append(tuple(sign if index == axis else 0.0 for index in range(4)))
    return points, fourd.edges_by_length(points)


def export(path, angle_rate=1, count=28, eye=2.6, duration=6.0, gap=2.4, style="tubes", radius=0.03):
    """Two 16-cells, left- and right-isoclinic loops of angle_rate turns, as one glTF with two animated meshes
    (unlit three-sided tubes, positions only, or LINES)."""
    points, edges = _cell16()
    colours = fourd.depth_colors([point[3] for point in points])
    times = [duration * index / count for index in range(count + 1)]
    meshes, channels = [], []
    for node, (side, offset) in enumerate((("left", -gap / 2.0), ("right", gap / 2.0))):
        poses = []
        for index in range(count + 1):
            rotation = isoclinic(2.0 * math.pi * angle_rate * index / count, (0.0, 0.0, 1.0), side)
            poses.append(fourd.project_points(fourd.rotate_points(rotation, points), "perspective", eye_distance=eye))
        if style == "tubes":
            shapes = [fourd.tube_mesh(pose, edges, radius, 3, colours) for pose in poses]
            mesh, poses = dict(shapes[0], normals=None), [shape["positions"] for shape in shapes]
        elif style == "lines":
            mesh = fourd.line_mesh(poses[0], edges, colours)
        else:
            raise ValueError("style is tubes or lines")
        mesh = dict(mesh, name=f"{side}_isoclinic", unlit=True, translation=(offset, 0.0, 0.0))
        animated, animation = fourd.morph_animation(mesh, poses, times, "isoclinic_loops", node)
        meshes.append(animated)
        channels += animation["channels"]
    document = fourd.gltf_document(meshes, animations=[{"name": "isoclinic_loops", "channels": channels}],
                                   generator="quaternion_pair_rotations.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), **fourd.gltf_summary(document)}


def rotations():
    """A few compositions and interpolations, checked by the package tests."""
    left = fourd.normalize((0.3, 0.5, -0.2, 0.7))
    right = fourd.normalize((0.9, -0.1, 0.3, 0.2))
    return [compose(left, right), interpolate(fourd.identity(4), compose(left, right), 0.3), isoclinic(0.7)]


def _difference(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(4) for j in range(4))


def invariants():
    sampler = random.Random(11)
    roundtrip, trace_error = 0.0, 0.0
    for _ in range(60):
        left = fourd.normalize(tuple(sampler.gauss(0.0, 1.0) for _ in range(4)))
        right = fourd.normalize(tuple(sampler.gauss(0.0, 1.0) for _ in range(4)))
        matrix = compose(left, right)
        again = compose(*decompose(matrix))
        roundtrip = max(roundtrip, _difference(again, matrix))
        alpha, beta = pair_angles(left, right)
        trace_error = max(trace_error, abs(math.cos(alpha) + math.cos(beta) - sum(matrix[i][i] for i in range(4)) / 2.0))
    left = fourd.normalize((0.3, 0.5, -0.2, 0.7))
    right = fourd.normalize((0.9, -0.1, 0.3, 0.2))
    matrix = compose(left, right)
    flipped = compose(fourd.scale(left, -1.0), right)
    left_only, right_only = compose(left, (1.0, 0.0, 0.0, 0.0)), compose((1.0, 0.0, 0.0, 0.0), right)
    half = interpolate(fourd.identity(4), matrix, 0.5)
    spin = isoclinic(0.6)
    moves = [fourd.angle_between(point, fourd.matvec(spin, point)) for point in ((1, 0, 0, 0), (0.3, -1.0, 2.0, 0.5))]
    turn = fourd.quat_from_axis_angle((0.0, 0.0, 1.0), 0.8)
    return {"decompose_roundtrip": roundtrip < 1e-12, "pair_angles_match_trace": trace_error < 1e-12,
            "double_cover_same_matrix": _difference(compose(fourd.scale(left, -1.0), fourd.scale(right, -1.0)), matrix) < 1e-14,
            "one_sign_flip_negates": _difference(flipped, tuple(tuple(-v for v in row) for row in matrix)) < 1e-14,
            "left_right_commute": _difference(fourd.matmul(left_only, right_only), fourd.matmul(right_only, left_only)) < 1e-14,
            "isoclinic_moves_every_vector": [round(value, 12) for value in moves],
            "slerp_midpoint_squared": _difference(fourd.matmul(half, half), matrix) < 1e-12,
            "classes": [classify((1.0, 0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0)), classify(turn, turn),
                        classify(turn, (1.0, 0.0, 0.0, 0.0)), classify((1.0, 0.0, 0.0, 0.0), turn), classify(left, right)],
            "conjugation_fixes_w": [round(v, 12) for v in fourd.matvec(compose(turn, turn), (0.0, 0.0, 0.0, 1.0))],
            "conjugation_turns_xy": [round(v, 12) for v in pair_angles(turn, turn)]}


def controls():
    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    stretched = tuple(tuple(1.05 * value for value in row) for row in fourd.identity(4))
    mirror = ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, -1.0, 0.0), (0.0, 0.0, 0.0, 1.0))
    left = fourd.normalize((0.3, 0.5, -0.2, 0.7))
    right = fourd.normalize((0.9, -0.1, 0.3, 0.2))
    return {"stretched_matrix_refused": refused(lambda: decompose(stretched)),
            "reflection_refused": refused(lambda: decompose(mirror)),
            "non_unit_quaternion_refused": refused(lambda: compose((2.0, 0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0))),
            "swapped_pair_is_another_rotation": _difference(compose(right, left), compose(left, right)) > 1e-3}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="quaternion_pair_rotations.py",
                                     description="Write left- and right-isoclinic 24-cell loops as a glTF animation.")
    parser.add_argument("--angle-rate", type=int, default=1, help="full isoclinic turns per loop (integer, 1 or more)")
    parser.add_argument("--frames", type=int, default=28, help="keyframes per loop")
    parser.add_argument("--style", choices=("tubes", "lines"), default="tubes", help="unlit three-sided tubes or LINES")
    parser.add_argument("--radius", type=float, default=0.03, help="tube radius (circumradius is 1)")
    parser.add_argument("--eye", type=float, default=2.6, help="4D eye distance (circumradius 1)")
    parser.add_argument("--duration", type=float, default=6.0, help="seconds per loop")
    parser.add_argument("--gap", type=float, default=2.4, help="distance between the two models")
    parser.add_argument("--out", required=True, help="output .gltf")
    args = parser.parse_args(argv)
    if args.angle_rate < 1 or not 4 <= args.frames <= 720 or args.eye <= 1.0 or args.duration <= 0:
        parser.error("angle rate is 1 or more, frames 4 to 720, eye above 1, duration positive")
    if args.radius <= 0:
        parser.error("radius is positive")
    summary = export(args.out, args.angle_rate, args.frames, args.eye, args.duration, args.gap, args.style, args.radius)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
