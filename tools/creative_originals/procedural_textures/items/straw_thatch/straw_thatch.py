"""Thatched roof: overlapping courses of long straw or of combed reed butts, tileable PBR maps.

The roof slope runs down the tile (ridge at the top, eaves at the bottom) and the tile holds a whole number of
courses. Every course is painted strand by strand with a z-buffer. Long straw lies along the slope from under the
course above to a ragged lower edge; combed reed shows the cut butts of the reeds as short, dense strokes. A
strand's height grows from the hidden top of its course to the exposed bottom, so each course sits on the one below
and casts a step at its edge. Weathering greys the straw and moss gathers in the shelter of the course edges.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "straw_thatch"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.45, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "style", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "0 long straw laid along the slope, 1 combed water reed showing the cut butts."},
    {"name": "courses", "type": "int", "default": 4, "minimum": 2, "maximum": 10,
     "meaning": "Courses down the tile; each overlaps the one below."},
    {"name": "density", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 2.0,
     "meaning": "Strands per course; 1 covers each course about three times over, so little shadow shows."},
    {"name": "strand_width", "type": "float", "default": 0.0032, "minimum": 0.0015, "maximum": 0.007,
     "meaning": "Straw or reed thickness in texture units."},
    {"name": "raggedness", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How uneven the lower edge of each course is."},
    {"name": "weathering", "type": "float", "default": 0.2, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Greying of the straw with age."},
    {"name": "moss", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Moss in the shelter below each course edge."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Golden long-straw thatch with ragged course edges.", "values": {}},
    "water_reed": {"description": "Combed water reed: dense cut butts, crisp courses.",
                   "values": {"style": 1, "courses": 5, "raggedness": 0.25, "strand_width": 0.0034}},
    "weathered_grey": {"description": "Old grey thatch with moss under the course edges.",
                       "values": {"weathering": 0.9, "moss": 0.6, "raggedness": 0.8, "courses": 3}},
    "fresh_wheat": {"description": "New pale wheat straw, fine and even.",
                    "values": {"strand_width": 0.0022, "density": 1.4, "raggedness": 0.3, "weathering": 0.0,
                               "courses": 5}},
}
#: Straw colours (three), grey weathered colour, moss colour and the shadow between strands per preset (sRGB).
PALETTES = {
    "default": (("#c9a254", "#b08a3e", "#dcbb72"), "#8a8478", "#4f5a2a", "#3a2c16"),
    "water_reed": (("#b8955a", "#a07c46", "#cfb07a"), "#8a8478", "#4f5a2a", "#33281a"),
    "weathered_grey": (("#a08a5e", "#8a7650", "#b49e72"), "#7d786e", "#4a5626", "#2a2620"),
    "fresh_wheat": (("#e0c47e", "#cfb06a", "#ecd596"), "#9a9486", "#5a6630", "#4a3a1e"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The thatch maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    straws, grey_code, moss_code, shadow_code = PALETTES[preset]
    straw_rgb = [tk.hex_rgb(code) for code in straws]
    grey_rgb, moss_rgb, shadow_rgb = tk.hex_rgb(grey_code), tk.hex_rgb(moss_code), tk.hex_rgb(shadow_code)
    courses, style = p["courses"], p["style"]
    course_height = 1.0 / courses
    radius = max(p["strand_width"], 0.6 / min(width, height))
    weathering, moss, ragged = p["weathering"], p["moss"], p["raggedness"]
    count = width * height
    heights = [0.0] * count
    red = [shadow_rgb[0]] * count
    green = [shadow_rgb[1]] * count
    blue = [shadow_rgb[2]] * count
    rough = [0.95] * count
    shelter = [0.0] * count
    patches = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 1))
    rng = tk.Rng(seed, 0x7A)
    lean = rng.uniform(-0.08, 0.08)
    for course in range(courses):
        top = course * course_height - 0.45 * course_height
        bottom = (course + 1) * course_height
        if style == 0:
            strands = int(p["density"] * 3.2 / (2.0 * radius))
            for _ in range(strands):
                u = rng.random()
                start = top + rng.uniform(0.0, 0.3) * course_height
                end = bottom + (rng.uniform(-0.18, 0.06) * ragged - 0.02) * course_height
                drift = (lean + rng.gauss(0.0, 0.03)) * (end - start)
                _paint(heights, red, green, blue, rough, shelter, width, height, u, start, u + drift, end,
                       radius * rng.uniform(0.8, 1.2), top, bottom, rng, straw_rgb, 0)
        else:
            strands = int(p["density"] * 0.19 * course_height / (radius * radius))
            for _ in range(strands):
                u = rng.random()
                end = bottom + (rng.uniform(-0.12, 0.04) * ragged - 0.01) * course_height
                v = rng.uniform(top + 0.4 * course_height, end)
                length = radius * rng.uniform(4.0, 9.0)
                drift = (lean + rng.gauss(0.0, 0.08)) * length
                _paint(heights, red, green, blue, rough, shelter, width, height, u, v - length, u + drift, v,
                       radius * rng.uniform(0.85, 1.15), top, bottom, rng, straw_rgb, 1)
    for index in range(count):
        shade_grey = weathering * (0.7 + 0.3 * tk.smoothstep(-0.3, 0.3, patches[index]))
        colour = (red[index], green[index], blue[index])
        luminance = 0.3 * colour[0] + 0.59 * colour[1] + 0.11 * colour[2]
        colour = [c + (g * (0.7 + 0.8 * luminance) - c) * shade_grey for c, g in zip(colour, grey_rgb)]
        growth = moss * shelter[index] * tk.smoothstep(-0.2, 0.25, patches[index])
        colour = [c + (m * (0.8 + 0.4 * luminance) - c) * growth for c, m in zip(colour, moss_rgb)]
        red[index], green[index], blue[index] = colour
        heights[index] += 0.05 * growth
        rough[index] = min(1.0, rough[index] + 0.1 * growth + 0.05 * shade_grey)
    peak = max(heights)
    heights = [value / peak for value in heights]
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.03, roughness=rough,
                     ao_radius=0.012, ao_strength=1.4, directx=directx_normal)


def _paint(heights, red, green, blue, rough, shelter, width, height, u0, v0, u1, v1, radius, top, bottom, rng,
           straw_rgb, style) -> None:
    """Paint one straw (style 0) or reed butt (style 1) with a z-buffer; height rises toward the course bottom."""
    tone = rng.uniform(0.82, 1.12)
    colour = straw_rgb[rng.integer(0, len(straw_rgb) - 1)]
    lift = rng.uniform(0.0, 0.08)
    span = bottom - top
    for index, d, t in tk.segment_pixels(width, height, u0, v0, u1, v1, radius):
        v = v0 + (v1 - v0) * t
        local = (v - top) / span
        surface = 0.25 + 0.65 * local + lift + 0.12 * (1.0 - d * d)
        if surface > heights[index]:
            heights[index] = surface
            if style == 1:
                end = tk.smoothstep(0.65, 1.0, t)
                shade = tone * (0.7 + 0.3 * (1.0 - d) + 0.25 * end)
            else:
                shade = tone * (0.72 + 0.32 * (1.0 - d)) * (0.85 + 0.15 * math.sin(math.pi * t))
            red[index], green[index], blue[index] = (c * shade for c in colour)
            rough[index] = 0.72 + 0.12 * d
            shelter[index] = tk.smoothstep(0.55, 0.0, local)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
