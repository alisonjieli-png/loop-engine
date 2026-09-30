"""Original static asset constructors and explicit sizing contracts.

Each family is one capability. Boundary/reference variants are data and never
count as different implementations. No external model, texture or prompt is copied.
"""
from __future__ import annotations

import itertools
import math

from .geometry import box, convex, inspect_mesh, round_body

FAMILIES = {
    "bear": ("Rounded bear character reference", (0.7, 1.0, 0.55), "character"),
    "round_creature": ("Round creature with feet and face", (0.8, 0.8, 0.7), "character"),
    "humanoid_proxy": ("Standing humanoid proportion blockout", (0.6, 1.8, 0.35), "body_reference"),
    "quadruped_proxy": ("Four-legged creature proportion blockout", (0.65, 1.0, 1.3), "body_reference"),
    "conifer": ("Layered conifer tree blockout", (2.8, 6.0, 2.8), "foliage"),
    "broadleaf": ("Broadleaf tree with clustered crown", (4.0, 5.0, 3.5), "foliage"),
    "boulder": ("Low-poly rounded rock reference", (1.6, 0.9, 1.1), "terrain_prop"),
    "house": ("Gabled house with door and windows", (6.0, 5.0, 7.0), "architecture"),
    "fence": ("Three-post fence section", (3.0, 1.2, 0.18), "architecture"),
    "vehicle": ("Four-wheel vehicle silhouette blockout", (1.8, 1.6, 4.2), "vehicle"),
    "water_surface": ("Analytic static water-wave reference", (8.0, 0.3, 8.0), "surface"),
    "sun_disc": ("Visible sun-disc mesh, not a light source", (2.0, 2.0, 0.2), "sky_reference"),
}
PALETTE = {"warm": [0.73, 0.47, 0.26], "cream": [0.94, 0.84, 0.62], "dark": [0.06, 0.09, 0.11],
           "leaf": [0.22, 0.56, 0.38], "bark": [0.33, 0.24, 0.17], "stone": [0.52, 0.57, 0.61],
           "wall": [0.92, 0.77, 0.59], "roof": [0.58, 0.23, 0.2], "glass": [0.3, 0.66, 0.75],
           "blue": [0.2, 0.46, 0.71], "sun": [1.0, 0.77, 0.19]}


def parameter_schema(family):
    _description, defaults, _category = FAMILIES[family]
    return {"type": "object", "additionalProperties": False, "required": ["width", "height", "depth"],
            "properties": {name: {"type": "number", "minimum": value * 0.5, "maximum": value * 1.5,
                                   "default": value, "description": "metres; constructor envelope, not measured anatomy"}
                           for name, value in zip(("width", "height", "depth"), defaults)}}


