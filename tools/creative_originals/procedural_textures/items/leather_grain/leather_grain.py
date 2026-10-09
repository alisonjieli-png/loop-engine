"""Pebbled leather: grain domes, crease network, pores, wrinkles, burnished wear, cracked finish or suede nap.

The grain is a cellular pattern on the torus. Every cell becomes a soft pebble whose height follows the distance to
the cell border, so the borders turn into a network of creases; the zero crossings of finer gradient noise add the
small creases inside the pebbles, and a smooth domain warp keeps the cells from looking like a polygon grid. Long wrinkles come from
ridged noise stretched across the hide, pores are small pits, and wear lightens and polishes the high points in
patches. An old finish can crack into a coarse network that shows the darker leather below; a nap hides the grain
under fine fibres with brushed light and dark patches, as on suede.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "leather_grain"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.015, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.18, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "grain_cells", "type": "int", "default": 26, "minimum": 6, "maximum": 64,
     "meaning": "Pebbles across the tile width: low values give a coarse bag grain, high values a fine one."},
    {"name": "grain_depth", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How deep the creases between pebbles are."},
    {"name": "fine_grain", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Small creases inside the pebbles, at about 2.3 times the pebble frequency (dropped where they "
                "would be finer than two pixels)."},
    {"name": "pores", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density and depth of the small pores of the hide."},
    {"name": "wrinkles", "type": "float", "default": 0.25, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Long creases from folding and use."},
    {"name": "wear", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Burnished, lighter and glossier high points, in patches."},
    {"name": "cracking", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Cracks in an old surface finish, showing the darker leather below."},
    {"name": "nap", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Suede nap: fine fibres hide the grain and brushing leaves light and dark patches."},
    {"name": "gloss", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Shine of the finish: 0 matte, 1 polished."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Black car-seat leather: fine even pebble grain with a satin finish.", "values": {}},
    "saddle_brown": {"description": "Smooth tan saddle leather: shallow grain, wrinkles and burnished wear.",
                     "values": {"grain_cells": 40, "grain_depth": 0.25, "fine_grain": 0.3, "wrinkles": 0.5,
                                "wear": 0.6, "gloss": 0.6, "pores": 0.5}},
    "pebbled_navy": {"description": "Navy handbag leather with a coarse, deep pebble grain.",
                     "values": {"grain_cells": 14, "grain_depth": 0.9, "fine_grain": 0.7, "wrinkles": 0.1,
                                "gloss": 0.3, "pores": 0.2}},
    "aged_oxblood": {"description": "Oxblood club-chair leather with a cracked finish and worn patches.",
                     "values": {"grain_cells": 32, "grain_depth": 0.45, "wrinkles": 0.6, "wear": 0.7,
                                "cracking": 0.7, "gloss": 0.5}},
    "suede_tan": {"description": "Tan suede: brushed nap with light and dark patches.",
                  "values": {"nap": 1.0, "grain_depth": 0.3, "wrinkles": 0.3, "gloss": 0.0, "pores": 0.0}},
}
#: Leather colour, worn or burnished colour, crease colour and the colour under a cracked finish (sRGB).
PALETTES = {
    "default": ("#2a292a", "#4a4849", "#121112", "#3a3634"),
    "saddle_brown": ("#8a5a32", "#b47b46", "#4e3018", "#5b3a20"),
    "pebbled_navy": ("#1f2c4a", "#35466b", "#0e1424", "#16203a"),
    "aged_oxblood": ("#5a1a1c", "#8a3b33", "#2a0b0c", "#b39a86"),
    "suede_tan": ("#a07650", "#c39a72", "#6b4a2e", "#7d5a3a"),
}


def _pebble(edge: list, nearest: list, rim: float) -> list:
    """A rounded pebble per cell: 0 in the crease, rising steeply from the border (edge distance in cell units) and
    capped by a dome around the cell's feature point, so the tops are round rather than flat polygons."""
    inverse = 1.0 / rim
    out = []
    for value, f1 in zip(edge, nearest):
        t = value * inverse
        t = 1.0 if t > 1.0 else t
        cap = 1.0 - 0.45 * f1 * f1
        out.append((1.0 - (1.0 - t) ** 2.2) * cap)
    return out


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The leather maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    base_rgb, worn_rgb, crease_rgb, under_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    cells = p["grain_cells"]
    count = width * height
    warp_u = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 1))
    warp_v = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 2))
    wobble_cells = min(max(4, min(width, height) // 3), max(4, cells))
    wobble_u = tk.gradient_noise(width, height, wobble_cells, wobble_cells, tk.hash_u32(seed, 12))
    wobble_v = tk.gradient_noise(width, height, wobble_cells, wobble_cells, tk.hash_u32(seed, 13))
    coarse = tk.voronoi(width, height, cells, cells, tk.hash_u32(seed, 3), jitter=0.95)
    pebbles = _pebble(coarse["edge"], coarse["f1"], 0.3)
    pebbles = tk.warp(pebbles, width, height, wobble_u, wobble_v, 0.22 / cells)
    pebbles = tk.warp(pebbles, width, height, warp_u, warp_v, 0.3 / cells)
    limit = max(4, min(width, height) // 2)
    fine_cells = min(limit, max(2, int(round(cells * 2.3))))
    small = [tk.smoothstep(0.0, 0.3, abs(value)) for value in
             tk.gradient_noise(width, height, fine_cells, fine_cells, tk.hash_u32(seed, 4))]
    folds = tk.ridged(width, height, 2, 4, tk.hash_u32(seed, 5), cells_y=5)
    folds = tk.warp(folds, width, height, warp_u, warp_v, 0.06)
    pore_cells = min(limit, cells * 5)
    pore_field = tk.value_noise(width, height, pore_cells, pore_cells, tk.hash_u32(seed, 6))
    patches = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 7))
    crack_cells = max(2, cells // 3)
    crack = tk.voronoi(width, height, crack_cells, crack_cells, tk.hash_u32(seed, 8), jitter=0.9)["edge"]
    crack_break = tk.fbm(width, height, crack_cells * 2, 3, tk.hash_u32(seed, 9))
    nap_field = tk.fbm(width, height, min(limit, max(16, cells * 6)), 2, tk.hash_u32(seed, 10))
    brushing = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 11))
    depth, fine_amount, pores, wrinkles = p["grain_depth"], p["fine_grain"], p["pores"], p["wrinkles"]
    wear, cracking, nap, gloss = p["wear"], p["cracking"], p["nap"], p["gloss"]
    grain_scale = depth * (1.0 - 0.8 * nap)
    crack_width = 0.012 + 0.025 * cracking
    pore_threshold = 1.0 - 0.18 * pores
    heights, red, green, blue, rough = [], [], [], [], []
    for index in range(count):
        dome, minor = pebbles[index], small[index]
        relief = 0.62 * dome + 0.38 * fine_amount * minor - 0.38 * fine_amount
        fold = folds[index]
        valley = tk.smoothstep(0.78, 0.97, fold) * wrinkles
        pit = tk.smoothstep(pore_threshold, 1.0, pore_field[index]) * pores if pores > 0.0 else 0.0
        level = 0.55 + 0.4 * grain_scale * relief - 0.22 * valley - 0.12 * pit * (1.0 - nap)
        broken = 0.0
        if cracking > 0.0:
            gap = crack[index] / crack_width
            if gap < 1.0 and crack_break[index] > 0.35 - 0.6 * cracking:
                broken = (1.0 - gap) * min(1.0, (crack_break[index] - 0.35 + 0.6 * cracking) * 4.0)
                level -= 0.18 * broken
        fibres = nap_field[index]
        level += 0.06 * nap * fibres
        heights.append(level)
        burnish = wear * tk.smoothstep(0.55, 0.95, dome * 0.7 + 0.3 * minor + 0.15 * patches[index]) \
            * tk.smoothstep(-0.25, 0.3, patches[index])
        shade = 0.82 + 0.22 * dome * grain_scale + 0.06 * (minor - 0.5) * fine_amount
        crease = (1.0 - dome) * 0.55 * grain_scale + 0.35 * valley
        colour = [b + (c - b) * crease for b, c in zip(base_rgb, crease_rgb)]
        colour = [c + (w - c) * burnish for c, w in zip(colour, worn_rgb)]
        if nap > 0.0:
            tone = 1.0 + nap * (0.16 * brushing[index] + 0.1 * fibres)
            shade = shade * (1.0 - nap) + nap * tone
        colour = [c * shade for c in colour]
        if broken > 0.0:
            colour = [c + (u - c) * broken for c, u in zip(colour, under_rgb)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        smooth = 0.78 - 0.45 * gloss + 0.12 * crease - 0.25 * burnish + 0.25 * pit + 0.2 * broken
        rough.append(smooth + (0.97 - smooth) * nap)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.45 / cells, roughness=rough,
                     ao_radius=0.6 / cells, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
