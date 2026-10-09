"""Pixel-art snow and ice: lumpy drifts, sparkles and glossy ice patches with streaks, tileable (standard library).

Snow is drawn on a small art grid (``art_pixels`` square) as rounded drift mounds: every cell of a Voronoi diagram is
a mound, and the offset of a pixel from its cell's seed, taken along a light from the top left, sets one of three
snow shades (lit, plain, blue shadow) with an ordered Bayer dither between them, so each mound has a bright cap and
a cold shadowed foot. Ice patches are where a periodic noise crosses a threshold set by ``ice``: flat glossy ice
with diagonal highlight streaks at fixed spacing, a darker rim where the ice meets the snow below and to the right,
and random-walk cracks. Sparkles are single bright pixels or four-point stars at Poisson-disc points; dirt specks
suit trodden snow. The art is enlarged with nearest-neighbour sampling; heights, normals and occlusion are computed
per art pixel, with low roughness on the ice.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "pixel_snow_ice"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "mounds", "type": "int", "default": 5, "minimum": 2, "maximum": 8,
     "meaning": "Snow drift mounds across the tile."},
    {"name": "ice", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of the tile covered by ice patches."},
    {"name": "streak_spacing", "type": "int", "default": 5, "minimum": 3, "maximum": 9,
     "meaning": "Distance between the diagonal highlight streaks on ice, in art pixels."},
    {"name": "cracks", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Number of cracks in the ice."},
    {"name": "sparkles", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of sparkles on the snow."},
    {"name": "dirt", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of dirt specks on trodden snow."},
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
    "default": {"description": "Fresh lumpy snow with sparkles and a few ice patches.", "values": {}},
    "frozen_pond": {"description": "Mostly glossy pond ice with cracks and small snow drifts.",
                    "values": {"ice": 0.8, "cracks": 0.7, "sparkles": 0.2, "mounds": 5}},
    "packed_snow": {"description": "Grey trodden snow with dirt specks, few sparkles and no ice.",
                    "values": {"ice": 0.0, "sparkles": 0.1, "dirt": 0.6, "mounds": 6}},
    "glacier": {"description": "Deep blue glacier ice crossed by cracks, with white snow patches.",
                "values": {"ice": 0.65, "cracks": 1.0, "streak_spacing": 7, "mounds": 3, "sparkles": 0.3}},
}
#: Per preset: snow shadow, snow, snow light, sparkle, ice, ice light (streak), ice rim, crack, dirt (sRGB).
PALETTES = {
    "default": ("#687da3", "#a8b7ce", "#cdd8e7", "#ffffff", "#86bfdb", "#c6e6f4", "#4a86ae", "#30688e", "#6b5a4a"),
    "frozen_pond": ("#8aa0bf", "#c3cfe1", "#e2eaf4", "#ffffff", "#7fbcd8", "#c8ecf8", "#4c88ad", "#2f6488",
                    "#5f5246"),
    "packed_snow": ("#7d8592", "#a9b0bb", "#c6ccd4", "#eef2f6", "#9cb8c8", "#cfe3ec", "#62808f", "#4a6474",
                    "#5d4a3a"),
    "glacier": ("#9cb4d2", "#d0dceb", "#eef3fa", "#ffffff", "#4f9cc8", "#9ad6ee", "#2a6f9a", "#1b4f76", "#4d4a48"),
}
#: Roughness of snow, ice, ice streaks, cracks and dirt.
ROUGHNESS = (0.86, 0.1, 0.06, 0.4, 0.9)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The snow and ice maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    shadow, snow, lit, sparkle, ice, streak, rim, crack, dirt = (tk.hex_rgb(code) for code in PALETTES[preset])
    art = p["art_pixels"]
    count = art * art
    mounds = min(p["mounds"], art // 4)
    cells = tk.voronoi(art, art, mounds, mounds, tk.hash_u32(seed, 1), jitter=0.9, edges=False)
    xs, ys = tk.cell_points(mounds, mounds, tk.hash_u32(seed, 1), 0.9)
    frozen = tk.fbm(art, art, max(2, art // 12), 3, tk.hash_u32(seed, 2))
    threshold = 1.0 - 2.0 * p["ice"] if p["ice"] > 0.0 else 9.0
    colour, heights, rough = [None] * count, [0.0] * count, [ROUGHNESS[0]] * count
    is_ice = [frozen[index] * 1.6 > threshold for index in range(count)]
    scale = mounds / art
    lines = max(1, round(art / p["streak_spacing"]))
    pieces = max(1, round(art / 5))
    for y in range(art):
        for x in range(art):
            index = y * art + x
            if is_ice[index]:
                along = (x + y) * lines / art
                piece = math.floor((x - y) * pieces / art) % pieces
                on_streak = along - math.floor(along) < lines / art and \
                    tk.hash_float(seed, math.floor(along) % lines, piece) < 0.6
                below = is_ice[((y + 1) % art) * art + x] and is_ice[y * art + (x + 1) % art]
                if not below:
                    colour[index], heights[index], rough[index] = rim, 0.3, ROUGHNESS[1]
                elif on_streak:
                    colour[index], heights[index], rough[index] = streak, 0.34, ROUGHNESS[2]
                else:
                    colour[index], heights[index], rough[index] = ice, 0.33, ROUGHNESS[1]
                continue
            cell = cells["cell"][index]
            du = tk.wrap_delta((x + 0.5) * scale / mounds - xs[cell] / mounds) * mounds
            dv = tk.wrap_delta((y + 0.5) * scale / mounds - ys[cell] / mounds) * mounds
            facing = -(du + dv) * 1.3 - 0.5 * cells["f1"][index]
            level = 1.15 + facing + 0.4 * (tk.bayer4(x, y) - 0.5)
            tone = 0 if level < 0.35 else 2 if level >= 1.5 else 1
            colour[index] = (shadow, snow, lit)[tone]
            heights[index] = 0.72 - 0.35 * cells["f1"][index] + 0.02 * tone
    rng = tk.Rng(seed, 0x50)
    if p["ice"] > 0.0:
        ice_pixels = [index for index in range(count) if is_ice[index]]
        for _ in range(round(p["cracks"] * len(ice_pixels) / 60.0)):
            index = ice_pixels[rng.integer(0, len(ice_pixels) - 1)]
            x, y = index % art, index // art
            for _ in range(rng.integer(3, 7)):
                target = (y % art) * art + x % art
                if not is_ice[target]:
                    break
                colour[target], heights[target], rough[target] = crack, 0.27, ROUGHNESS[3]
                step = rng.integer(0, 3)
                x, y = x + (1, 1, -1, 0)[step], y + (0, 1, 1, 1)[step]
    for u, v in tk.poisson_points(min(0.5, 4.0 / art), tk.hash_u32(seed, 3)):
        x, y = int(u * art), int(v * art)
        index = y * art + x
        if is_ice[index]:
            continue
        if rng.chance(p["dirt"] * 0.7):
            colour[index], rough[index] = dirt, ROUGHNESS[4]
            heights[index] -= 0.03
        elif rng.chance(p["sparkles"] * 0.7):
            colour[index] = sparkle
            if art >= 32 and rng.chance(0.3):
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    target = ((y + dy) % art) * art + (x + dx) % art
                    if not is_ice[target]:
                        colour[target] = lit
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.2 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 1.5 / art, 0.8)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