def construct(family, width, height, depth):
    if family not in FAMILIES:
        raise ValueError("unknown_asset_family")
    defaults = FAMILIES[family][1]
    for value, default in zip((width, height, depth), defaults):
        if type(value) not in (int, float) or not math.isfinite(value) or not default * 0.5 <= value <= default * 1.5:
            raise ValueError("size_outside_declared_range")
    w, h, d, parts = width, height, depth, []

    def cube(name, at, size, color):
        parts.append(box(name, at, size, PALETTE[color]))

    def blob(name, at, size, color, form="ellipsoid", axis=1):
        parts.append(round_body(name, at, size, PALETTE[color], form=form, axis=axis))

    if family in ("bear", "round_creature"):
        bear = family == "bear"
        blob("body", [0, h * (0.39 if bear else 0.5), 0], [w * 0.75, h * (0.57 if bear else 0.8), d * 0.85], "warm" if bear else "blue")
        if bear:
            blob("head", [0, h * 0.72, 0], [w * 0.85, h * 0.38, d * 0.85], "warm")
        face_y = h * (0.76 if bear else 0.62)
        for sign, side in ((-1, "left"), (1, "right")):
            blob(side + "_foot", [sign * w * 0.23, h * 0.1, -d * 0.13], [w * 0.3, h * 0.2, d * 0.6], "warm" if bear else "cream")
            blob(side + "_eye", [sign * w * 0.18, face_y, -d * 0.4], [w * 0.09, h * 0.06, d * 0.07], "dark")
            if bear:
                blob(side + "_ear", [sign * w * 0.32, h * 0.905, 0], [w * 0.23, h * 0.17, d * 0.23], "warm")
                blob(side + "_arm", [sign * w * 0.38, h * 0.43, 0], [w * 0.24, h * 0.34, d * 0.3], "warm")
        blob("muzzle", [0, face_y - h * 0.07, -d * 0.41], [w * 0.38, h * 0.15, d * 0.23], "cream")
        blob("nose", [0, face_y - h * 0.035, -d * 0.53], [w * 0.13, h * 0.06, d * 0.08], "dark")
    elif family == "humanoid_proxy":
        blob("torso", [0, h * 0.6, 0], [w * 0.65, h * 0.32, d], "blue")
        blob("head", [0, h * 0.89, 0], [w * 0.48, h * 0.22, d * 0.8], "cream")
        for sign, side in ((-1, "left"), (1, "right")):
            blob(side + "_leg", [sign * w * 0.18, h * 0.25, 0], [w * 0.25, h * 0.5, d * 0.8], "dark")
            blob(side + "_arm", [sign * w * 0.4, h * 0.56, 0], [w * 0.2, h * 0.35, d * 0.65], "cream")
    elif family == "quadruped_proxy":
        blob("torso", [0, h * 0.6, 0], [w, h * 0.5, d * 0.7], "warm")
        blob("head", [0, h * 0.84, -d * 0.4], [w * 0.65, h * 0.32, d * 0.3], "cream")
        for x, z in itertools.product((-1, 1), repeat=2):
            blob(f"leg_{x}_{z}", [x * w * 0.3, h * 0.23, z * d * 0.24], [w * 0.22, h * 0.46, d * 0.16], "warm")
    elif family in ("conifer", "broadleaf"):
        blob("trunk", [0, h * 0.33, 0], [w * 0.13, h * 0.66, d * 0.13], "bark", "cylinder")
        if family == "conifer":
            for i in range(3):
                blob(f"canopy_{i}", [0, h * (0.39 + i * 0.19), 0],
                     [w * (1 - i * 0.22), h * 0.46, d * (1 - i * 0.22)], "leaf", "cone")
        else:
            blob("crown", [0, h * 0.76, 0], [w * 0.78, h * 0.48, d], "leaf")
            for sign in (-1, 1):
                blob(f"branch_crown_{sign}", [sign * w * 0.28, h * 0.65, 0], [w * 0.44, h * 0.36, d * 0.8], "leaf")
    elif family == "boulder":
        blob("rock", [0, h / 2, 0], [w, h, d], "stone")
    elif family == "house":
        cube("walls", [0, h * 0.35, 0], [w, h * 0.7, d], "wall")
        vertices = []
        for z in (-d / 2, d / 2):
            vertices.extend([[-w / 2, h * 0.7, z], [w / 2, h * 0.7, z], [0, h, z]])
        faces = [(0, 1, 2), (3, 5, 4), (0, 3, 4), (0, 4, 1), (1, 4, 5), (1, 5, 2), (2, 5, 3), (2, 3, 0)]
        parts.append(convex("gable_roof", vertices, faces, [0, h * 0.8, 0], PALETTE["roof"]))
        cube("door", [0, h * 0.22, -d * 0.506], [w * 0.16, h * 0.44, d * 0.02], "bark")
        for sign in (-1, 1):
            cube(f"window_{sign}", [sign * w * 0.3, h * 0.42, -d * 0.51], [w * 0.19, h * 0.2, d * 0.025], "glass")
    elif family == "fence":
        for i in (-1, 0, 1):
            cube(f"post_{i}", [i * w * 0.46, h / 2, 0], [w * 0.08, h, d], "bark")
        for i in (0.3, 0.7):
            cube(f"rail_{i}", [0, h * i, 0], [w, h * 0.15, d * 0.6], "warm")
    elif family == "vehicle":
        cube("chassis", [0, h * 0.4, 0], [w * 0.84, h * 0.35, d], "blue")
        cube("cabin", [0, h * 0.78, d * 0.02], [w * 0.76, h * 0.44, d * 0.5], "glass")
        for x, z in itertools.product((-1, 1), repeat=2):
            blob(f"wheel_{x}_{z}", [x * w * 0.44, h * 0.19, z * d * 0.31],
                 [w * 0.12, h * 0.38, h * 0.38], "dark", "cylinder", axis=0)
    elif family == "water_surface":
        vertices, faces, steps = [], [], 12
        for z in range(steps + 1):
            for x in range(steps + 1):
                vertices.append([w * (x / steps - 0.5), h * 0.5 * math.sin(x * math.tau / steps) * math.cos(z * math.tau / steps), d * (z / steps - 0.5)])
        for z in range(steps):
            for x in range(steps):
                a = z * (steps + 1) + x
                faces.extend([(a, a + steps + 1, a + 1), (a + 1, a + steps + 1, a + steps + 2)])
        parts.append({"name": "wave_surface", "vertices": vertices, "triangles": faces, "color": PALETTE["glass"]})
    elif family == "sun_disc":
        blob("visible_disc", [0, h / 2, 0], [w, h, d], "sun")
    inspect_mesh(parts)
    return parts


def reference_cases(family):
    """Fifteen purposeful range cases: standard, six single-axis bounds and eight corners."""
    defaults = FAMILIES[family][1]
    yield "standard", dict(zip(("width", "height", "depth"), defaults))
    for axis, name in enumerate(("width", "height", "depth")):
        for label, factor in (("minimum", 0.5), ("maximum", 1.5)):
            values = list(defaults)
            values[axis] *= factor
            yield name + "_" + label, dict(zip(("width", "height", "depth"), values))
    for factors in itertools.product((0.5, 1.5), repeat=3):
        name = "boundary_" + "_".join("small" if x == 0.5 else "large" for x in factors)
        yield name, dict(zip(("width", "height", "depth"), [a * b for a, b in zip(defaults, factors)]))
