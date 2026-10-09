"""Grass seen from above: thousands of blades over soil, tileable PBR maps from the standard library only.

Each blade is a tapered stroke from its root, pointing in a random direction with a slight common lean, rising
toward the middle and drooping at the tip. Blades are painted with a z-buffer: a pixel keeps the highest blade, with
that blade's colour from dark base to lighter tip, so blades cross and occlude each other. Soil shows through
sparse turf, dry blades mix in by ``dryness``, and optional clover flowers dot the lawn. Strokes wrap around the
tile edges.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "grass_lawn"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.85]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.35, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "blades", "type": "int", "default": 4800, "minimum": 200, "maximum": 12000,
     "meaning": "Number of blades on the tile."},
    {"name": "blade_length", "type": "float", "default": 0.042, "minimum": 0.008, "maximum": 0.12,
     "meaning": "Average blade length in texture units."},
    {"name": "blade_width", "type": "float", "default": 0.0034, "minimum": 0.001, "maximum": 0.01,
     "meaning": "Blade width at the base in texture units."},
    {"name": "lean", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How strongly blades lean one way, as after mowing or wind."},
    {"name": "dryness", "type": "float", "default": 0.1, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of straw-coloured dry blades."},
    {"name": "flowers", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Small clover flowers in the turf."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Mown lawn: dense short green blades.", "values": {}},
    "meadow": {"description": "Long meadow grass with dry blades and clover flowers.",
               "values": {"blades": 2600, "blade_length": 0.07, "blade_width": 0.004, "lean": 0.1,
                          "dryness": 0.35, "flowers": 0.5}},
    "dry_summer": {"description": "Parched straw-coloured grass with bare soil.",
                   "values": {"blades": 2400, "dryness": 0.85, "blade_length": 0.04}},
    "lush_dark": {"description": "Dense, dark, well-watered turf.",
                  "values": {"blades": 7000, "blade_length": 0.034, "dryness": 0.0, "lean": 0.5}},
}
#: Base green, tip green, dry straw, soil and flower colours per preset (sRGB).
PALETTES = {
    "default": ("#2f5a1c", "#79a83e", "#b7a467", "#4a3a28", "#f2f0e6"),
    "meadow": ("#3a5e22", "#8bb04a", "#c9b57a", "#4f3f2b", "#f3eef5"),
    "dry_summer": ("#4f5a26", "#93944a", "#cdb683", "#7a6145", "#efe9d8"),
    "lush_dark": ("#1d4214", "#4f8a2c", "#a39257", "#33281c", "#f0efe8"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The grass maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    base_rgb, tip_rgb, dry_rgb, soil_rgb, flower_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    count = width * height
    soil = tk.fbm(width, height, 12, 3, tk.hash_u32(seed, 1))
    clumps = tk.fbm(width, height, 5, 3, tk.hash_u32(seed, 2))
    level = [0.08 + 0.04 * s for s in soil]
    red = [soil_rgb[0] * (0.8 + 0.4 * (s + 0.5)) for s in soil]
    green = [soil_rgb[1] * (0.8 + 0.4 * (s + 0.5)) for s in soil]
    blue = [soil_rgb[2] * (0.8 + 0.4 * (s + 0.5)) for s in soil]
    rough = [0.95] * count
    rng = tk.Rng(seed, 3)
    lean_angle = rng.uniform(0.0, math.tau)
    floor_width = 0.6 / min(width, height)
    for _ in range(p["blades"]):
        u, v = rng.random(), rng.random()
        if rng.random() > 0.55 + 0.45 * (clumps[int(v * height) % height * width + int(u * width) % width] + 0.5):
            continue
        angle = rng.uniform(0.0, math.tau) if rng.random() > p["lean"] else lean_angle + rng.gauss(0.0, 0.4)
        length = p["blade_length"] * rng.uniform(0.5, 1.4)
        tip_u, tip_v = u + length * math.cos(angle), v + length * math.sin(angle)
        radius = max(p["blade_width"] * rng.uniform(0.7, 1.3), floor_width)
        top = rng.uniform(0.6, 1.0)
        dry = rng.random() < p["dryness"]
        shade = rng.uniform(0.85, 1.15)
        root_rgb = dry_rgb if dry else base_rgb
        end_rgb = [c * 1.1 for c in dry_rgb] if dry else tip_rgb
        for index, d, t in tk.segment_pixels(width, height, u, v, tip_u, tip_v, radius):
            if d > 1.0 - 0.75 * t:
                continue
            rise = top * (0.35 + 0.65 * math.sin(math.pi * min(1.0, t * 0.85 + 0.15)))
            surface = rise * (1.0 - 0.4 * d * d) + 0.1
            if surface > level[index]:
                level[index] = surface
                mix = t ** 0.8
                colour = [(a + (b - a) * mix) * shade * (0.8 + 0.25 * (1.0 - d)) for a, b in zip(root_rgb, end_rgb)]
                red[index], green[index], blue[index] = colour
                rough[index] = 0.7 - 0.15 * (1.0 - d) + (0.15 if dry else 0.0)
    if p["flowers"] > 0.0:
        for _ in range(int(60 * p["flowers"])):
            cu, cv = rng.random(), rng.random()
            radius = rng.uniform(0.006, 0.01)
            for index, s, t in tk.ellipse_pixels(width, height, cu, cv, radius, radius):
                reach = s * s + t * t
                if reach < 1.0:
                    petals = 0.5 + 0.5 * math.cos(9.0 * math.atan2(t, s))
                    if reach < 0.6 + 0.4 * petals:
                        level[index] = 1.15 - 0.2 * reach
                        tint = 0.85 + 0.15 * petals
                        red[index], green[index], blue[index] = [c * tint for c in flower_rgb]
                        rough[index] = 0.6
    peak = max(level)
    heights = [v / peak for v in level]
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.01, roughness=rough,
                     ao_radius=0.015, ao_strength=1.4, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
