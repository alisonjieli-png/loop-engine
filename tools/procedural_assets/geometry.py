"""Small original mesh and preview engine, with no files, network or model calls.

Coordinates are right-handed, metres, Y up. These are static reference meshes,
not physical simulators, skinned characters or replacements for native editors.
"""
from __future__ import annotations

import base64
import html
import math
import struct


def normal(a, b, c):
    u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
    n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    length = math.sqrt(sum(x * x for x in n))
    if length <= 1e-12:
        raise ValueError("degenerate_triangle")
    return [x / length for x in n]


def convex(name, vertices, faces, center, color):
    """Orient each convex surface outwards; refuse zero-area triangles."""
    oriented = []
    for face in faces:
        a, b, c = [vertices[i] for i in face]
        n = normal(a, b, c)
        outside = sum(n[i] * ((a[i] + b[i] + c[i]) / 3 - center[i]) for i in range(3))
        oriented.append(list(face) if outside > 0 else [face[0], face[2], face[1]])
    return {"name": name, "vertices": vertices, "triangles": oriented, "color": color}


def box(name, center, size, color):
    vertices = [[center[i] + signs[i] * size[i] / 2 for i in range(3)]
                for signs in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                              (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))]
    faces = [(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1),
             (3, 2, 6), (3, 6, 7), (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2)]
    return convex(name, vertices, faces, center, color)


def round_body(name, center, size, color, *, form="ellipsoid", sides=10, axis=1):
    """Closed low-poly ellipsoid, cylinder or cone; geometry changes rather than labels."""
    vertices, faces = [], []
    if form == "ellipsoid":
        vertices = [[0, -1, 0]]
        for ring in range(1, 6):
            latitude = -math.pi / 2 + ring * math.pi / 6
            vertices.extend([[math.cos(latitude) * math.cos(i * math.tau / sides), math.sin(latitude),
                              math.cos(latitude) * math.sin(i * math.tau / sides)] for i in range(sides)])
        vertices.append([0, 1, 0])
        for i in range(sides):
            j = (i + 1) % sides
            faces.extend([(0, 1 + i, 1 + j), (len(vertices) - 1, 1 + 4 * sides + j, 1 + 4 * sides + i)])
        for ring in range(4):
            for i in range(sides):
                a, b = 1 + ring * sides + i, 1 + ring * sides + (i + 1) % sides
                faces.extend([(a, b, b + sides), (a, b + sides, a + sides)])
    elif form in ("cylinder", "cone"):
        vertices = [[0, -1, 0], [0, 1, 0]]
        vertices += [[math.cos(i * math.tau / sides), -1, math.sin(i * math.tau / sides)] for i in range(sides)]
        if form == "cylinder":
            vertices += [[math.cos(i * math.tau / sides), 1, math.sin(i * math.tau / sides)] for i in range(sides)]
        for i in range(sides):
            a, b = 2 + i, 2 + (i + 1) % sides
            faces.append((0, b, a))
            if form == "cone":
                faces.append((a, b, 1))
            else:
                faces.extend([(a, b, b + sides), (a, b + sides, a + sides), (1, a + sides, b + sides)])
    else:
        raise ValueError("unsupported_primitive")
    if axis != 1:
        for vertex in vertices:
            vertex[axis], vertex[1] = vertex[1], vertex[axis]
    vertices = [[center[i] + value[i] * size[i] / 2 for i in range(3)] for value in vertices]
    return convex(name, vertices, faces, center, color)


def bounds(parts):
    vertices = [v for part in parts for v in part["vertices"]]
    return [[min(v[i] for v in vertices) for i in range(3)], [max(v[i] for v in vertices) for i in range(3)]]


def inspect_mesh(parts):
    """A structural check, not visual approval or collision qualification."""
    if not isinstance(parts, list) or not 1 <= len(parts) <= 128:
        raise ValueError("part_budget")
    names, triangles = set(), 0
    for part in parts:
        if set(part) != {"name", "vertices", "triangles", "color"} or part["name"] in names:
            raise ValueError("invalid_or_duplicate_part")
        names.add(part["name"])
        if not isinstance(part["name"], str) or not part["name"] or len(part["name"]) > 80:
            raise ValueError("invalid_part_name")
        if len(part["vertices"]) > 10000 or not part["triangles"]:
            raise ValueError("mesh_budget")
        for vertex in part["vertices"]:
            if len(vertex) != 3 or any(type(n) not in (int, float) or not math.isfinite(n) or abs(n) > 10000 for n in vertex):
                raise ValueError("invalid_vertex")
        if len(part["color"]) != 3 or any(type(n) not in (int, float) or not 0 <= n <= 1 for n in part["color"]):
            raise ValueError("invalid_color")
        for face in part["triangles"]:
            if len(face) != 3 or any(type(i) is not int or not 0 <= i < len(part["vertices"]) for i in face):
                raise ValueError("invalid_triangle")
            normal(*[part["vertices"][i] for i in face])
        triangles += len(part["triangles"])
    if triangles > 20000:
        raise ValueError("triangle_budget")
    return {"parts": len(parts), "triangles": triangles, "bounds_m": bounds(parts),
            "finite_geometry": True, "nondegenerate_triangles": True,
            "collision_tested": False, "animation_tested": False, "visual_approved": False}


