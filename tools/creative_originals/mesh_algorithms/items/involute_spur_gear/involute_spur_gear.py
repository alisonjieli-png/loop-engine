"""Involute spur gear: a tooth profile from base-circle involutes, extruded into a solid with a round bore.

Command line: python3 involute_spur_gear.py --output gear.gltf --teeth 18 --module 0.1 --pressure-angle 20
"""
from __future__ import annotations

import math

import meshkit

PARAMETERS = [
    {"name": "teeth", "type": "int", "default": 18, "unit": "count", "minimum": 6, "maximum": 400,
     "meaning": "Number of teeth."},
    {"name": "module", "type": "float", "default": 0.1, "unit": "m", "minimum": 1e-05, "maximum": 1000.0,
     "meaning": "Pitch diameter divided by the tooth count; meshing gears share it."},
    {"name": "pressure_angle", "type": "float", "default": 20.0, "unit": "degrees", "minimum": 10.0, "maximum": 35.0,
     "meaning": "Angle between the line of action and the pitch circle tangent."},
    {"name": "thickness", "type": "float", "default": 0.25, "unit": "m", "minimum": 1e-06, "maximum": 1000000.0,
     "meaning": "Face width along Y."},
    {"name": "bore_radius", "type": "float", "default": 0.18, "unit": "m", "minimum": 0.0, "maximum": 1000000.0,
     "meaning": "Radius of the centre hole; 0 for none. Must stay inside the root circle."},
    {"name": "flank_samples", "type": "int", "default": 6, "unit": "count", "minimum": 1, "maximum": 200,
     "meaning": "Segments along each involute flank."},
]


def involute_function(angle):
    """inv(a) = tan(a) - a, the polar angle swept by the involute at pressure angle a."""
    return math.tan(angle) - angle


def gear_radii(teeth=18, module=0.1, pressure_angle=20.0):
    """(pitch, base, addendum, root) radii: z m / 2, pitch cos(alpha), pitch + m, pitch - 1.25 m."""
    pitch = module * teeth / 2.0
    return pitch, pitch * math.cos(math.radians(pressure_angle)), pitch + module, pitch - 1.25 * module


def gear_profile(teeth=18, module=0.1, pressure_angle=20.0, flank_samples=6, tip_samples=3, root_samples=4):
    """The counter-clockwise 2D outline of the gear, tooth 0 centred on +X.

    Each tooth: a radial segment from the root circle to the base circle when the root lies inside it, the
    right involute flank, ``tip_samples`` interior points on the addendum arc, the left flank, and
    ``root_samples`` interior points on the root arc to the next tooth. Tooth thickness at the pitch circle
    is half the circular pitch."""
    alpha = math.radians(pressure_angle)
    pitch, base, tip, root = gear_radii(teeth, module, pressure_angle)
    if root <= 0:
        raise meshkit.MeshError("parameter_invalid", "too few teeth for this module: the root circle vanishes")
    start = max(base, root)

    def half_angle(radius):
        return math.pi / (2.0 * teeth) + involute_function(alpha) - involute_function(math.acos(base / radius))

    tip_half = half_angle(tip)
    root_half = half_angle(start)
    if tip_half <= 0:
        raise meshkit.MeshError("teeth_pointed", "the flanks meet below the addendum circle")
    if 2.0 * root_half >= 2.0 * math.pi / teeth:
        raise meshkit.MeshError("teeth_overlap", "neighbouring teeth touch at the root")
    roll_start = math.sqrt(max(0.0, (start / base) ** 2 - 1.0))
    roll_end = math.sqrt((tip / base) ** 2 - 1.0)
    radii = [base * math.sqrt(1.0 + (roll_start + (roll_end - roll_start) * k / flank_samples) ** 2)
             for k in range(flank_samples + 1)]
    radii[-1] = tip
    outline = []

    def polar(radius, angle):
        outline.append((radius * math.cos(angle), radius * math.sin(angle)))

    for tooth in range(teeth):
        centre = 2.0 * math.pi * tooth / teeth
        if root < base:
            polar(root, centre - half_angle(base))
        for radius in radii:
            polar(radius, centre - half_angle(radius))
        for k in range(1, tip_samples + 1):
            polar(tip, centre - tip_half + 2.0 * tip_half * k / (tip_samples + 1))
        for radius in reversed(radii):
            polar(radius, centre + half_angle(radius))
        if root < base:
            polar(root, centre + half_angle(base))
        gap_start, gap_end = centre + root_half, centre + 2.0 * math.pi / teeth - root_half
        for k in range(1, root_samples + 1):
            polar(root, gap_start + (gap_end - gap_start) * k / (root_samples + 1))
    return outline


