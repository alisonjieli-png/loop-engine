"""Hand-hammered metal: overlapping dimples with polished ridges, tileable PBR maps (standard library only).

Each hammer blow is a cell of a jittered Voronoi diagram. Inside a cell the surface is a shallow spherical cap
around the blow's centre, so neighbouring dimples meet in soft ridges along the cell borders. Ridges catch the
polish and stay bright; aged presets let a dark patina settle in the dimples. A second, finer set of blows can
overlay the first, as on planished work.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "hammered_metal"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.98]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 0.9]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "dimples_across", "type": "int", "default": 9, "minimum": 3, "maximum": 30,
     "meaning": "Hammer blows across the tile."},
    {"name": "dimple_depth", "type": "float", "default": 0.6, "minimum": 0.1, "maximum": 1.0,
     "meaning": "Depth of the dimples."},
    {"name": "irregularity", "type": "float", "default": 0.85, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far blows stray from a regular grid."},
    {"name": "planishing", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Second layer of smaller, shallower blows."},
    {"name": "patina", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dark oxide settled in the dimples."},
    {"name": "polish", "type": "float", "default": 0.7, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Polish of the ridges and the metal overall."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Polished hammered copper.", "values": {}},
    "aged_copper": {"description": "Hammered copper darkened with patina in the dimples.",
                    "values": {"patina": 0.6, "polish": 0.4}},
    "pewter": {"description": "Soft grey hammered pewter with small, regular blows.",
               "values": {"dimples_across": 14, "irregularity": 0.5, "polish": 0.45, "dimple_depth": 0.45}},
    "brass_planished": {"description": "Brass with fine planishing marks over larger dimples.",
                        "values": {"planishing": 0.9, "dimples_across": 7, "polish": 0.8}},
    "silver": {"description": "Bright hammered silver with deep, large dimples.",
               "values": {"dimples_across": 6, "dimple_depth": 0.9, "polish": 0.9}},
}
#: Metal reflectance colour and patina colour per preset (sRGB).
PALETTES = {
    "default": ("#e6a383", "#3b2318"),
    "aged_copper": ("#b97a58", "#5e3a27"),
    "pewter": ("#b7b8b6", "#4a4a48"),
    "brass_planished": ("#d9b663", "#4d3a17"),
    "silver": ("#efefed", "#5a5a5c"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The hammered metal maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    metal, patina_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    count = width * height
    blows = p["dimples_across"]
    large = tk.voronoi(width, height, blows, blows, tk.hash_u32(seed, 1), jitter=p["irregularity"])
    small_count = blows * 3
    small = tk.voronoi(width, height, small_count, small_count, tk.hash_u32(seed, 2), jitter=1.0, edges=False)
    sheen = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 3))
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    depth, planish, patina, polish = p["dimple_depth"], p["planishing"], p["patina"], p["polish"]
    red, green, blue, heights, rough, metallic = [], [], [], [], [], []
    for index in range(count):
        r = min(1.0, large["f1"][index] / 0.75)
        cap = 1.0 - math.sqrt(max(0.0, 1.0 - r * r))
        fine = min(1.0, small["f1"][index] / 0.75)
        fine_cap = 1.0 - math.sqrt(max(0.0, 1.0 - fine * fine))
        level = 0.3 + 0.6 * depth * cap + 0.12 * planish * fine_cap + 0.02 * sheen[index]
        heights.append(level)
        ridge = tk.smoothstep(0.1, 0.0, large["edge"][index]) if large["edge"][index] < 0.1 else 0.0
        hollow = 1.0 - cap
        oxide = patina * tk.smoothstep(0.55, 0.98, hollow) * (0.7 + 0.3 * grain[index])
        shade = 0.9 + 0.08 * cap + 0.06 * ridge * polish + 0.04 * sheen[index]
        colour = [c * shade + (pc - c * shade) * oxide for c, pc in zip(metal, patina_rgb)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        metallic.append(1.0 - 0.7 * oxide)
        rough.append(0.45 - 0.35 * polish + 0.1 * hollow * (1.0 - polish) - 0.08 * ridge * polish + 0.4 * oxide
                     + 0.03 * grain[index])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.1 / blows + 0.004,
                     roughness=rough, metallic=metallic, ao_radius=0.3 / blows, ao_strength=0.6,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
