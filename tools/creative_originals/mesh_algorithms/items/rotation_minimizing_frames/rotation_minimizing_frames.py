"""Rotation-minimizing frames along a polyline by the double reflection method, with Frenet frames for
comparison and an optional closing twist.

Command line: python3 rotation_minimizing_frames.py --output rmf.gltf --curve trefoil --width 0.25
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "curve", "type": "str", "default": "trefoil", "unit": "name", "choices": ["trefoil", "helix", "wave"],
     "meaning": "Demonstration curve the ribbon follows."},
    {"name": "width", "type": "float", "default": 0.25, "unit": "m", "minimum": 0.001, "maximum": 100.0,
     "meaning": "Ribbon width across the frame normal."},
    {"name": "samples", "type": "int", "default": 300, "unit": "count", "minimum": 4, "maximum": 100000,
     "meaning": "Samples along the curve."},
]


def double_reflection_frames(points, tangents=None, normal=None):
    """Frames (tangent, normal, binormal) along sampled points by double reflection (Wang, Juttler, Zheng and
    Liu 2008): reflect the previous frame in the bisector plane of the chord, then in the plane that maps the
    reflected tangent onto the next tangent. Fourth-order accurate for smooth curves. Without ``tangents``,
    central differences of an open polyline are used; without ``normal``, one perpendicular to the first
    tangent is chosen."""
    points = [tuple(float(c) for c in p) for p in points]
    if tangents is None:
        tangents = _tangents(points, False)
    tangents = [meshkit.vnormalize(t) for t in tangents]
    first = tangents[0]
    if normal is None:
        helper = (0.0, 1.0, 0.0) if abs(first[1]) < 0.9 else (1.0, 0.0, 0.0)
        normal = meshkit.vcross(meshkit.vcross(first, helper), first)
    r = meshkit.vnormalize(meshkit.vsub(normal, meshkit.vscale(first, meshkit.vdot(normal, first))))
    frames = [(first, r, meshkit.vcross(first, r))]
    for i in range(len(points) - 1):
        v1 = meshkit.vsub(points[i + 1], points[i])
        c1 = meshkit.vdot(v1, v1)
        t, r = frames[-1][0], frames[-1][1]
        if c1 <= 1e-30:
            frames.append((tangents[i + 1], r, meshkit.vcross(tangents[i + 1], r)))
            continue
        r_left = meshkit.vsub(r, meshkit.vscale(v1, 2.0 / c1 * meshkit.vdot(v1, r)))
        t_left = meshkit.vsub(t, meshkit.vscale(v1, 2.0 / c1 * meshkit.vdot(v1, t)))
        v2 = meshkit.vsub(tangents[i + 1], t_left)
        c2 = meshkit.vdot(v2, v2)
        r_next = r_left if c2 <= 1e-30 else meshkit.vsub(r_left, meshkit.vscale(v2, 2.0 / c2 * meshkit.vdot(v2, r_left)))
        r_next = meshkit.vnormalize(meshkit.vsub(r_next, meshkit.vscale(tangents[i + 1], meshkit.vdot(r_next, tangents[i + 1]))))
        frames.append((tangents[i + 1], r_next, meshkit.vcross(tangents[i + 1], r_next)))
    return frames


def frenet_frames(points):
    """Frenet frames from finite differences (normal toward the centre of curvature); undefined where the
    curve is straight, where the previous normal is kept."""
    frames = []
    count = len(points)
    for i in range(count):
        a, b, c = points[max(i - 1, 0)], points[i], points[min(i + 1, count - 1)]
        tangent = meshkit.vnormalize(meshkit.vsub(c, a))
        bend = meshkit.vsub(meshkit.vadd(a, c), meshkit.vscale(b, 2.0))
        normal = meshkit.vsub(bend, meshkit.vscale(tangent, meshkit.vdot(bend, tangent)))
        if meshkit.vlength(normal) < 1e-12:
            normal = frames[-1][1] if frames else meshkit.vcross(tangent, (0.0, 1.0, 0.0))
        normal = meshkit.vnormalize(normal, (1.0, 0.0, 0.0))
        frames.append((tangent, normal, meshkit.vcross(tangent, normal)))
    return frames


def frame_normals(points, closed=False):
    """Just the normals of the rotation-minimizing frames for points with central-difference tangents."""
    return [frame[1] for frame in double_reflection_frames(points, _tangents(points, closed))]


def closing_twist(points, frames):
    """For a closed curve: the angle (radians, about the first tangent) between the first normal and the last
    frame carried once more across the closing chord. Zero means the frames join without a twist."""
    last_t, last_n = frames[-1][0], frames[-1][1]
    carried = double_reflection_frames([points[-1], points[0]], [last_t, frames[0][0]], last_n)[1][1]
    return math.atan2(meshkit.vdot(carried, frames[0][2]), meshkit.vdot(carried, frames[0][1]))


def twist_between(frames_a, frames_b):
    """Signed angle (radians) of each normal of ``frames_b`` relative to the matching normal of ``frames_a``,
    about the tangent of ``frames_a``."""
    return [math.atan2(meshkit.vdot(b[1], a[2]), meshkit.vdot(b[1], a[1])) for a, b in zip(frames_a, frames_b)]


def _tangents(points, closed):
    count = len(points)
    result = []
    for i in range(count):
        if closed:
            a, c = points[i - 1], points[(i + 1) % count]
        else:
            a, c = points[max(i - 1, 0)], points[min(i + 1, count - 1)]
        result.append(meshkit.vnormalize(meshkit.vsub(c, a)))
    return result


def demo_curve(curve="trefoil", samples=300):
    """Points of a demonstration curve: a closed trefoil knot, a three-turn helix or an open wave."""
    points = []
    for k in range(samples):
        if curve == "trefoil":
            t = 2.0 * math.pi * k / samples
            points.append((math.sin(t) + 2.0 * math.sin(2 * t), -math.sin(3 * t), math.cos(t) - 2.0 * math.cos(2 * t)))
        elif curve == "helix":
            t = 6.0 * math.pi * k / (samples - 1)
            points.append((math.cos(t), 0.25 * t - 2.4, -math.sin(t)))
        elif curve == "wave":
            x = -3.0 + 6.0 * k / (samples - 1)
            points.append((x, 0.6 * math.sin(2.0 * x), 0.6 * math.cos(1.3 * x)))
        else:
            raise meshkit.MeshError("curve_unknown", str(curve))
    return points


def ribbon(points, frames, width=0.25, closed=False, spread_twist=True):
    """A two-sided strip across each frame's binormal (the strip faces along the normal); a closed curve can
    spread its closing twist evenly so the strip joins without a jump."""
    count = len(points)
    twist = closing_twist(points, frames) if closed and spread_twist else 0.0
    vertices, normals, faces = [], [], []
    for k, (point, (tangent, normal, binormal)) in enumerate(zip(points, frames)):
        angle = -twist * k / count
        n = meshkit.vadd(meshkit.vscale(normal, math.cos(angle)), meshkit.vscale(binormal, math.sin(angle)))
        b = meshkit.vcross(tangent, n)
        for side in (-0.5, 0.5):
            vertices.append(meshkit.vadd(point, meshkit.vscale(b, side * width)))
            normals.append(n)
    for k in range(count if closed else count - 1):
        nk = (k + 1) % count
        faces.append((2 * k, 2 * k + 1, 2 * nk + 1, 2 * nk))
    return meshkit.Mesh(vertices, faces, normals=normals, name="ribbon",
                        material=meshkit.material("ribbon", (0.40, 0.78, 0.70, 1.0), double_sided=True))


def build(curve="trefoil", width=0.25, samples=300):
    """The ribbon along the demonstration curve, oriented by rotation-minimizing frames."""
    closed = curve == "trefoil"
    points = demo_curve(curve, samples)
    frames = double_reflection_frames(points, _tangents(points, closed))
    return ribbon(points, frames, width, closed)


def main(argv=None):
    """Command line: write the ribbon (.gltf or .obj) and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
