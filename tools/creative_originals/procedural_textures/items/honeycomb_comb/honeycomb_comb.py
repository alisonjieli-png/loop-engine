"""Honeycomb: hexagonal wax cells, open, honey-filled or capped, tileable PBR maps from the standard library only.

The cells are the Voronoi regions of a hexagonal lattice of points (a whole number of columns and an even number of
rows, so the comb repeats), jittered a little as bees build them. The distance to the cell border gives the wax
walls with a rounded top. Inside a wall a cell is empty (a deep tube), filled with honey (a glossy surface that
climbs the walls) or sealed with a domed wax cap; a smooth noise field decides which, so capped and open cells
gather in patches as in a real frame. Old brood comb darkens the wax and caps.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "honeycomb_comb"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.04, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "cells", "type": "int", "default": 9, "minimum": 4, "maximum": 26,
     "meaning": "Cells across the tile; the row count is the even number that keeps the hexagons near regular."},
    {"name": "wall", "type": "float", "default": 0.1, "minimum": 0.04, "maximum": 0.22,
     "meaning": "Wax wall thickness as a share of the cell width."},
    {"name": "capped", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of cells sealed with a wax cap."},
    {"name": "honey", "type": "float", "default": 0.75, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of open cells holding honey; the rest are empty."},
    {"name": "irregularity", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How unevenly the cells are built: jitter of the cell centres."},
    {"name": "age", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Darkening of the wax with use: 0 new white comb, 1 old dark brood comb."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Golden comb with patches of capped cells among cells full of honey.", "values": {}},
    "fresh_white": {"description": "New white comb, mostly empty, with thin clean walls.",
                    "values": {"capped": 0.08, "honey": 0.15, "age": 0.0, "wall": 0.07, "irregularity": 0.2}},
    "brood_comb": {"description": "Dark old brood comb with brown domed caps.",
                   "values": {"capped": 0.8, "honey": 0.0, "age": 0.85, "wall": 0.12, "cells": 11}},
    "brimming_honey": {"description": "Large open cells brimming with amber honey.",
                       "values": {"capped": 0.05, "honey": 0.95, "cells": 6, "wall": 0.09}},
}
#: New wax, old wax, honey, honey-cap and brood-cap colours per preset (sRGB).
PALETTES = {
    "default": ("#f2d27a", "#8a5a22", "#c27414", "#f3e0a0", "#c79a52"),
    "fresh_white": ("#f4ead0", "#9a7a46", "#d8a040", "#f7eed6", "#d8b47a"),
    "brood_comb": ("#d8b060", "#5a3412", "#9a5a10", "#e8cf90", "#9a6a34"),
    "brimming_honey": ("#efc860", "#8a5a22", "#b8620e", "#f3e0a0", "#c79a52"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The honeycomb maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    wax_new, wax_old, honey_rgb, cap_honey, cap_brood = (tk.hex_rgb(code) for code in PALETTES[preset])
    columns = p["cells"]
    rows = tk.hex_rows(columns)
    points = tk.hex_points(columns, rows, tk.hash_u32(seed, 1), p["irregularity"])
    cells = tk.voronoi(width, height, columns, rows, points=points)
    age, wall = p["age"], p["wall"]
    wax_rgb = [a + (b - a) * age for a, b in zip(wax_new, wax_old)]
    cap_rgb = [a + (b - a) * age for a, b in zip(cap_honey, cap_brood)]
    regions = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 2))
    detail = tk.fbm(width, height, min(max(4, min(width, height) // 3), columns * 5), 2, tk.hash_u32(seed, 3))
    rng = tk.Rng(seed, 0x4E)
    states = []
    for index in range(columns * rows):
        cu = (points[0][index]) / columns
        cv = (points[1][index]) / rows
        region = tk.sample(regions, width, height, cu % 1.0, cv % 1.0)
        draw = rng.random()
        capped = region * 0.9 + (draw - 0.5) * 0.5 > 0.45 - 0.9 * p["capped"]
        if p["capped"] <= 0.0:
            capped = False
        filled = not capped and rng.random() < p["honey"]
        states.append((2 if capped else 1 if filled else 0, rng.uniform(-1.0, 1.0), rng.uniform(0.0, 1.0)))
    half_wall = 0.5 * wall
    heights, red, green, blue, rough = [], [], [], [], []
    for index in range(width * height):
        edge = cells["edge"][index]
        state, tone, fill = states[cells["cell"][index]]
        grain = detail[index]
        if edge < half_wall:
            t = edge / half_wall
            level = 1.0 - 0.18 * t * t + 0.02 * grain
            colour = [c * (0.92 + 0.06 * (1.0 - t) + 0.04 * grain) for c in wax_rgb]
            roughness = 0.5 + 0.05 * grain
        else:
            inner = edge - half_wall
            if state == 2:
                f1 = cells["f1"][index]
                dome = math.sqrt(max(0.0, 1.0 - (f1 / 0.5) ** 2))
                level = 0.78 + 0.16 * dome + 0.025 * grain - 0.1 * (1.0 - tk.smoothstep(0.0, 0.05, inner))
                colour = [c * (0.88 + 0.08 * dome + 0.06 * grain + 0.04 * tone) for c in cap_rgb]
                roughness = 0.68 + 0.06 * grain
            elif state == 1:
                climb = 1.0 - tk.smoothstep(0.0, 0.12, inner)
                level = 0.5 + 0.12 * fill + 0.12 * climb
                glow = 0.82 + 0.25 * tk.smoothstep(0.05, 0.3, inner) + 0.05 * tone
                colour = [c * glow for c in honey_rgb]
                roughness = 0.06 + 0.04 * climb
            else:
                wall_drop = 1.0 - tk.smoothstep(0.0, 0.08, inner)
                level = 0.14 + 0.6 * wall_drop + 0.03 * grain
                colour = [c * (0.3 + 0.16 * (1.0 - age) + 0.4 * wall_drop + 0.05 * tone) for c in wax_rgb]
                roughness = 0.62
        heights.append(level)
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        rough.append(roughness)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.35 / columns, roughness=rough,
                     ao_radius=0.4 / columns, ao_strength=1.3, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
