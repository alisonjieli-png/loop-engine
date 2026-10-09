"""Basket weave paving: pairs or triples of pavers turning in a checkerboard, tileable PBR maps (standard library).

The tile is a checkerboard of squares, ``2 * repeats`` per side. Each square holds ``bricks_per_square`` pavers whose
length equals the square side, laid horizontally in one colour of the checkerboard and vertically in the other, so
the pavers seem to weave over and under each other. A paver's distance to its own sides shapes a worn, rounded top
above sand-filled joints; every paver takes its colour, fired flashing on its ends, tilt and roughness from a hash.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "basketweave_pavers"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "bricks_per_square", "type": "int", "default": 2, "minimum": 2, "maximum": 4,
     "meaning": "Pavers side by side in each square; the paver length is this many paver widths."},
    {"name": "repeats", "type": "int", "default": 2, "minimum": 1, "maximum": 6,
     "meaning": "Pairs of checkerboard squares across the tile."},
    {"name": "joint_width", "type": "float", "default": 0.08, "minimum": 0.02, "maximum": 0.25,
     "meaning": "Joint width in paver widths."},
    {"name": "joint_fill", "type": "float", "default": 0.55, "minimum": 0.0, "maximum": 0.95,
     "meaning": "Height of the sand in the joints relative to the paver tops."},
    {"name": "edge_wear", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Rounding and chipping of the paver edges from traffic."},
    {"name": "flashing", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Darker fired ends and blotches on clay pavers."},
    {"name": "settling", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Uneven paver heights and tilts from a settled bed."},
    {"name": "moss", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Moss and dark dirt growing in the joints."},
    {"name": "colour_variation", "type": "float", "default": 0.55, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of colour between pavers."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Red clay pavers in two-paver basket weave with light sand joints.", "values": {}},
    "charcoal_concrete": {"description": "Charcoal concrete pavers in three-paver basket weave, crisp chamfers.",
                          "values": {"bricks_per_square": 3, "joint_width": 0.05, "edge_wear": 0.12,
                                     "flashing": 0.0, "settling": 0.12, "colour_variation": 0.3,
                                     "joint_fill": 0.7}},
    "weathered_moss": {"description": "Old brown brick pavers, worn round, settled, with moss in the joints.",
                       "values": {"repeats": 3, "joint_width": 0.12, "edge_wear": 0.85, "settling": 0.8,
                                  "moss": 0.8, "flashing": 0.6, "colour_variation": 0.8, "joint_fill": 0.4}},
    "buff_patio": {"description": "Buff and tan clay pavers with grey sand and light flashing.",
                   "values": {"joint_width": 0.1, "flashing": 0.25, "colour_variation": 0.65}},
}
#: Paver colours, flash colour, sand colour, moss colour, paver roughness per preset (sRGB).
PALETTES = {
    "default": (["#9c4430", "#8a3a29", "#ad5139", "#7d3325", "#a24b33"], "#4e2219", "#c7b89a", "#4f6b2a", 0.86),
    "charcoal_concrete": (["#4a4a4b", "#545455", "#424243", "#5c5b5a"], "#2e2e2f", "#9b968c", "#4f6b2a", 0.9),
    "weathered_moss": (["#7a4a35", "#6b3f2e", "#875540", "#5c3729", "#80503a"], "#3b2018", "#8e8169", "#46622a",
                       0.88),
    "buff_patio": (["#c8a77a", "#b99668", "#d4b48a", "#ad8a5d", "#c29f72"], "#7c5a3a", "#a7a39a", "#55702e",
                   0.86),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The basket weave maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    pavers_hex, flash_hex, sand_hex, moss_hex, paver_rough = PALETTES[preset]
    pavers = [tk.hex_rgb(code) for code in pavers_hex]
    flash_rgb, sand_rgb, moss_rgb = tk.hex_rgb(flash_hex), tk.hex_rgb(sand_hex), tk.hex_rgb(moss_hex)
    n = p["bricks_per_square"]
    squares = 2 * p["repeats"]
    units = squares * n
    half_joint = p["joint_width"] * 0.5
    wear, flashing, settling, moss = p["edge_wear"], p["flashing"], p["settling"], p["moss"]
    variation = p["colour_variation"]
    rounding = 0.06 + 0.3 * wear
    fill = 0.3 + 0.45 * p["joint_fill"]
    face = tk.fbm(width, height, units * 2, 4, tk.hash_u32(seed, 2))
    chips = tk.fbm(width, height, units * 4, 3, tk.hash_u32(seed, 3))
    blotch = tk.fbm(width, height, max(4, units // 2), 3, tk.hash_u32(seed, 4))
    sand = tk.white_noise(width, height, tk.hash_u32(seed, 5))
    patches = tk.fbm(width, height, 5, 4, tk.hash_u32(seed, 6))
    traits = {}
    pixel = units / width
    count = len(pavers) - 1
    floor = math.floor
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        sy = (y + 0.5) / height * units
        cj = floor(sy / n)
        ly = sy - cj * n
        for x in range(width):
            index = y * width + x
            sx = (x + 0.5) / width * units
            ci = floor(sx / n)
            lx = sx - ci * n
            if (ci + cj) % 2 == 0:
                brick = min(int(ly), n - 1)
                along, across = lx, ly - brick
            else:
                brick = min(int(lx), n - 1)
                along, across = ly, lx - brick
            key = (ci % squares, cj % squares, brick)
            trait = traits.get(key)
            if trait is None:
                code = tk.hash_u32(seed, *key)
                trait = tuple(tk.hash_float(code, k) for k in range(7))
                traits[key] = trait
            side = min(across, 1.0 - across)
            end = min(along, n - along)
            inside = min(side, end) - half_joint - 0.06 * wear * max(0.0, chips[index] + 0.1)
            t = inside / rounding
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
            tilt = settling * 0.03 * ((trait[1] - 0.5) * (along / n - 0.5) * 2.0 + (trait[2] - 0.5) * (across - 0.5))
            top = 0.8 + settling * 0.04 * (trait[3] - 0.5) + tilt + 0.02 * face[index]
            sand_level = fill + 0.03 * face[index]
            level = max(sand_level, sand_level + (top - sand_level) * profile) if inside > 0.0 else sand_level
            heights.append(level)
            cover = tk.smoothstep(-pixel, pixel, inside)
            pick = (trait[0] * variation + 0.5 * (1.0 - variation)) * count
            low = min(int(pick), count - 1)
            f = pick - low
            paver = [a + (b - a) * f for a, b in zip(pavers[low], pavers[low + 1])]
            ends = 1.0 - tk.smoothstep(0.0, 0.6, end)
            burn = flashing * tk.clamp(0.5 * ends * (0.4 + trait[4]) + 0.6 * max(0.0, blotch[index] - 0.15))
            tone = 1.0 + 0.06 * face[index] + 0.05 * (sand[index] - 0.5) - 0.1 * (1.0 - profile) * cover
            paver = [(c + (fl - c) * burn) * tone for c, fl in zip(paver, flash_rgb)]
            grain = 0.82 + 0.3 * sand[index]
            joint = [c * grain for c in sand_rgb]
            growth = moss * tk.smoothstep(0.0, 0.5, 0.35 + patches[index]) if moss > 0.0 else 0.0
            if growth > 0.0:
                joint = [c + (m * (0.7 + 0.5 * sand[index]) - c) * growth for c, m in zip(joint, moss_rgb)]
                creep = growth * (1.0 - profile) * 0.6
                paver = [c + (m * 0.8 - c) * creep for c, m in zip(paver, moss_rgb)]
            colour = [j + (q - j) * cover for j, q in zip(joint, paver)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            stone_rough = paver_rough + 0.06 * (trait[5] - 0.5) - 0.12 * wear * profile * max(0.0, face[index])
            rough.append(0.97 + (stone_rough - 0.97) * cover)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.016, roughness=rough,
                     ao_radius=0.02, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
