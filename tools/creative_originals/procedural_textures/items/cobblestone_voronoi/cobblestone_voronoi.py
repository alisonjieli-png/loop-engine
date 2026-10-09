"""Cobblestone paving from Voronoi cells: tileable PBR maps from the standard library only.

Each stone is one cell of a jittered Voronoi diagram on the torus. The distance to the cell border (the bisector with
the nearest neighbour) shapes a domed, worn top; noise roughens the outline and the face. Soil, sand or moss fills
the gaps up to a set level, and each stone takes its own colour, height and roughness from a hash of its cell.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "cobblestone_voronoi"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.85]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.25, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "stones_across", "type": "int", "default": 7, "minimum": 3, "maximum": 16,
     "meaning": "Stones across the tile (cells of the Voronoi grid per side)."},
    {"name": "jitter", "type": "float", "default": 0.75, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far each stone's centre strays from a square grid: 0 square setts, 1 irregular cobbles."},
    {"name": "gap_width", "type": "float", "default": 0.08, "minimum": 0.01, "maximum": 0.3,
     "meaning": "Joint width between stones, in stone widths."},
    {"name": "roundness", "type": "float", "default": 0.35, "minimum": 0.05, "maximum": 1.0,
     "meaning": "How far in from the edge the dome rises, in stone widths: small values give flat tops."},
    {"name": "corner_rounding", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Rounds the stone corners: 0 keeps the Voronoi polygon, 1 trims each stone to a disc."},
    {"name": "irregularity", "type": "float", "default": 0.06, "minimum": 0.0, "maximum": 0.2,
     "meaning": "Noise on the stone outlines, in stone widths."},
    {"name": "wear", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Polish of the stone tops from foot traffic (lower roughness on the crowns)."},
    {"name": "gap_fill", "type": "float", "default": 0.45, "minimum": 0.0, "maximum": 0.9,
     "meaning": "Height of the soil or sand in the joints relative to the stone crowns."},
    {"name": "moss", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Moss growing in the joints and creeping onto stone edges."},
    {"name": "colour_variation", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of colour and brightness between stones."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Grey granite cobbles with dark soil joints.", "values": {}},
    "river_rounded": {"description": "Rounded river stones in warm sand, deep joints.",
                      "values": {"stones_across": 7, "jitter": 0.55, "gap_width": 0.06, "roundness": 0.9,
                                 "irregularity": 0.04, "gap_fill": 0.3, "wear": 0.8, "corner_rounding": 1.0}},
    "mossy": {"description": "Old irregular cobbles with moss in the joints.",
              "values": {"moss": 0.85, "gap_width": 0.1, "irregularity": 0.09, "wear": 0.2}},
    "basalt_setts": {"description": "Dark basalt setts in a near-square grid with flat tops.",
                     "values": {"stones_across": 8, "jitter": 0.15, "gap_width": 0.05, "roundness": 0.12,
                                "irregularity": 0.025, "gap_fill": 0.6, "colour_variation": 0.3,
                                "corner_rounding": 0.1}},
    "sandstone": {"description": "Warm sandstone cobbles with pale mortar-like sand.",
                  "values": {"stones_across": 6, "jitter": 0.6, "roundness": 0.25, "gap_fill": 0.65,
                             "colour_variation": 0.8}},
}
#: Stone colours, joint colour, moss colour, base stone roughness per preset (sRGB).
PALETTES = {
    "default": (["#6d6b68", "#7f7c77", "#5c5a57", "#8b8781", "#74706a"], "#3b3329", "#4f6b2a", 0.72),
    "river_rounded": (["#8a7d6e", "#9e9283", "#6f665d", "#a7988a", "#7b7066"], "#b59f7c", "#5d7334", 0.6),
    "mossy": (["#66655f", "#74726a", "#57564f", "#807d74", "#6b6a62"], "#352e24", "#4c6a22", 0.78),
    "basalt_setts": (["#3a3a3c", "#434345", "#333335", "#4b4b4d", "#3e3e40"], "#2c2925", "#45602a", 0.7),
    "sandstone": (["#b08a62", "#c29b70", "#9d7a55", "#c8a67e", "#a8835b"], "#cdb894", "#6a7a3a", 0.8),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The cobblestone maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    stones_hex, gap_hex, moss_hex, stone_rough = PALETTES[preset]
    stones = [tk.hex_rgb(code) for code in stones_hex]
    gap_rgb, moss_rgb = tk.hex_rgb(gap_hex), tk.hex_rgb(moss_hex)
    cells = p["stones_across"]
    cells_data = tk.voronoi(width, height, cells, cells, tk.hash_u32(seed, 1), jitter=p["jitter"])
    edge, ids, nearest = cells_data["edge"], cells_data["cell"], cells_data["f1"]
    radius = 1.0 - 0.45 * p["corner_rounding"]
    wobble = tk.fbm(width, height, cells * 3, 3, tk.hash_u32(seed, 2))
    face = tk.fbm(width, height, cells * 4, 4, tk.hash_u32(seed, 3))
    soil = tk.fbm(width, height, 48, 3, tk.hash_u32(seed, 4))
    patches = tk.fbm(width, height, 6, 4, tk.hash_u32(seed, 5))
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 6))
    rng = tk.Rng(seed, 7)
    traits = [(rng.random(), rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0), rng.random())
              for _ in range(cells * cells)]
    half_gap = p["gap_width"] * 0.5
    roundness = p["roundness"]
    irregularity = p["irregularity"]
    fill = 0.12 + 0.55 * p["gap_fill"]
    pixel = cells / width
    variation = p["colour_variation"]
    moss = p["moss"]
    count = len(stones)
    red, green, blue, heights, rough = [], [], [], [], []
    for index in range(width * height):
        trait = traits[ids[index]]
        inside = min(edge[index] - half_gap, radius - nearest[index]) + irregularity * wobble[index]
        t = inside / roundness
        dome = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
        crown = 0.78 + 0.08 * trait[1] * variation
        stone_height = 0.12 + (crown - 0.12) * dome + 0.035 * face[index] if inside > 0.0 else 0.12
        soil_height = fill + 0.03 * soil[index]
        cover = tk.smoothstep(-pixel, pixel, stone_height - soil_height)
        heights.append(max(stone_height, soil_height))
        pick = (trait[0] * variation + 0.5 * (1.0 - variation)) * (count - 1)
        low = min(int(pick), count - 2)
        f = pick - low
        tone = 1.0 + 0.18 * trait[2] * variation + 0.1 * face[index] + 0.06 * (grit[index] - 0.5)
        stone = [(a + (b - a) * f) * tone for a, b in zip(stones[low], stones[low + 1])]
        dirt = 1.0 - 0.35 * (1.0 - dome) if inside > 0.0 else 0.65
        stone = [c * dirt for c in stone]
        joint = [c * (0.8 + 0.4 * grit[index] + 0.2 * soil[index]) for c in gap_rgb]
        growth = 0.0
        if moss > 0.0:
            reach = moss * (0.6 + 0.5 * patches[index])
            growth = tk.smoothstep(0.15, 0.6, reach) * (1.0 - cover) + \
                tk.smoothstep(0.0, 0.25, reach - dome * 0.9) * cover * moss
            growth = min(1.0, growth)
        colour = [s * cover + j * (1.0 - cover) for s, j in zip(stone, joint)]
        if growth > 0.0:
            shade = 0.75 + 0.5 * grit[index]
            colour = [c + (m * shade - c) * growth for c, m in zip(colour, moss_rgb)]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        polish = p["wear"] * dome * 0.4
        rough.append(cover * (stone_rough + 0.08 * trait[3] - polish) + (1.0 - cover) * 0.97 - 0.02 * growth)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.03, roughness=rough,
                     ao_radius=0.025, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