def spur_gear(teeth=18, module=0.1, pressure_angle=20.0, thickness=0.25, bore_radius=0.18, flank_samples=6):
    """The gear extruded along Y and centred at the origin: two capped faces (triangulated around the bore)
    and quad side walls, closed and outward. With a bore the solid has genus 1."""
    outline = gear_profile(teeth, module, pressure_angle, flank_samples)
    _pitch, _base, _tip, root = gear_radii(teeth, module, pressure_angle)
    if bore_radius < 0 or bore_radius >= root or thickness <= 0:
        raise meshkit.MeshError("parameter_invalid", "0 <= bore_radius < root radius and thickness > 0")
    holes = []
    if bore_radius > 0:
        count = max(12, 4 * int(math.ceil(teeth / 4)))
        holes = [[(bore_radius * math.cos(-2 * math.pi * k / count), bore_radius * math.sin(-2 * math.pi * k / count))
                  for k in range(count)]]
    return _extrude(outline, holes, thickness)


def _extrude(outline, holes, thickness):
    rings = [outline] + holes
    flat = [p for ring in rings for p in ring]
    half = thickness / 2.0
    vertices = [meshkit.plane_to_3d(p, -half) for p in flat] + [meshkit.plane_to_3d(p, half) for p in flat]
    top = len(flat)
    faces = []
    for a, b, c in meshkit.triangulate_polygon_2d(outline, holes):
        faces.append((top + a, top + b, top + c))
        faces.append((c, b, a))
    start = 0
    for ring in rings:
        count = len(ring)
        for k in range(count):
            a, b = start + k, start + (k + 1) % count
            faces.append((a, b, top + b, top + a))
        start += count
    mesh = meshkit.Mesh(vertices, faces, name="spur_gear",
                        material=meshkit.material("gear", (0.70, 0.66, 0.58, 1.0), metallic=0.7, roughness=0.4))
    return mesh


def build(teeth=18, module=0.1, pressure_angle=20.0, thickness=0.25, bore_radius=0.18, flank_samples=6):
    """The gear the command line writes: each cap shares its vertices under one flat normal and every wall quad
    owns its corners, so edges between caps and walls and between flank segments stay crisp."""
    solid = spur_gear(teeth, module, pressure_angle, thickness, bore_radius, flank_samples)
    vertices, normals, faces, shared = [], [], [], {}
    for face in solid.faces:
        normal = meshkit.face_normal(solid.vertices, face)
        if abs(normal[1]) > 0.999:
            side = 1.0 if normal[1] > 0 else -1.0
            corners = []
            for index in face:
                key = (index, side)
                if key not in shared:
                    shared[key] = len(vertices)
                    vertices.append(solid.vertices[index])
                    normals.append((0.0, side, 0.0))
                corners.append(shared[key])
            faces.append(tuple(corners))
        else:
            start = len(vertices)
            for index in face:
                vertices.append(solid.vertices[index])
                normals.append(normal)
            faces.append(tuple(range(start, start + len(face))))
    return meshkit.Mesh(vertices, faces, normals=normals, name="spur_gear",
                        material=meshkit.material("gear", (0.70, 0.66, 0.58, 1.0), metallic=0.7, roughness=0.4))


def main(argv=None):
    """Command line: write the gear as .gltf or .obj and print a JSON summary."""
    return meshkit.run_cli(argv, description=__doc__, parameters=PARAMETERS, build=build)


if __name__ == "__main__":
    raise SystemExit(main())
