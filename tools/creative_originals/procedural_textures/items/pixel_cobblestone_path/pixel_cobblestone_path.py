"""Pixel-art cobblestone path: outlined round cobbles or square setts with grass or dirt between, tileable.

Stones sit on a jittered grid on a small art grid (``art_pixels`` square); with an even row count every other row
shifts by half a stone, as setts are laid. Each stone is a superellipse with its own size: its exponent blends from
a square sett (``roundness`` 0) to a round cobble (1). A pixel belongs to the stone whose shape it falls deepest
inside among the nine nearest, so neighbours never overlap. Inside a stone the offset from its centre along a light
from the top left picks highlight, light, base or shadow, and the outermost ring is a dark outline; wet stones
add a white glint. Between the stones grass with light tufts or packed dirt shows through. The art is enlarged with
nearest-neighbour sampling; heights (a dome per stone), normals and occlusion are computed per art pixel.
Standard library only.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "pixel_cobblestone_path"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.1, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "stones", "type": "int", "default": 4, "minimum": 2, "maximum": 8,
     "meaning": "Stones across the tile (and rows down it)."},
    {"name": "roundness", "type": "float", "default": 0.8, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Stone shape: 0 square setts, 1 round cobbles."},
    {"name": "stone_size", "type": "float", "default": 1.0, "minimum": 0.6, "maximum": 1.2,
     "meaning": "Stone size as a share of its cell; neighbours never overlap, larger values close the joints."},
    {"name": "jitter", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Random offset and size variation of the stones."},
    {"name": "grass", "type": "float", "default": 0.7, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of the joints grown with grass instead of bare dirt."},
    {"name": "wet", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Wetness: lower roughness and glints on the stones."},
    {"name": "relief", "type": "float", "default": 1.0, "minimum": 0.2, "maximum": 2.0,
     "meaning": "Strength of the per-pixel normal map."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Grey round cobbles with grass growing between them.", "values": {}},
    "sandstone_setts": {"description": "Warm square sandstone setts in offset rows with sandy joints.",
                        "values": {"roundness": 0.1, "stone_size": 0.92, "jitter": 0.2, "grass": 0.0,
                                   "stones": 4}},
    "wet_night": {"description": "Dark wet cobbles with glints and muddy joints.",
                  "values": {"wet": 0.9, "grass": 0.15, "stones": 5}},
    "mossy_path": {"description": "Old green-grey cobbles sunk in moss.",
                   "values": {"grass": 1.0, "stone_size": 0.85, "jitter": 0.8}},
}
#: Per preset: outline, shadow, base, light, highlight, glint, grass dark, grass light, dirt dark, dirt (sRGB).
PALETTES = {
    "default": ("#2c2b30", "#5d5c66", "#76757f", "#8f8e98", "#b1b0ba", "#ffffff", "#2f5a26", "#4f8a34", "#4a3a2a",
                "#65513a"),
    "sandstone_setts": ("#4e3a24", "#9c7b52", "#b48f60", "#c8a472", "#e0c08e", "#fff4dc", "#5a6a2c", "#7a8c3a",
                        "#8c7350", "#ab8f66"),
    "wet_night": ("#0f1015", "#2e3240", "#3c4152", "#4c5266", "#6a7290", "#e6f0ff", "#1e3020", "#2c4a2a", "#1f1a17",
                  "#2e2620"),
    "mossy_path": ("#1f2a22", "#4c5a4e", "#5f6d60", "#728274", "#91a192", "#ffffff", "#2a4a1e", "#4f7f2a",
                   "#3a3324", "#4f4530"),
}
#: Roughness of dry stone and of joints.
ROUGHNESS = (0.85, 0.95)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The path maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    (outline, shadow, base, light, highlight, glint, grass_dark, grass_light, dirt_dark,
     dirt) = (tk.hex_rgb(code) for code in PALETTES[preset])
    art = p["art_pixels"]
    count = art * art
    columns = min(p["stones"], art // 4)
    rows = columns
    stagger = 0.5 if rows % 2 == 0 else 0.0
    cell_w, cell_h = art / columns, art / rows
    rng = tk.Rng(seed, 0xC0)
    jitter = p["jitter"]
    stones = []
    for j in range(rows):
        for i in range(columns):
            cx = (i + 0.5 + stagger * (j % 2) + 0.4 * jitter * (rng.random() - 0.5)) * cell_w
            cy = (j + 0.5 + 0.4 * jitter * (rng.random() - 0.5)) * cell_h
            size = p["stone_size"] * (1.0 - 0.18 * jitter * rng.random())
            stones.append((cx, cy, 0.5 * size * cell_w, 0.5 * size * cell_h, rng.random()))
    exponent = 2.0 + 4.0 * (1.0 - p["roundness"])
    soil = tk.fbm(art, art, max(2, art // 8), 2, tk.hash_u32(seed, 1))
    colour, heights, rough = [None] * count, [0.0] * count, [0.0] * count
    wet_rough = ROUGHNESS[0] - 0.65 * p["wet"]
    for y in range(art):
        for x in range(art):
            index = y * art + x
            j0 = int((y + 0.5) // cell_h)
            best, chosen, offset = 9.0, None, (0.0, 0.0)
            for dj in (-1, 0, 1):
                j = (j0 + dj) % rows
                shift = stagger * cell_w * (j % 2)
                i0 = int(((x + 0.5 - shift) % art) // cell_w)
                for di in (-1, 0, 1):
                    cx, cy, rx, ry, tint = stones[j * columns + (i0 + di) % columns]
                    ox = (x + 0.5 - cx + art / 2.0) % art - art / 2.0
                    oy = (y + 0.5 - cy + art / 2.0) % art - art / 2.0
                    depth = (abs(ox / rx) ** exponent + abs(oy / ry) ** exponent) ** (1.0 / exponent)
                    if depth < best:
                        best, chosen, offset = depth, tint, (ox / rx, oy / ry)
            if best <= 1.0:
                facing = -(offset[0] + offset[1]) * 0.7 + 0.25 * (chosen - 0.5)
                if best > 0.8:
                    shade = outline
                elif facing > 0.5:
                    shade = glint if p["wet"] > 0.5 and best < 0.6 and facing > 0.6 else highlight
                elif facing > 0.1:
                    shade = light
                elif facing > -0.35:
                    shade = base
                else:
                    shade = shadow
                colour[index] = shade
                heights[index] = 0.35 + 0.45 * math.sqrt(max(0.0, 1.0 - best * best))
                rough[index] = wet_rough if shade is not outline else ROUGHNESS[0]
            else:
                grassy = soil[index] < 2.0 * p["grass"] - 1.0
                tuft = grassy and tk.hash_float(seed, x, y, 3) < 0.25
                shade = grass_light if tuft else grass_dark if grassy else (
                    dirt if tk.hash_float(seed, x, y, 4) < 0.6 else dirt_dark)
                colour[index], heights[index], rough[index] = shade, 0.12 + (0.08 if tuft else 0.0), ROUGHNESS[1]
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.0 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 1.5 / art, 1.0)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
