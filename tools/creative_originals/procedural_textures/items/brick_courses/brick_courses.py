"""Brick wall in running, Flemish, English or stack bond: tileable PBR maps from the standard library only.

Courses are laid out in texture space from a bond pattern (brick lengths in header units and an offset per course),
so the wall repeats every two courses. Each brick gets its own colour, face height, tilt and roughness from a hash of
its index; mortar joints are recessed, brick edges are rounded and chipped by noise.
"""
from __future__ import annotations

import math
import sys
from bisect import bisect_right

import texkit as tk

IDENTITY = "brick_courses"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.15, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "bond", "type": "int", "default": 0, "minimum": 0, "maximum": 3,
     "meaning": "0 running (stretchers offset by half a brick), 1 Flemish (headers and stretchers alternate in each "
                "course), 2 English (stretcher and header courses alternate), 3 stack (joints aligned)."},
    {"name": "course_pairs", "type": "int", "default": 4, "minimum": 1, "maximum": 12,
     "meaning": "Pairs of courses across the tile height; every bond repeats after two courses."},
    {"name": "bricks_per_course", "type": "int", "default": 3, "minimum": 1, "maximum": 10,
     "meaning": "Stretchers per course across the tile width (Flemish: header and stretcher pairs)."},
    {"name": "mortar_width", "type": "float", "default": 0.012, "minimum": 0.002, "maximum": 0.04,
     "meaning": "Joint width in texture units (fractions of the tile width)."},
    {"name": "joint_depth", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far the mortar sits below the brick faces: 0 flush, 1 deeply raked."},
    {"name": "bevel", "type": "float", "default": 0.008, "minimum": 0.001, "maximum": 0.03,
     "meaning": "Width of the rounded brick edge in texture units."},
    {"name": "chipping", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Broken and eroded brick edges, 0 crisp to 1 heavily damaged."},
    {"name": "colour_variation", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of colour between bricks."},
    {"name": "grime", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Soot and dirt in the joints and on the faces."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Red clay bricks in running bond with light grey mortar.", "values": {}},
    "weathered": {"description": "Old dark bricks, chipped edges, deep joints, soot and white salt bloom.",
                  "values": {"chipping": 0.8, "joint_depth": 0.8, "grime": 0.7, "colour_variation": 0.8}},
    "flemish_buff": {"description": "Buff yellow bricks in Flemish bond with darker headers.",
                     "values": {"bond": 1, "bricks_per_course": 2, "chipping": 0.15}},
    "english_brown": {"description": "Brown bricks in English bond with dark mortar.",
                      "values": {"bond": 2, "bricks_per_course": 3, "grime": 0.35}},
    "glazed_stack": {"description": "Glossy white glazed bricks in stack bond with thin flush joints.",
                     "values": {"bond": 3, "bricks_per_course": 4, "course_pairs": 6, "mortar_width": 0.006,
                                "joint_depth": 0.25, "chipping": 0.05, "colour_variation": 0.15, "grime": 0.05,
                                "bevel": 0.004}},
}
#: Brick colours, mortar colour, header tint, face roughness, salt bloom and blotch strength per preset (sRGB).
PALETTES = {
    "default": (["#8e3b2b", "#a34a34", "#7c3326", "#b25b3e", "#93422f"], "#b9b2a5", "#6a2a20", 0.82, 0.0, 0.1),
    "weathered": (["#6f3428", "#5e2c22", "#7f3d2c", "#4f2a22", "#86492f"], "#a39d92", "#3a1f1a", 0.88, 0.5, 0.16),
    "flemish_buff": (["#c9a46a", "#d4b077", "#bf9a5f", "#d9bb84", "#c49f63"], "#d8d2c4", "#7d5a34", 0.8, 0.0, 0.08),
    "english_brown": (["#6b4532", "#7a503a", "#5f3c2b", "#83583f", "#704a35"], "#5a554e", "#4a2e22", 0.84, 0.0, 0.1),
    "glazed_stack": (["#e8e6df", "#efede6", "#e1dfd7", "#f2f0ea", "#e5e3dc"], "#c9c6be", "#d8d5cc", 0.18, 0.0, 0.02),
}
#: Brick lengths in header units and the offset in units of each of the two courses, per bond.
BONDS = {
    0: (lambda n: [2.0] * n, 0.0, lambda n: [2.0] * n, 1.0),
    1: (lambda n: [1.0, 2.0] * n, 0.0, lambda n: [1.0, 2.0] * n, 1.5),
    2: (lambda n: [2.0] * n, 0.0, lambda n: [1.0] * (2 * n), 0.5),
    3: (lambda n: [2.0] * n, 0.0, lambda n: [2.0] * n, 0.0),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The brick maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    bricks, mortar_hex, header_hex, face_rough, bloom, blotch = PALETTES[preset]
    brick_colours = [tk.hex_rgb(code) for code in bricks]
    mortar = tk.hex_rgb(mortar_hex)
    header = tk.hex_rgb(header_hex)
    rows = 2 * p["course_pairs"]
    first, first_offset, second, second_offset = BONDS[p["bond"]]
    courses = []
    for lengths, offset in ((first(p["bricks_per_course"]), first_offset),
                            (second(p["bricks_per_course"]), second_offset)):
        bounds = [0.0]
        for length in lengths:
            bounds.append(bounds[-1] + length)
        courses.append((bounds, lengths, offset))
    units = courses[0][0][-1]
    unit, course_height = 1.0 / units, 1.0 / rows
    half = p["mortar_width"] * 0.5
    bevel = p["bevel"]
    chip_reach = p["chipping"] * (p["mortar_width"] + 0.01)
    variation, grime = p["colour_variation"], p["grime"]
    count = rows * max(len(courses[0][1]), len(courses[1][1]))
    rng = tk.Rng(seed, 0xB1)
    traits = [(rng.random(), rng.random(), rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1),
               rng.random(), rng.random()) for _ in range(count)]
    undulation = tk.fbm(width, height, 8, 4, tk.hash_u32(seed, 1))
    chips = tk.fbm(width, height, 16, 4, tk.hash_u32(seed, 2))
    blotches = tk.fbm(width, height, 4, 4, tk.hash_u32(seed, 3))
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    pixel = 1.0 / width
    heights, mask, ids, headers = [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        k = min(int(v * rows), rows - 1)
        local_y = v * rows - k
        dy = min(local_y, 1.0 - local_y) * course_height
        bounds, lengths, offset = courses[k % 2]
        per = len(lengths)
        base = y * width
        for x in range(width):
            index = base + x
            position = ((x + 0.5) / width * units - offset) % units
            s = min(bisect_right(bounds, position) - 1, per - 1)
            start, length = bounds[s], lengths[s]
            dx = min(position - start, start + length - position) * unit
            chip = chips[index]
            inside = min(dx, dy) - half - chip_reach * (chip + 0.15 if chip > -0.15 else 0.0)
            brick = k * per + s
            trait = traits[brick % count]
            if inside <= 0.0:
                level = 0.5 - 0.42 * p["joint_depth"] + 0.04 * undulation[index]
            else:
                t = inside / bevel
                profile = 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
                bx = (position - start) / length - 0.5
                top = 0.82 + 0.05 * trait[2] + 0.04 * (trait[3] * bx + trait[4] * (local_y - 0.5)) \
                    + 0.05 * undulation[index]
                low = 0.5 - 0.42 * p["joint_depth"]
                level = low + (top - low) * profile
            heights.append(level)
            mask.append(tk.smoothstep(-pixel, pixel, inside))
            ids.append(brick % count)
            headers.append(length < 1.5)
    red, green, blue, rough = [], [], [], []
    palette_size = len(brick_colours)
    for index in range(width * height):
        trait = traits[ids[index]]
        pick = trait[0] * variation + (1.0 - variation) * 0.5
        position = pick * (palette_size - 1)
        low_index = min(int(position), palette_size - 2)
        f = position - low_index
        c0, c1 = brick_colours[low_index], brick_colours[low_index + 1]
        colour = [a + (b - a) * f for a, b in zip(c0, c1)]
        if p["bond"] == 1 and headers[index]:
            colour = [a + (b - a) * (0.25 + 0.4 * variation) for a, b in zip(colour, header)]
        tone = 1.0 + blotch * blotches[index] + 0.08 * (grain[index] - 0.5) + 0.16 * (trait[1] - 0.5) * variation
        dirt = grime * max(0.0, -0.1 - blotches[index]) * 1.2
        brick_rgb = [c * tone * (1.0 - dirt) for c in colour]
        speck = grain[index]
        mortar_tone = 0.9 + 0.2 * speck - 0.35 * grime
        mortar_rgb = [c * mortar_tone for c in mortar]
        m = mask[index]
        rgb = [b * m + a * (1.0 - m) for a, b in zip(mortar_rgb, brick_rgb)]
        if bloom and blotches[index] > 0.12:
            salt = bloom * min(1.0, (blotches[index] - 0.12) * 5.0) * (1.0 - 0.7 * m) * (0.6 + 0.4 * speck)
            rgb = [c + (0.84 - c) * salt for c in rgb]
        red.append(rgb[0])
        green.append(rgb[1])
        blue.append(rgb[2])
        rough.append(m * (face_rough + 0.06 * (trait[5] - 0.5) + 0.05 * speck) + (1.0 - m) * 0.95)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.018, roughness=rough,
                     ao_radius=0.02, ao_strength=1.2, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
