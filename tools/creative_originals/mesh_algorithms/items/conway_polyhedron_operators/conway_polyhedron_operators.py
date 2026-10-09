"""Conway polyhedron notation: apply dual, ambo, kis, truncate, join, expand, ortho, gyro and snub to seed solids.

Command line: python3 conway_polyhedron_operators.py --output conway.gltf --notation tI --relax 40
"""
from __future__ import annotations

import itertools
import math

import meshkit

PARAMETERS = [
    {"name": "notation", "type": "str", "default": "tI", "unit": "notation",
     "meaning": "Operators read right to left, then a seed: T C O D I, Pn (prism) or An (antiprism), for example tI, sC, dkD."},
    {"name": "relax", "type": "int", "default": 40, "unit": "iterations", "minimum": 0, "maximum": 10000,
     "meaning": "Planarizing iterations after each operator (0 keeps raw centroids on the unit sphere)."},
]
OPERATORS = "dakjteogs"


def _icosahedron():
    golden = (1.0 + math.sqrt(5.0)) / 2.0
    points = []
    for a in (-1.0, 1.0):
        for b in (-golden, golden):
            points += [(0.0, a, b), (a, b, 0.0), (b, 0.0, a)]
    faces = []
    for a, b, c in itertools.combinations(range(12), 3):
        if all(abs(meshkit.vdistance(points[i], points[j]) - 2.0) < 1e-9 for i, j in ((a, b), (b, c), (a, c))):
            normal = meshkit.vcross(meshkit.vsub(points[b], points[a]), meshkit.vsub(points[c], points[a]))
            faces.append((a, b, c) if meshkit.vdot(normal, points[a]) > 0 else (a, c, b))
    return points, faces


def seed(name):
    """Seed polyhedron (vertices on the unit sphere, outward faces): T, C, O, D, I, Pn or An (n >= 3)."""
    if name == "T":
        mesh = meshkit.tetrahedron()
        return [meshkit.vnormalize(v) for v in mesh.vertices], list(mesh.faces)
    if name == "C":
        mesh = meshkit.box()
        return [meshkit.vnormalize(v) for v in mesh.vertices], list(mesh.faces)
    if name == "O":
        return dual(*seed("C"))
    if name == "I":
        points, faces = _icosahedron()
        return [meshkit.vnormalize(p) for p in points], faces
    if name == "D":
        return dual(*seed("I"))
    if name[:1] in ("P", "A") and name[1:].isdigit() and int(name[1:]) >= 3:
        n = int(name[1:])
        twist = math.pi / n if name[0] == "A" else 0.0
        height = 1.0 if name[0] == "P" else math.sqrt(max(0.1, (math.cos(math.pi / n) - math.cos(2 * math.pi / n)) / 2.0)) * 2.0
        top = [(math.cos(2 * math.pi * k / n), height / 2.0, -math.sin(2 * math.pi * k / n)) for k in range(n)]
        bottom = [(math.cos(2 * math.pi * k / n + twist), -height / 2.0, -math.sin(2 * math.pi * k / n + twist)) for k in range(n)]
        vertices = [meshkit.vnormalize(p) for p in top + bottom]
        faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        for k in range(n):
            j = (k + 1) % n
            if name[0] == "P":
                faces.append((k, n + k, n + j, j))
            else:
                faces += [(k, n + k, j), (j, n + k, n + j)]
        return vertices, faces
    raise meshkit.MeshError("seed_unknown", str(name))


def _around(faces):
    """For each vertex, its faces in counter-clockwise order seen from outside."""
    owner, first = {}, {}
    for number, face in enumerate(faces):
        for k in range(len(face)):
            owner[(face[k], face[(k + 1) % len(face)])] = number
            first.setdefault(face[k], number)
    cycles = {}
    for vertex, start in first.items():
        cycle, face = [], start
        while True:
            cycle.append(face)
            corners = faces[face]
            previous = corners[corners.index(vertex) - 1]
            face = owner[(vertex, previous)]
            if face == start:
                break
            if len(cycle) > len(faces):
                raise meshkit.MeshError("not_manifold", f"vertex {vertex}")
        cycles[vertex] = cycle
    return cycles


def _center(vertices, face):
    return tuple(math.fsum(vertices[i][k] for i in face) / len(face) for k in range(3))


def dual(vertices, faces):
    """Dual: one vertex per face (its centroid on the unit sphere), one face per vertex (its faces in order)."""
    cycles = _around(faces)
    return ([meshkit.vnormalize(_center(vertices, face)) for face in faces],
            [tuple(cycles[v]) for v in sorted(cycles)])


def ambo(vertices, faces):
    """Ambo (rectify): one vertex per edge midpoint; a face for each old face and each old vertex."""
    index, points = {}, []

    def mid(a, b):
        key = (a, b) if a < b else (b, a)
        if key not in index:
            index[key] = len(points)
            points.append(meshkit.vnormalize(meshkit.vlerp(vertices[a], vertices[b], 0.5)))
        return index[key]

    new_faces = [tuple(mid(face[k], face[(k + 1) % len(face)]) for k in range(len(face))) for face in faces]
    for vertex, cycle in sorted(_around(faces).items()):
        ring = []
        for number in cycle:
            face = faces[number]
            ring.append(mid(vertex, face[(face.index(vertex) + 1) % len(face)]))
        new_faces.append(tuple(ring))
    return points, new_faces


