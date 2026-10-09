"""Pixel-art roof tiles: overlapping courses of square, round (fish-scale) or pointed tiles, tileable.

A roof is drawn on a small art grid (``art_pixels`` square) as courses laid from the eaves upward: courses are
painted from the bottom of the tile to the top, and every tile reaches down past its course by an overlap, so each
higher course lies on the one below, exactly as roofing is laid. Every other course shifts by half a tile, which is
why the course count is always even. The end of each tile is square, round or pointed (``end_shape``); the pixels
just below a tile's end take a cast shadow on the course underneath, the end itself is outlined, the left column of
a tile is lit and the right column shaded, and a per-tile tint varies the colour. Wooden shingles add grain lines and
random widths; moss can grow in the shadows. The art is enlarged with nearest-neighbour sampling; heights (rising
toward each tile end), normals and occlusion are computed per art pixel. Standard library only.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "pixel_roof_tiles"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.95]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.2, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "art_pixels", "type": "int", "default": 32, "minimum": 16, "maximum": 64,
     "meaning": "Art pixels along each side of the tile; the maps enlarge them with nearest-neighbour sampling."},
    {"name": "course_pairs", "type": "int", "default": 2, "minimum": 1, "maximum": 4,
     "meaning": "Pairs of tile courses down the tile (the course count is twice this, so the offset repeats)."},
    {"name": "tiles_per_course", "type": "int", "default": 4, "minimum": 2, "maximum": 8,
     "meaning": "Roof tiles across the tile width in each course."},
    {"name": "end_shape", "type": "int", "default": 1, "minimum": 0, "maximum": 2,
     "meaning": "Tile end: 0 square, 1 round (fish scale), 2 pointed."},
    {"name": "overlap", "type": "float", "default": 0.45, "minimum": 0.2, "maximum": 0.7,
     "meaning": "How far each tile reaches over the course below, as a share of the course height."},
    {"name": "grain", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "1 draws wood grain lines and gives the tiles random widths (shingles and shakes)."},
    {"name": "moss", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Moss growing in the shadowed overlaps."},
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
    "default": {"description": "Terracotta fish-scale roof tiles with round ends.", "values": {}},
    "blue_slate": {"description": "Blue-grey slate in square-ended courses.",
                   "values": {"end_shape": 0, "tiles_per_course": 4, "course_pairs": 3, "overlap": 0.3}},
    "verdigris_scales": {"description": "Green copper scales with pointed ends.",
                         "values": {"end_shape": 2, "tiles_per_course": 5, "overlap": 0.5}},
    "wooden_shingles": {"description": "Brown wooden shingles of random widths with grain and moss.",
                        "values": {"end_shape": 0, "grain": 1, "moss": 0.35, "tiles_per_course": 5,
                                   "overlap": 0.3}},
}
#: Per preset: outline, cast shadow, shadow, base, light, highlight, three tints, grain line, moss dark, moss light
#: (sRGB), and the tile roughness.
PALETTES = {
    "default": (("#3a160d", "#5a2414", "#8a3a20", "#ad4d2a", "#c76436", "#e08a52", "#a54428", "#b4532e",
                 "#bb5b30", "#7a3018", "#3e5a26", "#5d7e34"), 0.78),
    "blue_slate": (("#14171d", "#22272f", "#3a4250", "#4b5566", "#5c6779", "#7c889b", "#465062", "#4d576a",
                    "#545e70", "#333a46", "#3c5230", "#58743e"), 0.6),
    "verdigris_scales": (("#0f2a24", "#173a32", "#2f6a5a", "#3f8a74", "#55a58c", "#86c9b0", "#3c8470",
                          "#448f7a", "#4a9880", "#2a5a4c", "#3e5a26", "#5d7e34"), 0.5),
    "wooden_shingles": (("#24160c", "#3a2414", "#5e3c22", "#77502e", "#8c603a", "#a8784c", "#6f4a2a", "#7c5532",
                         "#86603a", "#4e3220", "#3a5422", "#5a7a30"), 0.85),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The roof maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    codes, tile_rough = PALETTES[preset]
    (outline, cast, shadow, base, light, highlight, tint_a, tint_b, tint_c, grain_line, moss_dark,
     moss_light) = (tk.hex_rgb(code) for code in codes)
    tints = (tint_a, tint_b, tint_c, base)
    art = p["art_pixels"]
    count = art * art
    rng = tk.Rng(seed, 0x2F)
    courses = min(2 * p["course_pairs"], 2 * max(1, art // 10))
    bounds = [round(k * art / courses) for k in range(courses + 1)]
    across = min(p["tiles_per_course"], art // 4)
    colour, heights, rough = [shadow] * count, [0.2] * count, [tile_rough] * count
    shaded = [False] * count
    plans = []
    for course in range(courses):
        shift = (course % 2) * art / (2 * across)
        edges = [k * art / across for k in range(across + 1)]
        if p["grain"]:
            edges = [edges[0]] + [edge + rng.uniform(-0.3, 0.3) * art / across for edge in edges[1:-1]] + [art]
        plans.append([(edges[k] + shift, edges[k + 1] + shift, tints[rng.integer(0, len(tints) - 1)])
                      for k in range(across)])

    def paint(course: int, ends_only: bool) -> None:
        top, bottom = bounds[course], bounds[course + 1]
        reach = max(1, round((bottom - top) * p["overlap"]))
        for number, (left, right, tint) in enumerate(plans[course]):
            centre, half = 0.5 * (left + right), 0.5 * (right - left)
            inside = {}
            for y in range(top, bottom + reach):
                for x in range(math.floor(left), math.ceil(right)):
                    u = (x + 0.5 - centre) / half
                    if abs(u) > 1.0:
                        continue
                    below = (y + 0.5 - bottom) / reach
                    if below > 0.0 and ((p["end_shape"] == 1 and u * u + below * below > 1.0)
                                        or (p["end_shape"] == 2 and abs(u) + below > 1.0)):
                        continue
                    inside[(x, y)] = (u, (y + 0.5 - top) / (bottom + reach - top))
            for (x, y), (u, v) in inside.items():
                if ends_only and y < bottom:
                    continue
                index = (y % art) * art + x % art
                column = x - math.floor(left)
                if (x, y + 1) not in inside or column == 0:
                    shade = outline
                elif column == 1:
                    shade = highlight
                elif right - x < 1.5:
                    shade = shadow
                elif v < 0.25:
                    shade = shadow
                elif v > 0.75 and u < 0.0:
                    shade = light
                else:
                    shade = tint
                if p["grain"] and shade is tint and tk.hash_float(seed, x % art, number, course) < 0.35:
                    shade = grain_line
                finish = tile_rough + (0.12 if shade is outline else -0.08 if shade is highlight else 0.0)
                colour[index], rough[index], shaded[index] = shade, finish, False
                heights[index] = 0.25 + 0.5 * v + (0.08 * math.cos(0.5 * math.pi * u) if p["end_shape"] == 1 else 0.0)
            for (x, y) in inside:
                if (x, y + 1) not in inside:
                    target = ((y + 1) % art) * art + x % art
                    colour[target], shaded[target], rough[target] = cast, True, min(1.0, tile_rough + 0.15)
                    heights[target] = min(heights[target], 0.22)

    # Each course lies on the one below it, and the last course lies on the first one of the next repeat, so the
    # first course is painted first, then the others from the bottom up, and finally the ends of the first course
    # again, over the second course.
    paint(0, False)
    for course in range(courses - 1, 0, -1):
        paint(course, False)
    paint(0, True)
    if p["moss"] > 0.0:
        growth = tk.fbm(art, art, max(2, art // 8), 2, tk.hash_u32(seed, 1))
        for index in range(count):
            if shaded[index] and growth[index] > 0.6 - 1.2 * p["moss"]:
                colour[index] = moss_light if growth[index] > 0.8 - 1.2 * p["moss"] else moss_dark
                rough[index] = 0.92
    red, green, blue = ([c[k] for c in colour] for k in range(3))
    graded = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    albedo = tuple(tk.upscale_nearest(channel, art, art, width, height) for channel in graded)
    normal = tk.upscale_nearest_bytes(tk.normal_map(heights, art, art, p["relief"] * 1.2 / art, directx_normal),
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