def gltf(parts):
    """Embedded-buffer glTF 2.0; no external resource, extension or executable payload."""
    inspect_mesh(parts)
    document = {"asset": {"version": "2.0", "generator": "Baltor original procedural reference engine v1"},
                "scene": 0, "scenes": [{"nodes": list(range(len(parts)))}], "nodes": [], "meshes": [],
                "materials": [], "accessors": [], "bufferViews": [], "buffers": []}
    binary = bytearray()

    def accessor(values, kind, extrema=False):
        index = len(document["accessors"])
        offset = len(binary)
        for value in values:
            binary.extend(struct.pack("<" + "f" * len(value), *value))
        document["bufferViews"].append({"buffer": 0, "byteOffset": offset, "byteLength": len(binary) - offset, "target": 34962})
        record = {"bufferView": index, "componentType": 5126, "count": len(values), "type": kind}
        if extrema:
            record.update(min=[min(v[i] for v in values) for i in range(3)], max=[max(v[i] for v in values) for i in range(3)])
        document["accessors"].append(record)
        return index

    for index, part in enumerate(parts):
        positions, normals = [], []
        for face in part["triangles"]:
            vertices = [part["vertices"][i] for i in face]
            positions.extend(vertices)
            normals.extend([normal(*vertices)] * 3)
        p, n = accessor(positions, "VEC3", True), accessor(normals, "VEC3")
        document["nodes"].append({"name": part["name"], "mesh": index})
        document["meshes"].append({"primitives": [{"attributes": {"POSITION": p, "NORMAL": n}, "material": index}]})
        document["materials"].append({"name": part["name"], "doubleSided": False,
            "pbrMetallicRoughness": {"baseColorFactor": [*part["color"], 1], "metallicFactor": 0, "roughnessFactor": 0.85}})
    document["buffers"] = [{"byteLength": len(binary), "uri": "data:application/octet-stream;base64," + base64.b64encode(binary).decode()}]
    return document


def preview(parts, title, view="isometric"):
    """An original flat-shaded SVG reference derived from the same mesh, not a native-engine render."""
    inspect_mesh(parts)
    directions = {"isometric": (2.4, 0.35), "front": (math.pi, 0), "side": (math.pi / 2, 0), "top": (0, math.pi / 2)}
    if view not in directions:
        raise ValueError("unknown_view")
    yaw, pitch = directions[view]
    camera = [math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch)]

    def project(v):
        x, y, z = v
        horizontal = x * math.cos(yaw) - z * math.sin(yaw)
        depth = x * math.sin(yaw) + z * math.cos(yaw)
        return [horizontal, -y * math.cos(pitch) + depth * math.sin(pitch)]

    projected = [project(v) for part in parts for v in part["vertices"]]
    low = [min(v[i] for v in projected) for i in range(2)]
    high = [max(v[i] for v in projected) for i in range(2)]
    scale = min(440 / max(high[0] - low[0], 0.001), 365 / max(high[1] - low[1], 0.001))
    middle = [(high[i] + low[i]) / 2 for i in range(2)]
    faces = []
    for part in parts:
        for face in part["triangles"]:
            vertices = [part["vertices"][i] for i in face]
            n = normal(*vertices)
            if sum(n[i] * camera[i] for i in range(3)) <= 1e-8:
                continue
            shade = 0.5 + 0.5 * max(0, sum(n[i] * [0.4, 0.8, 0.4472136][i] for i in range(3)))
            color = "#" + "".join(f"{round(255 * c * shade):02x}" for c in part["color"])
            points = " ".join(f"{256 + (project(v)[0] - middle[0]) * scale:.2f},{224 + (project(v)[1] - middle[1]) * scale:.2f}" for v in vertices)
            depth = sum(sum(v[i] * camera[i] for i in range(3)) for v in vertices) / 3
            faces.append((depth, f'<polygon points="{points}" fill="{color}" stroke="{color}" stroke-width="0.3"/>'))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img">'
            f'<title>{html.escape(title)} — {view} structural reference</title>'
            '<rect width="512" height="512" rx="24" fill="#eef0eb"/>' +
            "".join(row[1] for row in sorted(faces)) +
            f'<text x="24" y="456" fill="#20302c" font-family="sans-serif" font-size="18">{html.escape(title)}</text>'
            f'<text x="24" y="483" fill="#53675f" font-family="sans-serif" font-size="12">{view} · metres · procedural blockout · not production-qualified</text></svg>')
