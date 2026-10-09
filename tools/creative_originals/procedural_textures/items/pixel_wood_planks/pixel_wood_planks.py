"""Pixel-art wooden planks: grain lines, knots, nails and dark gaps, tileable maps (standard library only).

Planks run across a small art grid (``art_pixels`` square). The top row of every plank is the gap to the plank
above, and each plank row is cut into boards at jittered joints with its own offset, so butt joints stagger and the
floor wraps around the tile. Inside a board the first row is a highlight edge and the last a shadow edge. Grain is
drawn as one-pixel lines that follow the level sets of the row position plus a periodic noise wave, broken into
segments by a second noise, so lines run along the board, bend and stop like quick hand-drawn grain. Knots are
small dark ovals with a lighter ring, and nail heads sit beside the joints. The art is enlarged with
nearest-neighbour sampling; heights, normals and occlusion are computed per art pixel.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "pixel_wood_planks"
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
    {"name": "planks", "type": "int", "default": 4, "minimum": 2, "maximum": 8,
     "meaning": "Plank rows across the tile height."},
    {"name": "boards_per_row", "type": "int", "default": 2, "minimum": 1, "maximum": 4,
     "meaning": "Boards in each plank row across the tile width (joints between them)."},
    {"name": "grain", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Amount of grain lines."},
    {"name": "waviness", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How much the grain lines bend."},
    {"name": "knots", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Chance of a knot in each board."},
    {"name": "nails", "type": "int", "default": 1, "minimum": 0, "maximum": 1,
     "meaning": "1 draws nail heads beside the joints, 0 leaves the boards unnailed."},
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
    "default": {"description": "Warm oak floor planks with nails and a few knots.", "values": {}},
    "dark_walnut": {"description": "Dark walnut boards, wavy grain, no nails.",
                    "values": {"waviness": 0.8, "nails": 0, "knots": 0.2, "boards_per_row": 1}},
    "pale_birch": {"description": "Pale birch boards in narrow rows with fine straight grain.",
                   "values": {"planks": 6, "waviness": 0.2, "grain": 0.45, "knots": 0.15, "boards_per_row": 3}},
    "weathered_grey": {"description": "Weathered grey deck boards with wide gaps, many knots and rusty nails.",
                       "values": {"planks": 3, "grain": 0.9, "knots": 0.6, "waviness": 0.6}},
}
#: Per preset: gap, shadow edge, grain line, board base, board light, highlight edge, knot core, nail head and nail
#: highlight (sRGB).
PALETTES = {
    "default": ("#2b170c", "#6b3d1f", "#7a4724", "#9a5c2e", "#ad6c38", "#c98a4f", "#4a2814", "#3a3a40", "#9fa0a8"),
    "dark_walnut": ("#170c07", "#3a2014", "#40241a", "#553222", "#633b28", "#7c5034", "#24130c", "#2d2d33",
                    "#8d8e96"),
    "pale_birch": ("#5b4630", "#b39468", "#bd9c6c", "#d6b885", "#e2c697", "#f0dcb2", "#8c6a42", "#4a4a50",
                   "#b4b5bc"),
    "weathered_grey": ("#26241f", "#5f5a50", "#6a645a", "#837c70", "#968f82", "#b2ab9d", "#4a453d", "#5a3420",
                       "#9a6a44"),
}
#: Roughness of gap, board, grain line, edges, knot and nail head.
ROUGHNESS = (0.95, 0.74, 0.8, 0.7, 0.82, 0.45)


def _board_cuts(rng, art: int, boards: int, offset: int) -> list:
    """Sorted joint columns of one plank row: evenly spaced, jittered and shifted by ``offset``, at least 4 apart."""
    step = art / boards
    cuts = sorted({(round(k * step + (rng.random() - 0.5) * 0.4 * step) + offset) % art for k in range(boards)})
    kept = [cuts[0]]
    for cut in cuts[1:]:
        if cut - kept[-1] >= 4 and art + kept[0] - cut >= 4:
            kept.append(cut)
    return kept


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The plank maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    gap, shadow, line, base, light, highlight, knot, nail, nail_light = (tk.hex_rgb(code) for code in PALETTES[preset])
    art = p["art_pixels"]
    count = art * art
    rng = tk.Rng(seed, 0x7D)
    rows = min(p["planks"], art // 4)
    bounds = [round(k * art / rows) for k in range(rows + 1)]
    wave = tk.fbm(art, art, max(2, art // 8), 2, tk.hash_u32(seed, 1), cells_y=max(2, art // 16))
    breaks = tk.fbm(art, art, max(4, art // 4), 2, tk.hash_u32(seed, 2), cells_y=max(2, art // 8))
    colour, heights, rough = [base] * count, [0.6] * count, [ROUGHNESS[1]] * count
    spacing = 3 if p["grain"] > 0.5 else 4
    for row in range(rows):
        top, bottom = bounds[row], bounds[row + 1]
        boards = max(1, min(p["boards_per_row"], art // 6))
        offset = rng.integer(0, art - 1)
        cuts = _board_cuts(rng, art, boards, offset)
        phase = [rng.integer(0, spacing - 1) for _ in cuts]
        for x in range(art):
            board = max((k for k, cut in enumerate(cuts) if cut <= x), default=len(cuts) - 1)
            joint = x == cuts[board]
            for y in range(top, bottom):
                index = y * art + x
                if y == top or joint:
                    colour[index], heights[index], rough[index] = gap, 0.08, ROUGHNESS[0]
                elif y == top + 1:
                    colour[index], heights[index], rough[index] = highlight, 0.56, ROUGHNESS[3]
                elif y == bottom - 1:
                    colour[index], heights[index], rough[index] = shadow, 0.5, ROUGHNESS[3]
                else:
                    level = y - top + p["waviness"] * 2.4 * wave[index] + phase[board]
                    on_line = math.floor(level + 0.5) % spacing == 0 and breaks[index] < p["grain"] * 1.2 - 0.35
                    if on_line:
                        colour[index], heights[index], rough[index] = line, 0.57, ROUGHNESS[2]
                    elif breaks[index] > 0.45:
                        colour[index] = light
        for cut in cuts:
            if not rng.chance(p["knots"]):
                continue
            middle = (top + bottom) // 2
            x0 = cut + rng.integer(3, max(3, art // boards - 3))
            for dx in range(-1, 3):
                for dy in (-1, 0, 1):
                    index = ((middle + dy) % art) * art + (x0 + dx) % art
                    if colour[index] is gap or (middle + dy) in (top, top + 1, bottom - 1):
                        continue
                    core = dy == 0 and 0 <= dx <= 1
                    colour[index] = knot if core else line
                    heights[index] = 0.54 if core else 0.57
                    rough[index] = ROUGHNESS[4]
        if p["nails"] and bottom - top >= 5:
            nail_rows = (top + 2, bottom - 2) if bottom - top >= 7 else ((top + bottom + 1) // 2,)
            for cut in cuts:
                for y in nail_rows:
                    for x, shade in ((cut + 2, nail), (cut - 2, nail)):
                        index = (y % art) * art + x % art
                        colour[index], heights[index], rough[index] = shade, 0.68, ROUGHNESS[5]
                        above = ((y - 1) % art) * art + (x - 1) % art
                        if colour[above] is not gap and bottom - top >= 7:
                            colour[above] = nail_light
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.4 / art, directx_normal),
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
