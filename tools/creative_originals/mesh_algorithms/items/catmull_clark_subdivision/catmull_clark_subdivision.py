"""Catmull-Clark subdivision of polygon meshes, with boundary rules and fixed boundary corners.

Command line: python3 catmull_clark_subdivision.py --output smooth.gltf --cage torus --levels 3
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "cage", "type": "str", "default": "torus", "unit": "name", "choices": ["cube", "torus", "plane", "l_block"],
     "meaning": "Control cage to subdivide."},
    {"name": "levels", "type": "int", "default": 3, "unit": "count", "minimum": 0, "maximum": 6,
     "meaning": "Number of subdivision steps; each step multiplies the face count by about four."},
]


def _average(points):
    count = len(points)
    return (math.fsum(p[0] for p in points) / count, math.fsum(p[1] for p in points) / count,
            math.fsum(p[2] for p in points) / count)


def _step(mesh):
    vertices, faces = mesh.vertices, mesh.faces
    face_points = [_average([vertices[i] for i in face]) for face in faces]
    adjacency = meshkit.edge_faces(mesh)
    edge_number, edge_points = {}, []
    incident = [[] for _ in vertices]
    for edge, owners in adjacency.items():
        a, b = edge
        if len(owners) == 2:
            point = _average([vertices[a], vertices[b], face_points[owners[0]], face_points[owners[1]]])
        else:
            point = _average([vertices[a], vertices[b]])
        edge_number[edge] = len(edge_points)
        edge_points.append(point)
        incident[a].append(edge)
        incident[b].append(edge)
    around = meshkit.vertex_faces(mesh)
    moved = []
    for v, position in enumerate(vertices):
        edges_here = incident[v]
        boundary = [e for e in edges_here if len(adjacency[e]) == 1]
        if not edges_here or (boundary and len(boundary) != 2):
            moved.append(position)
        elif boundary:
            if len(edges_here) == 2:
                moved.append(position)
            else:
                ends = [vertices[e[0] if e[1] == v else e[1]] for e in boundary]
                moved.append(tuple((6.0 * position[k] + ends[0][k] + ends[1][k]) / 8.0 for k in range(3)))
        else:
            valence = len(edges_here)
            q = _average([face_points[f] for f in around[v]])
            r = _average([_average([vertices[e[0]], vertices[e[1]]]) for e in edges_here])
            moved.append(tuple((q[k] + 2.0 * r[k] + (valence - 3) * position[k]) / valence for k in range(3)))
    base_edges = len(vertices)
    base_faces = base_edges + len(edge_points)
    new_faces = []
    for number, face in enumerate(faces):
        count = len(face)
        for k in range(count):
            here, after, before = face[k], face[(k + 1) % count], face[k - 1]
            new_faces.append((here, base_edges + edge_number[(here, after) if here < after else (after, here)],
                              base_faces + number,
                              base_edges + edge_number[(before, here) if before < here else (here, before)]))
    return meshkit.Mesh(moved + edge_points + face_points, new_faces, name=mesh.name, material=mesh.material)


def catmull_clark(mesh, levels=1):
    """Subdivide ``levels`` times; every output face is a quad and normals are angle weighted.

    Interior rules: face point = face centroid, edge point = mean of the edge ends and the two face points,
    vertex point = (Q + 2R + (n - 3)P) / n. Boundary edges use their midpoint, boundary vertices the cubic
    B-spline rule (6P + two boundary neighbours) / 8, and a boundary corner with two edges stays fixed.
    One step turns V, E, F into V + E + F vertices and the sum of face sizes as quads."""
    if levels < 0:
        raise meshkit.MeshError("levels_invalid", "levels is zero or more")
    result = meshkit.Mesh(mesh.vertices, mesh.faces, name=getattr(mesh, "name", "mesh"),
                          material=getattr(mesh, "material", None)).validate()
    for _ in range(int(levels)):
        result = _step(result)
    result.normals = meshkit.vertex_normals(result)
    return result


def cage(name="torus"):
    """A demonstration control cage: 'cube', 'torus' (4 x 4 square ring), 'plane' (open 2 x 2 grid with a raised
    centre) or 'l_block' (an extruded L whose caps are hexagons)."""
    if name == "cube":
        return meshkit.box((1.0, 1.0, 1.0))
    if name == "torus":
        vertices = []
        for i in range(4):
            angle = 2.0 * math.pi * i / 4
            radial = (math.cos(angle), 0.0, -math.sin(angle))
            for j in range(4):
                around = math.pi / 4 + math.pi * j / 2
                offset_r, offset_y = 0.45 * math.cos(around), 0.45 * math.sin(around)
                vertices.append((radial[0] * (1.0 + offset_r), offset_y, radial[2] * (1.0 + offset_r)))
        faces = meshkit.grid_faces(4, 4, wrap_columns=True, wrap_rows=True)
        mesh = meshkit.Mesh(vertices, faces, name="torus_cage")
        return mesh if meshkit.signed_volume(mesh) > 0 else meshkit.flipped(mesh)
    if name == "plane":
        vertices = [(x, 0.5 if (x, z) == (0.0, 0.0) else 0.0, z) for z in (-1.0, 0.0, 1.0) for x in (-1.0, 0.0, 1.0)]
        return meshkit.Mesh(vertices, meshkit.grid_faces(3, 3), name="plane_cage")
    if name == "l_block":
        outline = [(0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 1.0), (1.0, 2.0), (0.0, 2.0)]
        bottom = [(x, 0.0, -y) for x, y in outline]
        top = [(x, 0.8, -y) for x, y in outline]
        count = len(outline)
        faces = [tuple(range(count - 1, -1, -1)), tuple(range(count, 2 * count))]
        faces += [(k, (k + 1) % count, count + (k + 1) % count, count + k) for k in range(count)]
        return meshkit.Mesh(bottom + top, faces, name="l_block_cage")
    raise meshkit.MeshError("cage_unknown", str(name))


def build(cage="torus", levels=3):
    """The subdivided demonstration cage the command line writes."""
    result = catmull_clark(globals()["cage"](cage), levels)
    result.material = meshkit.material("catmull_clark", (0.85, 0.62, 0.42, 1.0))
    return result


def main(argv=None):
    """Command line: write the subdivided cage as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
