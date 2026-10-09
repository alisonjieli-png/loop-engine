"""Interlocking concrete pavers: zigzag, dogbone or wavy shapes in stretcher bond, tileable PBR maps (stdlib only).

Pavers are two units long and one unit wide, laid in rows that alternate their offset by one unit. The joint between
two rows is not straight: it follows a periodic curve b(x) in units of the row height, a cosine with the paver
length as period for dogbone (I-shaped) pavers, so each paver is wide at its ends and narrow in the middle where
the next row's ends reach in, or a zigzag or sine with half that period for zigzag and wavy pavers. Because both
rows read the same curve, neighbours interlock exactly. The distance to the curved sides and straight ends shapes
chamfers above sand joints; aggregate speckle, tumbled edges and per-paver colour finish the surface.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "interlocking_pavers"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.45, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "shape", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "0 zigzag sides (two teeth per paver), 1 dogbone or I shape (wide ends, narrow middle), "
                "2 wavy sides (a sine with two waves per paver)."},
    {"name": "pavers_per_row", "type": "int", "default": 4, "minimum": 2, "maximum": 10,
     "meaning": "Pavers across the tile in each row; the tile holds twice as many rows."},
    {"name": "amplitude", "type": "float", "default": 0.16, "minimum": 0.04, "maximum": 0.3,
     "meaning": "How far the curved sides swing, in paver widths."},
    {"name": "joint_width", "type": "float", "default": 0.05, "minimum": 0.015, "maximum": 0.15,
     "meaning": "Sand joint width in paver widths."},
    {"name": "chamfer", "type": "float", "default": 0.06, "minimum": 0.01, "maximum": 0.2,
     "meaning": "Width of the bevelled top edge in paver widths."},
    {"name": "joint_fill", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 0.95,
     "meaning": "Height of the jointing sand relative to the paver tops."},
    {"name": "aggregate", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Exposed stone aggregate speckling the concrete face."},
    {"name": "tumbling", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Tumbled, rounded and chipped edges of antique-style pavers."},
    {"name": "colour_variation", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of colour between pavers."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Grey concrete zigzag pavers with light sand joints.", "values": {}},
    "red_dogbone": {"description": "Red concrete I-shaped dogbone pavers interlocking in stretcher bond.",
                    "values": {"shape": 1, "amplitude": 0.2, "aggregate": 0.2, "colour_variation": 0.3}},
    "charcoal_wavy": {"description": "Charcoal wavy pavers with fine aggregate and tight joints.",
                      "values": {"shape": 2, "pavers_per_row": 5, "amplitude": 0.12, "joint_width": 0.035,
                                 "aggregate": 0.7, "colour_variation": 0.2}},
    "tumbled_blend": {"description": "Tumbled dogbone pavers in a brown, tan and charcoal blend.",
                      "values": {"shape": 1, "pavers_per_row": 3, "amplitude": 0.22, "joint_width": 0.08,
                                 "chamfer": 0.12, "tumbling": 0.85, "joint_fill": 0.45, "aggregate": 0.3,
                                 "colour_variation": 0.95}},
}
#: Paver colours, sand colour, aggregate colours (light, dark), paver roughness per preset (sRGB).
PALETTES = {
    "default": (["#8e8c88", "#9a9894", "#85837f", "#a29f9a"], "#c4b69c", "#d8d4cc", "#55524d", 0.88),
    "red_dogbone": (["#9a4a3a", "#8c4234", "#a65240", "#83402f"], "#c9b99a", "#c9a090", "#4b2a22", 0.86),
    "charcoal_wavy": (["#47474a", "#4f4f52", "#404043", "#57575a"], "#a8a294", "#bdbab3", "#262628", 0.84),
    "tumbled_blend": (["#7d5f47", "#a58663", "#4d4844", "#8e6c4f", "#b8966f", "#5d5650"], "#b6a687", "#d4c8b2",
                      "#3c342d", 0.9),
}


def _side(x: float, shape: int, amplitude: float) -> tuple:
    """(offset, slope) of the row joint at x units from a paver end, in paver widths; period two units for shape 1,
    one unit for shapes 0 and 2."""
    if shape == 1:
        phase = math.pi * x
        return -amplitude * math.cos(phase), amplitude * math.pi * math.sin(phase)
    t = x - math.floor(x)
    if shape == 0:
        offset = amplitude * (4.0 * abs(t - 0.5) - 1.0)
        return offset, amplitude * 4.0 * (1.0 if t > 0.5 else -1.0)
    phase = 2.0 * math.pi * t
    return -amplitude * math.cos(phase), amplitude * 2.0 * math.pi * math.sin(phase)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The paver maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    pavers_hex, sand_hex, light_hex, dark_hex, paver_rough = PALETTES[preset]
    palette = [tk.hex_rgb(code) for code in pavers_hex]
    sand_rgb, light_rgb, dark_rgb = tk.hex_rgb(sand_hex), tk.hex_rgb(light_hex), tk.hex_rgb(dark_hex)
    shape, n, amplitude = p["shape"], p["pavers_per_row"], p["amplitude"]
    rows = 2 * n
    columns = 2 * n
    half_joint = p["joint_width"] * 0.5
    chamfer = p["chamfer"]
    tumbling, aggregate, variation = p["tumbling"], p["aggregate"], p["colour_variation"]
    fill = 0.3 + 0.45 * p["joint_fill"]
    face = tk.fbm(width, height, 4 * n, 4, tk.hash_u32(seed, 2))
    chips = tk.fbm(width, height, 12 * n, 3, tk.hash_u32(seed, 3))
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    stains = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 5))
    pixel = columns / width
    count = len(palette)
    floor = math.floor
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        sy = (y + 0.5) / height * rows
        base_row = floor(sy)
        for x in range(width):
            index = y * width + x
            sx = (x + 0.5) / width * columns
            row = base_row
            top, top_slope = _side(sx - (row % 2), shape, amplitude)
            if sy < row + top:
                row -= 1
            else:
                bottom, _slope = _side(sx - ((row + 1) % 2), shape, amplitude)
                if sy >= row + 1 + bottom:
                    row += 1
            top, top_slope = _side(sx - (row % 2), shape, amplitude)
            bottom, bottom_slope = _side(sx - ((row + 1) % 2), shape, amplitude)
            along = (sx - (row % 2)) % 2.0
            paver = floor((sx - (row % 2)) / 2.0)
            key = (row % rows, paver % n)
            code = tk.hash_u32(seed, *key)
            pick, tone_jitter, tilt = tk.hash_float(code, 1), tk.hash_float(code, 2) - 0.5, tk.hash_float(code, 3)
            to_top = (sy - row - top) / math.sqrt(1.0 + top_slope * top_slope)
            to_bottom = (row + 1 + bottom - sy) / math.sqrt(1.0 + bottom_slope * bottom_slope)
            to_end = min(along, 2.0 - along)
            inside = min(to_top, to_bottom, to_end) - half_joint
            inside -= tumbling * 0.05 * max(0.0, chips[index] + 0.15)
            t = inside / (chamfer * (1.0 + tumbling))
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else (math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
                                                                   if tumbling > 0.3 else t)
            top_level = 0.8 + 0.02 * (tilt - 0.5) + 0.012 * face[index] - 0.02 * tumbling * (1.0 - profile)
            sand = fill + 0.03 * face[index]
            level = sand + (top_level - sand) * profile if inside > 0.0 else sand
            heights.append(max(level, sand))
            colour = palette[min(int((pick * variation + 0.5 * (1.0 - variation)) * count), count - 1)]
            tone = 1.0 + 0.1 * tone_jitter * variation + 0.06 * face[index] - 0.12 * (1.0 - profile)
            colour = [c * tone for c in colour]
            g = grain[index]
            if aggregate > 0.0:
                if g > 1.0 - 0.12 * aggregate:
                    colour = [c + (a - c) * 0.6 for c, a in zip(colour, light_rgb)]
                elif g < 0.1 * aggregate:
                    colour = [c + (a - c) * 0.6 for c, a in zip(colour, dark_rgb)]
            stain = 0.1 * tk.smoothstep(0.2, 0.6, stains[index])
            colour = [c * (1.0 - stain) for c in colour]
            cover = tk.smoothstep(-pixel, pixel, inside)
            joint = [c * (0.8 + 0.35 * g) for c in sand_rgb]
            colour = [j + (c - j) * cover for j, c in zip(joint, colour)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            stone_rough = paver_rough + 0.05 * (tilt - 0.5) - 0.06 * aggregate * (1.0 if g > 0.9 else 0.0)
            rough.append(0.97 + (stone_rough - 0.97) * cover)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.016, roughness=rough,
                     ao_radius=0.02, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
