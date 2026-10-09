"""Riven slate: cleft terraces, fine riving lines and iron spots, tileable PBR maps (standard library only).

Slate splits along its cleavage into thin sheets, so a riven face is a set of nearly flat terraces with short steps
between them. Here a warped fractal is quantized into terraces whose step edges are smoothed; each terrace gets its
own tone from its level. Fine streaks stretched along the cleavage add the riving texture, and optional iron spots
(pyrite weathering) leave small rusty halos. A slight sheen follows the streaks.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "slate_cleft"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.7]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.25, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "terraces", "type": "int", "default": 7, "minimum": 2, "maximum": 20,
     "meaning": "Cleavage levels over the height range."},
    {"name": "terrace_scale", "type": "int", "default": 3, "minimum": 1, "maximum": 10,
     "meaning": "Noise cells across the tile for the terrace outlines (higher gives smaller terraces)."},
    {"name": "step_softness", "type": "float", "default": 0.15, "minimum": 0.02, "maximum": 0.5,
     "meaning": "Share of each level spent on the step edge (low values give crisp steps)."},
    {"name": "riving", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Depth of the fine streaks along the cleavage."},
    {"name": "iron_spots", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Rusty spots from weathered pyrite."},
    {"name": "tone_variation", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Tone change between terraces."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Blue-grey riven slate with a few rust spots.", "values": {}},
    "green": {"description": "Grey-green slate with broad, soft terraces.",
              "values": {"terraces": 5, "step_softness": 0.3, "iron_spots": 0.05}},
    "heather": {"description": "Purple-grey slate with crisp steps.",
                "values": {"terraces": 9, "step_softness": 0.06, "terrace_scale": 4}},
    "rusty_multicolour": {"description": "Grey slate stained with heavy rust and ochre.",
                          "values": {"iron_spots": 0.8, "tone_variation": 0.8}},
    "black_honed": {"description": "Fine black slate, honed nearly flat.",
                    "values": {"terraces": 3, "step_softness": 0.45, "riving": 0.15, "iron_spots": 0.0,
                               "tone_variation": 0.2}},
}
#: Dark and light slate tones, rust colour, base roughness per preset (sRGB).
PALETTES = {
    "default": ("#2a2e33", "#5a6168", "#8a5631", 0.72),
    "green": ("#343e37", "#66746a", "#86603a", 0.75),
    "heather": ("#352f3a", "#685d70", "#8b5835", 0.7),
    "rusty_multicolour": ("#2f3133", "#64676a", "#9a5e2c", 0.78),
    "black_honed": ("#161719", "#2c2e31", "#6e4a2e", 0.45),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The slate maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    dark_hex, light_hex, rust_hex, base_rough = PALETTES[preset]
    dark, light, rust = tk.hex_rgb(dark_hex), tk.hex_rgb(light_hex), tk.hex_rgb(rust_hex)
    scale = p["terrace_scale"]
    field = tk.normalize(tk.fbm(width, height, scale, 5, tk.hash_u32(seed, 1), gain=0.55, cells_y=scale + 1))
    warp_u = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 2))
    warp_v = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 3))
    field = tk.warp(field, width, height, warp_u, warp_v, 0.05)
    streaks = tk.fbm(width, height, 6, 3, tk.hash_u32(seed, 4), cells_y=80)
    sheen = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 5), cells_y=24)
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 6))
    spots = [0.0] * (width * height)
    rng = tk.Rng(seed, 7)
    for _ in range(int(60 * p["iron_spots"])):
        radius = rng.uniform(0.006, 0.03)
        tk.stamp(spots, width, height, rng.random(), rng.random(), radius, radius * rng.uniform(0.6, 1.0),
                 lambda s, t: max(0.0, 1.0 - math.sqrt(s * s + t * t)) ** 0.7, angle=rng.uniform(0, 3.1))
    levels, softness = p["terraces"], p["step_softness"]
    tones = [tk.hash_float(level, seed, 8) for level in range(levels + 1)]
    riving, variation = p["riving"], p["tone_variation"]
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(width * height):
        scaled = field[index] * levels
        level = min(int(scaled), levels - 1)
        within = scaled - level
        step = tk.smoothstep(1.0 - softness, 1.0, within)
        terrace = (level + step) / levels
        heights.append(0.1 + 0.8 * terrace + 0.035 * riving * streaks[index] + 0.01 * (grit[index] - 0.5))
        tone = tones[level] * variation + 0.5 * (1.0 - variation)
        colour = [a + (b - a) * tone for a, b in zip(dark, light)]
        lip = tk.smoothstep(0.0, softness * 0.5, within) * (1.0 - tk.smoothstep(softness * 0.5, softness * 2.0,
                                                                                   within))
        colour = [c * (1.0 + 0.3 * riving * streaks[index] + 0.08 * (grit[index] - 0.5) - 0.3 * step + 0.25 * lip)
                  for c in colour]
        stain = min(1.0, spots[index] * 1.3)
        if stain > 0.0:
            colour = [c + (r * (0.7 + 0.5 * grit[index]) - c) * stain for c, r in zip(colour, rust)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        rough.append(base_rough - 0.12 * max(0.0, sheen[index]) + 0.1 * step + 0.15 * stain + 0.05 * grit[index])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.02, roughness=rough,
                     ao_radius=0.02, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
