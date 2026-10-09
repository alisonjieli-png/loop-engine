"""Cracked asphalt: aggregate in bitumen, branching cracks, sealant and stains, tileable PBR maps (standard library).

Aggregate is a fine Voronoi diagram: each cell is a stone with its own grey, and binder fills the narrow borders.
Cracks are random walks that wander and branch, drawn as narrow grooves; alligator cracking adds the borders of a
coarser Voronoi diagram in a patch. Sealant bands follow the main cracks as glossy black strips, and oil stains
darken soft blotches. Everything is placed in texture space and wraps around the tile edges.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "asphalt_cracked"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.6]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.2, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "aggregate_size", "type": "int", "default": 80, "minimum": 24, "maximum": 200,
     "meaning": "Aggregate stones across the tile (higher is finer)."},
    {"name": "cracks", "type": "int", "default": 4, "minimum": 0, "maximum": 16,
     "meaning": "Main cracks wandering across the tile; each may branch."},
    {"name": "crack_width", "type": "float", "default": 0.006, "minimum": 0.001, "maximum": 0.015,
     "meaning": "Main crack width in texture units."},
    {"name": "alligator", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Area of alligator (fatigue) cracking."},
    {"name": "sealant", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Glossy tar sealant painted over the main cracks."},
    {"name": "wear", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Binder worn off the stone tops: 0 fresh black, 1 old grey."},
    {"name": "stains", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Oil and water stains."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Worn grey road asphalt with a few long cracks.", "values": {}},
    "fresh": {"description": "New black asphalt with no cracks.",
              "values": {"cracks": 0, "wear": 0.05, "stains": 0.05, "aggregate_size": 110}},
    "alligator": {"description": "Old pavement with fatigue cracking and stains.",
                  "values": {"alligator": 0.8, "cracks": 6, "wear": 0.8, "stains": 0.6}},
    "sealed": {"description": "Repaired asphalt with tar sealant over the cracks.",
               "values": {"cracks": 7, "sealant": 1.0, "wear": 0.6}},
    "coarse_chip": {"description": "Coarse chip seal with large, light stones.",
                    "values": {"aggregate_size": 40, "wear": 0.9, "cracks": 2}},
}
#: Binder colour, stone greys and sealant colour per preset (sRGB).
PALETTES = {
    "default": ("#1f1f20", ["#5d5c5a", "#6f6d69", "#4b4a48", "#7e7b76", "#575553"], "#0b0b0c"),
    "fresh": ("#111112", ["#2e2e2f", "#3a3a3b", "#262627", "#444445"], "#060607"),
    "alligator": ("#232322", ["#64625e", "#76736d", "#55534f", "#86827b"], "#0c0c0c"),
    "sealed": ("#1d1d1e", ["#5a5957", "#6a6865", "#4a4947", "#77746f"], "#09090a"),
    "coarse_chip": ("#262524", ["#8a857c", "#9c968b", "#6f6b64", "#b0a99c", "#7c776f"], "#0c0c0c"),
}


def _walk(rng, start_u: float, start_v: float, heading: float, steps: int, step: float) -> list:
    points = [(start_u, start_v)]
    u, v = start_u, start_v
    for _ in range(steps):
        heading += rng.gauss(0.0, 0.16)
        u, v = u + step * math.cos(heading), v + step * math.sin(heading)
        points.append((u, v))
    return points


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The asphalt maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    binder_hex, stone_hex, sealant_hex = PALETTES[preset]
    binder, sealant_rgb = tk.hex_rgb(binder_hex), tk.hex_rgb(sealant_hex)
    stones = [tk.hex_rgb(code) for code in stone_hex]
    count = width * height
    size = p["aggregate_size"]
    cells = tk.voronoi(width, height, size, size, tk.hash_u32(seed, 1), jitter=1.0)
    rng = tk.Rng(seed, 2)
    crack = [0.0] * count
    seal = [0.0] * count
    width_main = p["crack_width"]
    for _ in range(p["cracks"]):
        path = _walk(rng, rng.random(), rng.random(), rng.uniform(0.0, math.tau), rng.integer(14, 30), 0.022)
        tk.draw_path(crack, width, height, path, width_main * 0.5)
        if p["sealant"] > 0.0:
            tk.draw_path(seal, width, height, path, width_main * 2.5 + 0.006, profile=lambda d: 1.0)
        for _branch in range(rng.integer(0, 3)):
            origin = path[rng.integer(1, len(path) - 1)]
            twig = _walk(rng, origin[0], origin[1], rng.uniform(0.0, math.tau), rng.integer(4, 10), 0.016)
            tk.draw_path(crack, width, height, twig, width_main * 0.3)
    if p["alligator"] > 0.0:
        net = tk.voronoi(width, height, 14, 14, tk.hash_u32(seed, 3), jitter=0.9)["edge"]
        region = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 4))
        threshold = 0.3 - 0.6 * p["alligator"]
        for index in range(count):
            inside = tk.smoothstep(threshold, threshold + 0.08, region[index])
            line = 1.0 - tk.smoothstep(0.0, 0.05, net[index])
            crack[index] = max(crack[index], line * inside * 0.9)
    stains = tk.fbm(width, height, 4, 5, tk.hash_u32(seed, 5))
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 6))
    wear, stain_amount, sealant = p["wear"], p["stains"], p["sealant"]
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(count):
        cell = cells["cell"][index]
        stone = tk.smoothstep(0.03, 0.12, cells["edge"][index])
        shade = stones[tk.hash_u32(cell, seed, 7) % len(stones)]
        exposed = stone * (0.25 + 0.75 * wear) * (0.6 + 0.4 * tk.hash_float(cell, seed, 8))
        colour = [b + (s * (0.9 + 0.2 * grit[index]) - b) * exposed for b, s in zip(binder, shade)]
        dark = stain_amount * tk.smoothstep(0.1, 0.4, stains[index]) * 0.6
        colour = [c * (1.0 - dark) for c in colour]
        groove = min(1.0, crack[index])
        colour = [c * (1.0 - 0.85 * groove) for c in colour]
        tar = sealant * min(1.0, seal[index])
        colour = [c + (s - c) * tar for c, s in zip(colour, sealant_rgb)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        level = 0.55 + 0.12 * stone * (0.3 + 0.7 * tk.hash_float(cell, seed, 9)) + 0.02 * grit[index] \
            - 0.45 * groove * (1.0 - tar) + 0.06 * tar
        heights.append(level)
        rough.append(0.9 - 0.12 * (1.0 - wear) * (1.0 - stone) - 0.35 * dark - 0.55 * tar + 0.05 * grit[index])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     ao_radius=0.008, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
