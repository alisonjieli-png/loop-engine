"""Clay roof tiles, barrel (pan and cover) or pantile, in overlapping courses: tileable PBR maps (standard library).

The slope runs down the tile (eaves toward the bottom). Across the slope the tile holds ``columns`` repeats of a
curved profile: a concave pan between two half-round covers for barrel tiles, or one S-shaped piece (a wide pan
rising into a narrow roll) for pantiles. Down the slope ``courses`` rows overlap: each tile rises from where it slides
under the course above to its nose, which rests on the course below, so every nose casts a step and a dark cavity.
Each piece takes its colour, mottling, offset and tilt from a hash; lichen, moss and dirt streaks weather the roof.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "roof_tiles_clay"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.08, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "profile", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "0 barrel tiles (concave pans with separate half-round covers over their joints), 1 pantiles "
                "(one S-shaped piece: a pan rising into a roll that laps the next pan)."},
    {"name": "columns", "type": "int", "default": 5, "minimum": 2, "maximum": 14,
     "meaning": "Profile repeats across the tile width (pan and cover pairs, or pantiles)."},
    {"name": "courses", "type": "int", "default": 5, "minimum": 2, "maximum": 14,
     "meaning": "Overlapping courses down the tile height."},
    {"name": "cover_width", "type": "float", "default": 0.42, "minimum": 0.25, "maximum": 0.55,
     "meaning": "Share of each repeat taken by the convex cover or roll."},
    {"name": "curvature", "type": "float", "default": 0.7, "minimum": 0.1, "maximum": 1.0,
     "meaning": "Depth of the curves across the slope."},
    {"name": "course_step", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Height of the step at each tile nose."},
    {"name": "misalignment", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Random offsets and tilts of individual tiles."},
    {"name": "lichen", "type": "float", "default": 0.25, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Orange and pale lichen spots."},
    {"name": "moss", "type": "float", "default": 0.1, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Moss in the pans under the noses."},
    {"name": "dirt", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Dark streaks washed down the pans."},
    {"name": "glaze", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "0 unglazed clay, 1 glossy glazed tiles."},
    {"name": "colour_variation", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of colour between tiles."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Terracotta barrel tiles with half-round covers and a little lichen.", "values": {}},
    "red_pantiles": {"description": "Even red pantiles in tight courses, recently laid.",
                     "values": {"profile": 1, "columns": 6, "courses": 7, "cover_width": 0.32, "curvature": 0.55,
                                "misalignment": 0.1, "lichen": 0.05, "moss": 0.0, "dirt": 0.1,
                                "colour_variation": 0.3}},
    "aged_mediterranean": {"description": "Faded, mottled barrel tiles with heavy lichen, moss and streaks.",
                           "values": {"courses": 6, "misalignment": 0.7, "lichen": 0.8, "moss": 0.5, "dirt": 0.7,
                                      "colour_variation": 0.9}},
    "glazed_jade": {"description": "Glossy green glazed barrel tiles with narrow covers in many courses.",
                    "values": {"columns": 7, "courses": 8, "cover_width": 0.34, "curvature": 0.8,
                               "misalignment": 0.15, "lichen": 0.0, "moss": 0.05, "dirt": 0.25, "glaze": 0.9,
                               "colour_variation": 0.35}},
}
#: Tile colours, cavity colour, lichen colours (orange, pale), moss, dirt colour per preset (sRGB).
PALETTES = {
    "default": (["#b8643f", "#a9573a", "#c47249", "#9c4f33", "#bf6a43"], "#2a1610", "#d9902f", "#d7d3bd",
                "#5a6f2c", "#3d2a20"),
    "red_pantiles": (["#a8432e", "#9b3d2a", "#b34a33", "#923826"], "#26120d", "#d9902f", "#d7d3bd", "#5a6f2c",
                     "#3b2620"),
    "aged_mediterranean": (["#c98e66", "#b97a55", "#d6a07a", "#a86a48", "#c48058"], "#2d1a12", "#de9a34",
                           "#e0dcc8", "#566b2a", "#4a3a2e"),
    "glazed_jade": (["#3f7a5c", "#356d51", "#4a8a69", "#2d6047"], "#0f1a14", "#c8a040", "#d0d3c0", "#4f6a2a",
                    "#22302a"),
}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The roof tile maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS and PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    tiles_hex, cavity_hex, orange_hex, pale_hex, moss_hex, dirt_hex = PALETTES[preset]
    palette = [tk.hex_rgb(code) for code in tiles_hex]
    cavity_rgb, orange_rgb, pale_rgb = tk.hex_rgb(cavity_hex), tk.hex_rgb(orange_hex), tk.hex_rgb(pale_hex)
    moss_rgb, dirt_rgb = tk.hex_rgb(moss_hex), tk.hex_rgb(dirt_hex)
    barrel = p["profile"] == 0
    columns, courses = p["columns"], p["courses"]
    cover = p["cover_width"]
    half_cover = 0.5 * cover
    curvature, step, misalign = p["curvature"], p["course_step"], p["misalignment"]
    lichen, moss, dirt, glaze = p["lichen"], p["moss"], p["dirt"], p["glaze"]
    variation = p["colour_variation"]
    mottle = tk.fbm(width, height, 3 * columns, 4, tk.hash_u32(seed, 2))
    streaks = tk.fbm(width, height, 6 * columns, 3, tk.hash_u32(seed, 3), cells_y=max(2, courses // 2))
    spots = tk.voronoi(width, height, 4 * columns, 4 * courses, tk.hash_u32(seed, 4), jitter=1.0, edges=False)
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 5))
    patches = tk.fbm(width, height, 4, 3, tk.hash_u32(seed, 6))
    count = len(palette) - 1
    traits = {}
    floor = math.floor
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        course_position = (y + 0.5) / height * courses
        for x in range(width):
            index = y * width + x
            column_position = (x + 0.5) / width * columns
            pair = floor(column_position)
            local = column_position - pair
            if barrel:
                to_cover = min(local, 1.0 - local)
                on_cover = to_cover < half_cover
                piece_column = (2 * pair + (0 if local < 0.5 else 2)) % (2 * columns) if on_cover \
                    else (2 * pair + 1) % (2 * columns)
            else:
                on_cover = local < cover
                piece_column = pair % columns
            key = (piece_column, on_cover)
            jitter = traits.get(key)
            if jitter is None:
                jitter = tk.hash_float(seed, 21, *key) - 0.5
                traits[key] = jitter
            shifted = course_position + 0.15 * misalign * jitter
            course = floor(shifted)
            along = shifted - course
            piece = (piece_column, course % courses, on_cover)
            trait = traits.get(piece)
            if trait is None:
                code = tk.hash_u32(seed, *piece)
                trait = tuple(tk.hash_float(code, k) for k in range(6))
                traits[piece] = trait
            if barrel:
                if on_cover:
                    s = to_cover / half_cover
                    cross = 0.62 + 0.3 * curvature * math.sqrt(max(0.0, 1.0 - s * s))
                else:
                    half_pan = 0.5 - half_cover
                    s = (local - 0.5) / half_pan
                    cross = 0.5 - 0.22 * curvature * (1.0 - s * s)
            else:
                if on_cover:
                    s = (local - 0.5 * cover) / (0.5 * cover)
                    cross = 0.58 + 0.28 * curvature * math.sqrt(max(0.0, 1.0 - s * s))
                else:
                    s = (local - cover) / (1.0 - cover)
                    cross = 0.5 - 0.22 * curvature * math.sin(math.pi * s) ** 1.5
            ramp = step * 0.26 * along * along
            tilt = misalign * 0.04 * (trait[1] - 0.5) * (along - 0.5)
            level = cross + ramp + tilt + 0.01 * mottle[index] - 0.13 * step
            crown = tk.clamp((cross - 0.28) / 0.64)
            cavity = 0.0
            if on_cover and along < 0.12:
                cavity = (1.0 - along / 0.12) * step * math.sqrt(max(0.0, 1.0 - s * s))
                level -= 0.25 * cavity
            heights.append(level)
            pick = (trait[0] * variation + 0.5 * (1.0 - variation)) * count
            low = min(int(pick), count - 1)
            f = pick - low
            tone = (1.0 + 0.16 * mottle[index] * variation + 0.04 * (grain[index] - 0.5)) * (0.84 + 0.26 * crown)
            if along > 0.94:
                tone *= 0.72 + 0.28 * (1.0 - along) / 0.06
            colour = [(a + (b - a) * f) * tone for a, b in zip(palette[low], palette[low + 1])]
            if dirt > 0.0 and not on_cover:
                wash = dirt * tk.clamp(0.4 + 1.6 * streaks[index]) * (0.3 + 0.7 * along)
                colour = [c + (d - c) * wash * 0.55 for c, d in zip(colour, dirt_rgb)]
            if lichen > 0.0:
                spot_key = spots["cell"][index]
                chance = tk.hash_float(seed, 31, spot_key)
                if chance < lichen * 0.35 * tk.clamp(0.6 + 1.5 * patches[index]):
                    size = 0.18 + 0.25 * tk.hash_float(seed, 32, spot_key)
                    cover_spot = 1.0 - tk.smoothstep(size * 0.8, size, spots["f1"][index] + 0.05 * grain[index])
                    shade = orange_rgb if tk.hash_float(seed, 33, spot_key) < 0.6 else pale_rgb
                    colour = [c + (l - c) * cover_spot * 0.85 for c, l in zip(colour, shade)]
            if moss > 0.0 and not on_cover:
                growth = moss * tk.smoothstep(0.75, 1.0, along) * tk.smoothstep(-0.2, 0.3, patches[index]) \
                    + moss * 0.6 * tk.smoothstep(0.15, 0.5, patches[index]) * (1.0 - abs(s))
                colour = [c + (m * (0.7 + 0.6 * grain[index]) - c) * min(1.0, growth) for c, m in
                          zip(colour, moss_rgb)]
            if cavity > 0.0:
                colour = [c + (k - c) * cavity for c, k in zip(colour, cavity_rgb)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            rough.append(0.85 - 0.72 * glaze + 0.06 * (trait[2] - 0.5) + 0.05 * abs(mottle[index]) + 0.1 * cavity)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.03, roughness=rough,
                     ao_radius=0.03, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