def kis(vertices, faces):
    """Kis: raise a vertex over every face centre and replace the face with a fan of triangles."""
    points = list(vertices)
    new_faces = []
    for face in faces:
        apex = len(points)
        points.append(meshkit.vnormalize(_center(vertices, face)))
        new_faces += [(face[k], face[(k + 1) % len(face)], apex) for k in range(len(face))]
    return points, new_faces


def gyro(vertices, faces):
    """Gyro: every n-gon becomes n pentagons around a new centre, with two new vertices on each edge."""
    points = list(vertices)
    third = {}

    def at_third(a, b):
        if (a, b) not in third:
            third[(a, b)] = len(points)
            points.append(meshkit.vnormalize(meshkit.vlerp(vertices[a], vertices[b], 1.0 / 3.0)))
        return third[(a, b)]

    new_faces = []
    for face in faces:
        center = len(points)
        points.append(meshkit.vnormalize(_center(vertices, face)))
        count = len(face)
        for k in range(count):
            a, b, c = face[k], face[(k + 1) % count], face[(k + 2) % count]
            new_faces.append((center, at_third(a, b), at_third(b, a), b, at_third(b, c)))
    return points, new_faces


def _relax(vertices, faces, iterations):
    """Move vertices toward the planes of their faces and keep the mean radius at 1 (planarizing relaxation)."""
    points = [tuple(p) for p in vertices]
    for _ in range(iterations):
        sums = [[0.0, 0.0, 0.0, 0] for _ in points]
        for face in faces:
            center = _center(points, face)
            normal = meshkit.face_normal(points, face)
            for i in face:
                offset = meshkit.vdot(meshkit.vsub(points[i], center), normal)
                target = meshkit.vsub(points[i], meshkit.vscale(normal, offset))
                total = sums[i]
                total[0] += target[0]
                total[1] += target[1]
                total[2] += target[2]
                total[3] += 1
        points = [(t[0] / t[3], t[1] / t[3], t[2] / t[3]) for t in sums]
        mean = math.fsum(meshkit.vlength(p) for p in points) / len(points)
        points = [meshkit.vscale(p, 1.0 / mean) for p in points]
    return points


def apply_operator(letter, vertices, faces):
    """One operator: d dual, a ambo, k kis, j join (da), t truncate (dkd), e expand (aa), o ortho (dad... de),
    g gyro, s snub (dg)."""
    if letter == "d":
        return dual(vertices, faces)
    if letter == "a":
        return ambo(vertices, faces)
    if letter == "k":
        return kis(vertices, faces)
    if letter == "g":
        return gyro(vertices, faces)
    if letter == "j":
        return dual(*ambo(vertices, faces))
    if letter == "t":
        return dual(*kis(*dual(vertices, faces)))
    if letter == "e":
        return ambo(*ambo(vertices, faces))
    if letter == "o":
        return dual(*ambo(*ambo(vertices, faces)))
    if letter == "s":
        return dual(*gyro(vertices, faces))
    raise meshkit.MeshError("operator_unknown", letter)


def conway(notation="tI", relax=40):
    """The polyhedron for a Conway notation string, as a closed mesh with polygon faces on about the unit sphere.

    Operators apply right to left after the seed (the trailing T, C, O, D, I, Pn or An). Faces are made
    nearly planar by ``relax`` iterations after every operator; they are not exactly planar or regular."""
    split = len(notation)
    while split > 0 and notation[split - 1].isdigit():
        split -= 1
    split -= 1
    if split < 0 or notation[split] not in "TCODIPA":
        raise meshkit.MeshError("notation_invalid", "the notation ends with a seed: T, C, O, D, I, Pn or An")
    vertices, faces = seed(notation[split:])
    for letter in reversed(notation[:split]):
        if letter not in OPERATORS:
            raise meshkit.MeshError("operator_unknown", letter)
        vertices, faces = apply_operator(letter, vertices, faces)
        vertices = _relax(vertices, faces, relax)
    return meshkit.Mesh(vertices, faces, name="conway_" + notation)


def build(notation="tI", relax=40):
    """The flat-shaded polyhedron the command line writes, each face coloured by its number of corners."""
    mesh = conway(notation, relax)
    palette = {3: (0.93, 0.62, 0.38), 4: (0.52, 0.76, 0.86), 5: (0.30, 0.32, 0.38), 6: (0.95, 0.95, 0.93)}
    vertices, faces, normals, colors = [], [], [], []
    for face in mesh.faces:
        normal = meshkit.face_normal(mesh.vertices, face)
        color = palette.get(len(face), (0.72, 0.60, 0.86))
        start = len(vertices)
        for i in face:
            vertices.append(mesh.vertices[i])
            normals.append(normal)
            colors.append(color)
        faces.append(tuple(range(start, start + len(face))))
    return meshkit.Mesh(vertices, faces, normals=normals, colors=colors, name=mesh.name,
                        material=meshkit.material("conway", (1.0, 1.0, 1.0, 1.0), roughness=0.5))


def main(argv=None):
    """Command line: write the polyhedron as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
