"""Penny round mosaic: small round tiles in hexagonal or square packing, tileable PBR maps (standard library only).

The tile holds ``columns`` rounds across. In hexagonal packing the row count is the even number closest to a
regular lattice (texkit.hex_rows) and each pixel finds its round among the centres of the two nearest rows; in
square packing the rounds sit on a square grid. Every round is a domed disc whose centre and radius stray a little,
as hand-set sheets do, with a bullnose edge, glaze pooling in a darker ring and grout filling the space between. The
colour rule picks a weighted random blend, scattered accents or clusters that drift between the palette colours.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "penny_round_mosaic"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.04, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "columns", "type": "int", "default": 12, "minimum": 4, "maximum": 40,
     "meaning": "Rounds across the tile width."},
    {"name": "packing", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "0 hexagonal close packing (rows offset by half a round), 1 square grid."},
    {"name": "pattern", "type": "int", "default": 0, "minimum": 0, "maximum": 2,
     "meaning": "Colour rule: 0 weighted random blend of the palette, 1 a base colour with scattered accents, "
                "2 clusters that drift between the palette colours."},
    {"name": "gap", "type": "float", "default": 0.12, "minimum": 0.03, "maximum": 0.4,
     "meaning": "Grout between neighbouring rounds as a share of the round spacing."},
    {"name": "dome", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How much each round's face bulges toward its centre."},
    {"name": "handmade", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Random offsets and size changes of the rounds, as on hand-set sheets."},
    {"name": "grout_depth", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far the grout sits below the rounds."},
    {"name": "accent_share", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Share of accent rounds (pattern 1) or of the second colour in the random blend (pattern 0)."},
    {"name": "glaze", "type": "float", "default": 0.85, "minimum": 0.0, "maximum": 1.0,
     "meaning": "0 unglazed matte porcelain, 1 glossy glaze."},
    {"name": "colour_variation", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of tone between rounds of one colour."},
    {"name": "dirt", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Darkening of the grout and the round edges."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "White glossy penny rounds in hexagonal packing with mid grey grout.",
                "values": {}},
    "salt_pepper": {"description": "Matte white rounds with scattered black ones and white grout.",
                    "values": {"columns": 16, "pattern": 1, "accent_share": 0.18, "glaze": 0.2, "dome": 0.3,
                               "colour_variation": 0.2}},
    "sage_blend": {"description": "Glossy green rounds drifting between sage and moss, uneven hand-set rows.",
                   "values": {"columns": 14, "pattern": 2, "handmade": 0.7, "dome": 0.8, "gap": 0.14,
                              "colour_variation": 0.5}},
    "porcelain_grid": {"description": "Unglazed speckled terracotta rounds on a square grid with dark grout.",
                       "values": {"columns": 10, "packing": 1, "pattern": 0, "accent_share": 0.3, "gap": 0.18,
                                  "glaze": 0.0, "dome": 0.25, "handmade": 0.2, "colour_variation": 0.6,
                                  "dirt": 0.35}},
}
#: Palette colours (blend order), accent, grout, edge ring tint, speckle strength per preset (sRGB).
PALETTES = {
    "default": (["#f1f0eb", "#e9e8e2", "#f5f4ef"], "#d5d6d2", "#8f8b84", "#b4b1aa", 0.0),
    "salt_pepper": (["#efeeea", "#e8e7e2"], "#232325", "#e6e3dc", "#c8c5be", 0.02),
    "sage_blend": (["#9db39a", "#7f9c7c", "#b8c9ad", "#6b8a6a", "#a6b88f"], "#c9d6be", "#cfcbc0", "#4f6b4e",
                   0.0),
    "porcelain_grid": (["#b8714b", "#c47e57", "#a9653f", "#cf9068"], "#8e5536", "#3f3a35", "#7e4a2f", 0.12),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The penny round maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    palette_hex, accent_hex, grout_hex, ring_hex, speckle = PALETTES[preset]
    palette = [tk.hex_rgb(code) for code in palette_hex]
    accent, grout_rgb, ring_rgb = tk.hex_rgb(accent_hex), tk.hex_rgb(grout_hex), tk.hex_rgb(ring_hex)
    columns, hexagonal = p["columns"], p["packing"] == 0
    rows = tk.hex_rows(columns) if hexagonal else columns
    spacing = columns / rows
    nearest_neighbour = min(1.0, math.sqrt(0.25 + spacing * spacing)) if hexagonal else 1.0
    radius = 0.5 * nearest_neighbour * (1.0 - p["gap"])
    handmade = p["handmade"]
    count = columns * rows
    rng = tk.Rng(seed, 0x9E)
    traits = []
    for _ in range(count):
        traits.append((rng.random(), rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0),
                       rng.uniform(-1.0, 1.0), rng.random()))
    pattern, share, variation = p["pattern"], p["accent_share"], p["colour_variation"]
    clusters = tk.fbm(2 * columns, 2 * rows, 2, 3, tk.hash_u32(seed, 9), kind=tk.VALUE)
    last = len(palette) - 1
    colours = []
    for index, trait in enumerate(traits):
        i, j = index % columns, index // columns
        if pattern == 1:
            colour = accent if trait[0] < share else palette[min(int(trait[5] * len(palette)), last)]
        elif pattern == 2:
            sample = clusters[(2 * j) * 2 * columns + 2 * i]
            position = tk.clamp((sample - 0.3) * 2.5 + 0.35 * (trait[5] - 0.5)) * last
            low = min(int(position), max(last - 1, 0))
            f = position - low if last else 0.0
            colour = tuple(a + (b - a) * f for a, b in zip(palette[low], palette[min(low + 1, last)]))
        else:
            if trait[0] < share:
                colour = palette[min(1, last)]
            else:
                colour = palette[0] if trait[5] < 0.6 else palette[min(int(trait[5] * len(palette)), last)]
        tone = 1.0 + 0.12 * trait[4] * variation
        colours.append(tuple(c * tone for c in colour))
    surface = tk.fbm(width, height, max(4, columns // 2), 3, tk.hash_u32(seed, 2))
    grime = tk.fbm(width, height, max(4, columns), 3, tk.hash_u32(seed, 3))
    speck = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    grout_level = 0.5 - 0.35 * p["grout_depth"]
    dome, glaze, dirt = p["dome"], p["glaze"], p["dirt"]
    bevel = radius * 0.3
    pixel = columns / width
    floor = math.floor
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        row_position = (y + 0.5) / height * rows
        first = floor(row_position)
        candidates = (first, first + 1 if row_position - first >= 0.5 else first - 1)
        for x in range(width):
            index = y * width + x
            column_position = (x + 0.5) / width * columns
            best = None
            for j in candidates:
                shift = 0.5 * (j & 1) if hexagonal else 0.0
                base_i = floor(column_position - shift)
                for i in (base_i, base_i + 1 if column_position - shift - base_i >= 0.5 else base_i - 1):
                    trait = traits[(i % columns) + (j % rows) * columns]
                    cx = i + 0.5 + shift + 0.06 * handmade * trait[1]
                    cy = (j + 0.5) * spacing + 0.06 * handmade * trait[2]
                    dx = column_position - cx
                    dy = row_position * spacing - cy
                    reach = radius * (1.0 + 0.06 * handmade * trait[3]) - math.sqrt(dx * dx + dy * dy)
                    if best is None or reach > best[0]:
                        best = (reach, (i % columns) + (j % rows) * columns)
            inside, tile = best
            trait = traits[tile]
            t = inside / bevel
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
            bulge = tk.clamp(inside / radius)
            top = 0.78 + 0.08 * dome * (1.0 - (1.0 - bulge) * (1.0 - bulge)) + 0.01 * surface[index]
            grout = grout_level + 0.03 * grime[index]
            level = grout + (top - grout) * profile
            heights.append(level)
            cover = tk.smoothstep(-pixel, pixel, inside)
            grout_tone = 0.88 + 0.16 * speck[index] - 0.35 * dirt * max(0.0, 0.15 - grime[index])
            colour = [c * grout_tone for c in grout_rgb]
            roughness = 0.94
            if cover > 0.0:
                ring = (1.0 - tk.smoothstep(0.0, bevel * 1.4, inside)) * (0.25 + 0.35 * glaze)
                dots = speckle * (1.0 if speck[index] > 0.95 else 0.0) * 1.8
                tone = 1.0 + 0.025 * surface[index] - dots - 0.2 * dirt * (1.0 - profile)
                tile_colour = [(c + (r - c) * ring) * tone for c, r in zip(colours[tile], ring_rgb)]
                tile_rough = 0.06 + 0.8 * (1.0 - glaze) + 0.05 * trait[5] + 0.1 * (1.0 - profile)
                colour = [a + (b - a) * cover for a, b in zip(colour, tile_colour)]
                roughness += (tile_rough - roughness) * cover
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            rough.append(roughness)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     ao_radius=0.015, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
