"""Pixel-art sand: dithered dune shading, wind ripple lines, shells and pebbles, tileable (standard library only).

Sand is drawn on a small art grid (``art_pixels`` square). Broad dunes are a periodic wave whose phase is bent by
noise; its slope toward a light from the top left becomes three sand shades, and an ordered 4 x 4 Bayer dither turns
the smooth slope into the stepped checker gradients of hand-made pixel art. Wind ripples are parallel lines from a
wave with whole-number frequencies across and down the tile (so they repeat exactly), bent by noise: the crest pixel
takes the light colour and the pixel below it the shadow colour, and a noise mask keeps ripples to patches. Shells
and pebbles are small sprites scattered with wrap-around. The art is enlarged with nearest-neighbour sampling;
heights, normals and occlusion are computed per art pixel.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "pixel_sand_dunes"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.98]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "dunes", "type": "int", "default": 1, "minimum": 1, "maximum": 3,
     "meaning": "Dune waves down the tile."},
    {"name": "dune_shading", "type": "float", "default": 0.45, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Contrast of the dithered dune shading."},
    {"name": "ripple_spacing", "type": "int", "default": 5, "minimum": 3, "maximum": 8,
     "meaning": "Distance between wind ripple lines in art pixels."},
    {"name": "ripple_slant", "type": "int", "default": 1, "minimum": -2, "maximum": 2,
     "meaning": "Slant of the ripple lines: whole steps of rise across the tile."},
    {"name": "ripples", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of the sand covered by ripple patches."},
    {"name": "shells", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of shells."},
    {"name": "pebbles", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of pebbles."},
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
    "default": {"description": "Warm beach sand with ripples, shells and a few pebbles.", "values": {}},
    "desert_dunes": {"description": "Orange desert dunes with strong shading and long ripples, no shells.",
                     "values": {"dunes": 2, "dune_shading": 0.9, "ripples": 0.85, "ripple_spacing": 4,
                                "shells": 0.0, "pebbles": 0.05}},
    "white_coral": {"description": "Bright white coral sand scattered with shells and coral bits.",
                    "values": {"dune_shading": 0.3, "ripples": 0.3, "shells": 0.8, "pebbles": 0.1,
                               "ripple_slant": -1}},
    "black_sand": {"description": "Black volcanic sand with grey pebbles and pale glints.",
                   "values": {"dune_shading": 0.5, "shells": 0.1, "pebbles": 0.6, "ripple_spacing": 6}},
}
#: Per preset: sand shadow, sand, sand light, ripple crest, shell, shell shadow, pebble, pebble light (sRGB).
PALETTES = {
    "default": ("#9c7444", "#c09659", "#d6b077", "#ecd09a", "#f6ece0", "#d08f80", "#706a5f", "#aaa293"),
    "desert_dunes": ("#b25a26", "#d0763a", "#e39350", "#f2b06c", "#f6e3cf", "#c98f6a", "#7a4a2e", "#b37552"),
    "white_coral": ("#c9c0ab", "#e3dcc8", "#f1ecdd", "#fdfbf4", "#f6c6c0", "#d08a86", "#9a948a", "#cfc9bd"),
    "black_sand": ("#1d1b1e", "#2c2a2e", "#3c3a40", "#5a5862", "#d9d6d0", "#8e8a86", "#6f6c70", "#a7a4aa"),
}
#: Roughness of sand, ripple crests, shells and pebbles.
ROUGHNESS = (0.9, 0.85, 0.55, 0.7)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The sand maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    shadow, sand, light, crest, shell, shell_dark, pebble, pebble_light = (tk.hex_rgb(code)
                                                                           for code in PALETTES[preset])
    shades = (shadow, sand, light)
    art = p["art_pixels"]
    count = art * art
    bend = tk.fbm(art, art, 2, 2, tk.hash_u32(seed, 1))
    wiggle = tk.fbm(art, art, max(2, art // 8), 2, tk.hash_u32(seed, 2))
    patches = tk.fbm(art, art, max(2, art // 10), 2, tk.hash_u32(seed, 3))
    spacing = p["ripple_spacing"]
    lines = max(1, round(art / spacing))
    colour, heights, rough = [None] * count, [0.0] * count, [ROUGHNESS[0]] * count
    for y in range(art):
        for x in range(art):
            index = y * art + x
            phase = math.tau * (p["dunes"] * (y + 0.5) / art + 0.5 * math.sin(math.tau * (x + 0.5) / art)
                                + 0.3 * bend[index])
            slope = math.cos(phase)
            level = 1.0 + 1.6 * p["dune_shading"] * slope + 0.5 * (tk.bayer4(x, y) - 0.5)
            tone = 0 if level < 0.5 else 2 if level >= 1.5 else 1
            colour[index] = shades[tone]
            heights[index] = 0.42 + 0.12 * math.sin(phase)
            ripple = (lines * y + p["ripple_slant"] * x) / art + 0.3 * bend[index] + 0.06 * wiggle[index] \
                + 0.3 * math.sin(math.tau * (2.0 * (x + 0.5) / art + 0.25 * bend[index]))
            step = (ripple - math.floor(ripple)) * spacing
            if patches[index] < 1.6 * p["ripples"] - 0.8:
                if step < 1.0:
                    colour[index], rough[index] = crest if tone else light, ROUGHNESS[1]
                    heights[index] += 0.08
                elif step < 2.0:
                    colour[index] = shadow
                    heights[index] -= 0.04
    rng = tk.Rng(seed, 0x5D)
    for _ in range(round(p["shells"] * count / 90.0)):
        x, y = rng.integer(0, art - 1), rng.integer(0, art - 1)
        sprite = ((0, 0, 1), (1, 0, 1), (-1, 1, 1), (0, 1, 2), (1, 1, 1), (2, 1, 2)) if art >= 32 else \
            ((0, 0, 1), (1, 0, 2))
        for dx, dy, shade in sprite:
            index = ((y + dy) % art) * art + (x + dx) % art
            colour[index] = shell if shade == 1 else shell_dark
            heights[index], rough[index] = 0.62 - 0.05 * dy, ROUGHNESS[2]
    for _ in range(round(p["pebbles"] * count / 90.0)):
        x, y = rng.integer(0, art - 1), rng.integer(0, art - 1)
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            index = ((y + dy) % art) * art + (x + dx) % art
            colour[index] = pebble_light if (dx, dy) == (0, 0) else pebble
            heights[index], rough[index] = 0.6 - 0.05 * dy, ROUGHNESS[3]
        index = ((y + 2) % art) * art + (x + 1) % art
        colour[index] = shadow
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.2 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 1.5 / art, 0.8)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
