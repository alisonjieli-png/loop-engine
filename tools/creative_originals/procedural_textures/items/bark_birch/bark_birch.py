"""Birch bark: white papery bark with lenticels, branch scars and peeling strips (standard library only).

The trunk axis runs down the tile. Lenticels are short horizontal dashes drawn as raised capsules; branch scars are
dark chevrons stamped from a V-shaped profile; dark fissured patches come from a thresholded fractal crossed by
cracks; peeling strips are ragged horizontal bands where the tan inner bark shows, with a bright curled lip along
their upper edge. Every mark is placed in texture space and wraps around the tile edges.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "bark_birch"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.4, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "lenticels", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of the horizontal lenticel dashes."},
    {"name": "lenticel_length", "type": "float", "default": 0.05, "minimum": 0.01, "maximum": 0.15,
     "meaning": "Average lenticel length in texture units."},
    {"name": "dark_patches", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of dark, fissured bark."},
    {"name": "branch_scars", "type": "int", "default": 2, "minimum": 0, "maximum": 8,
     "meaning": "Dark chevron branch scars on the tile."},
    {"name": "peeling", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Strips of outer bark peeled off, showing the inner bark."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Paper birch: chalk-white bark with dark lenticels and a few scars.", "values": {}},
    "silver_aged": {"description": "Older silver birch with large black fissured patches.",
                    "values": {"dark_patches": 0.45, "branch_scars": 4, "peeling": 0.1, "lenticels": 0.7}},
    "river_birch": {"description": "Salmon-tan river birch with heavy curling peel.",
                    "values": {"peeling": 0.85, "dark_patches": 0.1, "lenticels": 0.35, "branch_scars": 1}},
    "young_smooth": {"description": "Young smooth birch with fine, sparse lenticels and no scars.",
                     "values": {"lenticels": 0.3, "lenticel_length": 0.025, "dark_patches": 0.0,
                                "branch_scars": 0, "peeling": 0.1}},
}
#: Outer bark, warm tint, lenticel/scar colour, dark patch colour, inner bark colour per preset (sRGB).
PALETTES = {
    "default": ("#ece8df", "#e6d7c6", "#3d3530", "#1f1b19", "#c48a5c"),
    "silver_aged": ("#d9d8d3", "#d2cbc1", "#3a3634", "#151413", "#a8785a"),
    "river_birch": ("#d9b9a0", "#c99a7b", "#4a3a31", "#2b221d", "#a45f3c"),
    "young_smooth": ("#efece6", "#e9ded2", "#57493f", "#2a2421", "#c99169"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The birch bark maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    outer, warm, mark_rgb, dark_rgb, inner = (tk.hex_rgb(code) for code in PALETTES[preset])
    count = width * height
    rng = tk.Rng(seed, 1)
    marks = [0.0] * count
    min_radius = 0.7 / min(width, height)
    for _ in range(int(40 + 360 * p["lenticels"])):
        u, v = rng.random(), rng.random()
        length = p["lenticel_length"] * rng.uniform(0.3, 1.6)
        thickness = max(min_radius, rng.uniform(0.0015, 0.004))
        tk.draw_segment(marks, width, height, u, v, u + length, v + rng.uniform(-0.004, 0.004), thickness,
                        rng.uniform(0.6, 1.0))
    for _ in range(p["branch_scars"]):
        cu, cv = rng.random(), rng.random()
        spread = rng.uniform(0.05, 0.12)

        def chevron(s, t):
            centre = 0.55 * abs(s) - 0.25
            thick = 0.22 * (1.0 - s * s)
            gap = abs(t - centre)
            return 1.0 - gap / thick if gap < thick else None
        tk.stamp(marks, width, height, cu, cv, spread, spread * 0.6, chevron)
    patches = tk.fbm(width, height, 3, 5, tk.hash_u32(seed, 2), cells_y=14)
    breakup = tk.fbm(width, height, 12, 3, tk.hash_u32(seed, 7), cells_y=40)
    cracks = tk.voronoi(width, height, 6, 30, tk.hash_u32(seed, 3), jitter=0.9)["edge"]
    bands = tk.value_noise(width, height, 2, 40, tk.hash_u32(seed, 4))
    fibre = tk.fbm(width, height, 24, 3, tk.hash_u32(seed, 5), cells_y=96)
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 6))
    peel = [0.0] * count
    lip = [0.0] * count
    for _ in range(int(14 * p["peeling"])):
        cu, cv = rng.random(), rng.random()
        half_length, half_height = rng.uniform(0.06, 0.2), rng.uniform(0.008, 0.03)
        ragged = rng.random() * 50.0
        for index, s, t in tk.ellipse_pixels(width, height, cu, cv, half_length, half_height):
            edge = 1.0 - abs(s) ** 3 - 0.25 * math.sin(ragged + 9.0 * s) * (1.0 - abs(s))
            if abs(t) < edge:
                peel[index] = 1.0
                if t < -edge + 0.35:
                    lip[index] = max(lip[index], 1.0 - (t + edge) / 0.35)
    threshold = 0.3 - 0.45 * p["dark_patches"]
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(count):
        dark = tk.smoothstep(threshold, threshold + 0.05, patches[index] + 0.35 * breakup[index]) \
            if p["dark_patches"] > 0.0 else 0.0
        dark *= 0.55 + 0.45 * tk.smoothstep(-0.2, 0.2, breakup[index])
        fissure = dark * (1.0 - tk.smoothstep(0.0, 0.06, cracks[index]))
        colour = [o + (w - o) * bands[index] * 0.6 for o, w in zip(outer, warm)]
        colour = [c * (0.95 + 0.06 * fibre[index] + 0.04 * grit[index]) for c in colour]
        colour = [c + (m - c) * min(1.0, marks[index]) for c, m in zip(colour, mark_rgb)]
        colour = [c + (d * (0.8 + 0.4 * grit[index]) - c) * dark for c, d in zip(colour, dark_rgb)]
        if peel[index] > 0.0:
            colour = [i * (0.85 + 0.25 * fibre[index] + 0.1 * grit[index]) for i in inner]
            colour = [c + (0.97 - c) * lip[index] * 0.7 for c in colour]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        level = 0.55 + 0.03 * fibre[index] + 0.08 * min(1.0, marks[index]) - 0.12 * dark - 0.3 * fissure
        level = level - 0.08 * peel[index] + 0.18 * lip[index]
        heights.append(level)
        rough.append(0.72 + 0.12 * dark + 0.1 * grit[index] + 0.06 * peel[index] - 0.06 * min(1.0, marks[index]))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     ao_radius=0.015, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
