"""The five Platonic solids with exact edge length, faces found as supporting planes of their vertices.

Command line: python3 platonic_solids.py --output platonic.gltf --solid all --edge 1
"""
from __future__ import annotations

import itertools
import math

import meshkit

SOLIDS = ("tetrahedron", "cube", "octahedron", "dodecahedron", "icosahedron")
PARAMETERS = [
    {"name": "solid", "type": "str", "default": "all", "unit": "name", "choices": ["all"] + list(SOLIDS),
     "meaning": "Which solid to write; 'all' places the five in a row along X."},
    {"name": "edge", "type": "float", "default": 1.0, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Edge length of every solid."},
]


def solid_vertices(name, edge=1.0):
    """Vertex coordinates of a Platonic solid centred at the origin with the given edge length."""
    golden = (1.0 + math.sqrt(5.0)) / 2.0
    if name == "tetrahedron":
        raw, length = [(1.0, 1.0, 1.0), (1.0, -1.0, -1.0), (-1.0, 1.0, -1.0), (-1.0, -1.0, 1.0)], 2.0 * math.sqrt(2.0)
    elif name == "cube":
        raw, length = [(x, y, z) for x in (-1.0, 1.0) for y in (-1.0, 1.0) for z in (-1.0, 1.0)], 2.0
    elif name == "octahedron":
        raw, length = [(1.0, 0, 0), (-1.0, 0, 0), (0, 1.0, 0), (0, -1.0, 0), (0, 0, 1.0), (0, 0, -1.0)], math.sqrt(2.0)
    elif name == "dodecahedron":
        raw = [(x, y, z) for x in (-1.0, 1.0) for y in (-1.0, 1.0) for z in (-1.0, 1.0)]
        for a in (-1.0, 1.0):
            for b in (-1.0, 1.0):
                raw += [(0.0, a / golden, b * golden), (a / golden, b * golden, 0.0), (b * golden, 0.0, a / golden)]
        length = 2.0 / golden
    elif name == "icosahedron":
        raw = []
        for a in (-1.0, 1.0):
            for b in (-1.0, 1.0):
                raw += [(0.0, a, b * golden), (a, b * golden, 0.0), (b * golden, 0.0, a)]
        length = 2.0
    else:
        raise meshkit.MeshError("solid_unknown", str(name))
    return [meshkit.vscale(p, edge / length) for p in raw]


def hull_faces(vertices):
    """Faces of a convex polyhedron given only its vertices: each plane through three vertices with all
    vertices on one side is a face; its vertices are ordered counter-clockwise seen from outside."""
    scale = max(meshkit.vlength(v) for v in vertices)
    planes = {}
    for a, b, c in itertools.combinations(range(len(vertices)), 3):
        normal = meshkit.vcross(meshkit.vsub(vertices[b], vertices[a]), meshkit.vsub(vertices[c], vertices[a]))
        if meshkit.vlength(normal) < 1e-12 * scale * scale:
            continue
        normal = meshkit.vnormalize(normal)
        offset = meshkit.vdot(normal, vertices[a])
        if offset < 0:
            normal, offset = meshkit.vscale(normal, -1.0), -offset
        distances = [meshkit.vdot(normal, v) - offset for v in vertices]
        if max(distances) > 1e-9 * scale:
            continue
        members = tuple(i for i, d in enumerate(distances) if abs(d) <= 1e-9 * scale)
        planes.setdefault(members, normal)
    faces = []
    for members, normal in sorted(planes.items()):
        center = meshkit.vscale(meshkit.vadd((0.0, 0.0, 0.0), tuple(math.fsum(vertices[i][k] for i in members)
                                                                     for k in range(3))), 1.0 / len(members))
        reference = meshkit.vnormalize(meshkit.vsub(vertices[members[0]], center))
        other = meshkit.vcross(normal, reference)
        ordered = sorted(members, key=lambda i: math.atan2(meshkit.vdot(meshkit.vsub(vertices[i], center), other),
                                                           meshkit.vdot(meshkit.vsub(vertices[i], center), reference)))
        faces.append(tuple(ordered))
    return faces


def platonic_solid(name="dodecahedron", edge=1.0):
    """One Platonic solid: exact vertices, polygon faces (triangles, squares or pentagons), outward winding."""
    vertices = solid_vertices(name, edge)
    return meshkit.Mesh(vertices, hull_faces(vertices), name=name)


def build(solid="all", edge=1.0):
    """The flat-shaded solid, or all five side by side along X, as the command line writes them."""
    colors = {"tetrahedron": (0.90, 0.48, 0.42), "cube": (0.94, 0.78, 0.40), "octahedron": (0.52, 0.80, 0.52),
              "dodecahedron": (0.46, 0.66, 0.90), "icosahedron": (0.74, 0.56, 0.88)}
    names = SOLIDS if solid == "all" else (solid,)
    meshes = []
    for number, name in enumerate(names):
        part = meshkit.flat_shaded(platonic_solid(name, edge))
        offset = (number - (len(names) - 1) / 2.0) * 2.2 * edge
        part = meshkit.translated(part, (offset, 0.0, 0.0))
        part.name = name
        part.material = meshkit.material(name, colors[name] + (1.0,), roughness=0.45)
        meshes.append(part)
    return meshes


def main(argv=None):
    """Command line: write the solids as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
