"""4D rotation matrices: exponential, logarithm, invariant planes and geodesic interpolation.

A rotation of 4-space turns two absolutely orthogonal planes by angles alpha and beta. Its generator is a 4x4
skew-symmetric matrix A with A^2 having eigenvalues -a^2 and -b^2 (each twice); a^2 + b^2 = -tr(A^2)/2 and
a b = Pf(A) = A01 A23 - A02 A13 + A03 A12. Because A^4 + (a^2 + b^2) A^2 + a^2 b^2 = 0, the exponential is a cubic
in A: exp(A) = c0 + c1 A + c2 A^2 + c3 A^3 with
    c0 = (a^2 cos b - b^2 cos a)/(a^2 - b^2)    c1 = (a^2 sin(b)/b - b^2 sin(a)/a)/(a^2 - b^2)
    c2 = (cos b - cos a)/(a^2 - b^2)            c3 = (sin(b)/b - sin(a)/a)/(a^2 - b^2)
and cos a + A sin(a)/a when a = b (isoclinic). The logarithm reads cos(alpha) and cos(beta) from tr(R) and
tr(R^2), splits the symmetric part (R + R^T)/2 into the two plane projectors, and divides the skew part
(R - R^T)/2 by sin(angle) on each plane. Geodesic interpolation is R0 exp(t log(R0^T R1)). The CLI writes a
seamless glTF loop of a polytope under a one-parameter rotation group exp(t A).

    python rotation_exp_log.py --rates xw=1,yz=2 --polytope tesseract --out tesseract_loop.gltf
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import sys

import fourd

EPSILON = 1e-10


def generator(rates):
    """The skew-symmetric matrix of plane rates ("xw=1,yz=2" or [(plane, rate)]); exp(t E_xy) turns x toward y."""
    pairs = fourd.parse_rotation(rates) if isinstance(rates, str) else list(rates)
    matrix = [[0.0] * 4 for _ in range(4)]
    for plane, rate in pairs:
        first, second = fourd.AXES.index(plane[0]), fourd.AXES.index(plane[1])
        matrix[second][first] += rate
        matrix[first][second] -= rate
    return tuple(tuple(row) for row in matrix)


def is_skew(matrix, tolerance=1e-12):
    """True when the matrix equals minus its transpose."""
    return all(abs(matrix[i][j] + matrix[j][i]) <= tolerance for i in range(4) for j in range(4))


def generator_angles(matrix):
    """(a, b): the rates of the two invariant planes of a skew matrix, a >= |b|, with a b = Pf(A)."""
    if not is_skew(matrix):
        raise ValueError("a generator is a skew-symmetric 4x4 matrix")
    square = fourd.matmul(matrix, matrix)
    total = -sum(square[i][i] for i in range(4)) / 2.0
    pfaffian = matrix[0][1] * matrix[2][3] - matrix[0][2] * matrix[1][3] + matrix[0][3] * matrix[1][2]
    spread = math.sqrt(max(0.0, total * total - 4.0 * pfaffian * pfaffian))
    a = math.sqrt(max(0.0, (total + spread) / 2.0))
    b = pfaffian / a if a > EPSILON else 0.0
    return a, b


def expm(matrix):
    """Closed-form exponential of a 4x4 skew-symmetric matrix (a rotation)."""
    a, b = generator_angles(matrix)
    identity = fourd.identity(4)
    if a <= EPSILON:
        return identity
    square = fourd.matmul(matrix, matrix)
    if a * a - b * b <= 1e-9 * max(1.0, a * a):
        return tuple(tuple(math.cos(a) * identity[i][j] + math.sin(a) / a * matrix[i][j] for j in range(4))
                     for i in range(4))
    cube = fourd.matmul(square, matrix)
    sinc_a = math.sin(a) / a
    sinc_b = math.sin(b) / b if abs(b) > EPSILON else 1.0 - b * b / 6.0
    gap = a * a - b * b
    c0 = (a * a * math.cos(b) - b * b * math.cos(a)) / gap
    c1 = (a * a * sinc_b - b * b * sinc_a) / gap
    c2 = (math.cos(b) - math.cos(a)) / gap
    c3 = (sinc_b - sinc_a) / gap
    return tuple(tuple(c0 * identity[i][j] + c1 * matrix[i][j] + c2 * square[i][j] + c3 * cube[i][j]
                       for j in range(4)) for i in range(4))


def rotation_angles(rotation):
    """(alpha, beta) in [0, pi] with alpha >= beta. Cosines come from tr(R) and tr(R^2), sines from the skew part
    K = (R - R^T)/2 (sin^2 sum = -tr(K^2)/2, sin product = Pf(K)); each angle is atan2(sin, cos), which stays
    accurate near 0 and near pi where acos alone loses half the digits."""
    if not fourd.is_rotation(rotation, 1e-8):
        raise ValueError("not a rotation: orthogonal with determinant +1 is required")
    square = fourd.matmul(rotation, rotation)
    total = sum(rotation[i][i] for i in range(4)) / 2.0
    squares = (sum(square[i][i] for i in range(4)) / 2.0 + 2.0) / 2.0
    product = (total * total - squares) / 2.0
    spread = math.sqrt(max(0.0, total * total - 4.0 * product))
    cosines = ((total - spread) / 2.0, (total + spread) / 2.0)
    skew = tuple(tuple((rotation[i][j] - rotation[j][i]) / 2.0 for j in range(4)) for i in range(4))
    skew_square = fourd.matmul(skew, skew)
    sine_total = -sum(skew_square[i][i] for i in range(4)) / 2.0
    pfaffian = skew[0][1] * skew[2][3] - skew[0][2] * skew[1][3] + skew[0][3] * skew[1][2]
    sine_spread = math.sqrt(max(0.0, sine_total * sine_total - 4.0 * pfaffian * pfaffian))
    sines = (math.sqrt(max(0.0, (sine_total + sine_spread) / 2.0)), math.sqrt(max(0.0, (sine_total - sine_spread) / 2.0)))
    straight = abs(sines[0] ** 2 + cosines[0] ** 2 - 1.0) + abs(sines[1] ** 2 + cosines[1] ** 2 - 1.0)
    crossed = abs(sines[1] ** 2 + cosines[0] ** 2 - 1.0) + abs(sines[0] ** 2 + cosines[1] ** 2 - 1.0)
    if crossed < straight:
        sines = (sines[1], sines[0])
    angles = sorted((math.atan2(sine, max(-1.0, min(1.0, cosine))) for sine, cosine in zip(sines, cosines)),
                    reverse=True)
    return angles[0], angles[1]


def _plane_structure(projector):
    columns = fourd.transpose(projector)
    basis = []
    for column in sorted(columns, key=fourd.norm, reverse=True):
        vector = column
        for previous in basis:
            vector = fourd.sub(vector, fourd.scale(previous, fourd.dot(vector, previous)))
        if fourd.norm(vector) > 1e-6:
            basis.append(fourd.normalize(vector))
        if len(basis) == 2:
            break
    u, v = basis
    return tuple(tuple(v[i] * u[j] - u[i] * v[j] for j in range(4)) for i in range(4))


def logm(rotation):
    """A skew generator A with exp(A) = R and both plane angles in [0, pi] (the principal logarithm)."""
    alpha, beta = rotation_angles(rotation)
    identity = fourd.identity(4)
    symmetric = tuple(tuple((rotation[i][j] + rotation[j][i]) / 2.0 for j in range(4)) for i in range(4))
    skew = tuple(tuple((rotation[i][j] - rotation[j][i]) / 2.0 for j in range(4)) for i in range(4))
    if alpha <= 1e-12:
        return tuple(tuple(0.0 for _ in range(4)) for _ in range(4))
    if abs(math.cos(alpha) - math.cos(beta)) <= 1e-9:
        if math.sin(alpha) > 1e-9:
            return tuple(tuple(alpha * skew[i][j] / math.sin(alpha) for j in range(4)) for i in range(4))
        first = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
        second = ((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))
        return tuple(tuple(math.pi * (_plane_structure(first)[i][j] + _plane_structure(second)[i][j])
                           for j in range(4)) for i in range(4))
    gap = math.cos(alpha) - math.cos(beta)
    first = tuple(tuple((symmetric[i][j] - math.cos(beta) * identity[i][j]) / gap for j in range(4)) for i in range(4))
    second = tuple(tuple(identity[i][j] - first[i][j] for j in range(4)) for i in range(4))
    result = [[0.0] * 4 for _ in range(4)]
    for angle, projector in ((alpha, first), (beta, second)):
        if angle <= 1e-12:
            continue
        if math.sin(angle) > 1e-7:
            part = fourd.matmul(skew, projector)
            for i in range(4):
                for j in range(4):
                    result[i][j] += angle * part[i][j] / math.sin(angle)
        else:
            structure = _plane_structure(projector)
            for i in range(4):
                for j in range(4):
                    result[i][j] += math.pi * structure[i][j]
    return tuple(tuple(row) for row in result)


def classify(rotation, tolerance=1e-9):
    """identity, simple (one plane turns), isoclinic (equal angles) or double."""
    alpha, beta = rotation_angles(rotation)
    if alpha <= tolerance:
        return "identity"
    if beta <= tolerance:
        return "simple"
    if abs(alpha - beta) <= tolerance:
        return "isoclinic"
    return "double"


def geodesic(start, end, t):
    """The point at fraction t of the shortest path from start to end in SO(4): start exp(t log(start^T end))."""
    step = logm(fourd.matmul(fourd.transpose(start), end))
    return fourd.matmul(start, expm(tuple(tuple(t * value for value in row) for row in step)))


def _shape(name):
    if name == "tesseract":
        vertices = [tuple(point) for point in itertools.product((-1.0, 1.0), repeat=4)]
        return vertices, fourd.edges_by_length(vertices)
    if name == "24cell":
        vertices = []
        for first, second in itertools.combinations(range(4), 2):
            for a, b in itertools.product((-1.0, 1.0), repeat=2):
                point = [0.0] * 4
                point[first], point[second] = a, b
                vertices.append(tuple(point))
        return vertices, fourd.edges_by_length(vertices)
    raise ValueError("polytope is tesseract or 24cell")


def frames(rates="xw=1,yz=2", polytope="tesseract", count=48, eye=2.5, duration=8.0):
    """Projected vertex positions of exp(t A) applied to the polytope for t from 0 to 2 pi (count + 1 frames)."""
    matrix = generator(rates)
    vertices, edges = _shape(polytope)
    reach = max(fourd.norm(point) for point in vertices)
    times, poses = [], []
    for index in range(count + 1):
        t = 2.0 * math.pi * index / count
        rotation = expm(tuple(tuple(t * value for value in row) for row in matrix))
        poses.append(fourd.project_points(fourd.rotate_points(rotation, vertices), "perspective", eye_distance=eye * reach))
        times.append(duration * index / count)
    return {"times": times, "poses": poses, "edges": edges, "vertices": vertices}


def chord_error(rates="xw=1,yz=2", count=48):
    """Largest 4D distance between the exact rotation and the chord between keyframes, on the unit sphere."""
    a, b = generator_angles(generator(rates))
    step = 2.0 * math.pi * max(abs(a), abs(b)) / count
    return 1.0 - math.cos(step / 2.0)


def export(path, rates="xw=1,yz=2", polytope="tesseract", count=48, eye=2.5, duration=8.0, style="tubes", radius=0.025):
    """Write the looping animation as glTF morph targets: unlit three-sided tubes (positions only) or LINES."""
    data = frames(rates, polytope, count, eye, duration)
    colours = fourd.depth_colors([point[3] for point in data["vertices"]])
    reach = max(fourd.norm(point) for point in data["vertices"])
    if style == "tubes":
        shapes = [fourd.tube_mesh(pose, data["edges"], radius * reach, 3, colours) for pose in data["poses"]]
        mesh, poses = shapes[0], [shape["positions"] for shape in shapes]
        mesh = dict(mesh, normals=None)
    elif style == "lines":
        mesh, poses = fourd.line_mesh(data["poses"][0], data["edges"], colours), data["poses"]
    else:
        raise ValueError("style is tubes or lines")
    animated, animation = fourd.morph_animation(dict(mesh, name=f"{polytope}_rotation", unlit=True), poses,
                                                data["times"], "rotation_loop")
    document = fourd.gltf_document([animated], animations=[animation], generator="rotation_exp_log.py")
    return {"path": str(path), "bytes": fourd.write_gltf(path, document), "chord_error": chord_error(rates, count),
            **fourd.gltf_summary(document)}


def rotations():
    """Rotations built by expm and by geodesic interpolation (checked by the package tests)."""
    generator_matrix = generator("xy=0.3,zw=1.1,xw=0.2")
    return [expm(generator_matrix), geodesic(fourd.identity(4), expm(generator_matrix), 0.37),
            expm(generator("xy=0.5,zw=0.5"))]


def _difference(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(4) for j in range(4))


def invariants():
    generator_matrix = generator("xy=0.3,zw=1.1")
    rotation = expm(generator_matrix)
    sampler = random.Random(4)
    roundtrip = 0.0
    for _ in range(40):
        rates = [(plane, sampler.uniform(-2.5, 2.5)) for plane in fourd.PLANES]
        random_rotation = expm(generator(rates))
        roundtrip = max(roundtrip, _difference(expm(logm(random_rotation)), random_rotation))
    small = generator("xy=0.4,zw=-0.9,xz=0.3")
    period = expm(tuple(tuple(2.0 * math.pi * value for value in row) for row in generator("xw=1,yz=2")))
    midpoint = geodesic(fourd.identity(4), rotation, 0.5)
    left = fourd.quaternion_pair_matrix((math.cos(0.4), math.sin(0.4), 0.0, 0.0), (1.0, 0.0, 0.0, 0.0))
    return {"exp_log_roundtrip": roundtrip < 1e-10,
            "log_exp_roundtrip": _difference(logm(expm(small)), small) < 1e-10,
            "plane_rotation_matches": _difference(expm(generator("xy=0.9")), fourd.plane_rotation("xy", 0.9)) < 1e-14,
            "angles_of_double_rotation": [round(value, 12) for value in rotation_angles(rotation)],
            "classes": [classify(fourd.identity(4)), classify(expm(generator("xy=0.7"))),
                        classify(expm(generator("xy=0.5,zw=0.5"))), classify(rotation)],
            "left_multiplication_is_isoclinic": [classify(left)] + [round(v, 12) for v in rotation_angles(left)],
            "geodesic_midpoint_is_half_generator": _difference(midpoint, expm(tuple(tuple(v / 2.0 for v in row)
                                                                                    for row in generator_matrix))) < 1e-12,
            "loop_closes_after_two_pi": _difference(period, fourd.identity(4)) < 1e-12,
            "generator_angles_of_xw1_yz2": [round(abs(value), 12) for value in generator_angles(generator("xw=1,yz=2"))],
            "chord_error_example": round(chord_error(), 12)}


def controls():
    def refused(action):
        try:
            action()
        except ValueError:
            return True
        return False

    stretched = tuple(tuple(1.1 * value for value in row) for row in fourd.identity(4))
    mirror = ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, -1.0))
    symmetric = ((0.0, 1.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 0.0))
    wrong_angle = expm(generator("xy=0.3,zw=1.2"))
    return {"stretched_matrix_refused": refused(lambda: logm(stretched)),
            "reflection_refused": refused(lambda: logm(mirror)),
            "symmetric_generator_refused": refused(lambda: expm(symmetric)),
            "wrong_angles_detected": [round(v, 6) for v in rotation_angles(wrong_angle)] != [1.1, 0.3],
            "unknown_polytope_refused": refused(lambda: frames(polytope="cube"))}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rotation_exp_log.py",
                                     description="Write a polytope turning under exp(t A) as a looping glTF.")
    parser.add_argument("--rates", default="xw=1,yz=2", help="plane rates of the generator A, like xw=1,yz=2")
    parser.add_argument("--polytope", choices=("tesseract", "24cell"), default="tesseract", help="object to turn")
    parser.add_argument("--frames", type=int, default=48, help="keyframes over t in [0, 2 pi]")
    parser.add_argument("--style", choices=("tubes", "lines"), default="tubes",
                        help="unlit three-sided tubes or a LINES primitive")
    parser.add_argument("--radius", type=float, default=0.025, help="tube radius in circumradii")
    parser.add_argument("--eye", type=float, default=2.5, help="4D eye distance in circumradii")
    parser.add_argument("--duration", type=float, default=8.0, help="seconds per loop")
    parser.add_argument("--out", required=True, help="output .gltf")
    args = parser.parse_args(argv)
    if not 4 <= args.frames <= 720 or args.eye <= 1.0 or args.duration <= 0 or args.radius <= 0:
        parser.error("frames is 4 to 720, eye is above 1, duration and radius are positive")
    try:
        summary = export(args.out, args.rates, args.polytope, args.frames, args.eye, args.duration, args.style,
                         args.radius)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
