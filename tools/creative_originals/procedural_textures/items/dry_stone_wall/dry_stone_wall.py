"""Dry stone wall: irregular flat stones stacked in rough courses without mortar, tileable PBR maps (standard library).

Courses of random height fill the tile height and each course is split into stones of random length that wrap
around the tile width. Every stone is a rounded, slightly tilted slab: a rotated rounded rectangle whose outline is
roughened by noise, shrunk from its slot so dark voids open between neighbours. A pixel takes the nearest stone among
its own course's three closest slots and the slots above and below. Small chinking stones wedge into the joints,
and lichen patches and moss grow on faces and in crevices.
"""
from __future__ import annotations

import math
import sys
from bisect import bisect_right

import texkit as tk

IDENTITY = "dry_stone_wall"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.01, 0.88]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.45, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "courses", "type": "int", "default": 7, "minimum": 3, "maximum": 16,
     "meaning": "Rough courses of stones across the tile height."},
    {"name": "stone_length", "type": "float", "default": 0.22, "minimum": 0.08, "maximum": 0.45,
     "meaning": "Mean stone length in tile widths."},
    {"name": "irregularity", "type": "float", "default": 0.55, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Variation of stone size, thickness and outline."},
    {"name": "tilt", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Random rotation of the stones out of level."},
    {"name": "gap", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Width of the dark voids between stones."},
    {"name": "chinking", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Small filler stones wedged into the joints."},
    {"name": "face_relief", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Roughness of the stone faces."},
    {"name": "moss", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Moss in the crevices and on the lower edges of stones."},
    {"name": "lichen", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Pale lichen colonies on the faces."},
    {"name": "colour_variation", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of colour between stones."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Grey limestone field wall with lichen spots and chinking stones.", "values": {}},
    "gritstone_moss": {"description": "Brown gritstone in thick courses, mossy crevices, few chinks.",
                       "values": {"courses": 5, "stone_length": 0.3, "moss": 0.75, "lichen": 0.15,
                                  "chinking": 0.25, "face_relief": 0.7}},
    "slate_coursed": {"description": "Thin dark slate slabs in many tight courses.",
                      "values": {"courses": 12, "stone_length": 0.18, "irregularity": 0.35, "tilt": 0.2,
                                 "gap": 0.25, "chinking": 0.2, "moss": 0.05, "lichen": 0.1,
                                 "colour_variation": 0.4}},
    "rubble_rough": {"description": "Rough, chunky rubble with wide voids, heavy tilt and many chinks.",
                     "values": {"courses": 6, "stone_length": 0.16, "irregularity": 0.9, "tilt": 0.85,
                                "gap": 0.7, "chinking": 0.9, "moss": 0.3, "lichen": 0.4}},
}
#: Stone colours, void colour, moss colour, lichen colour, stone roughness per preset (sRGB).
PALETTES = {
    "default": (["#8f8b84", "#a19c93", "#7d7a74", "#b0aaa0", "#898379"], "#1e1b17", "#4d6a2b", "#d9d7c4", 0.85),
    "gritstone_moss": (["#7b6a55", "#8a7862", "#6b5c4a", "#968470", "#74644f"], "#191510", "#42622a",
                       "#c9c9a8", 0.88),
    "slate_coursed": (["#4b4f52", "#55595b", "#43474a", "#5e6062", "#4f5254"], "#121314", "#47602e", "#b8bba8",
                      0.78),
    "rubble_rough": (["#9a9286", "#857d72", "#a8a094", "#766f65", "#8f877b"], "#1c1915", "#4b672c", "#dcd9bf",
                     0.9),
}


def _courses(rows: int, mean: float, irregularity: float, tilt: float, gap: float, seed: int) -> tuple:
    """(row starts, row heights, stones per row); a stone is (centre u, centre v, half length, half thickness,
    angle, corner radius, trait) and every row's stone slots sum to the tile width."""
    rng = tk.Rng(seed, 0xD5)
    raw = [rng.uniform(1.0 - 0.4 * irregularity, 1.0 + 0.4 * irregularity) for _ in range(rows)]
    heights = [value / sum(raw) for value in raw]
    starts = [sum(heights[:k]) for k in range(rows)]
    courses = []
    for row in range(rows):
        lengths = []
        while sum(lengths) < 1.0 - 0.6 * mean or not lengths:
            lengths.append(mean * math.exp(rng.gauss(0.0, 0.15 + 0.4 * irregularity)))
        scale = 1.0 / sum(lengths)
        lengths = [length * scale for length in lengths]
        position = rng.random()
        stones = []
        for length in lengths:
            thickness = heights[row] * 0.5 * rng.uniform(1.0 - 0.45 * irregularity, 1.0)
            half_length = 0.5 * length - (0.002 + 0.006 * gap)
            half_thickness = thickness - (0.002 + 0.005 * gap)
            centre_v = starts[row] + 0.5 * heights[row] + rng.uniform(-0.12, 0.12) * heights[row] * irregularity
            angle = rng.uniform(-0.14, 0.14) * tilt
            radius = min(half_length, half_thickness) * rng.uniform(0.25, 0.25 + 0.6 * irregularity)
            taper = rng.uniform(-0.35, 0.35) * irregularity
            stones.append(((position + 0.5 * length) % 1.0, centre_v % 1.0, max(half_length, 0.004),
                           max(half_thickness, 0.003), angle, radius,
                           tuple(rng.random() for _ in range(5)) + (taper,)))
            position += length
        courses.append(stones)
    return starts, heights, courses


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The dry stone wall maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    stones_hex, void_hex, moss_hex, lichen_hex, stone_rough = PALETTES[preset]
    palette = [tk.hex_rgb(code) for code in stones_hex]
    void_rgb, moss_rgb, lichen_rgb = tk.hex_rgb(void_hex), tk.hex_rgb(moss_hex), tk.hex_rgb(lichen_hex)
    rows = p["courses"]
    irregularity, gap = p["irregularity"], p["gap"]
    starts, row_heights, courses = _courses(rows, p["stone_length"], irregularity, p["tilt"], gap,
                                            tk.hash_u32(seed, 1))
    bins = 512
    lookup = []
    for stones in courses:
        edges = sorted(((centre - half) % 1.0, k) for k, (centre, _v, half, *_rest) in enumerate(stones))
        positions = [edge for edge, _k in edges]
        table = []
        for b in range(bins):
            u = (b + 0.5) / bins
            slot = bisect_right(positions, u) - 1
            table.append(edges[slot][1])
        lookup.append(table)
    chinks = []
    rng = tk.Rng(seed, 0xC4)
    for row, stones in enumerate(courses):
        for centre, centre_v, half, *_rest in stones:
            if rng.random() < p["chinking"]:
                size = row_heights[row] * rng.uniform(0.12, 0.28)
                chinks.append(((centre + half + 0.004) % 1.0, (starts[row] + rng.uniform(0.1, 0.9)
                                                              * row_heights[row]) % 1.0, size * 0.7, size * 0.5,
                               rng.uniform(-0.6, 0.6), rng.random()))
    outline = tk.fbm(width, height, 24, 4, tk.hash_u32(seed, 2))
    rock = tk.fbm(width, height, 32, 4, tk.hash_u32(seed, 3))
    lumps = tk.fbm(width, height, 8, 3, tk.hash_u32(seed, 4))
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 5))
    colonies = tk.fbm(width, height, 10, 4, tk.hash_u32(seed, 6))
    lichen_level = 0.55 - 0.5 * p["lichen"]
    chink_field = [9.0] * (width * height)
    chink_owner = [-1] * (width * height)
    for k, (cu, cv, ru, rv, angle, _shade) in enumerate(chinks):
        if ru < 0.5 and rv < 0.5:
            for index, s, t in tk.ellipse_pixels(width, height, cu, cv, ru, rv, angle):
                value = s * s + t * t
                if value < chink_field[index]:
                    chink_field[index], chink_owner[index] = value, k
    relief, moss, variation = p["face_relief"], p["moss"], p["colour_variation"]
    count = len(palette) - 1
    pixel = 1.0 / width
    row_of = []
    for y in range(height):
        v = (y + 0.5) / height
        row = 0
        while row < rows - 1 and v >= starts[row] + row_heights[row]:
            row += 1
        row_of.append(row)
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        v = (y + 0.5) / height
        row = row_of[y]
        for x in range(width):
            index = y * width + x
            u = (x + 0.5) / width
            b = min(int(u * bins), bins - 1)
            own = lookup[row][b]
            count_row = len(courses[row])
            candidates = [(row, own), (row, (own + 1) % count_row), (row, (own - 1) % count_row),
                          ((row + 1) % rows, lookup[(row + 1) % rows][b]),
                          ((row - 1) % rows, lookup[(row - 1) % rows][b])]
            best, stone = 9.0, None
            for r, k in candidates:
                cu, cv, hx, hy, angle, radius, trait = courses[r][k]
                du, dv = tk.wrap_delta(u - cu), tk.wrap_delta(v - cv)
                ca, sa = math.cos(angle), math.sin(angle)
                lx, ly = du * ca + dv * sa, dv * ca - du * sa
                ly /= max(0.4, 1.0 + trait[5] * tk.clamp(lx / hx, -1.0, 1.0))
                distance = tk.box_distance(lx, ly, hx, hy, radius) + (0.08 + 0.3 * irregularity) * hy \
                    * outline[index]
                if distance < best:
                    best, stone = distance, (r, k, ly / hy)
            inside = -best
            if inside > 0.0:
                r, k, across = stone
                trait = courses[r][k][6]
                edge = min(courses[r][k][2], courses[r][k][3]) * 0.6
                t = inside / edge
                profile = 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
                level = 0.12 + (0.72 + 0.06 * trait[1] + relief * 0.05 * rock[index] + 0.03 * lumps[index]
                                - 0.12) * profile
                pick = (trait[0] * variation + 0.5 * (1.0 - variation)) * count
                low = min(int(pick), count - 1)
                f = pick - low
                tone = 1.0 + 0.1 * rock[index] * (0.5 + relief) + 0.06 * (grit[index] - 0.5) - 0.25 * (1.0 - profile)
                colour = [(a + (c - a) * f) * tone for a, c in zip(palette[low], palette[low + 1])]
                reach = colonies[index] + 0.25 * rock[index] - lichen_level
                spot = tk.smoothstep(0.0, 0.06, reach) * (0.45 + 0.35 * grit[index])
                if spot > 0.0:
                    colour = [c + (l - c) * spot for c, l in zip(colour, lichen_rgb)]
                growth = moss * tk.clamp(tk.smoothstep(0.2, -0.6, across) * (0.4 + lumps[index])
                                         + (1.0 - profile) * 0.5 * (0.3 + lumps[index]))
                if growth > 0.0:
                    colour = [c + (m * (0.7 + 0.6 * grit[index]) - c) * growth for c, m in zip(colour, moss_rgb)]
                roughness = stone_rough + 0.05 * trait[2] - 0.04 * relief * max(0.0, rock[index]) + 0.05 * growth
            else:
                level = 0.06 + 0.04 * lumps[index]
                colour = [c * (0.8 + 0.4 * grit[index]) for c in void_rgb]
                if moss > 0.0:
                    growth = moss * tk.smoothstep(-0.2, 0.4, lumps[index]) * 0.6
                    colour = [c + (m * 0.45 - c) * growth for c, m in zip(colour, moss_rgb)]
                roughness = 0.98
            fill = chink_field[index]
            if fill < 1.0 and level < 0.5:
                shade = chinks[chink_owner[index]][5]
                bump = math.sqrt(1.0 - fill)
                chink_level = 0.3 + 0.25 * bump
                if chink_level > level:
                    level = chink_level
                    tone = 0.75 + 0.3 * shade + 0.08 * rock[index]
                    colour = [c * tone * (0.75 + 0.25 * bump) for c in palette[int(shade * (count + 0.999))]]
                    roughness = stone_rough
            heights.append(level)
            cover = tk.smoothstep(-pixel, pixel, inside)
            if 0.0 < cover < 1.0:
                colour = [c * (0.6 + 0.4 * cover) for c in colour]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            rough.append(roughness)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.03, roughness=rough,
                     ao_radius=0.03, ao_strength=1.2, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
