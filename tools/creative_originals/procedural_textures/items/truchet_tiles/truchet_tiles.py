"""Truchet tiles: quarter-circle arcs, diagonal mazes and split triangles on a square grid (standard library).

Each cell of an n by n grid takes one of two orientations from a hash of its index (or, with `order`, from the
parity of i + j), and the same few tile designs, turned, join across every edge into long meandering paths.
Quarter-circle tiles (Smith's variant) hold two arcs of radius one half around opposite corners; the regions they
cut out are two-coloured by the parity of the grid corner each region touches, which is consistent across every
cell because both arcs of a cell meet the edges at their midpoints. Diagonal tiles make the classic random maze.
Triangle tiles (Truchet's originals) split each cell into a dark and a light half in four turns.

Lines are drawn from their exact distance in cell units with a rounded profile, so they can be raised as enamel or
sunk as inlay; with `metal_lines` they become metallic, as in brass inlay. Everything is periodic because the grid
has a whole number of cells across the tile and hashes wrap with the cell index.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "truchet_tiles"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "style", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "0 quarter-circle arcs, 1 diagonal maze, 2 split triangles."},
    {"name": "cells", "type": "int", "default": 8, "minimum": 2, "maximum": 32,
     "meaning": "Tiles across the tile."},
    {"name": "line_width", "type": "float", "default": 0.16, "minimum": 0.02, "maximum": 0.45,
     "meaning": "Width of the arcs or lines as a share of a cell."},
    {"name": "order", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of cells whose turn follows the checkerboard parity instead of chance."},
    {"name": "fill", "type": "float", "default": 0.8, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Contrast of the two-colour region fill (arcs and triangles)."},
    {"name": "relief", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far the lines stand above the ground (sunk below it for inlay and grout presets)."},
    {"name": "metal_lines", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Metallic value of the lines, 1 for metal inlay."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Glazed ceramic: cobalt arcs raised over white and pale blue regions.", "values": {}},
    "maze_print": {"description": "Random diagonal maze printed in black on off-white paper.",
                   "values": {"style": 1, "cells": 16, "line_width": 0.12, "relief": 0.05, "fill": 0.0}},
    "brass_inlay": {"description": "Brass arcs inlaid flush in dark walnut with alternating stained regions.",
                    "values": {"cells": 6, "line_width": 0.09, "metal_lines": 1.0, "relief": 0.15, "fill": 0.5}},
    "triangle_floor": {"description": "Cement floor of terracotta and cream half-square triangles.",
                       "values": {"style": 2, "cells": 8, "line_width": 0.04, "relief": 0.5, "fill": 1.0}},
}
#: Per preset: ground colour, second fill colour, line colour (sRGB), ground and line roughness, line sunk (1) or
#: raised (0), and wood grain on the ground (1) or not (0).
PALETTES = {
    "default": ("#f2f0ea", "#a8c4e0", "#1f3f8a", 0.18, 0.12, 0, 0),
    "maze_print": ("#ebe4d4", "#d8cfbc", "#1a1a1a", 0.9, 0.85, 0, 0),
    "brass_inlay": ("#4a3020", "#2e1c12", "#c9a24a", 0.45, 0.28, 1, 1),
    "triangle_floor": ("#e6dcc6", "#a8492e", "#7a7468", 0.75, 0.9, 1, 0),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The Truchet maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    ground_hex, fill_hex, line_hex, ground_rough, line_rough, sunk, grain_on = PALETTES[preset]
    ground, second, line_colour = tk.hex_rgb(ground_hex), tk.hex_rgb(fill_hex), tk.hex_rgb(line_hex)
    n, style = p["cells"], p["style"]
    half = 0.5 * p["line_width"]
    pixel = n / min(width, height)
    turns = []
    for j in range(n):
        for i in range(n):
            if tk.hash_float(seed, 1, i, j) < p["order"]:
                turns.append((i + j) % 2)
            else:
                turns.append(tk.hash_u32(seed, 2, i, j) & 3)
    grain = tk.fbm(width, height, 2, 5, tk.hash_u32(seed, 3), cells_y=24) if grain_on else None
    speck = tk.fbm(width, height, 40, 2, tk.hash_u32(seed, 4))
    relief, fill_strength, metal = p["relief"], p["fill"], p["metal_lines"]
    red, green, blue, heights, rough, metallic = [], [], [], [], [], []
    for y in range(height):
        cy = (y + 0.5) / height * n
        j = int(cy) % n
        fy = cy - math.floor(cy)
        for x in range(width):
            cx = (x + 0.5) / width * n
            i = int(cx) % n
            fx = cx - math.floor(cx)
            turn = turns[j * n + i]
            flip = turn & 1
            if style == 0:
                ax, ay = (0.0, 0.0) if flip == 0 else (1.0, 0.0)
                bx, by = 1.0 - ax, 1.0 - ay
                ra, rb = math.hypot(fx - ax, fy - ay), math.hypot(fx - bx, fy - by)
                distance = min(abs(ra - 0.5), abs(rb - 0.5))
                if ra < 0.5:
                    parity = (i + int(ax) + j + int(ay)) % 2
                elif rb < 0.5:
                    parity = (i + int(bx) + j + int(by)) % 2
                else:
                    parity = (i + j + 1 + flip) % 2
            elif style == 1:
                distance = abs(fx - fy) if flip == 0 else abs(fx + fy - 1.0)
                distance *= math.sqrt(0.5)
                parity = 0
            else:
                above = (fy > fx) if flip == 0 else (fx + fy < 1.0)
                parity = int(above) ^ ((turn >> 1) & 1)
                distance = min(fx, 1.0 - fx, fy, 1.0 - fy)
            index = y * width + x
            on_line = tk.smoothstep(half + 0.7 * pixel, half - 0.7 * pixel, distance)
            profile = math.sqrt(max(0.0, 1.0 - (distance / half) ** 2)) if distance < half else 0.0
            base = [g + (s - g) * fill_strength * parity for g, s in zip(ground, second)]
            texture = 0.94 + 0.06 * speck[index]
            if grain is not None:
                texture *= 0.85 + 0.3 * (0.5 + 0.5 * grain[index])
            base = [c * texture for c in base]
            colour = [b + (c - b) * on_line for b, c in zip(base, line_colour)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            lift = relief * (0.35 * on_line + 0.4 * profile)
            heights.append(0.5 + (-lift if sunk else lift) + 0.02 * speck[index])
            rough.append(ground_rough + (line_rough - ground_rough) * on_line + 0.04 * speck[index])
            metallic.append(metal * on_line)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.06 / n, roughness=rough,
                     metallic=metallic, ao_radius=0.3 / n, ao_strength=0.8, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
