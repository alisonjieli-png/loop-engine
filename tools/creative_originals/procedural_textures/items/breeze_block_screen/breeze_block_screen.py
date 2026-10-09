"""Breeze block screen wall: decorative concrete blocks with see-through openings, tileable PBR maps with alpha.

Square blocks are stacked in a grid, ``blocks_across`` per side, with mortar joints. Inside each block's solid rim
an opening motif is cut, defined by a signed distance in block coordinates: a large circle with four small ones, a
quatrefoil of four overlapping circles, a diamond with corner triangles, a four-petal flower around a solid centre,
or a grille of square holes. The albedo's alpha is 0 in the openings (anti-aliased over a pixel) and 1 on concrete
and mortar, for alpha-scissor rendering. The concrete darkens toward the openings, where the block's inner walls
would be seen, and rounds over a small bevel; pores, stains and per-block tone weather the face.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "breeze_block_screen"
MAPS = [
    {"name": "albedo", "channels": 4, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.92]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.5, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "motif", "type": "int", "default": 0, "minimum": 0, "maximum": 4,
     "meaning": "Opening cut in each block: 0 a circle with four small corner circles, 1 a quatrefoil, 2 a diamond "
                "with four corner triangles, 3 a four-petal flower around a solid centre, 4 a grille of nine "
                "square holes."},
    {"name": "blocks_across", "type": "int", "default": 2, "minimum": 1, "maximum": 6,
     "meaning": "Blocks across the tile width (and height)."},
    {"name": "frame", "type": "float", "default": 0.08, "minimum": 0.03, "maximum": 0.2,
     "meaning": "Solid rim between the block edge and its openings, in block widths."},
    {"name": "opening_scale", "type": "float", "default": 0.9, "minimum": 0.5, "maximum": 1.0,
     "meaning": "Size of the opening motif within the rim."},
    {"name": "joint_width", "type": "float", "default": 0.025, "minimum": 0.0, "maximum": 0.06,
     "meaning": "Mortar joint between blocks in block widths; 0 butts the blocks together."},
    {"name": "bevel", "type": "float", "default": 0.015, "minimum": 0.004, "maximum": 0.05,
     "meaning": "Rounded edge of the concrete around openings and joints, in block widths."},
    {"name": "weathering", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Stains, streaks and grime on the concrete."},
    {"name": "colour_variation", "type": "float", "default": 0.3, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of tone between blocks."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "White painted blocks with a large circle and four small ones, mid-century style.",
                "values": {}},
    "quatrefoil_cream": {"description": "Cream concrete quatrefoil blocks, three per side.",
                         "values": {"motif": 1, "blocks_across": 3, "frame": 0.07, "weathering": 0.2}},
    "raw_diamond": {"description": "Raw grey concrete diamond blocks with pores and rain streaks.",
                    "values": {"motif": 2, "frame": 0.06, "weathering": 0.7, "colour_variation": 0.5}},
    "terracotta_flower": {"description": "Terracotta clay flower blocks, butted with thin joints.",
                          "values": {"motif": 3, "blocks_across": 3, "joint_width": 0.012, "frame": 0.09,
                                     "weathering": 0.35, "colour_variation": 0.6}},
    "pastel_grille": {"description": "Pastel green blocks with nine square holes each.",
                      "values": {"motif": 4, "blocks_across": 2, "frame": 0.1, "opening_scale": 0.85,
                                 "weathering": 0.15}},
}
#: Block colours, mortar colour, stain colour, aggregate speckle strength per preset (sRGB).
PALETTES = {
    "default": (["#eceae4", "#e6e3dc", "#f0eee9"], "#d5d1c8", "#8c877c", 0.02),
    "quatrefoil_cream": (["#e6dcc6", "#ded3bb", "#ece3cf"], "#cfc5b1", "#857a66", 0.04),
    "raw_diamond": (["#9c9a96", "#a6a4a0", "#93918d"], "#8a8782", "#4a4844", 0.12),
    "terracotta_flower": (["#b8673f", "#a95c38", "#c27249"], "#c4b39a", "#5a3524", 0.05),
    "pastel_grille": (["#a7c9b4", "#9fc2ad", "#b0d0bb"], "#d6d3ca", "#5d6e64", 0.02),
}


def _circle(x: float, y: float, cx: float, cy: float, radius: float) -> float:
    return math.hypot(x - cx, y - cy) - radius


def opening_distance(x: float, y: float, motif: int, inner: float, scale: float) -> float:
    """Signed distance from (x, y), in block widths from the block centre, to the opening of ``motif``: negative
    inside an opening. ``inner`` is the half size of the area inside the rim and ``scale`` sizes the motif in it."""
    a = inner * scale
    ax, ay = abs(x), abs(y)
    if motif == 0:
        small = 0.2 * inner
        corner = inner - small - 0.02
        return min(_circle(ax, ay, 0.0, 0.0, 0.55 * a), _circle(ax, ay, corner, corner, small * scale))
    if motif == 1:
        offset, radius = 0.4 * a, 0.5 * a
        return min(_circle(ax, ay, offset, 0.0, radius), _circle(ax, ay, 0.0, offset, radius))
    if motif == 2:
        diamond = (ax + ay - 0.78 * a) * 0.7071
        band = 0.3 * inner
        corners = max(tk.box_distance(ax, ay, inner, inner), (0.78 * a + band - ax - ay) * 0.7071)
        return min(diamond, corners)
    if motif == 3:
        petals = min(math.hypot(ax - 0.52 * a, ay * 1.45) - 0.4 * a,
                     math.hypot(ax * 1.45, ay - 0.52 * a) - 0.4 * a) / 1.25
        return max(petals, 0.2 * a - math.hypot(ax, ay))
    step = 2.0 * inner / 3.0
    hole = 0.5 * step * 0.72 * scale
    gx = ax - step * min(1, round(ax / step))
    gy = ay - step * min(1, round(ay / step))
    return tk.box_distance(gx, gy, hole, hole, 0.15 * hole)


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The screen block maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    blocks_hex, mortar_hex, stain_hex, speckle = PALETTES[preset]
    palette = [tk.hex_rgb(code) for code in blocks_hex]
    mortar_rgb, stain_rgb = tk.hex_rgb(mortar_hex), tk.hex_rgb(stain_hex)
    n, motif = p["blocks_across"], p["motif"]
    half_joint = 0.5 * p["joint_width"]
    inner = 0.5 - half_joint - p["frame"]
    scale, bevel = p["opening_scale"], p["bevel"]
    weathering, variation = p["weathering"], p["colour_variation"]
    pores = tk.white_noise(width, height, tk.hash_u32(seed, 2))
    surface = tk.fbm(width, height, 8 * n, 4, tk.hash_u32(seed, 3))
    stains = tk.fbm(width, height, 3, 4, tk.hash_u32(seed, 4))
    streaks = tk.fbm(width, height, 12 * n, 3, tk.hash_u32(seed, 5), cells_y=2)
    pixel = n / width
    floor = math.floor
    red, green, blue, alpha, heights, rough = [], [], [], [], [], []
    for y in range(height):
        sy = (y + 0.5) / height * n
        j = floor(sy)
        ly = sy - j - 0.5
        for x in range(width):
            index = y * width + x
            sx = (x + 0.5) / width * n
            i = floor(sx)
            lx = sx - i - 0.5
            code = tk.hash_u32(seed, i % n, j % n)
            tone_jitter = tk.hash_float(code, 1) - 0.5
            joint = 0.5 - max(abs(lx), abs(ly)) - half_joint
            opening = opening_distance(lx, ly, motif, inner, scale)
            solid = min(joint, opening)
            open_cover = tk.smoothstep(-pixel, pixel, opening)
            t = solid / bevel
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
            face = 0.8 + 0.012 * surface[index] - (0.03 if pores[index] < 0.04 + speckle else 0.0) * 0.5
            if joint <= 0.0:
                level = 0.62 + 0.02 * surface[index]
            else:
                level = 0.62 + (face - 0.62) * profile
            if opening < 0.0:
                level = 0.3
            heights.append(level)
            block = palette[min(int(tk.hash_float(code, 2) * len(palette)), len(palette) - 1)]
            tone = 1.0 + 0.12 * tone_jitter * variation + 0.04 * surface[index]
            if pores[index] < speckle:
                tone *= 0.82
            wall = (1.0 - tk.smoothstep(0.0, 0.05, opening)) * 0.3
            colour = [c * tone * (1.0 - wall) for c in block]
            dirt = weathering * tk.clamp(0.5 * max(0.0, stains[index] - 0.05) + 0.5 * max(0.0, streaks[index])
                                         * (0.5 + 0.5 * tk.smoothstep(0.1, 0.0, opening)))
            colour = [c + (s - c) * dirt * 0.5 for c, s in zip(colour, stain_rgb)]
            joint_cover = tk.smoothstep(-pixel, pixel, joint)
            mortar = [c * (0.88 + 0.2 * pores[index]) for c in mortar_rgb]
            colour = [m + (c - m) * joint_cover for m, c in zip(mortar, colour)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            alpha.append(open_cover if joint > 0.0 else 1.0)
            rough.append(0.86 + 0.06 * surface[index] + 0.05 * dirt - 0.04 * (1.0 - profile))
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, alpha=alpha, heights=heights, depth=0.02,
                     roughness=rough, ao_radius=0.02, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
