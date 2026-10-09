"""Pixel-art dungeon floor: large irregular stone slabs, cracks, chipped corners, moss and puddles, tileable.

The floor is laid on a small art grid (``art_pixels`` square) as random ashlar: a coarse grid of cells on the torus
is filled greedily with slabs one or two cells wide and one or two cells tall, so long joint lines break wherever a
large slab spans them and the layout has no straight line through the whole tile. Every slab owns the joint on its
top and left edge, which keeps exactly one dark joint between neighbours across the tile edges; its next row and
column are a lit bevel and its last row and column a shadow bevel, and random corners are chipped into the joint.
Slab faces are posterized noise with a tone per slab, cracks are short branching random walks, moss grows in the
joints and spills onto the edges, and flooded floors gather glossy puddles. The art is enlarged with
nearest-neighbour sampling; heights, normals and occlusion are computed per art pixel. Standard library only.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "pixel_dungeon_floor"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.04, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "cells", "type": "int", "default": 4, "minimum": 2, "maximum": 8,
     "meaning": "Layout cells across the tile; slabs span one or two cells each way."},
    {"name": "large_slabs", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Chance that a slab spans two cells (0 is a square grid of slabs)."},
    {"name": "cracks", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of slabs with a crack."},
    {"name": "chips", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Chance that a slab corner is chipped."},
    {"name": "moss", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Moss in the joints."},
    {"name": "puddles", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Coverage of standing water."},
    {"name": "relief", "type": "float", "default": 1.0, "minimum": 0.2, "maximum": 2.0,
     "meaning": "Strength of the per-pixel normal map."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Grey dungeon slabs with cracks, chipped corners and a little moss.", "values": {}},
    "mossy_crypt": {"description": "Green-grey crypt floor overgrown with moss in every joint.",
                    "values": {"moss": 0.8, "cracks": 0.6, "chips": 0.6}},
    "sandstone_temple": {"description": "Warm sandstone temple slabs, large and tidy.",
                         "values": {"large_slabs": 0.8, "cracks": 0.15, "chips": 0.2, "moss": 0.0, "cells": 3}},
    "flooded_cellar": {"description": "Dark cellar flagstones with glossy puddles.",
                       "values": {"puddles": 0.45, "moss": 0.3, "cells": 5}},
}
#: Per preset: joint, slab shadow, slab dark, slab, slab light, bevel highlight, crack, moss dark, moss light,
#: water and water highlight (sRGB).
PALETTES = {
    "default": ("#1c1b20", "#3c3b44", "#4a4953", "#58575f", "#66656e", "#7f7e88", "#24232a", "#2f4a26", "#4a6b31",
                "#20324a", "#5c7ea4"),
    "mossy_crypt": ("#17201a", "#36413a", "#434f47", "#4f5b52", "#5c695f", "#77857a", "#1e261f", "#2d5222",
                    "#4f7f2e", "#1f3a3a", "#5a8e88"),
    "sandstone_temple": ("#4a3420", "#8a6845", "#9c774f", "#ad8659", "#bd9566", "#d6b07e", "#6b4c2e", "#5a6a2e",
                         "#7b8c3c", "#2c4a5c", "#7aa6bf"),
    "flooded_cellar": ("#121216", "#2c2b31", "#36353c", "#403f46", "#4b4a52", "#62616b", "#18181c", "#263c22",
                       "#3d5e2b", "#1a2a3c", "#6a8fb5"),
}
#: Roughness of joint, slab face, bevels, crack, moss and water.
ROUGHNESS = (0.95, 0.86, 0.8, 0.9, 0.92, 0.05)
#: Slab shapes in cells (width, height), largest first.
SHAPES = ((2, 2), (2, 1), (1, 2))


def _layout(rng, cells: int, large: float) -> list:
    """Slabs as (column, row, width, height) in cells, filling the torus greedily from the top-left cell."""
    owner = [[None] * cells for _ in range(cells)]
    slabs = []
    for row in range(cells):
        for column in range(cells):
            if owner[row][column] is not None:
                continue
            choice = (1, 1)
            if rng.chance(large):
                options = [shape for shape in SHAPES if all(
                    owner[(row + dy) % cells][(column + dx) % cells] is None
                    for dx in range(shape[0]) for dy in range(shape[1])) and max(shape) < cells]
                if options:
                    choice = options[rng.integer(0, len(options) - 1)]
            for dx in range(choice[0]):
                for dy in range(choice[1]):
                    owner[(row + dy) % cells][(column + dx) % cells] = len(slabs)
            slabs.append((column, row, choice[0], choice[1]))
    return slabs


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The floor maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    (joint, shadow, dark, stone, light, highlight, crack, moss_dark, moss_light, water,
     water_light) = (tk.hex_rgb(code) for code in PALETTES[preset])
    art = p["art_pixels"]
    count = art * art
    rng = tk.Rng(seed, 0xD7)
    cells = min(p["cells"], art // 5)
    bounds = [round(k * art / cells) for k in range(cells + 1)]
    slabs = _layout(rng, cells, p["large_slabs"])
    grain = tk.fbm(art, art, max(4, art // 4), 2, tk.hash_u32(seed, 1))
    growth = tk.fbm(art, art, max(2, art // 8), 3, tk.hash_u32(seed, 2))
    wet = tk.fbm(art, art, max(2, art // 10), 2, tk.hash_u32(seed, 3))
    slab_of, role = [0] * count, [0] * count  # role: 0 joint, 1 face, 2 lit bevel, 3 shadow bevel
    for number, (column, row, wide, tall) in enumerate(slabs):
        x0, y0 = bounds[column], bounds[row]
        x1 = bounds[column + wide] if column + wide <= cells else bounds[column + wide - cells] + art
        y1 = bounds[row + tall] if row + tall <= cells else bounds[row + tall - cells] + art
        chipped = {corner for corner in ((x0 + 1, y0 + 1), (x1 - 1, y0 + 1), (x0 + 1, y1 - 1), (x1 - 1, y1 - 1))
                   if rng.chance(p["chips"])}
        for y in range(y0, y1):
            for x in range(x0, x1):
                index = (y % art) * art + x % art
                slab_of[index] = number
                if x == x0 or y == y0 or (x, y) in chipped:
                    role[index] = 0
                elif x == x0 + 1 or y == y0 + 1:
                    role[index] = 2
                elif x == x1 - 1 or y == y1 - 1:
                    role[index] = 3
                else:
                    role[index] = 1
    tones = [rng.integer(-1, 1) for _ in slabs]
    colour, heights, rough = [None] * count, [0.0] * count, [0.0] * count
    for index in range(count):
        kind = role[index]
        if kind == 0:
            colour[index], heights[index], rough[index] = joint, 0.1, ROUGHNESS[0]
            continue
        level = tones[slab_of[index]] + (1 if grain[index] > 0.45 else -1 if grain[index] < -0.45 else 0)
        face = (dark, stone, light)[max(0, min(2, level + 1))]
        colour[index] = highlight if kind == 2 else shadow if kind == 3 else face
        heights[index] = (0.55 if kind == 2 else 0.5 if kind == 3 else 0.6) + 0.03 * grain[index]
        rough[index] = ROUGHNESS[1] if kind == 1 else ROUGHNESS[2]
    for number in range(len(slabs)):
        if not rng.chance(p["cracks"]):
            continue
        members = [index for index in range(count) if slab_of[index] == number and role[index] == 1]
        if len(members) < 8:
            continue
        start = members[rng.integer(0, len(members) - 1)]
        walkers = [(start % art, start // art, rng.integer(4, 8))]
        while walkers:
            x, y, steps = walkers.pop()
            for _ in range(steps):
                index = (y % art) * art + x % art
                if role[index] == 0 or slab_of[index] != number:
                    break
                colour[index], heights[index], rough[index] = crack, 0.32, ROUGHNESS[3]
                step = rng.integer(0, 3)
                x, y = x + (1, 1, -1, 0)[step], y + (0, 1, 1, 1)[step]
                if steps > 5 and rng.chance(0.12):
                    walkers.append((x, y, 3))
    for y in range(art):
        for x in range(art):
            index = y * art + x
            if p["puddles"] > 0.0 and wet[index] > 1.0 - 2.0 * p["puddles"] and role[index] != 0:
                edge = wet[((y - 1) % art) * art + x] <= 1.0 - 2.0 * p["puddles"]
                colour[index] = water_light if edge or tk.hash_float(seed, x, y, 0x77) < 0.06 else water
                heights[index], rough[index] = 0.45, ROUGHNESS[5]
                continue
            beside = role[index] == 0 or role[((y + 1) % art) * art + x] == 0 or role[y * art + (x + 1) % art] == 0
            level = growth[index] + 1.1 * p["moss"] - 0.85 + (0.3 if beside else -0.5) \
                + 0.2 * (tk.bayer4(x, y) - 0.5)
            if p["moss"] > 0.0 and level > 0.0:
                colour[index] = moss_light if level > 0.18 and role[index] != 0 else moss_dark
                heights[index], rough[index] = max(heights[index], 0.3), ROUGHNESS[4]
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.4 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 1.5 / art, 1.0)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
