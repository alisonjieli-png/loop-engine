"""Pixel-art grass tile: blade tufts, flowers and pebbles on a dithered lawn, tileable maps (standard library only).

Everything is drawn on a small art grid (``art_pixels`` square, 32 by default) and enlarged with nearest-neighbour
sampling, so every art pixel stays a crisp square. The lawn takes one of three greens from a periodic noise field;
an ordered 4 x 4 Bayer dither breaks the borders between them into the checker transitions of hand-made pixel art.
Blade tufts are short strokes two to five art pixels long, dark at the root and light at the tip, drawn from back to
front so lower tufts overlap higher ones. Flowers (a centre and four petals, or one pixel on small grids) and pebbles
(two-tone ovals with a highlight) sit on top. Heights, normals and occlusion are computed per art pixel, so the
normal map lights each pixel as a flat facet, as 2D engines expect.
"""
from __future__ import annotations

import sys

import texkit as tk

IDENTITY = "pixel_grass_tile"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "tufts", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of grass blade tufts."},
    {"name": "blade_length", "type": "int", "default": 3, "minimum": 2, "maximum": 5,
     "meaning": "Typical blade length in art pixels."},
    {"name": "flowers", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of flowers."},
    {"name": "pebbles", "type": "float", "default": 0.1, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Density of pebbles."},
    {"name": "patchiness", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Contrast of the large light and dark patches of the lawn."},
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
    "default": {"description": "Lush green lawn with a few white and yellow flowers.", "values": {}},
    "dry_meadow": {"description": "Late-summer straw and olive grass, sparse tufts, a few pebbles.",
                   "values": {"tufts": 0.35, "flowers": 0.05, "pebbles": 0.25, "patchiness": 0.8}},
    "flower_meadow": {"description": "Dense meadow full of red, violet and white flowers.",
                      "values": {"tufts": 0.7, "flowers": 0.7, "blade_length": 4, "pebbles": 0.0}},
    "frosted": {"description": "Blue-grey frosted grass on a winter morning, short stiff blades.",
                "values": {"tufts": 0.6, "blade_length": 2, "flowers": 0.0, "pebbles": 0.15, "patchiness": 0.4}},
}
#: Per preset: lawn greens dark to light, blade highlight, blade root, flower petal colours, flower centre and stem,
#: pebble dark, mid and highlight (sRGB).
PALETTES = {
    "default": (["#2f6b2a", "#3f8a32", "#55a83c"], "#8fd35a", "#24521f", ["#f4f1e8", "#f5d33c", "#f4f1e8"],
                "#f2b62f", "#2a5d23", ("#5b5a55", "#8a877e", "#c4c0b4")),
    "dry_meadow": (["#6b6b2c", "#8a843a", "#a79f4c"], "#d6c97a", "#4f4f22", ["#e9dfb8", "#d9a441"],
                   "#b5622b", "#55541f", ("#6d5f4e", "#9a8b74", "#cfc2a8")),
    "flower_meadow": (["#2c6a35", "#3a8541", "#4fa14b"], "#9fdc6c", "#21502a",
                      ["#d8343c", "#8c4fd0", "#f6f3ee", "#e8508f"], "#ffd64a", "#285e2c",
                      ("#5b5a55", "#8a877e", "#c4c0b4")),
    "frosted": (["#4c6b6a", "#6a8b88", "#8eaeaa"], "#e6f4f6", "#3a5453", ["#e6f4f6"], "#ffffff", "#3f5a59",
                ("#4f5560", "#7c8390", "#c9d2dc")),
}
#: Roughness of lawn, blades, flowers and pebbles.
ROUGHNESS = (0.92, 0.8, 0.62, 0.7)


def _wrap(x: int, y: int, art: int) -> int:
    return (y % art) * art + (x % art)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The grass maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    greens, tip_hex, root_hex, petals, centre_hex, stem_hex, stones = PALETTES[preset]
    lawn = [tk.hex_rgb(code) for code in greens]
    tip, root, centre, stem = (tk.hex_rgb(code) for code in (tip_hex, root_hex, centre_hex, stem_hex))
    petal_colours = [tk.hex_rgb(code) for code in petals]
    stone = [tk.hex_rgb(code) for code in stones]
    art = p["art_pixels"]
    count = art * art
    patches = tk.fbm(art, art, max(2, art // 12), 2, tk.hash_u32(seed, 1))
    colour, heights, rough = [None] * count, [0.0] * count, [ROUGHNESS[0]] * count
    for y in range(art):
        for x in range(art):
            index = y * art + x
            level = 1.0 + 1.7 * p["patchiness"] * patches[index] + 0.5 * (tk.bayer4(x, y) - 0.5)
            tone = 0 if level < 0.45 else 2 if level >= 1.7 else 1
            colour[index] = lawn[tone]
            heights[index] = 0.3 + 0.06 * tone
    rng = tk.Rng(seed, 0x6A)
    for _ in range(round(count / 16.0)):
        x, y = rng.integer(0, art - 1), rng.integer(0, art - 1)
        for dx, dy in ((-1, -1), (0, 0), (1, -1)):
            index = _wrap(x + dx, y + dy, art)
            colour[index], heights[index] = lawn[0], 0.24
    tufts = [(rng.integer(0, art - 1), rng.integer(0, art - 1), rng.integer(-1, 1))
             for _ in range(round(p["tufts"] * count / 14.0))]
    tufts.sort(key=lambda row: row[1])
    length = p["blade_length"]
    blade = tuple(0.5 * (a + b) for a, b in zip(lawn[2], tip))
    for x0, y0, lean in tufts:
        shadow = _wrap(x0 + 1, y0 + 1, art)
        colour[shadow], heights[shadow] = root, 0.22
        for offset, tall in ((-1, length - 1), (1, length - 1), (0, length)):
            for step in range(tall):
                outward = offset if step >= tall - 1 and tall > 1 else 0
                index = _wrap(x0 + offset + outward + (lean if step == tall - 1 else 0), y0 - step, art)
                colour[index] = root if step == 0 else tip if step == tall - 1 else blade
                heights[index] = 0.48 + 0.4 * step / max(1, length - 1)
                rough[index] = ROUGHNESS[1]
    for _ in range(round(p["flowers"] * count / 45.0)):
        x, y = rng.integer(0, art - 1), rng.integer(0, art - 1)
        petal = petal_colours[rng.integer(0, len(petal_colours) - 1)]
        colour[_wrap(x, y + 1, art)] = stem
        heights[_wrap(x, y + 1, art)] = 0.55
        if art >= 24:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                index = _wrap(x + dx, y + dy, art)
                colour[index], heights[index], rough[index] = petal, 0.82, ROUGHNESS[2]
            index = _wrap(x, y, art)
            colour[index], heights[index], rough[index] = centre, 0.9, ROUGHNESS[2]
        else:
            index = _wrap(x, y, art)
            colour[index], heights[index], rough[index] = petal, 0.85, ROUGHNESS[2]
    for _ in range(round(p["pebbles"] * count / 70.0)):
        x, y = rng.integer(0, art - 1), rng.integer(0, art - 1)
        wide = 2 + (art >= 32 and rng.chance(0.5))
        for dy in range(2):
            for dx in range(wide):
                index = _wrap(x + dx, y + dy, art)
                shade = stone[2] if (dx, dy) == (0, 0) else stone[0] if dy == 1 and dx == wide - 1 else stone[1]
                colour[index], heights[index], rough[index] = shade, 0.62 - 0.08 * dy, ROUGHNESS[3]
        index = _wrap(x + wide, y + 1, art)
        colour[index] = root
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.2 / art, directx_normal),
                                      3, art, art, width, height)
    occlusion = [round(value * 8.0) / 8.0 for value in tk.ambient_occlusion(heights, art, art, 2.0 / art, 1.2)]
    return tk.finish(width, height, MAPS, albedo=albedo, heights=tk.upscale_nearest(heights, art, art, width, height),
                     roughness=tk.upscale_nearest(rough, art, art, width, height),
                     ao=tk.upscale_nearest(occlusion, art, art, width, height), normal=normal,
                     directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
