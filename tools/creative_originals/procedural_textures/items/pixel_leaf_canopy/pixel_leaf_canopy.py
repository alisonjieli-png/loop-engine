"""Pixel-art tree canopy: overlapping shaded leaf clumps with dark gaps, fruit and blossoms, tileable (standard library).

Foliage is drawn on a small art grid (``art_pixels`` square) as round clumps centred on Poisson-disc points of the
torus, closer together than their size so they overlap, and painted from the top of the tile to the bottom so lower
clumps cover higher ones, as in a canopy seen from the front. Inside a clump the offset from its centre along a
light from the top left picks one of four tones from a highlight to a dark underside, the rim facing away from the
light is outlined in the darkest tone, and a hashed pattern of two-pixel leaves breaks the tone bands into leaves
(or into short needle strokes for conifers). Where no clump reaches, the deep gap colour shows through. Fruit and
blossoms are small sprites on the clumps. The art is enlarged with nearest-neighbour sampling; heights (a dome per
clump), normals and occlusion are computed per art pixel.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "pixel_leaf_canopy"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "clump_radius", "type": "float", "default": 4.5, "minimum": 2.5, "maximum": 7.0,
     "meaning": "Radius of a leaf clump in art pixels."},
    {"name": "coverage", "type": "float", "default": 0.9, "minimum": 0.3, "maximum": 1.0,
     "meaning": "Share of the clump positions that hold a clump; lower values open more gaps."},
    {"name": "leaf_texture", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How strongly single leaves break up the tone bands."},
    {"name": "needles", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "1 draws short needle strokes instead of round leaves (conifers)."},
    {"name": "fruit", "type": "float", "default": 0.1, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of fruit or blossoms on the clumps."},
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
    "default": {"description": "Summer broadleaf canopy with a few red apples.", "values": {}},
    "autumn": {"description": "Autumn canopy mixing orange, red and yellow clumps.",
               "values": {"fruit": 0.0, "coverage": 0.8, "leaf_texture": 0.7}},
    "cherry_blossom": {"description": "Pink blossom canopy with white petals.",
                       "values": {"fruit": 0.6, "clump_radius": 4.0, "leaf_texture": 0.6}},
    "pine": {"description": "Dark blue-green conifer canopy of needle strokes.",
             "values": {"needles": 1, "fruit": 0.0, "clump_radius": 5.5, "coverage": 1.0}},
}
#: Per preset: gap colour, one or more clump ramps (outline, dark, mid, light, highlight), fruit, fruit highlight.
PALETTES = {
    "default": ("#0d1f12", (("#173a1c", "#245a26", "#33782e", "#4c9a38", "#7cc252"),), "#c8302a", "#ff8f7a"),
    "autumn": ("#2a160c", (("#4a1f10", "#8a3416", "#bf4f1c", "#e07a2a", "#f6b04a"),
                           ("#4a160f", "#7c2016", "#a8301c", "#cf4a2a", "#ef7a4a"),
                           ("#4e3a10", "#8a6a16", "#bf961c", "#e0c02e", "#f8e07a")), "#5a2a10", "#a85a2a"),
    "cherry_blossom": ("#2c1a24", (("#5a2c44", "#9a4a6e", "#c86e94", "#e69ab6", "#f8cadb"),), "#ffffff",
                       "#ffe8f0"),
    "pine": ("#06120f", (("#0a1f1a", "#12342b", "#1b4a3a", "#286450", "#3f8a6c"),), "#5a3a22", "#8a6a44"),
}
#: Roughness of the gaps, leaves and fruit.
ROUGHNESS = (0.95, 0.72, 0.4)


def _on_lines(a: int, b: int, x: int, y: int, art: int, spacing: int) -> bool:
    """Whether art pixel (x, y) lies on one of the parallel one-pixel lines a*x + b*y = constant that repeat about
    every ``spacing`` pixels; the line count is a whole number across the tile, so the lines wrap seamlessly."""
    lines = max(1, round(art / spacing))
    position = (a * x + b * y) * lines / art
    return position - math.floor(position) < lines / art


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The canopy maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    gap_code, ramp_codes, fruit_code, fruit_light_code = PALETTES[preset]
    gap = tk.hex_rgb(gap_code)
    ramps = [[tk.hex_rgb(code) for code in ramp] for ramp in ramp_codes]
    fruit_colour, fruit_light = tk.hex_rgb(fruit_code), tk.hex_rgb(fruit_light_code)
    art = p["art_pixels"]
    count = art * art
    radius = min(p["clump_radius"], art / 4.0)
    rng = tk.Rng(seed, 0xCA)
    points = tk.poisson_points(min(0.5, max(0.004, 1.15 * radius / art)), tk.hash_u32(seed, 1))
    clumps = sorted(((u * art, v * art, rng.integer(0, len(ramps) - 1), rng.uniform(0.85, 1.1),
                      rng.integer(5, 7), rng.uniform(0.0, math.tau))
                     for u, v in points if rng.chance(p["coverage"])), key=lambda row: row[1])
    colour, heights, rough = [gap] * count, [0.05] * count, [ROUGHNESS[0]] * count
    owner = [-1] * count
    for number, (cu, cv, ramp_index, scale, lobes, turn) in enumerate(clumps):
        ramp = ramps[ramp_index]
        size = radius * scale
        reach = int(math.ceil(size * 1.15))
        for dy in range(-reach, reach + 1):
            for dx in range(-reach, reach + 1):
                x, y = int(math.floor(cu)) + dx, int(math.floor(cv)) + dy
                ox, oy = (x + 0.5 - cu) / size, (y + 0.5 - cv) / size
                distance = math.hypot(ox, oy) / (1.0 + 0.14 * math.sin(lobes * math.atan2(oy, ox) + turn))
                if distance > 1.0:
                    continue
                facing = -(ox + oy) * 0.75
                rim = distance > 0.8 and ox + oy > 0.15
                tone = 0 if rim else 4 if facing > 0.45 else 3 if facing > 0.05 else 2 if facing > -0.4 else 1
                gx, gy = x % art, y % art
                if p["needles"]:
                    stroke = _on_lines(1, 2, gx, gy, art, 5) or _on_lines(1, -1, gx, gy, art, 7)
                    leaf = stroke and tk.hash_float(seed, gx, gy, 2) < 0.7 * p["leaf_texture"] + 0.2
                else:
                    pair = tk.hash_float(seed, gx // 2, gy, number % 3)
                    leaf = pair < 0.35 * p["leaf_texture"]
                if leaf and 0 < tone:
                    tone = min(4, tone + 1) if tk.hash_float(seed, gx, gy, 5) < 0.5 else max(1, tone - 1)
                index = gy * art + gx
                colour[index] = ramp[tone]
                heights[index] = 0.35 + 0.5 * math.sqrt(max(0.0, 1.0 - distance * distance))
                rough[index] = ROUGHNESS[1]
                owner[index] = number
    for u, v in tk.poisson_points(min(0.5, 5.0 / art), tk.hash_u32(seed, 2)):
        if not rng.chance(p["fruit"]):
            continue
        x, y = int(u * art), int(v * art)
        index = y * art + x
        if owner[index] < 0:
            continue
        sprite = ((0, 0), (1, 0), (0, 1), (1, 1)) if art >= 32 else ((0, 0),)
        for dx, dy in sprite:
            target = ((y + dy) % art) * art + (x + dx) % art
            colour[target] = fruit_light if (dx, dy) == (0, 0) and len(sprite) > 1 else fruit_colour
            heights[target], rough[target] = heights[target] + 0.05, ROUGHNESS[2]
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.0 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 2.0 / art, 1.0)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
