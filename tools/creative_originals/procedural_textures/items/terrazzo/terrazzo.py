"""Terrazzo: stone and glass chips set in cement and polished flat, tileable PBR maps (standard library only).

Chips are irregular polygons: each has five to nine vertices at random radii around its centre, and a pixel is
inside when its distance from the centre is under the radius interpolated between the two nearest vertices. Chip
sizes follow a log-uniform spread between the smallest and largest size, and chips are painted largest first so
small ones settle between them. The cement matrix carries fine sand speckle and slight clouding. Polishing leaves
the surface nearly flat: chips stand a hair proud and the matrix holds tiny pores.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "terrazzo"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "chips", "type": "int", "default": 260, "minimum": 20, "maximum": 1200,
     "meaning": "Number of chips on the tile."},
    {"name": "smallest", "type": "float", "default": 0.006, "minimum": 0.002, "maximum": 0.05,
     "meaning": "Smallest chip radius in texture units."},
    {"name": "largest", "type": "float", "default": 0.03, "minimum": 0.004, "maximum": 0.12,
     "meaning": "Largest chip radius in texture units."},
    {"name": "angularity", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How jagged the chip outlines are (0 rounded pebbles, 1 sharp shards)."},
    {"name": "polish", "type": "float", "default": 0.8, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Surface finish from honed (0) to polished (1)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "White cement with mixed grey, black, rust and white marble chips.", "values": {}},
    "venetian": {"description": "Warm matrix with large, dense marble chips in reds and creams.",
                 "values": {"chips": 340, "largest": 0.055, "smallest": 0.008, "angularity": 0.35}},
    "pastel": {"description": "Pink matrix with sparse pastel chips.",
               "values": {"chips": 140, "largest": 0.035, "angularity": 0.6}},
    "noir": {"description": "Charcoal matrix with white and grey chips.",
             "values": {"chips": 420, "largest": 0.02, "smallest": 0.004}},
    "glass_honed": {"description": "Grey matrix with green and blue glass shards, honed.",
                    "values": {"chips": 300, "angularity": 1.0, "polish": 0.3}},
}
#: Matrix colour and chip colours per preset (sRGB).
PALETTES = {
    "default": ("#e7e4de", ["#2a2a2c", "#8d8f92", "#b4643f", "#f4f2ee", "#5f6062", "#c9b59a"]),
    "venetian": ("#d8cbb6", ["#9c3b2c", "#e9dcc4", "#7a5a46", "#c7a07a", "#3e2a22", "#efe7d8"]),
    "pastel": ("#e9c9c4", ["#f2e3c9", "#9fc2b7", "#e6a593", "#b7b2d8", "#f7f1e9"]),
    "noir": ("#2b2b2d", ["#f0eee9", "#a8a9ab", "#d8d6d1", "#6d6e70"]),
    "glass_honed": ("#a7a9a8", ["#2f7d5e", "#3a6f9a", "#9fd0c0", "#1f4f3e", "#e9ecea"]),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The terrazzo maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    matrix_hex, chip_hex = PALETTES[preset]
    matrix = tk.hex_rgb(matrix_hex)
    chip_colours = [tk.hex_rgb(code) for code in chip_hex]
    count = width * height
    owner = [-1] * count
    smallest, largest = sorted((p["smallest"], p["largest"]))
    rng = tk.Rng(seed, 1)
    chips = []
    for _ in range(p["chips"]):
        radius = math.exp(rng.uniform(math.log(smallest), math.log(largest)))
        sides = rng.integer(5, 9)
        jag = 0.15 + 0.5 * p["angularity"]
        radii = [1.0 - jag * rng.random() for _ in range(sides)]
        chips.append((radius, rng.random(), rng.random(), radii, rng.uniform(0.0, math.tau),
                      rng.integer(0, len(chip_colours) - 1), rng.uniform(-1.0, 1.0)))
    chips.sort(key=lambda chip: -chip[0])
    for number, (radius, cu, cv, radii, turn, _colour, _tone) in enumerate(chips):
        sides = len(radii)
        for index, s, t in tk.ellipse_pixels(width, height, cu, cv, radius, radius, turn):
            reach = s * s + t * t
            if reach > 1.0:
                continue
            angle = (math.atan2(t, s) / math.tau) % 1.0 * sides
            k = int(angle) % sides
            f = angle - int(angle)
            limit = radii[k] + (radii[(k + 1) % sides] - radii[k]) * f
            if reach <= limit * limit:
                owner[index] = number
    sand = tk.white_noise(width, height, tk.hash_u32(seed, 2))
    cloud = tk.fbm(width, height, 4, 4, tk.hash_u32(seed, 3))
    pores = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    polish = p["polish"]
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(count):
        number = owner[index]
        if number >= 0:
            chip = chips[number]
            colour = [c * (1.0 + 0.1 * chip[6] + 0.04 * (sand[index] - 0.5)) for c in chip_colours[chip[5]]]
            level = 0.56 + 0.01 * chip[6]
            roughness = 0.08 + 0.55 * (1.0 - polish) + 0.03 * sand[index]
        else:
            speck = 0.9 + 0.2 * sand[index] + 0.04 * cloud[index]
            colour = [c * speck for c in matrix]
            pore = pores[index] > 0.992
            level = 0.5 - (0.12 if pore else 0.0)
            roughness = 0.12 + 0.55 * (1.0 - polish) + (0.3 if pore else 0.0) + 0.04 * sand[index]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        heights.append(level)
        rough.append(roughness)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.004, roughness=rough,
                     ao_radius=0.006, ao_strength=0.5, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
