"""Versailles (French pattern) stone pavers from an exact periodic module: tileable PBR maps (standard library only).

The layout uses four sizes in units: 2 x 3, 2 x 2, 1 x 2 and 1 x 1. One piece of each forms a cluster (MODULE), and
the cluster is repeated by the lattice of index 13 made of the points (t, 4t mod 13), so 13 clusters fill a 13 x 13
unit torus exactly. The module was chosen so that no four pieces meet at a point and no straight joint runs longer
than four units; MODULE_CHECK states those properties and generate() re-measures them on every call, refusing a
module that breaks them. Each piece is tumbled stone: rounded, chipped edges, travertine pits elongated along its
bedding, and its own colour.
"""
from __future__ import annotations

import math
import sys

import texkit as tk

IDENTITY = "versailles_pavers"
MAPS = [
    {"name": "albedo", "channels": 3, "colour_space": "srgb", "convention": "gltf_base_color", "range": [0.03, 0.9]},
    {"name": "normal", "channels": 3, "colour_space": "linear", "convention": "opengl_y_up"},
    {"name": "roughness", "channels": 1, "colour_space": "linear", "convention": "gltf_roughness",
     "range": [0.3, 1.0]},
    {"name": "height", "channels": 1, "colour_space": "linear", "convention": "white_is_high"},
    {"name": "ao", "channels": 1, "colour_space": "linear", "convention": "white_is_unoccluded"},
]
PARAMETERS = [
    {"name": "repeats", "type": "int", "default": 1, "minimum": 1, "maximum": 3,
     "meaning": "Copies of the 13 x 13 unit pattern across the tile."},
    {"name": "joint_width", "type": "float", "default": 0.05, "minimum": 0.01, "maximum": 0.15,
     "meaning": "Joint width in units (the side of the smallest square)."},
    {"name": "joint_fill", "type": "float", "default": 0.55, "minimum": 0.0, "maximum": 0.95,
     "meaning": "Height of the jointing sand or grout relative to the stone faces."},
    {"name": "tumbling", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Rounded, chipped and worn edges from tumbling: 0 crisp sawn edges."},
    {"name": "pits", "type": "float", "default": 0.5, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Travertine holes elongated along each piece's bedding."},
    {"name": "veining", "type": "float", "default": 0.4, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Banded colour along the bedding of each piece."},
    {"name": "colour_variation", "type": "float", "default": 0.6, "minimum": 0.0, "maximum": 1.0,
     "meaning": "Spread of colour between pieces."},
    {"name": "hue_shift", "type": "float", "default": 0.0, "minimum": -0.5, "maximum": 0.5,
     "meaning": "Hue rotation of the albedo in turns."},
    {"name": "saturation", "type": "float", "default": 1.0, "minimum": 0.0, "maximum": 2.0,
     "meaning": "Albedo saturation multiplier."},
    {"name": "brightness", "type": "float", "default": 1.0, "minimum": 0.5, "maximum": 1.5,
     "meaning": "Albedo brightness multiplier."},
]
PRESETS = {
    "default": {"description": "Tumbled ivory travertine in the Versailles pattern with sand joints.", "values": {}},
    "walnut_travertine": {"description": "Darker walnut and noce travertine, strongly banded and pitted.",
                          "values": {"pits": 0.75, "veining": 0.8, "colour_variation": 0.8}},
    "honed_limestone": {"description": "Honed limestone with crisp sawn edges, few pits and thin grout joints.",
                        "values": {"joint_width": 0.025, "joint_fill": 0.8, "tumbling": 0.05, "pits": 0.12,
                                   "veining": 0.2, "colour_variation": 0.3}},
    "multicolour_slate": {"description": "Gauged slate in grey, rust and green, two pattern repeats per tile.",
                          "values": {"repeats": 2, "joint_width": 0.06, "tumbling": 0.2, "pits": 0.0,
                                     "veining": 0.7, "colour_variation": 1.0}},
}
#: Stone colours, joint colour, band colour, pit colour, stone roughness per preset (sRGB).
PALETTES = {
    "default": (["#d9c8a9", "#e2d3b8", "#cdb998", "#e8dcc6", "#d3c09f"], "#cbbb9f", "#bea47c", "#8f7b5c", 0.78),
    "walnut_travertine": (["#a7845f", "#b8956e", "#8f6d4c", "#c4a47f", "#9b7854"], "#b8a283", "#7d5c3f",
                          "#5a4230", 0.8),
    "honed_limestone": (["#e4ddcd", "#dcd4c2", "#ebe5d8", "#d6cdb9"], "#d1c9b8", "#c9bea6", "#a89d86", 0.62),
    "multicolour_slate": (["#4f5458", "#5e5a52", "#8a5a3c", "#4c5a4c", "#6b6f72", "#7a4e3a"], "#9a948a",
                          "#3a3d40", "#2b2c2e", 0.74),
}
#: The cluster: (width, height, x, y) in units of one piece of each size, relative to the 2 x 3 piece.
MODULE = ((2, 3, 0, 0), (2, 2, -2, -1), (1, 2, -2, -3), (1, 1, -3, 0))
#: Lattice of the cluster copies: (t, LATTICE_STEP * t mod MODULE_UNITS) for t in range(MODULE_UNITS).
MODULE_UNITS, LATTICE_STEP = 13, 4
#: Properties the module was chosen for (re-checked by module_properties()).
MODULE_CHECK = {"four_way_joints": 0, "longest_straight_joint": 4}


def module_pieces() -> list:
    """Every piece of the 13 x 13 unit torus as (x, y, width, height) with x and y wrapped into 0..12."""
    pieces = []
    for t in range(MODULE_UNITS):
        tx, ty = t, (LATTICE_STEP * t) % MODULE_UNITS
        for w, h, x, y in MODULE:
            pieces.append(((x + tx) % MODULE_UNITS, (y + ty) % MODULE_UNITS, w, h))
    return pieces


def module_owner() -> list:
    """owner[y][x]: the index into module_pieces() of the piece covering unit cell (x, y); ValueError when the
    pieces overlap or leave a hole."""
    n = MODULE_UNITS
    owner = [[-1] * n for _ in range(n)]
    for index, (x, y, w, h) in enumerate(module_pieces()):
        for j in range(h):
            for i in range(w):
                cell = owner[(y + j) % n][(x + i) % n]
                if cell >= 0:
                    raise ValueError("module pieces overlap")
                owner[(y + j) % n][(x + i) % n] = index
    if any(cell < 0 for row in owner for cell in row):
        raise ValueError("module pieces leave a hole")
    return owner


def module_properties(owner: list) -> dict:
    """Four-way joints (grid points where four different pieces meet with straight joints through) and the longest
    straight joint in units, measured on the torus."""
    n = len(owner)
    crosses, longest = 0, 0
    for y in range(n):
        for x in range(n):
            a, b = owner[(y - 1) % n][(x - 1) % n], owner[(y - 1) % n][x]
            c, d = owner[y][(x - 1) % n], owner[y][x]
            if a != b and c != d and a != c and b != d:
                crosses += 1
    for y in range(n):
        run = 0
        for x in list(range(n)) * 2:
            run = run + 1 if owner[(y - 1) % n][x] != owner[y][x] else 0
            longest = max(longest, min(run, n))
    for x in range(n):
        run = 0
        for y in list(range(n)) * 2:
            run = run + 1 if owner[y][(x - 1) % n] != owner[y][x] else 0
            longest = max(longest, min(run, n))
    return {"four_way_joints": crosses, "longest_straight_joint": longest}


def generate(width: int = 256, height: int = 256, seed: int = 0, preset: str = "default",
             directx_normal: bool = False, **params) -> dict:
    """The Versailles paver maps as {name: {"channels", "colour_space", "pixels"}}; see MAPS, PARAMETERS, PRESETS."""
    tk.check_size(width, height)
    tk.check_seed(seed)
    p = tk.resolve(PARAMETERS, PRESETS, preset, params)
    stones_hex, joint_hex, band_hex, pit_hex, stone_rough = PALETTES[preset]
    palette = [tk.hex_rgb(code) for code in stones_hex]
    joint_rgb, band_rgb, pit_rgb = tk.hex_rgb(joint_hex), tk.hex_rgb(band_hex), tk.hex_rgb(pit_hex)
    pieces = module_pieces()
    owner = module_owner()
    if module_properties(owner) != MODULE_CHECK:
        raise ValueError("the Versailles module no longer has its checked joint properties")
    n = MODULE_UNITS
    units = n * p["repeats"]
    half_joint = p["joint_width"] * 0.5
    tumbling, pits, veining, variation = p["tumbling"], p["pits"], p["veining"], p["colour_variation"]
    rounding = 0.03 + 0.12 * tumbling
    across = tk.fbm(width, height, units, 3, tk.hash_u32(seed, 2), cells_y=max(2, units // 4))
    down = tk.fbm(width, height, max(2, units // 4), 3, tk.hash_u32(seed, 3), cells_y=units)
    holes_across = tk.fbm(width, height, 3 * units, 2, tk.hash_u32(seed, 4), cells_y=units)
    holes_down = tk.fbm(width, height, units, 2, tk.hash_u32(seed, 5), cells_y=3 * units)
    chips = tk.fbm(width, height, 4 * units, 3, tk.hash_u32(seed, 6))
    face = tk.fbm(width, height, 2 * units, 4, tk.hash_u32(seed, 7))
    grain = tk.white_noise(width, height, tk.hash_u32(seed, 8))
    pit_level = 1.0 - 0.18 * pits
    count = len(palette)
    pixel = units / width
    floor = math.floor
    red, green, blue, heights, rough = [], [], [], [], []
    for y in range(height):
        sy = (y + 0.5) / height * units
        cell_y = floor(sy)
        for x in range(width):
            index = y * width + x
            sx = (x + 0.5) / width * units
            cell_x = floor(sx)
            piece = owner[cell_y % n][cell_x % n]
            x0, y0, w, h = pieces[piece]
            lx = (sx - x0) % n
            ly = (sy - y0) % n
            dx = min(lx, w - lx)
            dy = min(ly, h - ly)
            tile = (piece, (cell_x // n) % p["repeats"], (cell_y // n) % p["repeats"])
            code = tk.hash_u32(seed, *tile)
            pick, tone_jitter, tilt, bedding = (tk.hash_float(code, 1), tk.hash_float(code, 2) - 0.5,
                                                tk.hash_float(code, 3) - 0.5, tk.hash_float(code, 4))
            inside = min(dx, dy) - half_joint - 0.06 * tumbling * max(0.0, chips[index] + 0.1)
            t = inside / rounding
            profile = 0.0 if t <= 0.0 else 1.0 if t >= 1.0 else math.sqrt(1.0 - (1.0 - t) * (1.0 - t))
            horizontal = (w >= h) == (bedding < 0.75)
            band = across[index] if horizontal else down[index]
            hole = holes_across[index] if horizontal else holes_down[index]
            pit = pits * tk.smoothstep(0.5 * pit_level, 0.6 * pit_level, hole) if pits > 0.0 else 0.0
            top = 0.8 + 0.015 * tilt + 0.012 * face[index] * (0.5 + tumbling) - 0.06 * pit
            fill = 0.28 + 0.45 * p["joint_fill"]
            level = fill + (top - fill) * profile if inside > 0.0 else fill + 0.02 * face[index]
            heights.append(max(level, fill + 0.02 * face[index]))
            colour = palette[min(int((pick * variation + 0.5 * (1.0 - variation)) * count), count - 1)]
            tone = 1.0 + 0.1 * tone_jitter * variation + 0.04 * face[index] + 0.04 * (grain[index] - 0.5) \
                - 0.1 * (1.0 - profile)
            colour = [c * tone for c in colour]
            streak = veining * tk.smoothstep(0.05, 0.45, band) * 0.6
            colour = [c + (b - c) * streak for c, b in zip(colour, band_rgb)]
            if pit > 0.0:
                colour = [c + (q - c) * pit * 0.8 for c, q in zip(colour, pit_rgb)]
            cover = tk.smoothstep(-pixel, pixel, inside)
            joint = [c * (0.85 + 0.25 * grain[index]) for c in joint_rgb]
            colour = [j + (c - j) * cover for j, c in zip(joint, colour)]
            red.append(colour[0])
            green.append(colour[1])
            blue.append(colour[2])
            piece_rough = stone_rough + 0.05 * tilt + 0.15 * pit + 0.08 * tumbling * (1.0 - profile)
            rough.append(0.95 + (piece_rough - 0.95) * cover)
    albedo = tk.grade((red, green, blue), p["hue_shift"], p["saturation"], p["brightness"])
    return tk.finish(width, height, MAPS, albedo=albedo, heights=heights, depth=0.016, roughness=rough,
                     ao_radius=0.02, ao_strength=1.0, directx=directx_normal)


def main(argv=None) -> int:
    """Command line: write the maps as PNG files (see --help)."""
    return tk.cli(IDENTITY, generate, PRESETS, argv)


if __name__ == "__main__":
    sys.exit(main())
