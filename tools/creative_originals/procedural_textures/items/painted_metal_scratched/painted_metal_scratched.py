"""Painted metal with chips and scratches: paint over primer over steel, tileable PBR maps (standard library only).

Three layers: a top coat, a primer and bare steel. Chips come from a thresholded, warped fractal; a pixel deep inside
a chip has lost both coats and shows metal, one near the chip rim shows primer, so chips get the stepped edge of
real flaking paint. Scratches are thin strokes, mostly along one direction, that cut through to the metal. Exposed
metal can start to rust, grime settles in a soft layer, and the metallic map follows the exposed steel only.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "painted_metal_scratched"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "chipping", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of the paint chipped away."},
    {"name": "chip_scale", "type": "int", "default": 6, "minimum": 2, "maximum": 24,
     "meaning": "Noise cells across the tile for the chips (higher gives smaller chips)."},
    {"name": "scratches", "type": "int", "default": 40, "minimum": 0, "maximum": 300,
     "meaning": "Number of scratches."},
    {"name": "scratch_direction", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How strongly scratches follow one direction (0 random, 1 parallel)."},
    {"name": "rust", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Rust on the exposed metal."},
    {"name": "grime", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dirt and dust over the paint."},
    {"name": "paint_gloss", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Gloss of the top coat (0 flat, 1 glossy enamel)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Safety yellow over grey primer with chips and scratches.", "values": {}},
    "olive_drab": {"description": "Matte military olive drab, heavily scuffed.",
                   "values": {"paint_gloss": 0.1, "scratches": 120, "chipping": 0.3, "grime": 0.5}},
    "glossy_red": {"description": "Glossy red enamel with a few fine scratches.",
                   "values": {"paint_gloss": 0.95, "chipping": 0.08, "scratches": 25, "rust": 0.0, "grime": 0.05,
                              "scratch_direction": 0.8}},
    "machinery_blue": {"description": "Worn blue machinery paint with oily grime.",
                       "values": {"chipping": 0.45, "grime": 0.7, "paint_gloss": 0.4}},
    "old_tractor": {"description": "Faded green paint flaking off rusty steel.",
                    "values": {"chipping": 0.7, "rust": 0.85, "grime": 0.6, "paint_gloss": 0.2, "chip_scale": 5}},
}
#: Top coat, primer, steel, rust and grime colours per preset (sRGB).
PALETTES = {
    "default": ("#e3b21f", "#8f9294", "#a9adb2", "#8a4520", "#4a4235"),
    "olive_drab": ("#55593a", "#6f6b5c", "#9fa3a8", "#7a4020", "#3d3a2c"),
    "glossy_red": ("#b51d1d", "#9a9c9e", "#b4b8bd", "#8a4520", "#3a3330"),
    "machinery_blue": ("#2b5d8f", "#8c4a32", "#a5a9ae", "#80401e", "#2f2a22"),
    "old_tractor": ("#3f6b3a", "#8b5a3a", "#9b9fa4", "#7d3b1a", "#4a3e2e"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The painted metal maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    paint_rgb, primer_rgb, steel_rgb, rust_rgb, grime_rgb = (tk.hex_rgb(code) for code in PALETTES[preset])
    count = width * height
    scale = p["chip_scale"]
    chips = tk.fbm(width, height, scale, 5, tk.hash_u32(seed, 1), gain=0.6)
    warp_u = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 2))
    warp_v = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 3))
    chips = tk.warp(chips, width, height, warp_u, warp_v, 0.03)
    grime_field = tk.fbm(width, height, 4, 4, tk.hash_u32(seed, 4))
    orange_peel = tk.fbm(width, height, 40, 2, tk.hash_u32(seed, 5))
    rust_field = tk.fbm(width, height, 18, 3, tk.hash_u32(seed, 6))
    grain = tk.fbm(width, height, 4, 2, tk.hash_u32(seed, 7), cells_y=160)
    scratch = [0.0] * count
    rng = tk.Rng(seed, 8)
    main_angle = rng.uniform(0.0, math.pi)
    for _ in range(p["scratches"]):
        angle = main_angle + rng.gauss(0.0, 0.2) if rng.random() < p["scratch_direction"] else rng.uniform(0, math.pi)
        length = rng.uniform(0.03, 0.18)
        u, v = rng.random(), rng.random()
        tk.draw_segment(scratch, width, height, u, v, u + length * math.cos(angle), v + length * math.sin(angle),
                        rng.uniform(0.0012, 0.003), rng.uniform(0.5, 1.0))
    threshold = 0.3 - 0.62 * p["chipping"]
    red, green, blue, heights, rough, metallic = [], [], [], [], [], []
    for index in range(count):
        depth = chips[index] - threshold
        paint_lost = tk.smoothstep(0.0, 0.015, depth)
        primer_lost = tk.smoothstep(0.05, 0.065, depth)
        cut = min(1.0, scratch[index] * 1.4)
        primer_lost = max(primer_lost, cut)
        paint_lost = max(paint_lost, min(1.0, cut * 1.3))
        rusty = p["rust"] * primer_lost * tk.smoothstep(-0.15, 0.25, rust_field[index])
        metal = [c * (0.92 + 0.12 * grain[index]) for c in steel_rgb]
        metal = [m + (r * (0.8 + 0.4 * (rust_field[index] + 0.5)) - m) * rusty for m, r in zip(metal, rust_rgb)]
        colour = [pr + (m - pr) * primer_lost for pr, m in zip(primer_rgb, metal)]
        colour = [pa * (0.97 + 0.04 * orange_peel[index]) + (c - pa) * paint_lost for pa, c in zip(paint_rgb, colour)]
        dirt = p["grime"] * tk.smoothstep(-0.2, 0.35, grime_field[index]) * 0.55
        colour = [c + (g - c) * dirt for c, g in zip(colour, grime_rgb)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        metal_share = primer_lost * (1.0 - rusty)
        metallic.append(metal_share)
        paint_rough = 0.75 - 0.6 * p["paint_gloss"] + 0.03 * orange_peel[index]
        rough.append((1.0 - paint_lost) * paint_rough + paint_lost * (1.0 - primer_lost) * 0.7
                     + primer_lost * (0.35 + 0.5 * rusty + 0.05 * grain[index]) + 0.25 * dirt)
        heights.append(0.6 - 0.08 * paint_lost - 0.08 * primer_lost + 0.005 * orange_peel[index] + 0.03 * rusty
                       - 0.04 * cut)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     metallic=metallic, ao_radius=0.01, ao_strength=0.8, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
