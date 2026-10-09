"""Profile sweep: move a closed 2D profile along a 3D path with transported frames, scaling and twist, and cap
both ends.

Command line: python3 profile_sweep.py --output sweep.gltf --profile star --path arc --end-scale 0.4 --twist 90
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "profile", "type": "str", "default": "star", "unit": "name", "choices": ["star", "square", "circle", "cross"],
     "meaning": "Closed 2D cross-section."},
    {"name": "path", "type": "str", "default": "arc", "unit": "name", "choices": ["arc", "helix", "line", "s_curve"],
     "meaning": "3D path the profile follows."},
    {"name": "end_scale", "type": "float", "default": 0.4, "unit": "ratio", "minimum": 0.0, "maximum": 100.0,
     "meaning": "Profile scale at the end of the path (1 at the start, linear in between)."},
    {"name": "twist", "type": "float", "default": 90.0, "unit": "degrees", "minimum": -36000.0, "maximum": 36000.0,
     "meaning": "Total rotation of the profile about the path from start to end."},
    {"name": "steps", "type": "int", "default": 64, "unit": "count", "minimum": 1, "maximum": 100000,
     "meaning": "Path samples minus one."},
]


def demo_profile(name="star", size=0.3):
    """A counter-clockwise closed 2D profile: five-point star, square, 24-gon circle or plus-shaped cross."""
    if name == "star":
        return [(size * (1.0 if k % 2 == 0 else 0.45) * math.cos(math.pi * k / 5),
                 size * (1.0 if k % 2 == 0 else 0.45) * math.sin(math.pi * k / 5)) for k in range(10)]
    if name == "square":
        return [(-size, -size), (size, -size), (size, size), (-size, size)]
    if name == "circle":
        return [(size * math.cos(2 * math.pi * k / 24), size * math.sin(2 * math.pi * k / 24)) for k in range(24)]
    if name == "cross":
        a, b = size, size / 3.0
        return [(b, -a), (b, -b), (a, -b), (a, b), (b, b), (b, a), (-b, a), (-b, b), (-a, b), (-a, -b), (-b, -b), (-b, -a)]
    raise meshkit.MeshError("profile_unknown", str(name))


def demo_path(name="arc", steps=64):
    """``steps`` + 1 points along a demonstration path."""
    points = []
    for k in range(steps + 1):
        u = k / steps
        if name == "arc":
            angle = math.pi * u
            points.append((-1.5 * math.cos(angle), 1.5 * math.sin(angle), 0.0))
        elif name == "helix":
            angle = 4.0 * math.pi * u
            points.append((math.cos(angle), 2.0 * u - 1.0, -math.sin(angle)))
        elif name == "line":
            points.append((0.0, 2.0 * u - 1.0, 0.0))
        elif name == "s_curve":
            points.append((3.0 * u - 1.5, 0.0, 0.8 * math.sin(2.0 * math.pi * u)))
        else:
            raise meshkit.MeshError("path_unknown", str(name))
    return points


def _rotate(vector, axis, angle):
    c, s = math.cos(angle), math.sin(angle)
    return meshkit.vadd(meshkit.vadd(meshkit.vscale(vector, c), meshkit.vscale(meshkit.vcross(axis, vector), s)),
                        meshkit.vscale(axis, meshkit.vdot(axis, vector) * (1.0 - c)))


def sweep(profile, path, end_scale=1.0, twist=0.0, caps=True):
    """A mesh of len(path) rings of len(profile) vertices; ring k is the profile scaled by lerp(1, end_scale,
    k / (n - 1)) and turned by twist * k / (n - 1) degrees, placed in a frame carried along the path by the
    rotation between consecutive tangents. Caps triangulate the profile, so the result is closed. Profile x
    maps to the frame normal and profile y to the binormal; the profile is made counter-clockwise first."""
    path = [tuple(float(c) for c in p) for p in path]
    if len(path) < 2 or len(profile) < 3:
        raise meshkit.MeshError("sweep_invalid", "a path of two points and a profile of three")
    shape = [tuple(map(float, p)) for p in profile]
    if meshkit.polygon_area_2d(shape) < 0:
        shape.reverse()
    count = len(path)
    tangents = [meshkit.vnormalize(meshkit.vsub(path[min(k + 1, count - 1)], path[max(k - 1, 0)])) for k in range(count)]
    first = tangents[0]
    helper = (0.0, 1.0, 0.0) if abs(first[1]) < 0.9 else (1.0, 0.0, 0.0)
    normal = meshkit.vnormalize(meshkit.vcross(meshkit.vcross(first, helper), first))
    vertices, frames = [], []
    for k in range(count):
        if k:
            axis = meshkit.vcross(tangents[k - 1], tangents[k])
            size = meshkit.vlength(axis)
            if size > 1e-15:
                normal = _rotate(normal, meshkit.vscale(axis, 1.0 / size), math.atan2(size, meshkit.vdot(tangents[k - 1], tangents[k])))
            normal = meshkit.vnormalize(meshkit.vsub(normal, meshkit.vscale(tangents[k], meshkit.vdot(normal, tangents[k]))))
        u = k / (count - 1)
        angle = math.radians(twist) * u
        n = _rotate(normal, tangents[k], angle)
        b = meshkit.vcross(tangents[k], n)
        scale = 1.0 + (end_scale - 1.0) * u
        frames.append((tangents[k], n, b))
        for x, y in shape:
            vertices.append(meshkit.vadd(path[k], meshkit.vadd(meshkit.vscale(n, scale * x), meshkit.vscale(b, scale * y))))
    sides = len(shape)
    faces = []
    for k in range(count - 1):
        for j in range(sides):
            nj = (j + 1) % sides
            faces.append((k * sides + j, k * sides + nj, (k + 1) * sides + nj, (k + 1) * sides + j))
    if caps:
        triangles = meshkit.triangulate_polygon_2d(shape)
        last = (count - 1) * sides
        faces += [(c, b, a) for a, b, c in triangles]
        faces += [(last + a, last + b, last + c) for a, b, c in triangles]
    mesh = meshkit.Mesh(vertices, faces, name="sweep")
    if meshkit.vdot(meshkit.vcross(frames[0][1], frames[0][2]), frames[0][0]) < 0:
        mesh.faces = [tuple(reversed(face)) for face in mesh.faces]
    return mesh


def build(profile="star", path="arc", end_scale=0.4, twist=90.0, steps=64):
    """The swept demonstration solid, flat shaded so profile corners stay crisp."""
    solid = sweep(demo_profile(profile), demo_path(path, steps), end_scale, twist)
    result = meshkit.flat_shaded(solid)
    result.material = meshkit.material("sweep", (0.80, 0.60, 0.90, 1.0), roughness=0.5)
    return result


def main(argv=None):
    """Command line: write the swept solid (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
