"""Lava crust: dark cooling plates over glowing cracks, tileable PBR maps with an emissive map (standard library).

Plates are Voronoi cells drifting apart on the torus; the gap between them is molten. Glow follows depth into the
crack through a heat ramp (yellow-white core, orange, deep red), and plate rims carry a dim heat halo. Plate tops
are rough basalt with ropy wrinkles: a sine of the warped distance from the cell centre, as on pahoehoe. The
emissive map is the glow alone (sRGB); albedo stays dark where the lava glows so engines add light rather than
reflect it.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "lava_crust"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.5]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
    {"name": "emissive", "channels": 3, "colour_space": "srgb", "convention": "gltf_emissive"},
]
PARAMETERS = [
    {"name": "plates_across", "type": "int", "default": 6, "minimum": 2, "maximum": 20,
     "meaning": "Crust plates across the tile."},
    {"name": "crack_width", "type": "float", "default": 0.08, "minimum": 0.01, "maximum": 0.3,
     "meaning": "Molten gap width in plate widths."},
    {"name": "heat", "type": "float", "default": 0.85, "minimum": 0.05, "maximum": 1.0,
     "meaning": "Temperature of the melt: brightness and colour of the glow."},
    {"name": "rim_glow", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Heat halo creeping onto the plate rims."},
    {"name": "ropes", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Ropy wrinkles on the crust."},
    {"name": "fragmentation", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Secondary cracks breaking plates into clinker."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo and glow in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Active flow: black crust plates over bright orange cracks.", "values": {}},
    "cooling": {"description": "Cooling flow: thin dull-red cracks and grey crust.",
                "values": {"heat": 0.35, "crack_width": 0.04, "rim_glow": 0.15, "ropes": 0.7}},
    "clinker": {"description": "Blocky a'a clinker broken into many small glowing pieces.",
                "values": {"plates_across": 10, "fragmentation": 0.9, "ropes": 0.1, "crack_width": 0.06}},
    "lava_lake": {"description": "Wide molten seams between drifting rafts.",
                  "values": {"plates_across": 4, "crack_width": 0.22, "heat": 1.0, "rim_glow": 0.7}},
}
HEAT_RAMP = [(0.0, "#000000"), (0.25, "#3a0400"), (0.5, "#a81800"), (0.75, "#ff6a00"), (0.92, "#ffc23a"),
             (1.0, "#fff1b0")]


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The lava maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    plates = p["plates_across"]
    cells = tk.voronoi(width, height, plates, plates, tk.hash_u32(seed, 1), jitter=0.9)
    shards = tk.voronoi(width, height, plates * 3, plates * 3, tk.hash_u32(seed, 2), jitter=0.9)["edge"]
    warp = tk.fbm(width, height, plates * 2, 3, tk.hash_u32(seed, 3))
    rough_noise = tk.fbm(width, height, 40, 3, tk.hash_u32(seed, 4))
    grit = tk.white_noise(width, height, tk.hash_u32(seed, 5))
    half = p["crack_width"] * 0.5
    heat, rim, ropes, fragmentation = p["heat"], p["rim_glow"], p["ropes"], p["fragmentation"]
    pixel = plates / min(width, height)
    glow_values, red, green, blue, heights, rough = [], [], [], [], [], []
    for index in range(width * height):
        edge = cells["edge"][index] + 0.25 * half * warp[index]
        gap = 1.0 - tk.smoothstep(half - pixel, half + pixel, edge)
        depth = 1.0 - tk.smoothstep(0.0, half, edge)
        shard = fragmentation * (1.0 - tk.smoothstep(0.0, 0.02 + 0.02 * fragmentation, shards[index])) * (1.0 - gap)
        halo = rim * (1.0 - tk.smoothstep(half, half + 0.18, edge))
        glow = heat * max(gap * (0.55 + 0.45 * depth), 0.55 * halo, 0.6 * shard)
        glow_values.append(glow)
        wrinkle = math.sin(cells["f1"][index] * 38.0 + 5.0 * warp[index])
        crust_level = 0.7 + 0.06 * ropes * wrinkle + 0.06 * rough_noise[index] + 0.04 * (grit[index] - 0.5)
        level = crust_level * (1.0 - gap) + 0.15 * gap - 0.25 * shard
        heights.append(level)
        shade = 0.12 + 0.05 * ropes * wrinkle + 0.06 * rough_noise[index] + 0.04 * grit[index]
        cooled = (1.0 - heat) * 0.18
        colour = [shade + cooled, shade * 0.9 + cooled * 0.9, shade * 0.85 + cooled * 0.85]
        colour = [c * (1.0 - 0.8 * gap) for c in colour]
        red.append(colour[0])
        green.append(colour[1])
        blue.append(colour[2])
        rough.append(0.9 - 0.45 * gap + 0.06 * grit[index])
    emissive = tk.ramp(glow_values, HEAT_RAMP)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    emissive = tk.grade(emissive, p["hue_shift"], 1.0, 1.0)
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.03, roughness=rough,
                     emissive=emissive, ao_radius=0.02, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
