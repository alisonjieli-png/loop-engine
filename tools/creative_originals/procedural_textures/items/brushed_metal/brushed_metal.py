"""Brushed metal: fine directional streaks on steel, aluminium, brass, copper or titanium (standard library only).

Brushing leaves countless parallel micro-grooves. Here they are noise stretched hundreds of times along the
brushing direction (horizontal across the tile), at two scales, slightly waved so the lines are not ruled. Broader
bands, where the abrasive pressed harder or softer on one pass, vary the brightness and roughness at a scale that
stays visible from a distance. A few deeper scratches run along the same direction, and faint swirl blotches vary
the roughness. The whole surface is metal, so the metallic map is uniform; the base colour is the metal's reflectance.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "brushed_metal"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.3, 0.98]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 0.9]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "streak_density", "type": "int", "default": 220, "minimum": 40, "maximum": 600,
     "meaning": "Streak cells across the tile height (higher gives finer lines)."},
    {"name": "streak_depth", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Depth of the brushing grooves."},
    {"name": "waviness", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How much the streaks wave."},
    {"name": "scratches", "type": "int", "default": 12, "minimum": 0, "maximum": 120,
     "meaning": "Deeper scratches along the brushing direction."},
    {"name": "roughness_base", "type": "float", "default": 0.32, "minimum": 0.05, "maximum": 0.8,
     "meaning": "Average roughness."},
    {"name": "smudges", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Faint blotches of different roughness, like fingerprints and wiping marks."},
    {"name": "banding", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Broad bands along the brushing direction from uneven abrasive passes."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Albedo brightness multiplier (metals keep at most their reflectance)."},
]
PRESETS = {
    "default": {"description": "Brushed stainless steel.", "values": {}},
    "aluminium": {"description": "Bright brushed aluminium, slightly finer.",
                  "values": {"streak_density": 300, "roughness_base": 0.28}},
    "brass": {"description": "Brushed brass with soft smudges.", "values": {"smudges": 0.6, "roughness_base": 0.3}},
    "copper": {"description": "Brushed copper with coarse grooves.",
               "values": {"streak_density": 140, "streak_depth": 0.8, "roughness_base": 0.35}},
    "titanium_satin": {"description": "Satin titanium, fine and smooth, few scratches.",
                       "values": {"streak_density": 420, "streak_depth": 0.3, "roughness_base": 0.22,
                                  "scratches": 4, "waviness": 0.1}},
}
#: Metal reflectance colour per preset (sRGB, as glTF expects for metals).
PALETTES = {"default": "#c5c8cb", "aluminium": "#dcdfe2", "brass": "#d6b465", "copper": "#e0a487",
            "titanium_satin": "#b8b3aa"}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The brushed metal maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    metal = tk.hex_rgb(PALETTES[preset])
    count = width * height
    density = p["streak_density"]
    fine = tk.fbm(width, height, 3, 2, tk.hash_u32(seed, 1), cells_y=density)
    coarse = tk.fbm(width, height, 2, 2, tk.hash_u32(seed, 2), cells_y=max(8, density // 6))
    wave = tk.fbm(width, height, 2, 2, tk.hash_u32(seed, 3), cells_y=3)
    zero = [0.0] * count
    amount = p["waviness"] * 2.0 / density
    fine = tk.warp(fine, width, height, zero, wave, amount)
    coarse = tk.warp(coarse, width, height, zero, wave, amount)
    bands = tk.fbm(width, height, 1, 3, tk.hash_u32(seed, 6), cells_y=max(4, density // 20))
    bands = tk.warp(bands, width, height, zero, wave, amount)
    smudge = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 4))
    scratch = [0.0] * count
    rng = tk.Rng(seed, 5)
    for _ in range(p["scratches"]):
        u, v = rng.random(), rng.random()
        length = rng.uniform(0.1, 0.45)
        slope = rng.gauss(0.0, 0.02)
        tk.draw_segment(scratch, width, height, u, v, u + length, v + length * slope, rng.uniform(0.0008, 0.002),
                        rng.uniform(0.4, 1.0))
    depth, base, smudges, banding = p["streak_depth"], p["roughness_base"], p["smudges"], p["banding"]
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(count):
        groove = 0.6 * fine[index] + 0.4 * coarse[index]
        cut = min(1.0, scratch[index])
        band = banding * bands[index]
        shade = 0.92 + 0.14 * depth * groove + 0.16 * band - 0.12 * cut
        red.append(metal[0] * shade)
        green.append(metal[1] * shade)
        blue.append(metal[2] * shade)
        heights.append(0.5 + 0.12 * depth * groove - 0.15 * cut)
        rough.append(base + 0.08 * depth * abs(groove) - 0.1 * band + smudges * 0.15 * smudge[index] + 0.1 * cut)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.004, roughness=rough,
                     metallic=1.0, ao_radius=0.005, ao_strength=0.3, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
