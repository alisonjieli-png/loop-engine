"""Eight-point star and cross tiles with handmade zellige glaze: tileable PBR maps from the standard library only.

Stars sit on a square lattice, ``stars_across`` per tile. Each star is the union of an axis-aligned square and the
same square turned 45 degrees, sized so neighbouring stars meet tip to tip; the space left between four stars is a
cross with pointed arms. A pixel measures its signed distance to the four stars at the corners of its lattice cell:
inside one of them it belongs to that star, otherwise to the cross of the cell. The distance shapes the grout and
a steep, chipped cut edge; uneven glaze thickness, pinholes and per-piece tone give the handmade look.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "zellige_star_tiles"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.04, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "stars_across", "type": "int", "default": 3, "minimum": 1, "maximum": 12,
     "meaning": "Stars across the tile width; a cross sits between every four stars."},
    {"name": "colour_mode", "type": "int", "default": 0, "minimum": 0, "maximum": 1,
     "meaning": "0 stars take the star colours and crosses the cross colours, 1 every piece picks from both."},
    {"name": "grout_width", "type": "float", "default": 0.012, "minimum": 0.002, "maximum": 0.05,
     "meaning": "Joint width in star spacings."},
    {"name": "grout_depth", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far the grout sits below the glaze."},
    {"name": "edge_cut", "type": "float", "default": 0.018, "minimum": 0.004, "maximum": 0.06,
     "meaning": "Width of the steep cut edge around each piece, in star spacings."},
    {"name": "glaze_unevenness", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Thick and thin glaze: bumps in the surface and darker pools where the glaze is thick."},
    {"name": "pinholes", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Small craters in the glaze."},
    {"name": "chipping", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Chipped edges that show the clay body."},
    {"name": "colour_variation", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of tone between pieces of one colour."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "White stars and cobalt blue crosses with glossy, uneven zellige glaze.",
                "values": {}},
    "emerald_white": {"description": "Variegated emerald stars and white crosses, more stars per tile.",
                      "values": {"stars_across": 4, "glaze_unevenness": 0.8, "colour_variation": 0.7}},
    "honey_terracotta": {"description": "Honey-glazed terracotta stars with dark green crosses and wider joints.",
                         "values": {"stars_across": 2, "grout_width": 0.02, "edge_cut": 0.025, "chipping": 0.6,
                                    "pinholes": 0.5, "colour_variation": 0.6}},
    "souk_mix": {"description": "Small pieces in a mixed palette of blue, green, ochre, white and black.",
                 "values": {"stars_across": 6, "colour_mode": 1, "grout_width": 0.016, "edge_cut": 0.02,
                            "glaze_unevenness": 0.7}},
}
#: Star colours, cross colours, grout, clay body, glaze roughness per preset (sRGB).
PALETTES = {
    "default": (["#eeebe2", "#e6e2d7", "#f2efe7"], ["#1d4f9c", "#17428a", "#255bb0"], "#d9d4c8", "#c9a27c",
                0.07),
    "emerald_white": (["#1f7a4f", "#16653f", "#2c8c5c", "#0f5534"], ["#ece9df", "#e4e0d4"], "#d2cdc0",
                      "#c69b72", 0.06),
    "honey_terracotta": (["#c27a3a", "#b0682d", "#d08b48", "#a35e28"], ["#2c4a33", "#243f2b", "#35573c"],
                         "#bcae95", "#b4643a", 0.1),
    "souk_mix": (["#1d4f9c", "#1f7a4f", "#d1a03a", "#eeebe2", "#1a1a1c"], ["#1d4f9c", "#1f7a4f", "#d1a03a",
                                                                         "#eeebe2", "#2a6f8f"], "#d6d0c3",
                 "#c9a27c", 0.07),
}
#: Half side of each star's squares when neighbouring stars meet tip to tip: the turned square reaches 0.5.
HALF_SIDE = 0.5 / math.sqrt(2.0)
INVERSE_ROOT2 = 1.0 / math.sqrt(2.0)


def star_distance(x: float, y: float) -> float:
    """Signed distance from (x, y), relative to a star centre in star spacings, to the eight-point star: negative
    inside. The star is an axis-aligned square of half side HALF_SIDE united with the same square turned 45 degrees."""
    ax, ay = abs(x), abs(y)
    first = tk.box_distance(ax, ay, HALF_SIDE, HALF_SIDE)
    second = tk.box_distance((ax + ay) * INVERSE_ROOT2, (ay - ax) * INVERSE_ROOT2, HALF_SIDE, HALF_SIDE)
    return min(first, second)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The star and cross maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    stars_hex, crosses_hex, grout_hex, body_hex, glaze_rough = PALETTES[preset]
    star_colours = [tk.hex_rgb(code) for code in stars_hex]
    cross_colours = [tk.hex_rgb(code) for code in crosses_hex]
    mixed = star_colours + cross_colours
    grout_rgb, body_rgb = tk.hex_rgb(grout_hex), tk.hex_rgb(body_hex)
    n = p["stars_across"]
    variation, unevenness = p["colour_variation"], p["glaze_unevenness"]
    pieces = {}
    for kind in (0, 1):
        for j in range(n):
            for i in range(n):
                code = tk.hash_u32(seed, kind, i, j)
                pick = tk.hash_float(code, 1)
                family = mixed if p["colour_mode"] == 1 else (star_colours if kind == 0 else cross_colours)
                colour = family[min(int(pick * len(family)), len(family) - 1)]
                tone = 1.0 + 0.14 * (tk.hash_float(code, 2) * 2.0 - 1.0) * variation
                pieces[(kind, i, j)] = ([c * tone for c in colour], tk.hash_float(code, 3) * 2.0 - 1.0,
                                        tk.hash_float(code, 4) * 2.0 - 1.0, tk.hash_float(code, 5))
    thickness = tk.fbm(width, height, 4 * n, 4, tk.hash_u32(seed, 2))
    chips = tk.fbm(width, height, 10 * n, 3, tk.hash_u32(seed, 3))
    grime = tk.fbm(width, height, 6 * n, 3, tk.hash_u32(seed, 4))
    speck = tk.white_noise(width, height, tk.hash_u32(seed, 5))
    craters = tk.voronoi(width, height, 12 * n, 12 * n, tk.hash_u32(seed, 6), jitter=1.0, edges=False)
    kept = [tk.hash_float(seed, 7, cell) < 0.3 for cell in range(144 * n * n)]
    holes = [distance if kept[cell] else 1.0 for distance, cell in zip(craters["f1"], craters["cell"])]
    half_grout = p["grout_width"] * 0.5
    cut = p["edge_cut"]
    chip_reach = p["chipping"] * (cut * 1.5 + 0.01)
    pinholes = p["pinholes"]
    grout_level = 0.5 - 0.32 * p["grout_depth"]
    pixel = n / width
    floor = math.floor
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        sy = (y + 0.5) / height * n
        cell_y = floor(sy)
        for x in range(width):
            index = y * width + x
            sx = (x + 0.5) / width * n
            cell_x = floor(sx)
            best, star = 9.0, None
            for oy in (0, 1):
                for ox in (0, 1):
                    distance = star_distance(sx - cell_x - ox, sy - cell_y - oy)
                    if distance < best:
                        best, star = distance, (cell_x + ox, cell_y + oy)
            if best < 0.0:
                key = (0, star[0] % n, star[1] % n)
                inside = -best
            else:
                key = (1, cell_x % n, cell_y % n)
                inside = best
            colour, tilt_x, tilt_y, rough_jitter = pieces[key]
            edge = inside - half_grout
            t = edge / cut
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else t * (2.0 - t)
            glaze = thickness[index] * unevenness
            hole = pinholes * max(0.0, 1.0 - holes[index] / 0.12) if holes[index] < 0.12 else 0.0
            top = 0.8 + 0.035 * glaze + 0.01 * (tilt_x * (sx - cell_x - 0.5) + tilt_y * (sy - cell_y - 0.5)) \
                - 0.05 * hole
            grout = grout_level + 0.025 * grime[index]
            level = grout + (top - grout) * profile
            carve = chip_reach * max(0.0, chips[index] - 0.1) * 2.5 - edge
            chipped = tk.smoothstep(-pixel, pixel, carve) if edge > -pixel else 0.0
            if chipped > 0.0:
                level = min(level, grout + (top - grout) * (0.45 + 0.15 * chips[index]))
            heights.append(level)
            cover = tk.smoothstep(-pixel, pixel, edge)
            grout_tone = 0.88 + 0.14 * speck[index] - 0.2 * max(0.0, 0.1 - grime[index])
            mix = [c * grout_tone for c in grout_rgb]
            roughness = 0.93
            if cover > 0.0:
                lightness = 0.2126 * colour[0] + 0.7152 * colour[1] + 0.0722 * colour[2]
                depth_tone = 1.0 - (0.18 * glaze + 0.08 * (1.0 - profile)) * (1.0 - 0.7 * lightness)
                piece = [c * depth_tone * (1.0 + 0.03 * (speck[index] - 0.5)) for c in colour]
                if hole > 0.0:
                    piece = [c + (b * 0.9 - c) * min(1.0, hole * 1.5) for c, b in zip(piece, body_rgb)]
                piece_rough = glaze_rough + 0.05 * rough_jitter + 0.08 * abs(glaze) + 0.5 * hole \
                    + 0.15 * (1.0 - profile)
                if chipped > 0.0:
                    body = [c * (0.88 + 0.12 * speck[index]) for c in body_rgb]
                    piece = [a + (b - a) * chipped for a, b in zip(piece, body)]
                    piece_rough += (0.85 - piece_rough) * chipped
                mix = [a + (b - a) * cover for a, b in zip(mix, piece)]
                roughness += (piece_rough - roughness) * cover
            red.append(mix[0])
            green.append(mix[1])
            blue.append(mix[2])
            rough.append(roughness)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     ao_radius=0.015, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
