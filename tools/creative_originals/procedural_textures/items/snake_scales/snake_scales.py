"""Snake skin: overlapping keeled scales on a rhombic lattice with a body pattern, tileable PBR maps.

Scales sit in offset rows (a rhombic lattice) with whole counts across and down, so the skin repeats; the body axis
runs down the tile, head at the top. Each scale is a rounded diamond whose upper part slips under the row above, so
only its free lower part shows. A scale rises from its hidden base, carries a ridge (keel) along its middle and
drops at its rim onto the scale below. The colour pattern is evaluated once per scale, at its centre, so blotches,
bands and diamonds follow the scale grid the way real snake patterns do; the skin between scales shows dark.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "snake_scales"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.15, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "scales", "type": "int", "default": 14, "minimum": 6, "maximum": 32,
     "meaning": "Scale columns across the tile; rows follow from the scale length."},
    {"name": "elongation", "type": "float", "default": 1.35, "minimum": 0.9, "maximum": 2.2,
     "meaning": "Scale length divided by width."},
    {"name": "overlap", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How much scales overlap; low values show the skin between them."},
    {"name": "keel", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Height of the ridge along each scale (0 for smooth scales)."},
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 3,
     "meaning": "0 blotches with dark outlines, 1 cross bands, 2 dorsal diamonds, 3 plain with a fine speckle."},
    {"name": "pattern_repeat", "type": "int", "default": 2, "minimum": 1, "maximum": 6,
     "meaning": "How many times the body pattern repeats across the tile."},
    {"name": "gloss", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Shine of the scales: 0 dry and matte, 1 freshly shed and glossy."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Olive and tan python skin with dark-edged blotches.", "values": {"scales": 16}},
    "coral_banded": {"description": "Banded red, black and yellow scales, smooth and glossy.",
                     "values": {"pattern": 1, "keel": 0.15, "gloss": 0.8, "scales": 16, "pattern_repeat": 3}},
    "diamondback": {"description": "Dusty brown skin with dark dorsal diamonds and strong keels.",
                    "values": {"pattern": 2, "keel": 0.95, "gloss": 0.25, "elongation": 1.6, "scales": 20}},
    "green_tree": {"description": "Bright green smooth scales with a fine speckle.",
                   "values": {"pattern": 3, "keel": 0.0, "gloss": 0.9, "scales": 20, "elongation": 1.1,
                              "overlap": 0.4}},
}
#: Ground colour, pattern colour, outline (or accent) colour and skin colour between scales, per preset (sRGB).
PALETTES = {
    "default": ("#8e7f4e", "#4f3f22", "#1c160d", "#2a2418"),
    "coral_banded": ("#c0302a", "#151214", "#e6c14a", "#2a1210"),
    "diamondback": ("#9a8566", "#4a3a2a", "#e0d2b0", "#2e261c"),
    "green_tree": ("#3d9a3a", "#2a7a2c", "#d8e86a", "#173a16"),
}


def _pattern(kind: int, u: float, v: float, repeat: int, blotch: float, wobble: float, palette: tuple) -> tuple:
    """The colour of the scale centred at (u, v) for a pattern kind; blotch and wobble are noise at that point."""
    ground, figure, outline = palette[0], palette[1], palette[2]
    if kind == 0:
        if blotch > 0.34:
            return palette[4]
        if blotch > 0.13:
            return figure
        if blotch > 0.04:
            return outline
        return ground
    if kind == 1:
        band = (v * repeat * 2.0 + 0.15 * wobble) % 2.0
        if band < 0.9:
            return ground
        if 1.0 <= band < 1.45:
            return outline
        return figure
    if kind == 2:
        du = abs(((u * repeat) % 1.0) - 0.5)
        dv = abs(((v * repeat + 0.08 * wobble) % 1.0) - 0.5)
        diamond = du + 0.8 * dv
        if diamond < 0.25:
            return figure
        if diamond < 0.33:
            return outline
        return ground
    return figure if blotch > 0.32 else outline if blotch < -0.42 else ground


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The snake skin maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    palette = tuple(tk.hex_rgb(code) for code in PALETTES[preset])
    palette = palette + (tuple(min(1.0, 0.3 + 0.85 * c) for c in palette[0]),)
    skin_rgb = palette[3]
    columns = p["scales"]
    overlap, keel, gloss = p["overlap"], p["keel"], p["gloss"]
    half_width = 0.5 * (1.0 + 0.35 * overlap)
    half_length = half_width * p["elongation"]
    rows = max(2, 2 * int(round(columns / (half_length * (1.6 - 0.6 * overlap)) / 2.0)))
    stretch = rows / columns
    repeat = p["pattern_repeat"]
    blotches = tk.fbm(width, height, 2 * repeat, 3, tk.hash_u32(seed, 1))
    wobble = tk.fbm(width, height, 3, 2, tk.hash_u32(seed, 2))
    rng = tk.Rng(seed, 0x53)
    tones = [rng.uniform(-1.0, 1.0) for _ in range(columns * rows)]
    count = width * height
    colours = [None] * (columns * rows)
    for j in range(rows):
        for i in range(columns):
            cu = (i + 0.5 + 0.5 * (j % 2)) / columns
            cv = (j + 0.5) / rows
            colours[j * columns + i] = _pattern(p["pattern"], cu, cv, repeat,
                                                tk.sample(blotches, width, height, cu, cv),
                                                tk.sample(wobble, width, height, cu, cv), palette)
    exponent = 1.2
    heights, red, green, blue, rough = [0.0] * count, [], [], [], []
    for y in range(height):
        gy = (y + 0.5) / height * rows
        j0 = int(math.floor(gy))
        for x in range(width):
            gx = (x + 0.5) / width * columns
            index = y * width + x
            chosen = None
            for dj in (-2, -1, 0, 1):
                j = j0 + dj
                shift = 0.5 * (j % 2)
                i0 = int(math.floor(gx - shift))
                for di in (0, 1, -1):
                    i = i0 + di
                    sx = (gx - (i + 0.5 + shift)) / half_width
                    sy = (gy - (j + 0.5)) / (half_length * stretch)
                    shape = abs(sx) ** exponent + abs(sy) ** exponent
                    if shape < 1.0:
                        chosen = (sx, sy, shape, (j % rows) * columns + i % columns)
                        break
                if chosen is not None:
                    break
            if chosen is None:
                heights[index] = 0.05
                red.append(skin_rgb[0])
                green.append(skin_rgb[1])
                blue.append(skin_rgb[2])
                rough.append(0.8)
                continue
            sx, sy, shape, key = chosen
            rim = tk.smoothstep(0.78, 1.0, shape)
            ridge = keel * max(0.0, 1.0 - abs(sx) / 0.28) ** 2 * (1.0 - 0.5 * max(0.0, sy))
            heights[index] = 0.38 + 0.2 * (1.0 - sy * sy) + 0.08 * sy + 0.3 * ridge - 0.25 * rim
            colour = colours[key]
            shade = 0.88 + 0.08 * tones[key] - 0.3 * rim + 0.12 * ridge
            red.append(colour[0] * shade)
            green.append(colour[1] * shade)
            blue.append(colour[2] * shade)
            rough.append(0.72 - 0.5 * gloss + 0.25 * rim + 0.04 * tones[key])
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.22 / columns, roughness=rough,
                     ao_radius=0.3 / columns, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
