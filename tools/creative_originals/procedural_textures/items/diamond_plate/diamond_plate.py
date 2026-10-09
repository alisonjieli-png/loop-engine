"""Diamond tread plate: raised lugs in alternating diagonals, tileable PBR maps from the standard library only.

The tile is a grid of cells; each cell holds one elongated lug, a capsule turned to +45 or -45 degrees in a
checkerboard, which gives the familiar herringbone of tread plate and repeats with the grid. Lugs have a rounded
dome profile. Foot traffic polishes the lug tops, dirt collects in the valleys, and a painted preset wears through
to bare metal on the lug tops. The metallic map follows the bare metal.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "diamond_plate"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.08, 1.0]},
    {"name": "metallic", "channels": 1, "colour_space": "linear", "convention": "gltf_metallic"},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "lugs_across", "type": "int", "default": 6, "minimum": 2, "maximum": 20,
     "meaning": "Lug cells across the tile (and down it)."},
    {"name": "lug_length", "type": "float", "default": 0.7, "minimum": 0.3, "maximum": 1.1,
     "meaning": "Lug length as a share of the cell diagonal."},
    {"name": "lug_width", "type": "float", "default": 0.22, "minimum": 0.05, "maximum": 0.35,
     "meaning": "Lug width as a share of the cell."},
    {"name": "wear", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Polish of the lug tops (and paint worn through on painted plate)."},
    {"name": "dirt", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dirt in the valleys."},
    {"name": "paint", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Paint coverage (0 bare metal, 1 fully painted plate)."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Aluminium tread plate, lightly worn.", "values": {}},
    "steel_dirty": {"description": "Dark steel tread plate with dirt in the valleys.",
                    "values": {"dirt": 0.8, "wear": 0.7, "lugs_across": 8}},
    "painted_yellow": {"description": "Yellow painted tread plate worn to metal on the lug tops.",
                       "values": {"paint": 1.0, "wear": 0.6, "dirt": 0.4}},
    "fine_pattern": {"description": "Fine-pitched bright plate with short lugs.",
                     "values": {"lugs_across": 12, "lug_length": 0.6, "lug_width": 0.2, "wear": 0.2,
                                "dirt": 0.1}},
}
#: Metal, paint and dirt colours, base metal roughness per preset (sRGB).
PALETTES = {
    "default": ("#d2d5d8", "#d4a51c", "#4b4439", 0.35),
    "steel_dirty": ("#8f9397", "#d4a51c", "#3a3329", 0.45),
    "painted_yellow": ("#b9bdc1", "#e0b020", "#3d3528", 0.4),
    "fine_pattern": ("#dfe2e5", "#d4a51c", "#4b4439", 0.25),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The tread plate maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    metal_hex, paint_hex, dirt_hex, metal_rough = PALETTES[preset]
    metal, paint_rgb, dirt_rgb = tk.hex_rgb(metal_hex), tk.hex_rgb(paint_hex), tk.hex_rgb(dirt_hex)
    count = width * height
    cells = p["lugs_across"]
    half_length = p["lug_length"] * math.sqrt(2.0) * 0.5
    half_width = p["lug_width"] * 0.5
    grain = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 1), cells_y=96)
    grime = tk.fbm(width, height, 5, 4, tk.hash_u32(seed, 2))
    scuff = tk.fbm(width, height, 24, 3, tk.hash_u32(seed, 3))
    speck = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    root = 1.0 / math.sqrt(2.0)
    wear, dirt, paint = p["wear"], p["dirt"], p["paint"]
    red, green, blue, heights, rough, metallic = [], [], [], [], [], []
    for y in range(height):
        fv = (y + 0.5) / height * cells
        j = int(fv)
        cv = fv - j - 0.5
        base = y * width
        for x in range(width):
            index = base + x
            fu = (x + 0.5) / width * cells
            i = int(fu)
            cu = fu - i - 0.5
            sign = 1.0 if (i + j) % 2 == 0 else -1.0
            along = (cu + sign * cv) * root
            across = (sign * cu - cv) * root * sign
            reach = max(0.0, abs(along) - (half_length - half_width))
            distance = math.sqrt(reach * reach + across * across)
            dome = 0.0 if distance >= half_width else math.sqrt(1.0 - (distance / half_width) ** 2)
            top = tk.smoothstep(0.6, 0.95, dome)
            polish = wear * top * (0.6 + 0.4 * (scuff[index] + 0.5))
            valley = 1.0 - tk.smoothstep(0.0, 0.3, dome)
            grime_amount = dirt * valley * tk.smoothstep(-0.25, 0.3, grime[index]) * 0.7
            bare = [c * (0.88 + 0.08 * grain[index] + 0.12 * top + 0.08 * polish) for c in metal]
            painted = 0.0
            if paint > 0.0:
                painted = paint * (1.0 - tk.smoothstep(0.3, 0.7, polish * 1.6))
                coat = [c * (0.95 + 0.06 * speck[index]) for c in paint_rgb]
                bare = [b + (c - b) * painted for b, c in zip(bare, coat)]
            colour = [c + (d - c) * grime_amount for c, d in zip(bare, dirt_rgb)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            heights.append(0.3 + 0.55 * dome + 0.01 * grain[index] + 0.01 * painted)
            metal_share = (1.0 - painted) * (1.0 - grime_amount)
            metallic.append(metal_share)
            rough.append(metal_share * (metal_rough - 0.22 * polish + 0.05 * grain[index])
                         + (1.0 - metal_share) * (0.6 + 0.3 * grime_amount))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012 * 6 / cells + 0.004,
                     roughness=rough, metallic=metallic, ao_radius=0.3 / cells, ao_strength=1.0,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
