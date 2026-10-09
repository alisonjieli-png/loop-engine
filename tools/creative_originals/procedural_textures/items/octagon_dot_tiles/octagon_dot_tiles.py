"""Octagon and dot tiles: octagons on a square grid with small square dots at their corners, tileable PBR maps.

Each grid cell holds an octagon, the square |x|, |y| <= 1/2 with its corners cut by |x| + |y| <= 1 - r. The four cut
corners around every grid point leave a small square turned 45 degrees, the dot, with half-diagonal r. A pixel's
signed distance to the octagon of its cell (the larger of the side and the diagonal cut distances) says which piece
it is on and how far it is from the joint; grout, bevels, glaze and wear follow from that distance. Marble veins are
read from one vein field at a random offset per piece, so they break at the joints as in cut stone.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "octagon_dot_tiles"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.02, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.05, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "tiles_across", "type": "int", "default": 4, "minimum": 1, "maximum": 14,
     "meaning": "Octagons across the tile width (and height)."},
    {"name": "dot_size", "type": "float", "default": 0.2, "minimum": 0.1, "maximum": 0.38,
     "meaning": "Half-diagonal of each corner dot in octagon widths; larger dots cut deeper corners."},
    {"name": "grout_width", "type": "float", "default": 0.02, "minimum": 0.004, "maximum": 0.08,
     "meaning": "Joint width in octagon widths."},
    {"name": "grout_depth", "type": "float", "default": 0.45, "minimum": 0.0, "maximum": 1.0,
     "meaning": "How far the grout sits below the tile faces."},
    {"name": "bevel", "type": "float", "default": 0.03, "minimum": 0.005, "maximum": 0.12,
     "meaning": "Width of the rounded tile edge in octagon widths."},
    {"name": "gloss", "type": "float", "default": 0.7, "minimum": 0.0, "maximum": 1.0,
     "meaning": "0 matte or honed, 1 glossy glaze."},
    {"name": "veining", "type": "float", "default": 0.0, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Marble veins through the octagons (light) and dots (pale veins on dark stone)."},
    {"name": "wear", "type": "float", "default": 0.15, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Scuffed, duller and lighter traffic patches and slightly worn edges."},
    {"name": "colour_variation", "type": "float", "default": 0.35, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of tone between pieces."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "White glazed octagons with black dots and grey grout.", "values": {}},
    "terracotta_tozzetti": {"description": "Unglazed terracotta octagons with small dark green glazed dots.",
                            "values": {"tiles_across": 3, "dot_size": 0.16, "grout_width": 0.03, "gloss": 0.1,
                                       "wear": 0.4, "colour_variation": 0.75}},
    "marble_classic": {"description": "Honed white marble octagons with black marble dots, thin joints, veins.",
                       "values": {"dot_size": 0.24, "grout_width": 0.012, "grout_depth": 0.3, "bevel": 0.015,
                                  "gloss": 0.45, "veining": 0.8, "colour_variation": 0.25}},
    "small_mosaic": {"description": "Small matte white octagon mosaic with blue dots.",
                     "values": {"tiles_across": 10, "dot_size": 0.22, "grout_width": 0.05, "bevel": 0.05,
                                "gloss": 0.25, "colour_variation": 0.25}},
}
#: Octagon colours, dot colours, grout colour, vein colour on octagons, vein colour on dots (sRGB).
PALETTES = {
    "default": (["#f0efea", "#e9e8e3", "#f3f2ee"], ["#1c1c1e", "#222224"], "#9d9a93", "#d0cfca", "#4a4a4c"),
    "terracotta_tozzetti": (["#b8643f", "#a9573a", "#c47249", "#9c4f33"], ["#2f4a35", "#264030"], "#c2b49b",
                            "#9c5a3c", "#3c5a43"),
    "marble_classic": (["#e9e7e2", "#e2dfd9", "#efede8"], ["#1e1e20", "#262628"], "#d6d3cc", "#9a9894",
                       "#d9d8d4"),
    "small_mosaic": (["#ecebe6", "#e6e5e0"], ["#2d4f8a", "#264577"], "#c9c6be", "#d6d5d0", "#5677ad"),
}
INVERSE_ROOT2 = 1.0 / math.sqrt(2.0)


def octagon_distance(x: float, y: float, dot: float) -> float:
    """Signed distance from (x, y), relative to an octagon's centre in octagon widths, to the octagon whose corners
    are cut by dots of half-diagonal ``dot``: negative inside the octagon, positive in a dot or a neighbour."""
    ax, ay = abs(x), abs(y)
    return max(ax - 0.5, ay - 0.5, (ax + ay - (1.0 - dot)) * INVERSE_ROOT2)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The octagon and dot maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    octagons_hex, dots_hex, grout_hex, vein_hex, dot_vein_hex = PALETTES[preset]
    octagons = [tk.hex_rgb(code) for code in octagons_hex]
    dots = [tk.hex_rgb(code) for code in dots_hex]
    grout_rgb, vein_rgb, dot_vein_rgb = tk.hex_rgb(grout_hex), tk.hex_rgb(vein_hex), tk.hex_rgb(dot_vein_hex)
    n = p["tiles_across"]
    dot = p["dot_size"]
    half_grout = p["grout_width"] * 0.5
    bevel = p["bevel"]
    gloss, veining, wear, variation = p["gloss"], p["veining"], p["wear"], p["colour_variation"]
    surface = tk.fbm(width, height, 3 * n, 3, tk.hash_u32(seed, 2))
    scuffs = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 3))
    speck = tk.white_noise(width, height, tk.hash_u32(seed, 4))
    veins = None
    if veining > 0.0:
        base = tk.fbm(width, height, 2, 4, tk.hash_u32(seed, 5))
        warp_u = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 6))
        warp_v = tk.fbm(width, height, 2, 3, tk.hash_u32(seed, 7))
        gate = tk.fbm(width, height, 3, 3, tk.hash_u32(seed, 8))
        distance = tk.isoline_distance(tk.warp(base, width, height, warp_u, warp_v, 0.2), width, height, 0.0)
        thin = 0.0012 + 0.002 * veining
        veins = [(math.exp(-(d / thin) ** 2) + 0.3 * math.exp(-(d / (5.0 * thin)) ** 2))
                 * tk.smoothstep(-0.25, 0.35, g) for d, g in zip(distance, gate)]
    grout_level = 0.5 - 0.35 * p["grout_depth"]
    pixel = n / width
    floor = math.floor
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        sy = (y + 0.5) / height * n
        j = floor(sy)
        ly = sy - j - 0.5
        for x in range(width):
            index = y * width + x
            sx = (x + 0.5) / width * n
            i = floor(sx)
            lx = sx - i - 0.5
            distance = octagon_distance(lx, ly, dot)
            if distance < 0.0:
                piece, inside = (0, i % n, j % n), -distance
            else:
                cx = (i + (1 if lx > 0.0 else 0)) % n
                cy = (j + (1 if ly > 0.0 else 0)) % n
                dx, dy = lx - (0.5 if lx > 0.0 else -0.5), ly - (0.5 if ly > 0.0 else -0.5)
                piece, inside = (1, cx, cy), ((dot - abs(dx) - abs(dy)) * INVERSE_ROOT2)
            code = tk.hash_u32(seed, *piece)
            pick, tone_jitter, tilt = tk.hash_float(code, 1), tk.hash_float(code, 2) - 0.5, tk.hash_float(code, 3)
            edge = inside - half_grout
            t = edge / bevel
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
            worn_edge = wear * 0.03 * (1.0 - profile)
            top = 0.8 + 0.02 * surface[index] + 0.035 * (tilt - 0.5) - worn_edge
            level = grout_level + (top - grout_level) * profile
            heights.append(level)
            family = octagons if piece[0] == 0 else dots
            colour = family[min(int(pick * len(family)), len(family) - 1)]
            tone = 1.0 + 0.12 * tone_jitter * variation + 0.03 * surface[index] + 0.03 * (speck[index] - 0.5)
            colour = [c * tone for c in colour]
            if veins is not None:
                shifted = ((y + int(tk.hash_float(code, 4) * height)) % height) * width \
                    + (x + int(tk.hash_float(code, 5) * width)) % width
                streak = min(1.0, veins[shifted]) * veining
                tint = vein_rgb if piece[0] == 0 else dot_vein_rgb
                colour = [c + (v - c) * streak for c, v in zip(colour, tint)]
            scuff = wear * tk.smoothstep(0.15, 0.6, scuffs[index])
            colour = [c + (0.8 - c) * 0.12 * scuff for c in colour]
            cover = tk.smoothstep(-pixel, pixel, edge)
            joint = [c * (0.88 + 0.18 * speck[index]) for c in grout_rgb]
            colour = [g + (c - g) * cover for g, c in zip(joint, colour)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            face_rough = 0.08 + 0.75 * (1.0 - gloss) + 0.3 * scuff + 0.04 * (tilt - 0.5) + 0.1 * (1.0 - profile)
            rough.append(0.93 + (face_rough - 0.93) * cover)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.012, roughness=rough,
                     ao_radius=0.015, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
