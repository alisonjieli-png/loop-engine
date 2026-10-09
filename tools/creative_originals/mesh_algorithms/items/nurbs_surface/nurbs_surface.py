"""Tensor-product NURBS surfaces: rational de Boor in two directions, with an exact sphere and torus built as
surfaces of revolution.

Command line: python3 nurbs_surface.py --output nurbs_surface.gltf --shape torus --u-samples 48 --v-samples 24
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "shape", "type": "str", "default": "torus", "unit": "name", "choices": ["sphere", "torus", "wave"],
     "meaning": "Demonstration surface: exact sphere, exact torus or a free-form wave patch."},
    {"name": "u_samples", "type": "int", "default": 48, "unit": "count", "minimum": 2, "maximum": 4096,
     "meaning": "Grid lines across the first parameter."},
    {"name": "v_samples", "type": "int", "default": 24, "unit": "count", "minimum": 2, "maximum": 4096,
     "meaning": "Grid lines across the second parameter."},
]
_QUARTER = [0.0, 0.0, 0.0, 0.25, 0.25, 0.5, 0.5, 0.75, 0.75, 1.0, 1.0, 1.0]


def _span(knots, degree, count, t):
    if t >= knots[count]:
        return count - 1
    span = degree
    while span < count - 1 and knots[span + 1] <= t:
        span += 1
    return span


def _de_boor(rows, degree, knots, t):
    count = len(rows)
    span = _span(knots, degree, count, t)
    points = [list(rows[span - degree + j]) for j in range(degree + 1)]
    for r in range(1, degree + 1):
        for j in range(degree, r - 1, -1):
            left, right = knots[span - degree + j], knots[span + 1 + j - r]
            alpha = 0.0 if right == left else (t - left) / (right - left)
            points[j] = [(1.0 - alpha) * a + alpha * b for a, b in zip(points[j - 1], points[j])]
    return points[degree]


def surface_point(surface, u, v):
    """Point at (u, v): each control row is reduced at v in homogeneous coordinates, then the column at u."""
    controls, weights, degree_u, degree_v, knots_u, knots_v = surface
    column = []
    for row, row_weights in zip(controls, weights):
        homogeneous = [[w * c for c in point] + [w] for point, w in zip(row, row_weights)]
        column.append(_de_boor(homogeneous, degree_v, knots_v, v))
    h = _de_boor(column, degree_u, knots_u, u)
    return (h[0] / h[3], h[1] / h[3], h[2] / h[3])


def revolve_profile(profile, profile_weights, profile_degree, profile_knots):
    """Surface of revolution about Y: an (r, y) NURBS profile times the nine-point exact circle.

    Returns (controls, weights, degree_u, degree_v, knots_u, knots_v) with u along the profile and v around."""
    corner = math.sqrt(0.5)
    square = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0)]
    controls, weights = [], []
    for (r, y), w in zip(profile, profile_weights):
        controls.append([(r * x, y, -r * z) for x, z in square])
        weights.append([w * (1.0 if k % 2 == 0 else corner) for k in range(9)])
    return controls, weights, profile_degree, 2, list(profile_knots), list(_QUARTER)


def sphere_surface(radius=1.0):
    """Exact sphere: a five-point rational semicircle from the south to the north pole, revolved."""
    corner = math.sqrt(0.5)
    profile = [(0.0, -radius), (radius, -radius), (radius, 0.0), (radius, radius), (0.0, radius)]
    return revolve_profile(profile, [1.0, corner, 1.0, corner, 1.0], 2, [0.0, 0.0, 0.0, 0.5, 0.5, 1.0, 1.0, 1.0])


def torus_surface(major_radius=1.0, minor_radius=0.35):
    """Exact torus: the nine-point circle of the tube cross-section, revolved."""
    corner = math.sqrt(0.5)
    square = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1), (1, 0)]
    profile = [(major_radius + minor_radius * x, minor_radius * y) for x, y in square]
    return revolve_profile(profile, [1.0 if k % 2 == 0 else corner for k in range(9)], 2, _QUARTER)


def wave_surface():
    """A bicubic free-form patch over [-1.5, 1.5]^2 with a 5 x 5 control net and unit weights."""
    controls = [[(x, 0.5 * math.sin(1.7 * x) * math.cos(1.3 * z), z) for z in (-1.5, -0.75, 0.0, 0.75, 1.5)]
                for x in (-1.5, -0.75, 0.0, 0.75, 1.5)]
    knots = [0.0, 0.0, 0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 1.0]
    return controls, [[1.0] * 5 for _ in range(5)], 3, 3, knots, list(knots)


def tessellate(surface, u_samples=48, v_samples=24, closed_v=False):
    """A grid mesh of u_samples x v_samples points evenly spaced in the parameters, normals from central
    differences in parameter space. ``closed_v`` leaves out the repeated last column of a closed direction."""
    _c, _w, degree_u, degree_v, knots_u, knots_v = surface
    u0, u1 = knots_u[degree_u], knots_u[-degree_u - 1]
    v0, v1 = knots_v[degree_v], knots_v[-degree_v - 1]
    columns = v_samples if closed_v else v_samples
    vertices, normals = [], []
    h = 1e-6
    for i in range(u_samples):
        u = u0 + (u1 - u0) * i / (u_samples - 1)
        for j in range(columns):
            v = v0 + (v1 - v0) * j / (v_samples if closed_v else v_samples - 1)
            vertices.append(surface_point(surface, u, v))
            du = meshkit.vsub(surface_point(surface, min(u1, u + h), v), surface_point(surface, max(u0, u - h), v))
            dv = meshkit.vsub(surface_point(surface, u, min(v1, v + h)), surface_point(surface, u, max(v0, v - h)))
            normals.append(meshkit.vnormalize(meshkit.vcross(du, dv), (0.0, 0.0, 0.0)))
    faces = []
    for i in range(u_samples - 1):
        for j in range(columns if closed_v else columns - 1):
            nj = (j + 1) % columns
            faces.append((i * columns + j, (i + 1) * columns + j, (i + 1) * columns + nj, i * columns + nj))
    mesh = meshkit.Mesh(vertices, faces, normals=normals, name="nurbs_surface")
    mesh.normals = [n if meshkit.vlength(n) > 0.5 else m for n, m in zip(normals, meshkit.vertex_normals(mesh))]
    if meshkit.signed_volume(mesh) < 0 and closed_v:
        mesh.faces = [tuple(reversed(f)) for f in mesh.faces]
    return mesh


def build(shape="torus", u_samples=48, v_samples=24):
    """The tessellated demonstration surface the command line writes."""
    if shape == "sphere":
        mesh = tessellate(sphere_surface(), u_samples, v_samples, closed_v=True)
    elif shape == "torus":
        mesh = tessellate(torus_surface(), u_samples, v_samples, closed_v=True)
    elif shape == "wave":
        mesh = tessellate(wave_surface(), u_samples, v_samples)
    else:
        raise meshkit.MeshError("shape_unknown", str(shape))
    mesh.material = meshkit.material("nurbs", (0.62, 0.80, 0.92, 1.0), double_sided=(shape == "wave"))
    return mesh


def main(argv=None):
    """Command line: write the tessellated surface (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
